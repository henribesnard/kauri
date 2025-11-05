# KAURI OCR Service - Architecture Détaillée

## Vue d'ensemble

Le service OCR KAURI est un microservice asynchrone conçu pour traiter des documents comptables et financiers avec validation OHADA. Il utilise une architecture orientée événements avec workers distribués.

## Architecture Technique

### 1. Couche API (FastAPI)

**Responsabilités:**
- Endpoints REST pour soumettre/consulter documents
- Validation des requêtes (Pydantic)
- Authentification et autorisation
- Rate limiting par tenant
- Documentation automatique (OpenAPI)

**Routes principales:**
```
POST   /api/v1/ocr/process        # Soumettre document pour OCR
GET    /api/v1/ocr/document/{id}  # Consulter résultats
GET    /api/v1/ocr/document/{id}/status  # Statut traitement
POST   /api/v1/ocr/search         # Rechercher documents
GET    /api/v1/ocr/stats/tenant/{id}  # Statistiques tenant
DELETE /api/v1/ocr/document/{id}  # Supprimer document
GET    /api/v1/health             # Health check
```

### 2. Couche Traitement Asynchrone

**Workers RabbitMQ:**
- Pool de workers CPU (PaddleOCR)
- Pool de workers GPU (Qwen2.5-VL) - optionnel
- Gestion des priorités (1-10)
- Retry automatique avec backoff exponentiel
- Dead letter queue pour échecs

**Queues:**
```
ocr_processing       # Queue principale
ocr_priority         # Queue prioritaire
ocr_results          # Résultats traitement
ocr_dead_letter      # Documents échoués
```

**Workflow Worker:**
```
1. Récupération message RabbitMQ
   └→ Extraction job details (document_id, file_path, options)

2. Mise à jour statut → PROCESSING

3. Prétraitement image
   ├→ Rotation si nécessaire
   ├→ Denoising
   ├→ Deskewing
   └→ Normalisation

4. OCR Processing
   ├→ Détection layout
   ├→ Extraction texte
   ├→ Détection tables
   └→ Bounding boxes

5. Post-processing
   ├→ Entity extraction (spaCy)
   ├→ Validation OHADA
   ├→ Génération markdown
   └→ Structuration JSON

6. Sauvegarde résultats
   ├→ PostgreSQL (métadonnées + résultats)
   ├→ Redis (cache)
   └→ MinIO (fichiers markdown/JSON)

7. Notification
   └→ Webhook vers services consommateurs

8. Acknowledgement RabbitMQ
```

### 3. Moteurs OCR

#### PaddleOCR (CPU - Dev/Prod)
- **Usage:** Documents standards
- **Performance:** 5-10s/page
- **Mémoire:** 2-4GB RAM
- **Features:**
  - Détection texte multilingue
  - Angle classification
  - 80+ langues supportées
  - Optimisé CPU

#### Qwen2.5-VL (GPU - Production)
- **Usage:** Documents complexes, tables avancées
- **Performance:** 2-3s/page
- **VRAM:** 12-16GB (7B) / 6-8GB (2B)
- **Features:**
  - Compréhension contextuelle
  - Layout understanding
  - Extraction intelligente
  - Output markdown natif

#### Surya (GPU - Spécialiste)
- **Usage:** Manuscrits, handwriting
- **Performance:** 3-5s/page
- **VRAM:** 4-6GB
- **Features:**
  - Excellente reconnaissance manuscrite
  - Multilingue optimisé
  - Layout detection

### 4. Base de Données

#### PostgreSQL
```sql
Tables principales:
- ocr_documents       # Documents et résultats principaux
- ocr_pages          # Détails par page
- ocr_tables         # Tables extraites
- ocr_entities       # Entités nommées (NER)

Index:
- idx_tenant_status
- idx_tenant_created
- idx_requires_review
- idx_document_page
```

**Optimisations:**
- Partition par tenant (futur)
- Index B-tree sur tenant_id, status, created_at
- JSONB pour métadonnées flexibles
- Full-text search sur extracted_text

#### Redis
```
Patterns:
ocr:document:{id}              # Résultats OCR (TTL: 7j)
ocr:stats:tenant:{id}:{date}   # Stats agrégées (TTL: 1h)
ocr:ratelimit:tenant:{id}      # Rate limiting
ocr:worker:{id}:heartbeat      # Health workers
ocr:job:{id}:progress          # Progression temps réel
```

**Usage:**
- Cache résultats OCR fréquemment consultés
- Rate limiting par tenant
- Session de progression pour UI temps réel
- Heartbeat workers pour monitoring

#### MinIO/S3
```
Buckets:
kauri-ocr/
  ├── documents/        # Fichiers originaux
  ├── processed/        # Images prétraitées
  ├── markdown/         # Outputs markdown
  ├── json/             # Outputs JSON structuré
  └── thumbnails/       # Vignettes (futur)
```

### 5. Validation OHADA

**OHADAValidator** valide:

1. **Factures:**
   - Champs obligatoires (n°, date, émetteur, destinataire)
   - Numéro fiscal émetteur
   - Calculs TVA (18%, 19%)
   - Total HT + TVA = Total TTC

2. **Bilans Comptables:**
   - Équation comptable: Actif = Passif + Capitaux propres
   - Sections requises (actif, passif, capitaux)

3. **Écritures de Journal:**
   - Équilibre Débit = Crédit
   - Champs obligatoires (date, journal, description, lignes)
   - Chaque ligne: compte + (débit XOR crédit)

4. **Codes de compte SYSCOHADA:**
   - Format: 1-8 chiffres
   - Classes valides: 1-8
   - Validation par classe

5. **Montants financiers:**
   - Devise OHADA (XOF, XAF)
   - Cohérence montants
   - Détection anomalies (négatifs inattendus)

### 6. Extraction d'Entités

**Types d'entités extraites:**

**Financières:**
- Montants (total, HT, TTC)
- TVA (taux, montant)
- Devise

**Identifiants:**
- N° facture, commande
- ID client, fournisseur
- Matricule fiscal
- IBAN, n° compte

**Dates:**
- Date facture, échéance
- Date paiement
- Date transaction

**Parties:**
- Noms sociétés, personnes
- Adresses
- Email, téléphone

**Comptable:**
- Codes comptes SYSCOHADA
- Codes journaux
- Débit, crédit

**Méthodes:**
- Regex patterns (montants, dates, codes)
- spaCy NER (noms, lieux)
- LLM extraction (contexte complexe) - futur

### 7. Qualité et Révision

**Calcul Score Qualité:**
```python
quality_score = (
    confidence_score * 0.4 +      # Confiance OCR
    text_coverage * 0.3 +          # Couverture texte
    structure_detected * 0.2 +     # Structure détectée
    error_indicators * 0.1         # Indicateurs erreur
)
```

**Déclenchement Révision Humaine:**
- Quality score < 0.8
- Confidence score < 0.6
- Validation OHADA échouée
- Montants incohérents
- Champs critiques manquants

### 8. Sécurité

**Multi-tenant:**
- Isolation stricte par tenant_id
- Index sur tenant_id pour performances
- RLS (Row Level Security) - futur

**Données sensibles:**
- Chiffrement at-rest (AES-256)
- Chiffrement in-transit (TLS 1.3)
- Tokenization n° comptes, IDs fiscaux

**Accès:**
- JWT Authentication
- RBAC (Role-Based Access Control)
- Audit logs complets
- Rate limiting par tenant

**RGPD:**
- Soft delete (is_deleted flag)
- Anonymisation données personnelles
- Droit à l'oubli
- Consentement tracking

### 9. Monitoring & Observabilité

**Métriques Prometheus:**
```
ocr_requests_total
ocr_processing_duration_seconds
ocr_queue_depth
ocr_worker_active
ocr_success_rate
ocr_confidence_score_avg
ocr_quality_score_avg
```

**Health Checks:**
- `/health` - Basic health
- `/health/ready` - Readiness (DB, Redis, RabbitMQ)
- `/health/live` - Liveness

**Logs structurés:**
```json
{
  "timestamp": "2024-10-15T10:30:00Z",
  "level": "INFO",
  "service": "kauri_ocr_service",
  "tenant_id": "uuid",
  "document_id": "uuid",
  "event": "ocr_completed",
  "duration_ms": 5432,
  "confidence": 0.92
}
```

### 10. Scalabilité

**Horizontal Scaling:**
- API: Multiple pods derrière load balancer
- Workers: Auto-scaling basé sur queue depth
- Database: Read replicas pour queries
- Redis: Cluster mode pour haute disponibilité

**Optimisations:**
- Connection pooling (DB, Redis)
- Batch processing documents similaires
- ONNX Runtime pour accélération modèles
- Lazy loading modèles OCR
- Cache intelligent (Redis)

**Limites actuelles:**
- 50MB/document
- 100 pages/document
- 4096px dimension max
- 100 req/h/tenant (dev)

## Intégrations Services KAURI

### Document Management Service
```
Trigger OCR:
Document uploaded → Webhook → OCR Service

Store Results:
OCR completed → Update document metadata
```

### Accounting Core Service
```
Auto-suggestion écritures:
OCR invoice → Extract entities → Suggest journal entries
```

### Chatbot Service
```
Indexation:
OCR completed → Index text → ChromaDB/Pinecone
```

### Notification Service
```
Alerts:
- OCR completed
- Review required
- Processing failed
```

## Déploiement

### Développement
```
docker-compose up -d
```

### Production (Kubernetes)
```yaml
Deployments:
- kauri-ocr-api (3 replicas)
- kauri-ocr-worker-cpu (5 replicas)
- kauri-ocr-worker-gpu (2 replicas)

Services:
- PostgreSQL (StatefulSet, PVC)
- Redis (Cluster, 3 nodes)
- RabbitMQ (HA, 3 nodes)
- MinIO (Distributed, 4+ nodes)
```

## Roadmap

**Q1 2025:**
- [ ] Qwen2.5-VL integration
- [ ] Advanced table detection
- [ ] Signature detection
- [ ] Elasticsearch full-text search

**Q2 2025:**
- [ ] Handwriting OCR (Surya/TrOCR)
- [ ] LLM-based entity extraction
- [ ] Auto-scaling workers
- [ ] A/B testing framework

**Q3 2025:**
- [ ] Multi-model ensemble
- [ ] Active learning pipeline
- [ ] Custom model fine-tuning
- [ ] Advanced analytics dashboard
