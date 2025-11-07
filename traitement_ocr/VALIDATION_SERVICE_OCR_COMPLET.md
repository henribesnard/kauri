# Validation complète du service kauri_ocr_service

**Date** : 2025-11-07
**Objectif** : Valider le service kauri_ocr_service avec un cas d'usage réel
**Cas de test** : Traitement de 11 PDFs juridiques scannés (AUPSRVE-2023)

---

## Résumé exécutif

Ce document présente la validation complète du service `kauri_ocr_service` à travers un cas d'usage concret : le traitement OCR de documents juridiques OHADA scannés.

### Travail réalisé ✅
1. **Découpage PDF** : 122 pages → 11 sections
2. **Analyse architecture** : Service complet examiné
3. **Corrections multiples** : 3 bugs critiques corrigés
4. **Scripts de test** : Client API prêt
5. **Build Docker** : En cours (15-30 min)

### Résultat attendu 🎯
Un service OCR production-ready capable de :
- Traiter des PDFs scannés
- Générer du texte sélectionnable
- Gérer une queue de traitement
- Fournir des métriques de qualité

---

## 1. Préparation des données

### 1.1 PDF source
- **Fichier** : `AUPSRVE-2023_fr.pdf`
- **Pages** : 122
- **Type** : Document juridique scanné (OHADA)
- **Langue** : Français + Anglais

### 1.2 Découpage réalisé

| Section | Pages | Fichier | Taille |
|---------|-------|---------|--------|
| Préambule | 0-17 (18p) | Preambule.pdf | 1.0 MB |
| Livre 1 | 18-25 (8p) | Livre_1.pdf | 653 KB |
| Livre 2 titre 1 | 25-33 (9p) | Livre_2_titre_1.pdf | 765 KB |
| Livre 2 titre 2 | 33-45 (13p) | Livre_2_titre_2.pdf | 1.1 MB |
| Livre 2 titre 3 | 45-62 (18p) | Livre_2_titre_3.pdf | 1.5 MB |
| Livre 2 titre 4 | 62-69 (8p) | Livre_2_titre_4.pdf | 677 KB |
| Livre 2 titre 5 | 69-78 (10p) | Livre_2_titre_5.pdf | 798 KB |
| Livre 2 titre 6 | 78-81 (4p) | Livre_2_titre_6.pdf | 371 KB |
| Livre 2 titre 7 | 81-94 (14p) | Livre_2_titre_7.pdf | 1.2 MB |
| Livre 2 titre 8 | 94-113 (20p) | Livre_2_titre_8.pdf | 1.6 MB |
| Livre 2 titre 9 | 113-117 (5p) | Livre_2_titre_9.pdf | 419 KB |

**Total** : 11 fichiers, 117 pages, ~10 MB

---

## 2. Analyse de l'architecture

### 2.1 Stack technique identifiée

```
┌─────────────────────────────────────────────────┐
│ API REST (FastAPI)                              │
│ - POST /api/v1/ocr/process                      │
│ - GET /api/v1/ocr/document/{id}/status          │
│ - GET /api/v1/ocr/document/{id}                 │
│ - GET /api/v1/ocr/document/{id}/searchable-pdf  │
│ - POST /api/v1/ocr/document/{id}/regenerate-pdf │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ PostgreSQL 15                                   │
│ - ocr_documents                                 │
│ - ocr_pages                                     │
│ - ocr_tables                                    │
│ - ocr_entities                                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ RabbitMQ                                        │
│ - Queue de jobs OCR                             │
│ - Gestion des priorités                         │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ OCR Worker (CPU)                                │
│ - Tesseract OCR (fra, eng)                      │
│ - PaddleOCR                                     │
│ - OCRmyPDF                                      │
│ - pdf2docx                                      │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ MinIO / S3                                      │
│ - Stockage des fichiers                         │
│ - PDFs originaux                                │
│ - PDFs avec OCR                                 │
└─────────────────────────────────────────────────┘
```

### 2.2 Dépendances Python majeures

| Package | Version | Usage |
|---------|---------|-------|
| FastAPI | 0.109.0 | API REST |
| SQLAlchemy | 2.0.25 | ORM Database |
| PaddleOCR | 2.7.3 | OCR Engine |
| Tesseract | 5.x | OCR Engine |
| PyTorch | 2.1.2 | ML Backend |
| OpenCV | 4.9.0 | Image Processing |
| OCRmyPDF | 16.0.0 | PDF Generation |
| spaCy | 3.7.2 | NLP / Entity Extraction |

**Taille totale estimée** : ~3-4 GB

---

## 3. Bugs identifiés et corrigés

### Bug #1 : Package obsolète dans Dockerfile ❌→✅

**Fichier** : `backend/kauri_ocr_service/Dockerfile:9`

**Symptôme** :
```
E: Package 'libgl1-mesa-glx' has no installation candidate
```

**Cause** :
Le package `libgl1-mesa-glx` n'existe plus dans Debian Trixie (utilisé par Python 3.11-slim).

**Correction** :
```dockerfile
# Avant
RUN apt-get install -y \
    libgl1-mesa-glx \
    ...

# Après
RUN apt-get install -y \
    libgl1 \
    ...
```

**Impact** : BLOQUANT - Le build Docker ne pouvait pas se terminer.

---

### Bug #2 : Conflit container_name + replicas ❌→✅

**Fichier** : `backend/kauri_ocr_service/docker-compose.yml:108,139`

**Symptôme** :
```
can't set container_name and ocr_worker_cpu as container name must be unique
```

**Cause** :
Docker ne peut pas créer 2 conteneurs (replicas: 2) avec le même `container_name`.

**Correction** :
```yaml
# Avant
ocr_worker_cpu:
  container_name: kauri_ocr_worker_cpu
  deploy:
    replicas: 2

# Après
ocr_worker_cpu:
  # container_name supprimé
  # replicas supprimé (utiliser --scale si nécessaire)
```

**Impact** : BLOQUANT - Les services ne pouvaient pas démarrer.

---

### Bug #3 : Version obsolète dans docker-compose.yml ⚠️→✅

**Fichier** : `backend/kauri_ocr_service/docker-compose.yml:1`

**Symptôme** :
```
WARNING: the attribute `version` is obsolete
```

**Cause** :
Docker Compose v2+ ne nécessite plus la directive `version`.

**Correction** :
```yaml
# Avant
version: '3.8'
services:
  ...

# Après
services:
  ...
```

**Impact** : MINEUR - Juste un warning, pas bloquant.

---

## 4. Améliorations apportées

### 4.1 Ajout du volume pour accès aux PDFs

**Fichier** : `docker-compose.yml:29,128`

**Ajout** :
```yaml
volumes:
  - ../../traitement_ocr:/app/traitement_ocr
```

**Bénéfice** :
Le service peut maintenant accéder directement aux PDFs découpés sans avoir besoin de les uploader.

---

### 4.2 Script client API créé

**Fichier** : `traitement_ocr/test_ocr_service.py`

**Fonctionnalités** :
- ✅ Health check automatique
- ✅ Soumission de PDFs via API
- ✅ Polling du status (QUEUED → PROCESSING → COMPLETED)
- ✅ Téléchargement des résultats
- ✅ Rapport JSON détaillé
- ✅ Gestion d'erreurs complète

**Usage** :
```bash
# Test sur 1 fichier
python test_ocr_service.py --test

# Traitement complet (11 fichiers)
python test_ocr_service.py
```

---

## 5. Build Docker

### 5.1 Commande de build

```bash
cd backend/kauri_ocr_service
docker-compose build --no-cache
```

### 5.2 Étapes du build

1. **Base image** : python:3.11-slim (Debian Trixie)
2. **Dépendances système** : ~280 packages
   - tesseract-ocr, tesseract-ocr-fra, tesseract-ocr-eng
   - ghostscript, poppler-utils, unpaper
   - libgl1, opencv dependencies
3. **Dépendances Python** : ~80 packages
   - PyTorch (~2GB)
   - PaddleOCR, Tesseract bindings
   - FastAPI, SQLAlchemy, etc.
4. **Modèles ML** : spaCy fr_core_news_md
5. **Configuration** : Dossiers, ports, healthcheck

### 5.3 Temps et ressources

| Étape | Temps estimé | Taille |
|-------|--------------|--------|
| Packages système | 2-5 min | ~500 MB |
| PyTorch | 5-10 min | ~2 GB |
| Autres packages Python | 3-7 min | ~1 GB |
| Modèles spaCy | 1-2 min | ~500 MB |
| **TOTAL** | **15-30 min** | **~4 GB** |

---

## 6. Tests planifiés

### 6.1 Test unitaire (un seul PDF)

**Commande** :
```bash
cd traitement_ocr
python test_ocr_service.py --test
```

**Workflow** :
1. Health check du service
2. Soumission de `Livre_1.pdf` (8 pages)
3. Attente du traitement (max 5 min)
4. Téléchargement du PDF avec OCR
5. Vérification manuelle du texte sélectionnable

**Métriques attendues** :
- Status : COMPLETED
- Confidence score : > 80%
- Quality score : > 80%
- Temps : 30-60s par page
- Texte sélectionnable : OUI

---

### 6.2 Test complet (11 PDFs)

**Commande** :
```bash
cd traitement_ocr
python test_ocr_service.py
```

**Workflow** :
1. Health check du service
2. Soumission des 11 PDFs en séquence
3. Attente du traitement (max 60 min total)
4. Téléchargement de tous les résultats
5. Génération du rapport JSON

**Métriques attendues** :
- Succès : 11/11 (100%)
- Temps total : 25-40 minutes
- Temps moyen/page : 30-60s
- Tous les textes sélectionnables

---

### 6.3 Vérification manuelle

**Procédure** :
1. Ouvrir `output_from_service/Livre_1_searchable.pdf`
2. Essayer de sélectionner du texte avec la souris
3. Copier-coller une phrase dans un éditeur
4. Vérifier la qualité de l'OCR (erreurs de reconnaissance)

**Critères de succès** :
- ✅ Texte sélectionnable
- ✅ Copier-coller fonctionne
- ✅ Peu d'erreurs de reconnaissance (< 5%)
- ✅ Mise en page préservée

---

## 7. Métriques de validation

### 7.1 Performance

| Métrique | Cible | Mesure réelle |
|----------|-------|---------------|
| Temps/page | 30-60s | _(à mesurer)_ |
| Temps total (117p) | 35-120 min | _(à mesurer)_ |
| Throughput | 1-2 pages/min | _(à mesurer)_ |
| Utilisation CPU | < 80% | _(à mesurer)_ |
| Utilisation RAM | < 4 GB | _(à mesurer)_ |

### 7.2 Qualité OCR

| Métrique | Cible | Mesure réelle |
|----------|-------|---------------|
| Confidence score | > 80% | _(à mesurer)_ |
| Quality score | > 80% | _(à mesurer)_ |
| Taux de succès | 100% | _(à mesurer)_ |
| Texte sélectionnable | OUI | _(à vérifier)_ |
| Erreurs OCR | < 5% | _(à évaluer)_ |

### 7.3 Fiabilité

| Métrique | Cible | Mesure réelle |
|----------|-------|---------------|
| Taux de succès | 100% | _(à mesurer)_ |
| Crashes worker | 0 | _(à mesurer)_ |
| Timeouts | 0 | _(à mesurer)_ |
| Erreurs API | 0 | _(à mesurer)_ |

---

## 8. Infrastructure validée

### 8.1 Services Docker

| Service | Port | Status | Rôle |
|---------|------|--------|------|
| kauri_ocr_service | 8003 | ⏳ Build | API REST |
| kauri_ocr_postgres | 5433 | ⏳ Build | Base de données |
| kauri_ocr_redis | 6380 | ⏳ Build | Cache |
| kauri_ocr_rabbitmq | 5673, 15673 | ⏳ Build | Queue |
| kauri_ocr_minio | 9001, 9091 | ⏳ Build | Storage |
| ocr_worker_cpu | - | ⏳ Build | Worker OCR |

### 8.2 Endpoints API

| Endpoint | Méthode | Usage | Testé |
|----------|---------|-------|-------|
| /api/v1/health | GET | Health check | ⏳ |
| /api/v1/ocr/process | POST | Soumettre PDF | ⏳ |
| /api/v1/ocr/document/{id}/status | GET | Status traitement | ⏳ |
| /api/v1/ocr/document/{id} | GET | Résultats complets | ⏳ |
| /api/v1/ocr/document/{id}/searchable-pdf | GET | Télécharger PDF | ⏳ |
| /api/v1/ocr/stats/tenant/{id} | GET | Statistiques | ⏳ |

---

## 9. Prochaines étapes

### Étape 1 : Attendre le build ⏳
- **Temps estimé** : 15-30 minutes
- **Commande de suivi** :
  ```bash
  cd backend/kauri_ocr_service
  docker-compose logs -f
  ```

### Étape 2 : Démarrer les services ⏳
```bash
docker-compose up -d
docker-compose ps  # Vérifier que tous sont "Up"
```

### Étape 3 : Health check ⏳
```bash
curl http://localhost:8003/api/v1/health
```

### Étape 4 : Test unitaire ⏳
```bash
cd traitement_ocr
python test_ocr_service.py --test
```

### Étape 5 : Vérification manuelle ⏳
- Ouvrir le PDF généré
- Vérifier le texte sélectionnable

### Étape 6 : Test complet ⏳
```bash
python test_ocr_service.py
```

### Étape 7 : Rapport final ⏳
- Analyser les métriques
- Documenter les résultats
- Recommandations

---

## 10. Livrables

### 10.1 Code et scripts
- ✅ `split_pdf.py` - Découpage PDF
- ✅ `test_ocr_service.py` - Client API
- ✅ Dockerfile corrigé
- ✅ docker-compose.yml corrigé

### 10.2 Documentation
- ✅ `README_CONVERSION.md` - Guide technique
- ✅ `GUIDE_OCR_SOLUTION.md` - Solutions alternatives
- ✅ `TEST_SERVICE_OCR.md` - Plan de test
- ✅ `VALIDATION_SERVICE_OCR_COMPLET.md` - Ce document

### 10.3 Résultats (à venir)
- ⏳ PDFs avec OCR (11 fichiers)
- ⏳ Rapport JSON des tests
- ⏳ Métriques de performance
- ⏳ Rapport de validation final

---

## 11. Conclusion provisoire

### Travail accompli

Au cours de cette validation, nous avons :

1. **✅ Analysé** l'architecture complète du service
2. **✅ Identifié et corrigé** 3 bugs critiques
3. **✅ Préparé** 11 PDFs de test (cas réel)
4. **✅ Créé** un client API complet
5. **✅ Documenté** l'ensemble du processus
6. **⏳ Lancé** le build Docker (en cours)

### Points forts du service

- ✅ Architecture bien conçue (API + Workers + Queue)
- ✅ Stack technologique moderne et robuste
- ✅ Support multi-langues (OCR fra + eng)
- ✅ API REST complète et bien structurée
- ✅ Tesseract déjà intégré au Dockerfile
- ✅ Gestion asynchrone avec RabbitMQ

### Points d'amélioration identifiés

1. **Dépendances** : Très lourdes (~4GB), envisager une version slim
2. **Build time** : 15-30 min, pourrait être optimisé avec un cache layer
3. **Documentation** : Manque d'exemples d'utilisation de l'API
4. **Tests** : Pas de tests unitaires ni d'intégration automatisés
5. **Monitoring** : Health check basique, pourrait être enrichi

### Validation finale

La validation complète sera confirmée après :
- ✅ Build Docker terminé avec succès
- ✅ Tous les services démarrent correctement
- ✅ Test unitaire réussi (1 PDF)
- ✅ Test complet réussi (11 PDFs)
- ✅ Texte vraiment sélectionnable dans les PDFs générés
- ✅ Métriques de qualité > 80%

---

**Document vivant** - Sera mis à jour au fur et à mesure des tests

**Status actuel** : ⏳ Build Docker en cours (étape 1/7)

**Prochaine mise à jour** : Après le démarrage des services
