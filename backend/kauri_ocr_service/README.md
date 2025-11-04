# KAURI OCR Service

Service OCR pour le traitement automatisé de documents comptables et financiers avec validation OHADA.

## Architecture

### Stack Technologique
- **Framework**: FastAPI (async, haute performance)
- **OCR Engine**: PaddleOCR (dev/prod CPU) / Qwen2.5-VL (prod GPU)
- **Base de données**: PostgreSQL 15+
- **Cache**: Redis
- **Queue**: RabbitMQ
- **Storage**: MinIO/S3
- **ML/NLP**: spaCy, OpenCV, Pillow

### Fonctionnalités

- ✅ **OCR Multi-Engine**: PaddleOCR (CPU), Qwen2.5-VL (GPU), Surya
- ✅ **Multi-format**: PDF, PNG, JPG, TIFF, BMP
- ✅ **Multi-page**: Support documents multi-pages
- ✅ **Détection de tables**: Extraction et structuration des tables
- ✅ **Extraction d'entités**: Montants, dates, numéros de facture, etc.
- ✅ **Validation OHADA**: Conformité SYSCOHADA pour documents comptables
- ✅ **Traitement asynchrone**: Workers RabbitMQ avec priorités
- ✅ **Qualité & Confiance**: Scores de qualité et révision humaine si nécessaire
- ✅ **Multi-tenant**: Isolation stricte des données

## Installation

### Prérequis
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis
- RabbitMQ

### Installation locale

```bash
# Cloner le repository
cd backend/kauri_ocr_service

# Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer dépendances
pip install -r requirements.txt

# Télécharger modèle spaCy
python -m spacy download fr_core_news_md

# Copier configuration
cp .env.example .env
# Éditer .env avec vos paramètres
```

### Installation Docker

```bash
# Lancer tous les services
docker-compose up -d

# Voir les logs
docker-compose logs -f kauri_ocr_service

# Arrêter les services
docker-compose down
```

## Configuration

Variables d'environnement principales (voir `.env.example`):

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/kauri_ocr

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_USER=kauri
RABBITMQ_PASSWORD=password

# OCR
OCR_DEFAULT_ENGINE=paddleocr
OCR_LANG=fr,en
OCR_USE_GPU=False

# OHADA
OHADA_COUNTRIES=BJ,BF,CI,GW,ML,NE,SN,TG,CM,CF,TD,CG,GQ,GA
DEFAULT_CURRENCY=XOF
```

## Usage

### Démarrer l'application

```bash
# Mode développement
python -m uvicorn app.main:app --reload --port 8003

# Ou avec Docker
docker-compose up kauri_ocr_service
```

### Démarrer les workers

```bash
# Worker CPU
python -m app.workers.ocr_worker

# Ou avec Docker (2 workers)
docker-compose up ocr_worker_cpu
```

### API Endpoints

**Health Check**
```http
GET /api/v1/health
```

**Process Document**
```http
POST /api/v1/ocr/process
Content-Type: application/json

{
  "document_id": "uuid",
  "tenant_id": "uuid",
  "user_id": "uuid",
  "source_document_id": "uuid",
  "file_path": "/path/to/document.pdf",
  "filename": "facture_001.pdf",
  "mime_type": "application/pdf",
  "priority": 5,
  "enable_table_detection": true,
  "enable_entity_extraction": true,
  "enable_ohada_validation": true
}
```

**Get Document Status**
```http
GET /api/v1/ocr/document/{document_id}/status?tenant_id={tenant_id}
```

**Get Document Results**
```http
GET /api/v1/ocr/document/{document_id}?tenant_id={tenant_id}
```

**Search Documents**
```http
POST /api/v1/ocr/search
Content-Type: application/json

{
  "tenant_id": "uuid",
  "status": "completed",
  "document_type": "invoice",
  "requires_review": false,
  "from_date": "2024-01-01T00:00:00Z",
  "limit": 50,
  "offset": 0
}
```

**Get Tenant Statistics**
```http
GET /api/v1/ocr/stats/tenant/{tenant_id}
```

## Architecture des Données

### Tables Principales

**ocr_documents**
- Métadonnées du document
- Résultats OCR (texte, markdown, JSON)
- Scores de qualité et confiance
- Type de document et statut
- Données financières extraites
- Validation OHADA

**ocr_pages**
- Détails par page
- Layout et régions
- Bounding boxes
- Tables et signatures

**ocr_tables**
- Tables extraites
- Formats multiples (JSON, Markdown, HTML, CSV)
- Validation comptable

**ocr_entities**
- Entités nommées (montants, dates, etc.)
- Position et bounding boxes
- Valeurs normalisées

## Workflow OCR

```
1. Upload Document → Document Management Service

2. Trigger OCR
   └→ POST /api/v1/ocr/process
   └→ Document enqueued in RabbitMQ

3. Worker Processing
   ├→ Prétraitement (rotation, denoising)
   ├→ OCR (PaddleOCR/Qwen2.5-VL)
   ├→ Détection layout & tables
   ├→ Extraction entités (spaCy)
   └→ Validation OHADA

4. Post-Processing
   ├→ Structuration données
   ├→ Génération Markdown
   └→ Calcul qualité

5. Storage
   ├→ PostgreSQL (métadonnées, résultats)
   ├→ Redis (cache)
   └→ MinIO (fichiers)

6. Notification
   └→ Webhook vers services consommateurs
```

## Validation OHADA

Le service valide automatiquement les documents comptables selon les normes OHADA:

- ✅ Structure des factures (champs obligatoires)
- ✅ Calculs TVA (taux 18%, 19%)
- ✅ Équilibre comptable (Débit = Crédit)
- ✅ Codes de compte SYSCOHADA
- ✅ Devises OHADA (XOF, XAF)

## Intégrations

### Document Management Service
- Récupération fichiers originaux
- Enrichissement métadonnées

### Accounting Core Service
- Suggestions écritures automatiques
- Pré-remplissage formulaires

### Chatbot Service
- Indexation texte extrait
- Recherche sémantique

### Notification Service
- Alertes traitement terminé
- Notifications révision requise

## Métriques & Monitoring

- **Prometheus**: Métriques applicatives
- **Health Checks**: `/api/v1/health`, `/api/v1/health/ready`, `/api/v1/health/live`
- **Logs**: Format JSON structuré
- **Statistiques**: Par tenant, par type de document

Métriques disponibles:
- Total documents traités
- Temps de traitement moyen
- Score qualité moyen
- Taux de révision humaine
- Répartition par statut

## Tests

```bash
# Installer dépendances de test
pip install pytest pytest-asyncio pytest-cov httpx faker

# Lancer les tests
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=app --cov-report=html
```

## Développement

### Structure du projet

```
kauri_ocr_service/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── health.py
│   │       └── ocr.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── ocr_document.py
│   │   ├── ocr_page.py
│   │   ├── ocr_table.py
│   │   └── ocr_entity.py
│   ├── schemas/
│   │   └── ocr_document.py
│   ├── services/
│   │   └── ocr_engine.py
│   ├── workers/
│   │   └── ocr_worker.py
│   ├── utils/
│   │   └── ohada_validator.py
│   └── main.py
├── tests/
├── alembic/
├── models/           # OCR models cache
├── data/            # Temporary data
├── logs/            # Application logs
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Ajouter un moteur OCR

1. Créer une classe héritant de `OCREngine` dans `app/services/ocr_engine.py`
2. Implémenter `process_image()` et `process_pdf()`
3. Enregistrer dans `OCRService._initialize_engines()`

### Migrations Database

```bash
# Créer migration
alembic revision --autogenerate -m "Description"

# Appliquer migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance

### CPU Mode (PaddleOCR)
- **Temps de traitement**: ~5-10s par page
- **Throughput**: ~6-12 pages/minute
- **RAM**: 2-4GB
- **Idéal pour**: Développement, documents simples

### GPU Mode (Qwen2.5-VL)
- **Temps de traitement**: ~2-3s par page
- **Throughput**: ~20-30 pages/minute
- **VRAM**: 12-16GB (7B model) / 6-8GB (2B model)
- **Idéal pour**: Production, documents complexes, tables

### Optimisations
- Workers concurrents avec RabbitMQ
- Cache Redis pour résultats fréquents
- Batch processing pour documents similaires
- ONNX Runtime pour accélération

## Roadmap

- [ ] Support Qwen2.5-VL pour GPU
- [ ] Surya pour handwriting
- [ ] Détection avancée de tables (TableTransformer)
- [ ] Extraction d'entités avec LLM
- [ ] Détection de signatures
- [ ] OCR multi-lingue avancé
- [ ] A/B testing des modèles
- [ ] Auto-scaling workers
- [ ] Elasticsearch pour recherche full-text

## Licence

Propriétaire - KAURI © 2024

## Support

Pour toute question ou problème:
- Issues: [GitHub Issues]
- Email: support@kauri.com
- Documentation: [docs.kauri.com]
