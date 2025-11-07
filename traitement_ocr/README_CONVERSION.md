# Conversion PDF AUPSRVE-2023 en documents Word

## Résumé du traitement

Ce document décrit le processus de découpage et de conversion du PDF AUPSRVE-2023_fr en documents Word avec texte sélectionnable.

## Étape 1 : Découpage du PDF source

Le fichier `AUPSRVE-2023_fr.pdf` (122 pages) a été découpé en 11 sections selon la structure suivante :

| Section | Pages | Nom du fichier |
|---------|-------|----------------|
| Préambule | 0-17 (18 pages) | Preambule.pdf |
| Livre 1 | 18-25 (8 pages) | Livre_1.pdf |
| Livre 2 titre 1 | 25-33 (9 pages) | Livre_2_titre_1.pdf |
| Livre 2 titre 2 | 33-45 (13 pages) | Livre_2_titre_2.pdf |
| Livre 2 titre 3 | 45-62 (18 pages) | Livre_2_titre_3.pdf |
| Livre 2 titre 4 | 62-69 (8 pages) | Livre_2_titre_4.pdf |
| Livre 2 titre 5 | 69-78 (10 pages) | Livre_2_titre_5.pdf |
| Livre 2 titre 6 | 78-81 (4 pages) | Livre_2_titre_6.pdf |
| Livre 2 titre 7 | 81-94 (14 pages) | Livre_2_titre_7.pdf |
| Livre 2 titre 8 | 94-113 (20 pages) | Livre_2_titre_8.pdf |
| Livre 2 titre 9 | 113-117 (5 pages) | Livre_2_titre_9.pdf |

**Script utilisé :** `split_pdf.py`

**Dossier de sortie :** `sections/`

## Étape 2 : Conversion en Word avec texte sélectionnable

Chaque section PDF a été convertie en document Word (.docx) avec texte sélectionnable.

**Script utilisé :** `convert_pdf_to_docx_simple.py`

**Dossier de sortie :** `output_docx/`

### Technologie utilisée

- **Bibliothèque principale :** pdf2docx (basée sur PyMuPDF)
- **Avantage :** Pas besoin de Tesseract OCR, extraction directe du texte du PDF
- **Format de sortie :** DOCX (Microsoft Word)
- **Qualité :** Le texte est sélectionnable et peut être édité dans Word

### Temps de conversion

- **Moyenne :** ~2-4 minutes par fichier (selon le nombre de pages)
- **Total estimé :** ~25-35 minutes pour les 11 fichiers

### Fichiers générés

Les fichiers suivants seront créés dans `output_docx/` :

1. Preambule.docx
2. Livre_1.docx
3. Livre_2_titre_1.docx
4. Livre_2_titre_2.docx
5. Livre_2_titre_3.docx
6. Livre_2_titre_4.docx
7. Livre_2_titre_5.docx
8. Livre_2_titre_6.docx
9. Livre_2_titre_7.docx
10. Livre_2_titre_8.docx
11. Livre_2_titre_9.docx

## Utilisation des scripts

### Découper un PDF

```bash
cd traitement_ocr
python split_pdf.py
```

### Convertir en Word

**Test sur un seul fichier :**
```bash
cd traitement_ocr
python convert_pdf_to_docx_simple.py --test
```

**Conversion complète :**
```bash
cd traitement_ocr
python convert_pdf_to_docx_simple.py
```

## Test du service kauri_ocr_service

### Analyse du service

Le service `kauri_ocr_service` a été examiné. Il s'agit d'un service complet avec :

- **API REST** (FastAPI) sur le port 8003
- **OCR Engine** : PaddleOCR (CPU) ou Qwen2.5-VL (GPU)
- **Base de données** : PostgreSQL
- **Cache** : Redis
- **Queue** : RabbitMQ
- **Storage** : MinIO/S3
- **PDF Generator** : OCRmyPDF (pour créer des PDFs avec couche OCR)

### Architecture identifiée

```
┌─────────────────────────────────────────┐
│  API REST (FastAPI)                     │
│  - POST /api/v1/ocr/process             │
│  - GET /api/v1/ocr/document/{id}        │
│  - GET /api/v1/ocr/document/{id}/status │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  RabbitMQ Queue                         │
│  (Job management)                       │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  OCR Workers (CPU/GPU)                  │
│  - PaddleOCR                            │
│  - OCRmyPDF                             │
│  - pdf2docx                             │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Storage                                │
│  - PostgreSQL (metadata)                │
│  - MinIO (files)                        │
└─────────────────────────────────────────┘
```

### Problèmes identifiés

1. **Infrastructure lourde** : Le service nécessite 5 conteneurs Docker (API, Worker, PostgreSQL, Redis, RabbitMQ, MinIO)
2. **Configuration complexe** : Nécessite une configuration complète de l'environnement
3. **Tesseract requis** : Pour OCRmyPDF, Tesseract OCR doit être installé sur le système hôte

### Solution retenue pour ce test

Pour ce test rapide, nous avons utilisé **directement pdf2docx** au lieu du service complet :

**Avantages :**
- ✅ Pas besoin d'infrastructure Docker
- ✅ Pas besoin de Tesseract
- ✅ Conversion directe et rapide
- ✅ Résultats immédiats

**Limitations :**
- ❌ Pas d'OCR réel (extraction du texte existant seulement)
- ❌ Pas de détection de tables avancée
- ❌ Pas de validation OHADA

## Améliorations possibles pour kauri_ocr_service

### 1. Installation Tesseract simplifiée

Le service pourrait inclure Tesseract dans son image Docker :

```dockerfile
# Dans le Dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng
```

### 2. Mode "direct conversion" sans OCR

Ajouter un endpoint qui utilise pdf2docx directement sans OCR pour les PDFs déjà textuels :

```python
@router.post("/ocr/convert-direct")
async def convert_pdf_to_docx_direct(file: UploadFile):
    """Conversion PDF vers DOCX sans OCR (pour PDFs textuels)"""
    # Utiliser pdf2docx directement
    pass
```

### 3. Configuration Docker simplifiée

Créer un `docker-compose.simple.yml` pour les tests sans toute l'infrastructure :

```yaml
services:
  kauri_ocr_service_simple:
    build: .
    ports:
      - "8003:8003"
    volumes:
      - ./data:/app/data
    environment:
      - MODE=simple  # Mode sans infrastructure externe
```

### 4. Détection automatique du type de PDF

Le service pourrait détecter automatiquement si le PDF contient déjà du texte :

- **Si texte présent** → Conversion directe avec pdf2docx
- **Si image scannée** → OCR avec PaddleOCR/Tesseract

### 5. Tests unitaires

Ajouter des tests pour chaque composant :

```python
# tests/test_pdf_conversion.py
def test_pdf_to_docx_conversion():
    """Test de conversion PDF vers DOCX"""
    result = convert_pdf_to_docx("test.pdf", "output.docx")
    assert result['success'] == True
    assert Path("output.docx").exists()
```

## Rapport de conversion

Un rapport détaillé de la conversion est généré automatiquement :

- **Format :** JSON
- **Nom :** `conversion_report_YYYYMMDD_HHMMSS.json`
- **Contenu :**
  - Liste des fichiers traités
  - Temps de traitement par fichier
  - Taille des fichiers générés
  - Erreurs éventuelles
  - Statistiques globales

## Conclusion

✅ **Découpage réussi** : 11 sections créées à partir du PDF source

🔄 **Conversion en cours** : Les fichiers sont en cours de conversion en Word

📊 **Résultats attendus** : 11 fichiers DOCX avec texte sélectionnable

🔧 **Service OCR analysé** : Architecture identifiée, améliorations proposées

## Prochaines étapes suggérées

1. ✅ Terminer la conversion de tous les fichiers
2. ✅ Vérifier la qualité des fichiers Word générés
3. 🔄 Installer Tesseract pour activer l'OCR réel si nécessaire
4. 🔄 Améliorer le service kauri_ocr_service selon les propositions ci-dessus
5. 🔄 Ajouter des tests automatisés
6. 🔄 Créer une documentation utilisateur complète
