# Test du service kauri_ocr_service avec cas réel

## Objectif du test

Valider le fonctionnement du service `kauri_ocr_service` avec un cas d'usage concret :
- **Entrée** : 11 PDFs découpés du document AUPSRVE-2023 (documents juridiques scannés)
- **Objectif** : Obtenir des PDFs avec texte sélectionnable grâce à l'OCR
- **Validation** : Vérifier la qualité de l'OCR et du texte extrait

## Architecture testée

```
┌──────────────────────────────────────────────────┐
│  Script Client (test_ocr_service.py)             │
│  - Soumet les PDFs au service                    │
│  - Poll le status                                │
│  - Télécharge les résultats                      │
└──────────────────────────────────────────────────┘
                    │ HTTP REST API
                    ▼
┌──────────────────────────────────────────────────┐
│  kauri_ocr_service (FastAPI)                     │
│  Port 8003                                       │
│  - POST /api/v1/ocr/process                      │
│  - GET /api/v1/ocr/document/{id}/status          │
│  - GET /api/v1/ocr/document/{id}/searchable-pdf  │
└──────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│  RabbitMQ Queue                                  │
│  - Gestion des jobs OCR                          │
│  - Priorités                                     │
└──────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│  OCR Worker (CPU)                                │
│  - Tesseract OCR (fra + eng)                     │
│  - OCRmyPDF                                      │
│  - Traitement asynchrone                         │
└──────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│  PostgreSQL                                      │
│  - Métadonnées documents                         │
│  - Résultats OCR                                 │
│  - Statistiques                                  │
└──────────────────────────────────────────────────┘
```

## Corrections apportées au service

### 1. Dockerfile - Package obsolète (libgl1-mesa-glx)

**Problème identifié :**
```
E: Package 'libgl1-mesa-glx' has no installation candidate
```

**Cause :** Le package `libgl1-mesa-glx` n'existe plus dans Debian Trixie (Python 3.11-slim utilise Debian Trixie).

**Correction :**
```dockerfile
# Avant
RUN apt-get install -y libgl1-mesa-glx ...

# Après
RUN apt-get install -y libgl1 ...
```

**Fichier :** `backend/kauri_ocr_service/Dockerfile:9`

---

### 2. docker-compose.yml - Conflit replicas + container_name

**Problème identifié :**
```
can't set container_name and ocr_worker_cpu as container name must be unique
```

**Cause :** On ne peut pas utiliser `container_name` avec `deploy.replicas: 2` car Docker ne peut pas créer 2 conteneurs avec le même nom.

**Correction :**
```yaml
# Avant
ocr_worker_cpu:
  container_name: kauri_ocr_worker_cpu
  deploy:
    replicas: 2

# Après
ocr_worker_cpu:
  # Pas de container_name
  # Pas de replicas (ou utiliser --scale)
```

**Fichier :** `backend/kauri_ocr_service/docker-compose.yml:108,139`

---

### 3. Ajout du volume traitement_ocr

**Amélioration ajoutée :**

Pour que le service puisse accéder aux PDFs découpés, ajout du volume :

```yaml
volumes:
  - ../../traitement_ocr:/app/traitement_ocr
```

Cela permet au service d'accéder directement aux fichiers dans `traitement_ocr/sections/`.

---

## Services Docker démarrés

1. **kauri_ocr_postgres** (PostgreSQL 15)
   - Port : 5433
   - Base : kauri_ocr
   - User : kauri_user

2. **kauri_ocr_redis** (Redis 7)
   - Port : 6380
   - Cache et sessions

3. **kauri_ocr_rabbitmq** (RabbitMQ 3.12)
   - Port AMQP : 5673
   - Port Management UI : 15673
   - Vhost : /kauri

4. **kauri_ocr_minio** (MinIO)
   - Port API : 9001
   - Port Console : 9091
   - Stockage des fichiers

5. **kauri_ocr_service** (FastAPI)
   - Port : 8003
   - API REST

6. **ocr_worker_cpu**
   - Worker asynchrone
   - Tesseract OCR
   - Traitement CPU (pas GPU)

---

## Script de test créé

**Fichier :** `traitement_ocr/test_ocr_service.py`

### Fonctionnalités :

1. **Health check**
   - Vérifie que le service est actif

2. **Soumission de PDFs**
   - Envoie les PDFs au service via l'API
   - Récupère un `document_id`

3. **Monitoring du traitement**
   - Poll le status toutes les 5 secondes
   - Détecte : QUEUED → PROCESSING → COMPLETED/FAILED

4. **Téléchargement des résultats**
   - Récupère le PDF avec couche OCR
   - Sauvegarde dans `output_from_service/`

5. **Rapport**
   - Statistiques de succès/échec
   - Temps de traitement
   - Rapport JSON détaillé

### Utilisation :

```bash
# Test sur un seul fichier
cd traitement_ocr
python test_ocr_service.py --test

# Traitement complet (11 fichiers)
python test_ocr_service.py
```

---

## Tests à effectuer

### Test 1 : Health Check ✓
```bash
curl http://localhost:8003/api/v1/health
```

Attendu : `{"status": "healthy"}`

---

### Test 2 : Vérifier Tesseract dans le conteneur
```bash
docker exec kauri_ocr_service tesseract --version
docker exec kauri_ocr_service tesseract --list-langs
```

Attendu :
- Version Tesseract 5.x
- Langues : fra, eng

---

### Test 3 : Soumission d'un PDF
```bash
cd traitement_ocr
python test_ocr_service.py --test
```

Attendu :
- PDF soumis avec succès
- Récupération d'un `document_id`
- Status passe de QUEUED → PROCESSING → COMPLETED
- PDF téléchargé avec texte sélectionnable

---

### Test 4 : Traitement complet
```bash
cd traitement_ocr
python test_ocr_service.py
```

Attendu :
- 11 PDFs traités
- Tous avec status COMPLETED
- PDFs téléchargés dans `output_from_service/`
- Texte sélectionnable dans les PDFs

---

### Test 5 : Vérification manuelle du texte

1. Ouvrir un PDF de `output_from_service/`
2. Essayer de sélectionner du texte avec la souris
3. Copier-coller du texte dans un éditeur

✓ **Succès si** : Le texte est sélectionnable et copiable
✗ **Échec si** : On ne peut que déplacer des images

---

## Métriques à mesurer

1. **Temps de traitement**
   - Temps moyen par page
   - Temps total pour 11 fichiers
   - Comparaison avec le traitement local

2. **Qualité de l'OCR**
   - Confidence score (fourni par le service)
   - Quality score (fourni par le service)
   - Taux d'erreurs visuelles

3. **Fiabilité**
   - Nombre de succès vs échecs
   - Gestion des erreurs
   - Robustesse du worker

4. **Performance système**
   - Utilisation CPU
   - Utilisation RAM
   - Utilisation disque

---

## Critères de validation

### ✓ Le service est validé si :

1. **Infrastructure**
   - ✓ Tous les conteneurs démarrent sans erreur
   - ✓ Health check répond correctement
   - ✓ Tesseract est disponible dans les conteneurs

2. **API**
   - ✓ Soumission de PDFs fonctionne
   - ✓ Status tracking fonctionne
   - ✓ Téléchargement des résultats fonctionne

3. **OCR**
   - ✓ Les PDFs sont traités avec succès
   - ✓ Le texte est vraiment sélectionnable
   - ✓ La qualité de l'OCR est acceptable (> 80% confidence)

4. **Robustesse**
   - ✓ Pas de crash du worker
   - ✓ Gestion correcte des erreurs
   - ✓ Queue RabbitMQ fonctionne

### ✗ Le service nécessite des corrections si :

1. **Échecs OCR**
   - ✗ Texte non sélectionnable
   - ✗ Taux d'erreur > 20%
   - ✗ Timeout fréquents

2. **Bugs**
   - ✗ Crash du worker
   - ✗ Fuites mémoire
   - ✗ Deadlocks dans la queue

3. **Performance**
   - ✗ Temps de traitement excessif (> 2 min/page)
   - ✗ Utilisation mémoire excessive (> 4GB)

---

## Prochaines étapes

1. **Attendre que le build Docker se termine**
   - Vérifier que tous les services démarrent

2. **Lancer le test simple**
   ```bash
   python test_ocr_service.py --test
   ```

3. **Analyser les résultats**
   - Vérifier le texte sélectionnable
   - Examiner les logs du worker
   - Mesurer les performances

4. **Si test OK : Traitement complet**
   ```bash
   python test_ocr_service.py
   ```

5. **Documenter les résultats**
   - Rapport de test
   - Corrections apportées
   - Recommandations

---

## Commandes utiles

### Vérifier les logs
```bash
# Tous les services
cd backend/kauri_ocr_service
docker-compose logs -f

# Service API uniquement
docker-compose logs -f kauri_ocr_service

# Worker uniquement
docker-compose logs -f ocr_worker_cpu
```

### Vérifier les conteneurs
```bash
docker-compose ps
```

### Entrer dans un conteneur
```bash
docker exec -it kauri_ocr_service bash
```

### Arrêter les services
```bash
docker-compose down
```

### Nettoyer complètement
```bash
docker-compose down -v  # Supprime aussi les volumes
```

---

## Résultats attendus

Une fois le test terminé, nous aurons :

1. **PDFs avec OCR** dans `output_from_service/`
2. **Rapport de test** en JSON
3. **Documentation** des problèmes rencontrés
4. **Recommandations** pour améliorer le service
5. **Validation** que le service fonctionne en production

---

**Date :** 2025-11-07
**Status :** Build Docker en cours
**Prochain milestone :** Test avec un seul PDF
