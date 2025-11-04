# KAURI Chatbot - Analyse d'Architecture et Recommandations d'Amélioration

> **Date**: 2025-11-04
> **Projet**: KAURI - Solution Comptable Intelligente OHADA
> **Service**: KAURI Chatbot (Microservice #13)
> **Version**: 2.0 (Migration depuis OHAD'AI)

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Analyse de l'Architecture Actuelle](#2-analyse-de-larchitecture-actuelle)
3. [Points Forts](#3-points-forts)
4. [Points à Améliorer](#4-points-à-améliorer)
5. [Recommandations Architecturales](#5-recommandations-architecturales)
6. [Architecture Cible](#6-architecture-cible)
7. [Plan de Migration](#7-plan-de-migration)
8. [Roadmap d'Implémentation](#8-roadmap-dimplémentation)

---

## 1. Vue d'Ensemble

### 1.1 Contexte

Le chatbot KAURI est l'un des **25 microservices** de la plateforme KAURI. Il doit s'intégrer dans une architecture microservices cloud-native tout en conservant ses capacités RAG (Retrieval-Augmented Generation) expert en OHADA.

### 1.2 Architecture Actuelle (héritée d'OHAD'AI)

**Type**: Application monolithique avec capacités RAG  
**Stack**: FastAPI + ChromaDB + BGE-M3 + DeepSeek  
**Déploiement**: Serveur standalone sur port 8000  

---

## 2. Analyse de l'Architecture Actuelle

### 2.1 Stack Technique Actuelle

```yaml
Backend Framework: FastAPI 0.115.11
Base Vectorielle: ChromaDB 0.5.23 (locale, persistée sur disque)
Embeddings: BGE-M3 (local, 1024 dimensions)
LLM: DeepSeek-Chat (API) + OpenAI GPT-4 (fallback)
Reranking: Cross-Encoder (ms-marco-MiniLM-L-6-v2)
Cache: Redis 5.2.1 (optionnel, standalone)
Base SQL: SQLite (dev) / PostgreSQL (prod)
Serveur: Uvicorn 0.34.0
```

### 2.2 Points Forts ✅

#### 2.2.1 Recherche Hybride Sophistiquée
```
✅ BM25 (keyword) + Vector Search + Cross-Encoder Reranking
✅ Parallel search execution
✅ Intent classification avec LLM
✅ Query reformulation
✅ Context processing
```

**Forces**:
- Excellente qualité de recherche (NDCG@10 estimé 0.70-0.75)
- Combinaison de plusieurs approches complémentaires
- Reranking final pour optimiser la pertinence

#### 2.2.2 Optimisations Performance
```
✅ Warm-up au startup (~200-500ms gagnés)
✅ Cache Redis pour queries (95-98% gain latence)
✅ Cache embeddings (50-150ms par embedding)
✅ BGE-M3 local (vs API OpenAI)
✅ Batch embeddings
✅ Singleton pattern pour embedder
```

**Impact**: Latence 2-4s sans cache → 0.05s avec cache

#### 2.2.3 Features Complètes
```
✅ Streaming SSE
✅ Authentification JWT
✅ Gestion conversations
✅ Versioning documents
✅ Metadata enrichment
✅ Multi-collections (7 collections OHADA)
```

#### 2.2.4 Documentation Exhaustive
- Architecture détaillée
- Configuration LLM centralisée (YAML)
- Scripts d'ingestion documentés
- Guide de reproduction complet

---

## 3. Points à Améliorer ⚠️

### 3.1 Architecture Microservices

#### 🔴 **Problème Critique**: Monolithe dans un Écosystème Microservices

**État actuel**:
```
┌──────────────────────────────────────┐
│   OHAD'AI Backend (Monolithe)       │
│                                       │
│  ┌────────────────────────────────┐  │
│  │  API Routes                    │  │
│  │  - /query, /stream             │  │
│  │  - /auth, /conversations       │  │
│  │  - /documents                  │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │  Retrieval System              │  │
│  │  - BM25, Vector, Reranking     │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │  Generation System             │  │
│  │  - Intent, Reformulation       │  │
│  │  - Response Generation         │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │  Auth Manager                  │  │
│  │  - JWT, Password Utils         │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
        ↓ Port 8000
   [Client unique]
```

**Architecture cible KAURI**:
```
┌──────────────────────────────────────────────┐
│         KAURI Ecosystem (25 services)        │
│                                              │
│  Auth Service → User Service → Chatbot       │
│  Accounting → Invoice → Payment              │
│  Document Service → OCR Service              │
│  Notification → Workflow → Analytics         │
└──────────────────────────────────────────────┘
        ↓ API Gateway
   [Multiple clients]
```

**Impacts**:
- ❌ Couplage fort entre fonctionnalités
- ❌ Auth répliquée (déjà dans Auth Service)
- ❌ Pas de communication inter-services
- ❌ Scalabilité limitée (tout ou rien)
- ❌ Déploiement monolithique

**Recommandation**: Découper en **3 microservices** :
1. **Chatbot API Service** (orchestration, endpoints)
2. **RAG Engine Service** (recherche, embeddings)
3. **Knowledge Base Service** (gestion corpus, ingestion)

---

### 3.2 Base de Données Vectorielle

#### 🟠 **ChromaDB Local: Limites en Production**

**État actuel**:
```python
# ChromaDB stocké sur disque local
chroma_db/
├── chroma.sqlite3
└── [collections vectorielles]
```

**Problèmes**:
- ❌ Pas de scalabilité horizontale
- ❌ Pas de haute disponibilité
- ❌ Backup/restore complexe
- ❌ Pas de réplication multi-région
- ❌ Performances limitées (disque local)
- ❌ Pas adapté au cloud distribué

**Alternatives recommandées**:

| Solution | Avantages | Inconvénients | Recommandation |
|----------|-----------|---------------|----------------|
| **Pinecone** | Managed, HA, scalable, performant | Coût élevé, vendor lock-in | ✅ **Idéal production** |
| **Qdrant** | Open-source, scalable, performant | Self-hosted | ✅ Bon compromis |
| **Weaviate** | Open-source, GraphQL, hybrid search | Plus complexe | ⚠️ Si GraphQL utile |
| **Milvus** | Open-source, très performant, features avancées | Infrastructure lourde | ⚠️ Si gros volumes |
| **ChromaDB** | Simple, léger | Pas pour production scale | ❌ Dev/test uniquement |

**Choix recommandé**: **Pinecone** (production) + **Qdrant** (alternative self-hosted)

**Migration estimée**: 2-3 semaines

---

### 3.3 Base de Données Relationnelle

#### 🟠 **SQLite: Non adapté à la production**

**État actuel**:
```python
# Backend utilise SQLite en dev/test
data/
└── ohada_users.db  # SQLite
```

**Problèmes**:
- ❌ Pas de concurrence
- ❌ Pas de scalabilité
- ❌ Pas de réplication
- ❌ Limites transactions

**Recommandation**: 
- ✅ PostgreSQL déjà prévu dans spécifications
- ✅ Migrations SQLAlchemy en place
- ⚠️ Vérifier que tout fonctionne bien avec PostgreSQL

**Action**: Basculer définitivement sur PostgreSQL (déjà configuré dans docker-compose)

---

### 3.4 Sécurité

#### 🟡 **Manques Critiques**

**État actuel**:
```python
# JWT optionnel
# Pas de rate limiting
# Pas de validation d'entrées stricte
# Pas de protection DDoS
# Secrets en environnement simple
```

**Recommandations**:

1. **Rate Limiting**
```python
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

@app.post("/query", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
```

2. **Input Validation**
```python
from pydantic import BaseModel, Field, validator

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    
    @validator('query')
    def sanitize_query(cls, v):
        # Nettoyer injection, XSS, etc.
        return v.strip()
```

3. **Secrets Management**
- ✅ Utiliser AWS Secrets Manager / HashiCorp Vault
- ❌ Pas de secrets dans .env en production

4. **CORS Strict**
```python
# Actuellement trop permissif
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Dangereux
    allow_methods=["*"],
)

# Recommandé
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Liste blanche
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
```

5. **Auth avec Auth Service**
- Déléguer authentification au Auth Service (SSO)
- Token validation via API Gateway

---

### 3.5 Observabilité

#### 🟡 **Monitoring Insuffisant**

**État actuel**:
```python
# Logs basiques
# Pas de métriques structurées
# Pas de tracing distribué
# Pas d'alertes
```

**Recommandations**:

1. **Structured Logging**
```python
import structlog

logger = structlog.get_logger()

logger.info("query_received", 
    user_id=user_id,
    query_length=len(query),
    intent=intent,
    duration_ms=duration
)
```

2. **Métriques Prometheus**
```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)

# Métriques custom
query_duration = Histogram('query_duration_seconds', 'Query processing time')
query_errors = Counter('query_errors_total', 'Total query errors')
```

3. **Distributed Tracing (Jaeger)**
```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

tracer = trace.get_tracer(__name__)

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    with tracer.start_as_current_span("process_query"):
        # Trace chaque étape
        with tracer.start_as_current_span("embed_query"):
            embedding = await generate_embedding(query)
        with tracer.start_as_current_span("search_documents"):
            results = await search(embedding)
```

4. **Health Checks Avancés**
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "checks": {
            "database": check_db(),
            "vector_db": check_vector_db(),
            "redis": check_redis(),
            "llm_api": check_llm_api(),
            "embedder": check_embedder()
        }
    }
```

5. **Alerting (Grafana + Prometheus)**
- Alertes sur latence > 5s
- Alertes sur taux d'erreur > 5%
- Alertes sur disponibilité < 99%

---

### 3.6 Communication Inter-Services

#### 🔴 **Pas d'Event-Driven Architecture**

**État actuel**:
- Communication synchrone uniquement (REST)
- Pas de message bus
- Couplage temporel fort

**Recommandations**:

1. **Event Bus (Kafka ou RabbitMQ)**
```yaml
Events à publier:
  - chatbot.query.received
  - chatbot.query.completed
  - chatbot.error.occurred
  - knowledge.document.added
  - knowledge.document.updated

Events à consommer:
  - user.created (du User Service)
  - accounting.entry.created (pour enrichir contexte)
  - document.uploaded (du Document Service)
```

2. **Async Processing (Celery déjà en place)**
```python
# Bien: ingestion asynchrone
@celery.task
def ingest_document(document_id):
    # Tâche longue en arrière-plan
    pass
```

3. **Saga Pattern pour Transactions Distribuées**
```python
# Si création conversation nécessite plusieurs services
async def create_conversation_saga(user_id, query):
    # 1. Créer conversation
    conversation = await conversation_service.create(user_id)
    
    # 2. Publier event
    await event_bus.publish("chatbot.conversation.created", conversation)
    
    # 3. Traiter query
    try:
        response = await process_query(query)
    except Exception as e:
        # Rollback: supprimer conversation
        await conversation_service.delete(conversation.id)
        raise
```

---

### 3.7 Configuration et Environnements

#### 🟡 **Config YAML Bien Mais Peut Être Mieux**

**État actuel**:
```yaml
# llm_config_test.yaml et llm_config_production.yaml
# Bien: séparation environnements
# Manque: gestion centralisée multi-services
```

**Recommandations**:

1. **Config Service Centralisé (Consul ou Spring Cloud Config)**
```
Config Service
    ↓
[Chatbot] [Auth] [Accounting] ...
```

2. **Feature Flags (LaunchDarkly ou Unleash)**
```python
if feature_flags.is_enabled("use_gpt4_for_complex_queries"):
    llm = "gpt-4"
else:
    llm = "deepseek"
```

3. **Secrets Rotation**
- Rotation automatique des API keys
- Alertes sur secrets expirant

---

### 3.8 Testing

#### 🟡 **Tests Limités**

**État actuel**:
```bash
# Tests unitaires mentionnés mais pas détaillés
pytest tests/ -v
```

**Recommandations**:

1. **Test Pyramid**
```
       /\
      /  \  E2E Tests (10%)
     /    \
    / Inte \  Integration Tests (30%)
   /  gration\
  /    Tests  \
 /              \
/________________\  Unit Tests (60%)
```

2. **Tests Spécifiques RAG**
```python
def test_hybrid_search_quality():
    """Test NDCG@10 > 0.70"""
    queries = load_test_queries()
    results = [retriever.search(q) for q in queries]
    ndcg = calculate_ndcg(results)
    assert ndcg > 0.70

def test_response_quality():
    """Test réponses avec ground truth"""
    qa_pairs = load_qa_dataset()
    for question, expected in qa_pairs:
        response = chatbot.query(question)
        similarity = compute_similarity(response, expected)
        assert similarity > 0.80
```

3. **Load Testing**
```bash
# Tester 100 req/s pendant 10 minutes
locust -f tests/load_test.py --users 100 --spawn-rate 10 --run-time 10m
```

4. **Regression Testing**
- Tester automatiquement à chaque déploiement
- Dataset de questions/réponses de référence

---

### 3.9 Déploiement

#### 🟡 **Pas de CI/CD Ni Containerisation Mentionnée**

**État actuel**:
```bash
# Scripts .bat pour Windows
# Pas de Docker pour le code (uniquement services)
```

**Recommandations**:

1. **Dockerization**
```dockerfile
# Dockerfile.chatbot
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download BGE-M3 model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

# Copy application
COPY src/ ./src/

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s \
  CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "src.api.ohada_api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Kubernetes Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kauri-chatbot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: kauri-chatbot
  template:
    metadata:
      labels:
        app: kauri-chatbot
    spec:
      containers:
      - name: chatbot
        image: kauri/chatbot:1.0.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: chatbot-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

3. **CI/CD Pipeline (GitHub Actions)**
```yaml
name: Chatbot CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Run tests
      run: |
        pip install -r requirements.txt
        pytest tests/ --cov=src --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Build Docker image
      run: docker build -t kauri/chatbot:${{ github.sha }} .
    - name: Push to registry
      run: docker push kauri/chatbot:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/kauri-chatbot \
          chatbot=kauri/chatbot:${{ github.sha }}
```

4. **Helm Charts**
```yaml
# values.yaml
replicaCount: 3

image:
  repository: kauri/chatbot
  tag: "1.0.0"

resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80
```

---

### 3.10 Documentation

#### ✅ **Excellent mais Peut Être Enrichi**

**Points forts**:
- Architecture détaillée
- Configuration exhaustive
- Scripts documentés

**Améliorations**:
1. **API Documentation (OpenAPI/Swagger)**
```python
@app.post("/query", 
    summary="Query the chatbot",
    description="Send a query and get AI-powered response with OHADA sources",
    response_model=QueryResponse,
    responses={
        200: {"description": "Successful response"},
        400: {"description": "Invalid query"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"}
    }
)
```

2. **ADRs (Architecture Decision Records)**
```markdown
# ADR-001: Choice of Vector Database

Date: 2025-11-03
Status: Accepted

## Context
Need scalable vector database for production.

## Decision
Use Pinecone for production deployments.

## Consequences
+ Managed service, high availability
+ Excellent performance
- Cost ~$70/month for 1M vectors
```

3. **Runbooks**
```markdown
# Runbook: High Latency on /query Endpoint

## Symptoms
- Response time > 5s
- User complaints

## Investigation
1. Check Grafana dashboard
2. Check vector DB latency
3. Check LLM API status
4. Check cache hit rate

## Resolution
1. If LLM API down → switch to fallback
2. If cache hit rate low → warm cache
3. If vector DB slow → check indices
```

---

## 4. Architecture Cible Proposée

### 4.1 Vue d'Ensemble Microservices

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Gateway (Kong)                        │
│  - Rate Limiting, Auth, Routing, Load Balancing                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Chatbot API  │  │ RAG Engine   │  │ Knowledge    │
│   Service    │  │   Service    │  │Base Service  │
│              │  │              │  │              │
│ - REST API   │  │ - Embeddings │  │ - Ingestion  │
│ - Streaming  │  │ - Search     │  │ - Corpus Mgt │
│ - Validation │  │ - Reranking  │  │ - Versioning │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
        ┌────────────────┼────────────────────────┐
        │                │                        │
        ▼                ▼                        ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Auth Service │  │ User Service │  │ Document Service │
│ (External)   │  │ (External)   │  │ (External)       │
└──────────────┘  └──────────────┘  └──────────────────┘
        │                │                        │
        └────────────────┼────────────────────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │    Event Bus (Kafka)   │
            │  - chatbot.*           │
            │  - knowledge.*         │
            │  - user.*              │
            └────────────────────────┘
```

### 4.2 Service #1: Chatbot API Service

**Responsabilités**:
- Exposer API REST pour le chatbot
- Gérer conversations et sessions
- Orchestrer appels aux autres services
- Streaming SSE
- Rate limiting, validation

**Stack**:
```yaml
Framework: FastAPI
Language: Python 3.11+
Dependencies:
  - RAG Engine Service (gRPC)
  - Auth Service (REST)
  - User Service (REST)
  - Event Bus (Kafka producer)
```

**Endpoints**:
```
POST   /v1/chat/query              # Query synchrone
GET    /v1/chat/stream             # Query streaming SSE
GET    /v1/chat/conversations      # Liste conversations
POST   /v1/chat/conversations      # Créer conversation
GET    /v1/chat/conversations/:id  # Détails conversation
DELETE /v1/chat/conversations/:id  # Supprimer conversation
GET    /v1/health                  # Health check
GET    /v1/metrics                 # Prometheus metrics
```

**Scaling**: 3-10 replicas selon charge

---

### 4.3 Service #2: RAG Engine Service

**Responsabilités**:
- Recherche hybride (BM25 + Vector)
- Génération embeddings (BGE-M3)
- Reranking (Cross-Encoder)
- Appel LLM (DeepSeek, GPT-4)
- Cache résultats

**Stack**:
```yaml
Framework: FastAPI (ou gRPC pour performance)
Language: Python 3.11+
Vector DB: Pinecone (prod) / Qdrant (self-hosted)
Cache: Redis Cluster
Models:
  - BGE-M3 (embeddings)
  - Cross-Encoder (reranking)
  - DeepSeek API (LLM)
```

**API interne (gRPC)**:
```protobuf
service RAGEngine {
  rpc Search(SearchRequest) returns (SearchResponse);
  rpc GenerateResponse(GenerateRequest) returns (stream GenerateResponse);
  rpc GenerateEmbedding(EmbeddingRequest) returns (EmbeddingResponse);
}
```

**Scaling**: 2-5 replicas (CPU/GPU-intensive)

---

### 4.4 Service #3: Knowledge Base Service

**Responsabilités**:
- Ingestion documents (batch/streaming)
- Parsing (Word, PDF, etc.)
- Chunking et preprocessing
- Enrichissement métadonnées
- Versioning corpus
- Synchronisation avec Pinecone

**Stack**:
```yaml
Framework: FastAPI
Language: Python 3.11+
Database: PostgreSQL (metadata)
Object Storage: AWS S3 / MinIO (documents bruts)
Queue: Celery + Redis (async tasks)
Vector DB: Pinecone (sync)
```

**Endpoints**:
```
POST /v1/knowledge/documents          # Ingest single doc
POST /v1/knowledge/documents/batch    # Ingest batch
GET  /v1/knowledge/documents          # Liste documents
GET  /v1/knowledge/documents/:id      # Détails document
PUT  /v1/knowledge/documents/:id      # Update document
DELETE /v1/knowledge/documents/:id    # Delete document
GET  /v1/knowledge/stats              # Statistiques corpus
POST /v1/knowledge/sync               # Force sync avec Pinecone
```

**Scaling**: 1-3 replicas (IO-intensive)

---

### 4.5 Infrastructure Partagée

#### 4.5.1 Bases de Données

```yaml
PostgreSQL:
  Type: AWS RDS / GCP Cloud SQL
  Réplication: Multi-AZ
  Backup: Daily automated
  Connexions: PgBouncer pool
  Usage:
    - Chatbot: conversations, messages
    - Knowledge: documents metadata, versions

Pinecone:
  Type: Managed Vector DB
  Index: Standard (1024 dim)
  Pods: p1 ou s1 selon volume
  Regions: Multi-region replication
  Usage: Embeddings OHADA corpus

Redis Cluster:
  Type: AWS ElastiCache / Redis Enterprise
  Nodes: 3+ nodes (HA)
  Persistence: AOF + RDB
  Usage:
    - Cache queries/embeddings
    - Celery broker
    - Rate limiting
```

#### 4.5.2 Message Bus

```yaml
Kafka:
  Type: Confluent Cloud / AWS MSK
  Topics:
    - chatbot.query.received
    - chatbot.query.completed
    - chatbot.error
    - knowledge.document.added
    - knowledge.document.updated
    - user.created (from User Service)
  Retention: 7 days
  Partitions: 3-10 par topic
```

#### 4.5.3 Observabilité

```yaml
Logging:
  Stack: ELK (Elasticsearch + Logstash + Kibana)
  Format: JSON structured logs
  Retention: 30 days

Metrics:
  Stack: Prometheus + Grafana
  Exporters: Per-service /metrics endpoint
  Alerts: PagerDuty integration

Tracing:
  Stack: Jaeger
  Sampling: 10% in prod, 100% in staging
```

---

## 5. Comparaison Architecture Actuelle vs Cible

| Aspect | Actuel | Cible | Bénéfices |
|--------|--------|-------|-----------|
| **Architecture** | Monolithe | 3 microservices | Scalabilité indépendante, isolation des pannes |
| **Vector DB** | ChromaDB local | Pinecone managed | HA, performance, réplication |
| **SQL DB** | SQLite | PostgreSQL (RDS) | Concurrence, réplication, backup |
| **Cache** | Redis standalone | Redis Cluster | HA, sharding |
| **Auth** | Interne (JWT) | Auth Service (SSO) | Centralisation, sécurité |
| **Communication** | REST sync | REST + gRPC + Events | Performance, découplage |
| **Déploiement** | Scripts .bat | Kubernetes + Helm | Automation, orchestration |
| **Monitoring** | Logs basiques | ELK + Prometheus + Jaeger | Observabilité complète |
| **CI/CD** | Aucun | GitHub Actions | Déploiement automatisé |
| **Sécurité** | Basique | Rate limiting + Secrets Mgmt | Protection DDoS, secrets sécurisés |
| **Testing** | Minimal | Pyramid (unit/integration/e2e) | Qualité, non-régression |

---

## 6. Plan de Migration

### Phase 1: Préparation (2 semaines)

**Objectifs**:
- Finaliser spécifications détaillées
- Setup infrastructure cible
- Préparer environnements

**Tâches**:
1. ✅ Provisionner PostgreSQL (RDS)
2. ✅ Provisionner Redis Cluster (ElastiCache)
3. ✅ Créer compte Pinecone et setup index
4. ✅ Setup Kubernetes cluster (EKS / GKE / AKS)
5. ✅ Configurer API Gateway (Kong)
6. ✅ Setup Kafka (MSK / Confluent)
7. ✅ Setup observabilité (ELK + Prometheus + Jaeger)
8. ✅ Créer repos Git séparés pour chaque service

---

### Phase 2: Migration Backend (6 semaines)

#### Semaine 1-2: Découpage Monolithe

**Objectif**: Extraire les 3 microservices

**Tâches**:
1. Créer structure projet `kauri-chatbot-api/`
   ```
   kauri-chatbot-api/
   ├── src/
   │   ├── api/
   │   ├── models/
   │   ├── services/
   │   └── utils/
   ├── tests/
   ├── Dockerfile
   ├── requirements.txt
   └── helm/
   ```

2. Extraire endpoints API uniquement
3. Remplacer auth interne par appels Auth Service
4. Implémenter gRPC client vers RAG Engine

5. Créer structure projet `kauri-rag-engine/`
   ```
   kauri-rag-engine/
   ├── src/
   │   ├── retrieval/
   │   ├── generation/
   │   ├── embeddings/
   │   └── cache/
   ├── proto/
   ├── tests/
   ├── Dockerfile
   └── requirements.txt
   ```

6. Migrer système de recherche hybride
7. Implémenter serveur gRPC
8. Setup cache Redis Cluster

9. Créer structure projet `kauri-knowledge-base/`
   ```
   kauri-knowledge-base/
   ├── src/
   │   ├── ingest/
   │   ├── parsers/
   │   ├── sync/
   │   └── api/
   ├── celery_worker/
   ├── tests/
   ├── Dockerfile
   └── requirements.txt
   ```

10. Migrer scripts d'ingestion
11. Implémenter API REST
12. Setup Celery workers

#### Semaine 3: Migration Vector DB

**Objectif**: Migrer ChromaDB → Pinecone

**Tâches**:
1. Export données ChromaDB
   ```python
   from src.vector_db.ohada_vector_db_structure import OhadaVectorDB
   
   db = OhadaVectorDB()
   all_collections = db.get_all_collections()
   
   for collection_name in all_collections:
       collection = db.client.get_collection(collection_name)
       data = collection.get(include=["embeddings", "documents", "metadatas"])
       
       # Export to JSON
       with open(f"{collection_name}_export.json", "w") as f:
           json.dump(data, f)
   ```

2. Import vers Pinecone
   ```python
   import pinecone
   
   pinecone.init(api_key="...", environment="...")
   
   # Créer index (1024 dimensions pour BGE-M3)
   pinecone.create_index("kauri-ohada", dimension=1024, metric="cosine")
   index = pinecone.Index("kauri-ohada")
   
   # Batch upsert
   for collection_name in all_collections:
       with open(f"{collection_name}_export.json") as f:
           data = json.load(f)
       
       vectors = [
           (id, embedding, metadata)
           for id, embedding, metadata in zip(data["ids"], data["embeddings"], data["metadatas"])
       ]
       
       # Upsert par batches de 100
       for i in range(0, len(vectors), 100):
           batch = vectors[i:i+100]
           index.upsert(vectors=batch, namespace=collection_name)
   ```

3. Tester recherche Pinecone vs ChromaDB (qualité identique)
4. Basculer code sur Pinecone
5. Vérifier performances

#### Semaine 4: Containerisation

**Objectif**: Dockeriser les 3 services

**Tâches**:
1. Écrire Dockerfiles optimisés (multi-stage builds)
2. Setup CI pour build images
3. Push vers registry (AWS ECR / GCP GCR)
4. Tester images localement

#### Semaine 5: Déploiement Kubernetes

**Objectif**: Déployer sur Kubernetes

**Tâches**:
1. Écrire Helm charts
2. Configurer secrets (Sealed Secrets)
3. Setup Ingress (API Gateway)
4. Déployer sur cluster staging
5. Tests end-to-end

#### Semaine 6: Observabilité & Monitoring

**Objectif**: Setup monitoring complet

**Tâches**:
1. Intégrer structured logging
2. Exposer métriques Prometheus
3. Configurer Jaeger tracing
4. Créer dashboards Grafana
5. Setup alertes

---

### Phase 3: Migration Base de Données (1 semaine)

**Objectif**: Migrer SQLite → PostgreSQL

**Tâches**:
1. Export données SQLite
   ```bash
   sqlite3 data/ohada_users.db .dump > dump.sql
   ```

2. Adapter SQL pour PostgreSQL
   ```bash
   # Remplacer syntaxe SQLite par PostgreSQL
   sed -i 's/AUTOINCREMENT/SERIAL/g' dump.sql
   ```

3. Import vers PostgreSQL
   ```bash
   psql -U ohada_user -d ohada -f dump.sql
   ```

4. Vérifier intégrité données
5. Basculer `DATABASE_URL` sur PostgreSQL

---

### Phase 4: Tests & Validation (2 semaines)

#### Semaine 1: Tests Fonctionnels

**Tâches**:
1. Tests unitaires (coverage > 80%)
2. Tests d'intégration inter-services
3. Tests end-to-end
4. Tests de régression (qualité réponses)

#### Semaine 2: Tests Non-Fonctionnels

**Tâches**:
1. Load testing (1000 req/s pendant 10 min)
2. Stress testing (jusqu'à rupture)
3. Tests de résilience (chaos engineering)
4. Tests de sécurité (OWASP)

---

### Phase 5: Déploiement Production (1 semaine)

**Objectif**: Mise en production avec Blue/Green

**Tâches**:
1. Déploiement environnement Blue (nouveau)
2. Smoke tests sur Blue
3. Basculer 10% trafic sur Blue (canary)
4. Monitorer métriques 24h
5. Si OK → Basculer 100% trafic sur Blue
6. Si KO → Rollback sur Green
7. Après validation → Supprimer Green

---

## 7. Roadmap d'Implémentation

### Timeline Global: 12 semaines

```
Semaines 1-2:   [===== Préparation =====]
Semaines 3-8:   [========== Migration Backend ==========]
Semaine 9:      [= Migration DB =]
Semaines 10-11: [====== Tests ======]
Semaine 12:     [== Prod ==]
```

### Priorités

**P0 - Critique (blocker production)**:
- ✅ Migration Vector DB (ChromaDB → Pinecone)
- ✅ Migration SQL DB (SQLite → PostgreSQL)
- ✅ Sécurité (rate limiting, input validation)
- ✅ Monitoring (logs, métriques, alertes)

**P1 - Important (qualité production)**:
- ✅ Découpage microservices (3 services)
- ✅ Containerisation + Kubernetes
- ✅ CI/CD pipeline
- ✅ Event-driven communication (Kafka)

**P2 - Nice to have (optimisations)**:
- ⚠️ gRPC pour communication inter-services (vs REST)
- ⚠️ Service mesh (Istio) pour traffic management
- ⚠️ GitOps (ArgoCD) pour déploiements
- ⚠️ API versioning strict (v2, v3, etc.)

---

## 8. Risques et Mitigation

### Risque 1: Migration Vector DB Perd en Qualité

**Impact**: Réponses moins pertinentes  
**Probabilité**: Faible (Pinecone > ChromaDB)  
**Mitigation**:
- Tests A/B ChromaDB vs Pinecone avant migration
- Garder backup ChromaDB pendant 1 mois
- Rollback facile si problème

### Risque 2: Latence Augmente (Communication Inter-Services)

**Impact**: UX dégradée  
**Probabilité**: Moyenne  
**Mitigation**:
- Utiliser gRPC (plus rapide que REST)
- Cache agressif (Redis)
- Async processing (événements)
- Load testing avant prod

### Risque 3: Complexité Opérationnelle

**Impact**: Difficulté maintenance  
**Probabilité**: Élevée  
**Mitigation**:
- Documentation exhaustive
- Runbooks pour incidents courants
- Formation équipe DevOps
- Observabilité complète (logs, metrics, tracing)

### Risque 4: Coûts Infrastructure

**Impact**: Budget dépassé  
**Probabilité**: Moyenne  
**Mitigation**:
- Estimation coûts à l'avance:
  - Pinecone: ~$70/mois (1M vectors)
  - RDS PostgreSQL: ~$100/mois
  - ElastiCache Redis: ~$50/mois
  - Kubernetes: ~$150/mois
  - **Total: ~$370/mois** (estimé)
- Monitoring coûts (AWS Cost Explorer)
- Auto-scaling pour optimiser

---

## 9. Métriques de Succès

### 9.1 Performance

| Métrique | Actuel | Cible | Mesure |
|----------|--------|-------|--------|
| Latence p50 (sans cache) | 2-4s | < 2s | Prometheus |
| Latence p95 (sans cache) | 4-6s | < 3s | Prometheus |
| Latence p50 (avec cache) | 50ms | < 100ms | Prometheus |
| Throughput | 10 req/s | 100 req/s | Load testing |

### 9.2 Qualité

| Métrique | Actuel | Cible | Mesure |
|----------|--------|-------|--------|
| NDCG@10 | 0.70-0.75 | > 0.75 | Tests régression |
| Precision@5 | Non mesuré | > 80% | Tests régression |
| Recall@10 | Non mesuré | > 70% | Tests régression |

### 9.3 Disponibilité

| Métrique | Actuel | Cible | Mesure |
|----------|--------|-------|--------|
| Uptime | Non mesuré | 99.9% | Prometheus |
| MTTR | Non mesuré | < 5 min | Incidents |

### 9.4 Évolutivité

| Métrique | Actuel | Cible | Mesure |
|----------|--------|-------|--------|
| Scalabilité | Verticale uniquement | Horizontale | Kubernetes HPA |
| Replicas | 1 | 2-10 (auto) | Kubernetes |
| Multi-région | Non | Oui (3 régions) | Infrastructure |

---

## 10. Conclusion

### Résumé des Améliorations Clés

1. **Architecture Microservices**: Découpage en 3 services autonomes
2. **Vector DB Production-Ready**: Pinecone avec HA et réplication
3. **SQL DB Robuste**: PostgreSQL avec réplication multi-AZ
4. **Sécurité Renforcée**: Rate limiting, input validation, secrets management
5. **Observabilité Complète**: Logs structurés, métriques, tracing distribué
6. **CI/CD Automatisé**: GitHub Actions + Kubernetes + Helm
7. **Event-Driven**: Communication asynchrone via Kafka
8. **Scalabilité**: Auto-scaling horizontal Kubernetes

### Gains Attendus

| Aspect | Gain |
|--------|------|
| **Disponibilité** | 99.5% → 99.9% |
| **Scalabilité** | 10 req/s → 100 req/s |
| **Latence** | -30% (grâce à Pinecone + gRPC) |
| **Maintenabilité** | +50% (grâce à microservices) |
| **Time to Market** | -40% (grâce à CI/CD) |
| **Coûts Ops** | -20% (grâce à monitoring) |

### Prochaines Étapes Immédiates

1. ✅ Valider architecture cible avec équipe
2. ✅ Estimer coûts infrastructure (Pinecone + RDS + K8s)
3. ✅ Provisionner infrastructure cible
4. ✅ Démarrer Phase 1 (Préparation)
5. ✅ Recruter/former équipe DevOps si nécessaire

---

**Date de création**: 2025-11-04
**Version**: 2.0
**Auteur**: Architecture Team
**Statut**: Proposition - En attente de validation

---

## Annexes

### A. Comparatif Vector Databases

| Feature | ChromaDB | Pinecone | Qdrant | Weaviate | Milvus |
|---------|----------|----------|--------|----------|--------|
| **Type** | Embedded | Managed | Self/Managed | Self/Managed | Self-hosted |
| **Scalabilité** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **HA** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Performance** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Coût** | Free | $$$ | $$ | $$ | $$ |
| **Facilité** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **API** | Python | REST/gRPC | REST/gRPC | GraphQL/REST | Python/gRPC |

**Recommandation**: Pinecone (prod) ou Qdrant (self-hosted)

### B. Estimation Coûts Mensuelle

```
Infrastructure:
  - Pinecone (1M vectors, p1):     $70
  - RDS PostgreSQL (db.t3.medium): $100
  - ElastiCache Redis (3 nodes):   $50
  - Kubernetes (3 nodes t3.large): $150
  - S3 (documents storage):        $10
  - CloudWatch (logs):             $20
  - Data Transfer:                 $30
  ──────────────────────────────────
  TOTAL:                           ~$430/mois

Personnel (estimé):
  - DevOps Engineer:               $5000/mois
  - Backend Engineer:              $4000/mois
  ──────────────────────────────────
  TOTAL:                           $9000/mois

Total Mensuel:                     ~$9430/mois
```

### C. Glossaire

- **RAG**: Retrieval-Augmented Generation
- **BM25**: Okapi Best Matching 25 (algorithme de recherche keyword)
- **BGE-M3**: BAAI General Embedding Model M3
- **Cross-Encoder**: Modèle de reranking
- **NDCG**: Normalized Discounted Cumulative Gain
- **SSE**: Server-Sent Events
- **HPA**: Horizontal Pod Autoscaler (Kubernetes)
- **RDS**: Relational Database Service (AWS)
- **ELK**: Elasticsearch, Logstash, Kibana
