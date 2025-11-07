# Guide : Obtenir du texte vraiment sélectionnable

## Problème identifié ✗

Les fichiers DOCX créés contiennent **des images, pas du texte sélectionnable**.

**Cause :** Les PDFs sources sont des **scans d'images**. La bibliothèque `pdf2docx` extrait simplement les images sans faire d'OCR (reconnaissance de caractères).

## Solution 1 : Installer Tesseract localement (Recommandé pour tests rapides)

### Installation de Tesseract sur Windows

1. **Télécharger Tesseract**
   - URL : https://github.com/UB-Mannheim/tesseract/wiki
   - Téléchargez : `tesseract-ocr-w64-setup-5.3.x.exe` (dernière version)

2. **Installer Tesseract**
   - Lancez l'installateur
   - **Important** : Cochez les langues :
     - ✓ French (fra)
     - ✓ English (eng)
   - Chemin d'installation par défaut : `C:\Program Files\Tesseract-OCR`

3. **Vérifier l'installation**
   ```bash
   tesseract --version
   ```

4. **Lancer la conversion avec OCR**
   ```bash
   cd traitement_ocr

   # Test sur un fichier
   python convert_with_real_ocr.py --test

   # Conversion complète (11 fichiers)
   python convert_with_real_ocr.py
   ```

### Temps estimé
- **OCR** : ~3-5 minutes par fichier (selon nombre de pages)
- **Total pour 11 fichiers** : ~35-55 minutes

---

## Solution 2 : Utiliser kauri_ocr_service avec Docker (Recommandé pour production)

Le service `kauri_ocr_service` inclut déjà Tesseract dans son image Docker.

### Étape 1 : Vérifier le Dockerfile

```dockerfile
# Dans backend/kauri_ocr_service/Dockerfile
FROM python:3.11-slim

# Installer Tesseract et langues
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# ... reste du Dockerfile
```

### Étape 2 : Lancer le service

```bash
cd backend/kauri_ocr_service

# Construire l'image
docker-compose build

# Lancer les services
docker-compose up -d

# Vérifier que le service fonctionne
curl http://localhost:8003/api/v1/health
```

### Étape 3 : Créer un script client pour utiliser le service

```python
# traitement_ocr/use_ocr_service.py
import requests
from pathlib import Path

OCR_SERVICE_URL = "http://localhost:8003/api/v1"

def upload_and_process_pdf(pdf_path: Path):
    """Envoie un PDF au service OCR"""

    # Lire le fichier
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path.name, f, 'application/pdf')}

        # Envoyer au service
        response = requests.post(
            f"{OCR_SERVICE_URL}/ocr/process",
            files=files,
            data={
                'tenant_id': 'test-tenant',
                'user_id': 'test-user',
                'enable_table_detection': True,
                'enable_entity_extraction': True
            }
        )

    if response.status_code == 200:
        result = response.json()
        document_id = result['document_id']
        print(f"✓ Document en traitement: {document_id}")
        return document_id
    else:
        print(f"✗ Erreur: {response.text}")
        return None

# Utilisation
for pdf_file in Path("sections").glob("*.pdf"):
    print(f"Traitement de {pdf_file.name}...")
    upload_and_process_pdf(pdf_file)
```

---

## Solution 3 : Utiliser un service OCR en ligne (Alternative rapide)

Si vous voulez un résultat immédiat sans installation :

### Services recommandés :
1. **Adobe Acrobat Online** - https://www.adobe.com/acrobat/online/ocr-pdf.html
2. **OnlineOCR.net** - https://www.onlineocr.net/
3. **PDFCandy** - https://pdfcandy.com/ocr-pdf.html

**Avantages :**
- ✓ Pas d'installation
- ✓ Résultats immédiats
- ✓ Interface graphique

**Inconvénients :**
- ✗ Traitement manuel fichier par fichier
- ✗ Limites de taille/nombre de fichiers
- ✗ Confidentialité (upload sur serveur externe)

---

## Solution 4 : Améliorer le Dockerfile de kauri_ocr_service

Modifions le Dockerfile pour inclure Tesseract :

```dockerfile
# backend/kauri_ocr_service/Dockerfile
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Installer dépendances système + Tesseract
RUN apt-get update && apt-get install -y \
    # Dépendances système
    gcc \
    g++ \
    libpq-dev \
    # Tesseract OCR + langues
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    # Outils image
    poppler-utils \
    libimage-exiftool-perl \
    ghostscript \
    unpaper \
    # Nettoyage
    && rm -rf /var/lib/apt/lists/*

# Vérifier Tesseract
RUN tesseract --version && \
    tesseract --list-langs

# Reste de l'installation...
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

---

## Comparaison des solutions

| Solution | Temps setup | Temps traitement | Qualité OCR | Automatisation | Coût |
|----------|-------------|------------------|-------------|----------------|------|
| **Tesseract local** | 10 min | 35-55 min | Bonne | ✓ Script | Gratuit |
| **kauri_ocr_service** | 15 min | 25-35 min | Excellente | ✓✓ API | Gratuit |
| **Service en ligne** | 0 min | 5-10 min/fichier | Variable | ✗ Manuel | Gratuit/Payant |
| **Docker + Tesseract** | 20 min | 25-35 min | Bonne | ✓✓ Container | Gratuit |

---

## Recommandation finale

### Pour ce test immédiat :
**→ Solution 1** : Installer Tesseract localement
- Plus rapide à mettre en place
- Script déjà prêt (`convert_with_real_ocr.py`)
- Pas besoin d'infrastructure Docker

### Pour une utilisation en production :
**→ Solution 2** : Utiliser kauri_ocr_service avec Docker
- Service complet avec API
- Queue de traitement (RabbitMQ)
- Monitoring et logs
- Scalable

---

## Prochaines étapes

### Si vous choisissez Solution 1 (Tesseract local) :

```bash
# 1. Télécharger Tesseract
# https://github.com/UB-Mannheim/tesseract/wiki

# 2. Installer avec langues fra + eng

# 3. Tester
cd traitement_ocr
python convert_with_real_ocr.py --test

# 4. Vérifier que le texte est sélectionnable dans le DOCX généré

# 5. Si OK, lancer conversion complète
python convert_with_real_ocr.py
```

### Si vous choisissez Solution 2 (kauri_ocr_service) :

```bash
# 1. Modifier le Dockerfile pour inclure Tesseract
# (voir code ci-dessus)

# 2. Reconstruire l'image
cd backend/kauri_ocr_service
docker-compose build

# 3. Lancer les services
docker-compose up -d

# 4. Créer un script client
python traitement_ocr/use_ocr_service.py

# 5. Vérifier les résultats
curl http://localhost:8003/api/v1/ocr/stats/tenant/test-tenant
```

---

## Vérification que l'OCR fonctionne

Après la conversion, vérifiez que le texte est vraiment sélectionnable :

1. **Ouvrir le fichier DOCX** dans Microsoft Word
2. **Essayer de sélectionner du texte** avec la souris
3. **Copier-coller** quelques phrases dans un éditeur de texte

✓ **Si vous pouvez copier-coller du texte** → OCR réussi !
✗ **Si vous ne pouvez que déplacer des images** → OCR n'a pas fonctionné

---

## Corrections identifiées pour kauri_ocr_service

1. ✅ **Ajouter Tesseract au Dockerfile**
   - Inclure `tesseract-ocr`, `tesseract-ocr-fra`, `tesseract-ocr-eng`

2. ✅ **Tester l'installation Tesseract au démarrage**
   ```python
   # app/main.py
   import subprocess

   @app.on_event("startup")
   async def verify_tesseract():
       try:
           result = subprocess.run(['tesseract', '--version'],
                                 capture_output=True, text=True)
           logger.info(f"Tesseract installé: {result.stdout.split()[1]}")
       except Exception as e:
           logger.error(f"Tesseract non disponible: {e}")
   ```

3. ✅ **Ajouter un endpoint de test OCR**
   ```python
   @router.get("/ocr/test-capabilities")
   async def test_ocr_capabilities():
       """Teste les capacités OCR du service"""
       return {
           "tesseract_available": check_tesseract(),
           "languages": get_available_languages(),
           "pdf_tools": check_pdf_tools()
       }
   ```

4. ✅ **Améliorer la documentation**
   - Ajouter des exemples de requêtes
   - Documenter les prérequis système
   - Ajouter un guide de troubleshooting
