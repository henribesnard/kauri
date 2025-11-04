# KAURI Chatbot - Diagrammes d'Architecture

> **Visualisations de l'architecture actuelle et cible**

---

## 1. Architecture Actuelle (Monolithe OHAD'AI)

### 1.1 Vue d'Ensemble Système Actuel

```
┌──────────────────────────────────────────────────────────────────┐
│                         CLIENT WEB                                │
│                    (Vite.js Frontend)                             │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP/SSE
                             │ Port 8000
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│              OHAD'AI BACKEND MONOLITHE (FastAPI)                   │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │                     API LAYER                                  │ │
│ │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │ │
│ │  │  /query  │  │ /stream  │  │  /auth   │  │/conversations│  │ │
│ │  └──────────┘  └──────────┘  └──────────┘  └──────────────┘  │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │                   BUSINESS LOGIC                               │ │
│ │  ┌───────────────┐  ┌────────────────┐  ┌──────────────────┐ │ │
│ │  │Intent         │  │Query           │  │Context           │ │ │
│ │  │Classifier     │  │Reformulator    │  │Processor         │ │ │
│ │  └───────────────┘  └────────────────┘  └──────────────────┘ │ │
│ │  ┌───────────────────────────────────────────────────────────┐ │ │
│ │  │            HYBRID RETRIEVAL                               │ │ │
│ │  │  ┌─────────────┐              ┌──────────────┐           │ │ │
│ │  │  │BM25 Search  │    Parallel  │Vector Search │           │ │ │
│ │  │  │(Keyword)    │◄────────────►│(BGE-M3)      │           │ │ │
│ │  │  └──────┬──────┘              └──────┬───────┘           │ │ │
│ │  │         │                            │                   │ │ │
│ │  │         └──────────►┌────────────────┴──────┐            │ │ │
│ │  │                     │  Cross-Encoder        │            │ │ │
│ │  │                     │  Reranking            │            │ │ │
│ │  │                     └───────────────────────┘            │ │ │
│ │  └───────────────────────────────────────────────────────────┘ │ │
│ │  ┌──────────────────────────────────────────────────────────┐ │ │
│ │  │         RESPONSE GENERATION                              │ │ │
│ │  │  ┌──────────┐         ┌──────────┐                      │ │ │
│ │  │  │DeepSeek  │Fallback │ GPT-4    │                      │ │ │
│ │  │  │LLM       │────────►│OpenAI    │                      │ │ │
│ │  │  └──────────┘         └──────────┘                      │ │ │
│ │  └──────────────────────────────────────────────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │                   AUTH & USER MANAGEMENT                       │ │
│ │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │ │
│ │  │ JWT Manager  │  │Password Utils│  │User Management   │    │ │
│ │  └──────────────┘  └──────────────┘  └──────────────────┘    │ │
│ └────────────────────────────────────────────────────────────────┘ │
└─────────────────┬───────────────────────┬───────────────────────────┘
                  │                       │
         ┌────────▼────────┐    ┌────────▼────────┐
         │   ChromaDB      │    │  Redis Cache    │
         │   (Local Disk)  │    │  (Optional)     │
         │                 │    │                 │
         │ • 7 Collections │    │ • Query Cache   │
         │ • BGE-M3 1024   │    │ • Embedding     │
         │ • Persistent    │    │   Cache         │
         └─────────────────┘    └─────────────────┘
                  │
         ┌────────▼────────┐
         │   SQLite DB     │
         │  (ohada_users)  │
         │                 │
         │ • Users         │
         │ • Conversations │
         │ • Documents     │
         └─────────────────┘
```

### 1.2 Flux de Traitement d'une Requête

```
User Query → API → [Cache Check] → Intent Classification → Query Reformulation
                          ↓ Hit                                    ↓
                    Return Cached                          ┌───────┴────────┐
                                                           │                │
                                                      BM25 Search    Vector Search
                                                    (keyword-based)  (semantic)
                                                           │                │
                                                           └───────┬────────┘
                                                                   │
                                                           Combine & Deduplicate
                                                                   │
                                                            Cross-Encoder Rerank
                                                                   │
                                                            Context Processing
                                                                   │
                                                              LLM Generation
                                                           (DeepSeek/GPT-4)
                                                                   │
                                                               Response
                                                                   │
                                                          [Cache Response]
                                                                   │
                                                            Return to User
```

---

## 2. Architecture Cible (Microservices KAURI)

### 2.1 Vue d'Ensemble Écosystème KAURI

```
                        ┌──────────────────────────────────┐
                        │      KAURI PLATFORM              │
                        │   (25 Microservices)             │
                        └──────────────────┬───────────────┘
                                           │
                ┌──────────────────────────┼──────────────────────────┐
                │                          │                          │
        ┌───────▼────────┐        ┌───────▼────────┐        ┌───────▼────────┐
        │  Auth Service  │        │  User Service  │        │Accounting Core │
        │                │        │                │        │    Service     │
        │ • Login/Logout │        │ • User CRUD    │        │ • Écritures    │
        │ • JWT/OAuth2   │        │ • Organizations│        │ • Grand Livre  │
        │ • 2FA          │        │ • Profiles     │        │ • Balances     │
        └────────────────┘        └────────────────┘        └────────────────┘
                │                          │                          │
                │                          │                          │
        ┌───────▼────────┐        ┌───────▼────────┐        ┌───────▼────────┐
        │Document Service│        │ Invoice Service│        │  Bank Service  │
        │                │        │                │        │                │
        │ • GED          │        │ • Devis        │        │ • Agrégation   │
        │ • Versioning   │        │ • Facturation  │        │ • Rapprochement│
        │ • Search       │        │ • Relances     │        │ • Multi-banques│
        └────────────────┘        └────────────────┘        └────────────────┘
                │                          │                          │
                └──────────────────────────┼──────────────────────────┘
                                           │
                                  ┌────────▼────────┐
                                  │  CHATBOT SYSTEM │
                                  │  (3 Services)   │
                                  └─────────────────┘
```

### 2.2 Architecture Détaillée Chatbot (3 Microservices)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          API GATEWAY (KONG)                              │
│  • Routing • Rate Limiting • Auth • Load Balancing • SSL Termination   │
└────────────────────────────┬────────────────────────────────────────────┘
                             │
                             │ HTTPS
                             │
            ┌────────────────┼────────────────────┐
            │                │                    │
            ▼                ▼                    ▼
┌────────────────────┐ ┌────────────────┐ ┌─────────────────────┐
│  Chatbot API       │ │  RAG Engine    │ │ Knowledge Base      │
│  Service           │ │  Service       │ │ Service             │
│                    │ │                │ │                     │
│ PORT: 8001         │ │ PORT: 8002     │ │ PORT: 8003          │
│ REPLICAS: 3-10     │ │ REPLICAS: 2-5  │ │ REPLICAS: 1-3       │
│                    │ │                │ │                     │
│ RESPONSIBILITIES:  │ │ RESPONSIBILITIES│ │ RESPONSIBILITIES:   │
│ • REST API         │ │ • Embeddings   │ │ • Document Ingest   │
│ • SSE Streaming    │ │ • Hybrid Search│ │ • Parsing           │
│ • Validation       │ │ • BM25         │ │ • Chunking          │
│ • Orchestration    │ │ • Vector Search│ │ • Metadata          │
│ • Rate Limiting    │ │ • Reranking    │ │ • Versioning        │
│ • Conv Management  │ │ • LLM Calls    │ │ • Corpus Sync       │
│                    │ │ • Cache Mgmt   │ │                     │
│ TECH:              │ │                │ │ TECH:               │
│ • FastAPI          │ │ TECH:          │ │ • FastAPI           │
│ • PostgreSQL       │ │ • FastAPI/gRPC │ │ • PostgreSQL        │
│ • Redis            │ │ • BGE-M3       │ │ • Celery            │
│                    │ │ • Cross-Encoder│ │ • S3/MinIO          │
│ API:               │ │ • DeepSeek API │ │ • Pinecone          │
│ POST /v1/chat/query│ │ • Redis Cluster│ │                     │
│ GET  /v1/chat/     │ │ • Pinecone     │ │ API:                │
│      stream        │ │                │ │ POST /v1/knowledge/ │
│ GET  /v1/chat/     │ │ API (gRPC):    │ │      documents      │
│      conversations │ │ rpc Search()   │ │ POST /v1/knowledge/ │
│ GET  /v1/health    │ │ rpc Generate() │ │      batch          │
│ GET  /v1/metrics   │ │ rpc Embed()    │ │ GET  /v1/knowledge/ │
│                    │ │                │ │      stats          │
└──────────┬─────────┘ └────────┬───────┘ └──────────┬──────────┘
           │                    │                    │
           │ REST/gRPC          │ gRPC               │ REST
           └────────────────────┼────────────────────┘
                                │
               ┌────────────────┼────────────────┐
               │                │                │
               ▼                ▼                ▼
     ┌──────────────────┐ ┌──────────────┐ ┌──────────────┐
     │  PostgreSQL      │ │ Pinecone     │ │Redis Cluster │
     │  (RDS Multi-AZ)  │ │ (Managed)    │ │(ElastiCache) │
     │                  │ │              │ │              │
     │ • Conversations  │ │ • Embeddings │ │ • Query Cache│
     │ • Messages       │ │ • 7 Namespaces│ │ • Embed Cache│
     │ • Users          │ │ • 1024 dims  │ │ • Sessions   │
     │ • Documents Meta │ │ • Cosine     │ │ • Celery Broker│
     └──────────────────┘ └──────────────┘ └──────────────┘
               │                │                │
               └────────────────┼────────────────┘
                                │
                         ┌──────▼──────┐
                         │   Kafka     │
                         │ (Event Bus) │
                         │             │
                         │ TOPICS:     │
                         │ • chatbot.* │
                         │ • knowledge.│
                         │ • user.*    │
                         └─────────────┘
```

### 2.3 Flux de Traitement dans Architecture Microservices

```
┌─────────┐
│  User   │
└────┬────┘
     │ HTTPS
     ▼
┌──────────────────────┐
│   API Gateway        │
│   (Kong)             │
│ • Auth Check         │
│ • Rate Limit         │
│ • Route to Service   │
└───────┬──────────────┘
        │
        ▼
┌───────────────────────┐
│ Chatbot API Service   │
│                       │
│ 1. Validate Input     │
│ 2. Check Cache (Redis)│──► Cache Hit? → Return Cached Response
│ 3. Publish Event:     │
│    "query.received"   │
└───────┬───────────────┘
        │ gRPC
        ▼
┌────────────────────────┐
│  RAG Engine Service    │
│                        │
│ 1. Intent Classify     │
│ 2. Query Reformulate   │
│ 3. Generate Embedding  │
│ 4. Hybrid Search:      │
│    ┌─────────┐         │
│    │  BM25   │         │
│    └────┬────┘         │
│    ┌────▼─────┐        │
│    │ Vector   │        │
│    │ (Pinecone│        │
│    └────┬─────┘        │
│    ┌────▼─────┐        │
│    │ Rerank   │        │
│    └────┬─────┘        │
│ 5. LLM Generate        │
│    (DeepSeek)          │
└────────┬───────────────┘
         │ Response
         ▼
┌────────────────────────┐
│ Chatbot API Service    │
│                        │
│ 1. Save to DB          │
│ 2. Cache Response      │
│ 3. Publish Event:      │
│    "query.completed"   │
│ 4. Stream to User (SSE)│
└────────┬───────────────┘
         │
         ▼
┌─────────────────┐
│   Event Bus     │
│   (Kafka)       │
│                 │
│ • Analytics     │
│ • Audit Log     │
│ • Notification  │
└─────────────────┘
```

---

## 3. Comparaison Architecture

### 3.1 Scalabilité

#### Architecture Actuelle (Monolithe)
```
                    ┌─────────────┐
                    │   Backend   │
                    │  (All-in-1) │
                    │             │
   Load ────────►   │  CPU 100%   │   ◄── Bottleneck
                    │  Memory 90% │
                    └─────────────┘
                          ↑
                    Scale vertically
                    (larger instance)
```

#### Architecture Cible (Microservices)
```
                    ┌────────────┐
   Light Load  ──►  │ Chatbot API│ ◄── Scales to 10 replicas
                    │  (3 pods)  │
                    └────────────┘
                    
                    ┌────────────┐
   Heavy Load  ──►  │ RAG Engine │ ◄── Scales to 5 replicas
                    │  (5 pods)  │     (CPU-intensive)
                    └────────────┘
                    
                    ┌────────────┐
   Low Load    ──►  │ Knowledge  │ ◄── Scales to 2 replicas
                    │  (2 pods)  │     (mostly idle)
                    └────────────┘
```

### 3.2 Résilience

#### Architecture Actuelle
```
┌──────────────────────────────┐
│      Backend Monolithe       │
│                              │
│  ┌──────┐                    │
│  │ Bug  │ ───► CRASH         │
│  └──────┘                    │
│                              │
│  Entire System DOWN ❌       │
└──────────────────────────────┘
```

#### Architecture Cible
```
┌────────────┐  ┌────────────┐  ┌────────────┐
│ Chatbot API│  │ RAG Engine │  │ Knowledge  │
│            │  │            │  │            │
│  ┌──────┐  │  │            │  │            │
│  │ Bug  │  │  │            │  │            │
│  └───┬──┘  │  │            │  │            │
│      │     │  │            │  │            │
│  Pod DOWN   │  │   OK ✅    │  │   OK ✅    │
│      │     │  │            │  │            │
│  Auto-heal  │  │            │  │            │
│  (K8s)      │  │            │  │            │
│      │     │  │            │  │            │
│   Back UP   │  │            │  │            │
└────────────┘  └────────────┘  └────────────┘

Partial degradation instead of total failure
```

---

## 4. Architecture des Données

### 4.1 Distribution des Données

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│   PostgreSQL         │  │   Pinecone           │  │   Redis Cluster      │
│   (Structured Data)  │  │   (Vector Data)      │  │   (Cache/Session)    │
│                      │  │                      │  │                      │
│ DATABASE: kauri      │  │ INDEX: kauri-ohada   │  │ CLUSTER: 3 nodes     │
│                      │  │                      │  │                      │
│ TABLES:              │  │ NAMESPACES:          │  │ DATABASES:           │
│ • users              │  │ • syscohada_revise   │  │ • db0: queries       │
│ • conversations      │  │ • syscoa              │  │ • db1: embeddings    │
│ • messages           │  │ • guide_tresor        │  │ • db2: sessions      │
│ • documents          │  │ • dgi_fiches          │  │ • db3: celery        │
│ • document_versions  │  │ • jurisprudence       │  │                      │
│ • document_embeddings│  │ • doctrine            │  │ KEYS:                │
│                      │  │ • references          │  │ • query:{hash}       │
│ REPLICAS:            │  │                      │  │ • embed:{text_hash}  │
│ • Primary (write)    │  │ DIMENSIONS: 1024     │  │ • session:{user_id}  │
│ • 2x Standby (read)  │  │ METRIC: cosine       │  │ • celery-task:{id}   │
│                      │  │ PODS: p1 (standard)  │  │                      │
│ BACKUP:              │  │                      │  │ PERSISTENCE:         │
│ • Daily snapshots    │  │ BACKUP:              │  │ • AOF + RDB          │
│ • Point-in-time      │  │ • Auto backups       │  │ • Daily backups      │
│   recovery (PITR)    │  │ • Collections export │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                          ┌─────────▼────────┐
                          │  S3 / MinIO      │
                          │  (Object Storage)│
                          │                  │
                          │ BUCKETS:         │
                          │ • kauri-documents│
                          │ • kauri-backups  │
                          │ • kauri-exports  │
                          │                  │
                          │ VERSIONING: ✅   │
                          │ LIFECYCLE: 90d   │
                          └──────────────────┘
```

### 4.2 Flux de Données Document

```
┌──────────┐
│  Upload  │
│  (.docx) │
└────┬─────┘
     │
     ▼
┌────────────────────────┐
│ Knowledge Base Service │
│                        │
│ 1. Save to S3          │──────►  ┌──────────┐
│    (raw document)      │         │   S3     │
│                        │         │ /documents│
│ 2. Parse document      │         └──────────┘
│    (extract text)      │
│                        │
│ 3. Chunk text          │
│    (500 tokens/chunk)  │
│                        │
│ 4. Save metadata       │──────►  ┌──────────────┐
│    (PostgreSQL)        │         │ PostgreSQL   │
│    • title             │         │ • documents  │
│    • author            │         │ • versions   │
│    • hierarchy         │         └──────────────┘
└───────┬────────────────┘
        │
        │ Async Task (Celery)
        ▼
┌────────────────────────┐
│  RAG Engine Service    │
│                        │
│ 5. Generate embeddings │
│    (BGE-M3)            │
│    • Batch of 10 chunks│
│    • 1024 dimensions   │
│                        │
│ 6. Upsert to Pinecone  │──────►  ┌──────────────┐
│    (with metadata)     │         │  Pinecone    │
│    • id: doc_chunk_id  │         │  Vector DB   │
│    • vector: [1024]    │         │              │
│    • metadata: {...}   │         │ • Indexed    │
│                        │         │ • Searchable │
│ 7. Cache embeddings    │──────►  └──────────────┘
│    (Redis)             │               ▲
└────────────────────────┘               │
                                         │
                                    ┌────┴─────┐
                                    │  Redis   │
                                    │  Cache   │
                                    └──────────┘
```

---

## 5. Communication Inter-Services

### 5.1 Patterns de Communication

```
┌──────────────────────────────────────────────────────────────┐
│              SYNCHRONOUS (Request-Response)                   │
│                                                               │
│  Chatbot API ────REST───► Auth Service                       │
│               ◄──────────                                     │
│                                                               │
│  Chatbot API ────gRPC───► RAG Engine                         │
│               ◄──────────  (faster than REST)                │
│                                                               │
│  RAG Engine  ────gRPC───► Knowledge Base                     │
│               ◄──────────                                     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│              ASYNCHRONOUS (Event-Driven)                      │
│                                                               │
│  Chatbot API ────publish──► Kafka Topic                      │
│                              "chatbot.query.received"         │
│                                   │                           │
│                                   ├──► Analytics Service      │
│                                   ├──► Audit Log Service      │
│                                   └──► Notification Service   │
│                                                               │
│  Knowledge   ────publish──► Kafka Topic                      │
│   Base                           "knowledge.document.added"   │
│                                   │                           │
│                                   ├──► RAG Engine (reindex)   │
│                                   ├──► Search Service         │
│                                   └──► Audit Log              │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Circuit Breaker Pattern

```
Chatbot API ──request──► RAG Engine
                              │
                         [Health Check]
                              │
                    ┌─────────┴─────────┐
                    │                   │
                HEALTHY              UNHEALTHY
                    │                   │
                    │                   ▼
                    │            ┌──────────────┐
                    │            │ Circuit Open │
                    │            │ (5 failures) │
                    │            └──────┬───────┘
                    │                   │
                    │           Return Cached Response
                    │           or Fallback
                    │                   │
                    │            [Wait 30s]
                    │                   │
                    │            ┌──────▼────────┐
                    │            │Circuit Half-Open│
                    │            │(test 1 request)│
                    │            └──────┬──────────┘
                    │                   │
                    │           ┌───────┴────────┐
                    │           │                │
                    │       SUCCESS           FAILURE
                    │           │                │
                    └───────────┘                │
                              │                  │
                       ┌──────▼──────┐    ┌─────▼──────┐
                       │Circuit Closed│   │Circuit Open│
                       │(normal mode) │   │(retry later)│
                       └─────────────┘    └────────────┘
```

---

## 6. Déploiement Kubernetes

### 6.1 Cluster Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                            │
│                    (AWS EKS / GCP GKE / Azure AKS)              │
└─────────────────────────────────────────────────────────────────┘

                      ┌──────────────────┐
                      │   Ingress        │
                      │   Controller     │
                      │   (NGINX/Traefik)│
                      └────────┬─────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
┌────────────────────┐ ┌────────────────┐ ┌────────────────┐
│  NAMESPACE:        │ │  NAMESPACE:    │ │  NAMESPACE:    │
│  kauri-chatbot     │ │  kauri-data    │ │  kauri-infra   │
│                    │ │                │ │                │
│ ┌────────────────┐ │ │ ┌────────────┐ │ │ ┌────────────┐ │
│ │ Deployment     │ │ │ │StatefulSet │ │ │ │ Prometheus │ │
│ │ chatbot-api    │ │ │ │ redis      │ │ │ │            │ │
│ │ replicas: 3    │ │ │ │ replicas: 3│ │ │ └────────────┘ │
│ └────────────────┘ │ │ └────────────┘ │ │                │
│                    │ │                │ │ ┌────────────┐ │
│ ┌────────────────┐ │ │ ┌────────────┐ │ │ │  Grafana   │ │
│ │ Deployment     │ │ │ │StatefulSet │ │ │ │            │ │
│ │ rag-engine     │ │ │ │ postgres   │ │ │ └────────────┘ │
│ │ replicas: 2    │ │ │ │ replicas: 3│ │ │                │
│ └────────────────┘ │ │ └────────────┘ │ │ ┌────────────┐ │
│                    │ │                │ │ │   Jaeger   │ │
│ ┌────────────────┐ │ │ ┌────────────┐ │ │ │            │ │
│ │ Deployment     │ │ │ │ Service    │ │ │ └────────────┘ │
│ │ knowledge-base │ │ │ │ kafka      │ │ │                │
│ │ replicas: 1    │ │ │ │            │ │ │ ┌────────────┐ │
│ └────────────────┘ │ │ └────────────┘ │ │ │ELK Stack   │ │
│                    │ │                │ │ │            │ │
│ ┌────────────────┐ │ │                │ │ └────────────┘ │
│ │ HPA            │ │ │                │ │                │
│ │ • min: 2       │ │ │                │ │                │
│ │ • max: 10      │ │ │                │ │                │
│ │ • CPU: 80%     │ │ │                │ │                │
│ └────────────────┘ │ │                │ │                │
└────────────────────┘ └────────────────┘ └────────────────┘
```

### 6.2 Pod Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    POD: chatbot-api-xyz                  │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │      CONTAINER: chatbot-api                    │    │
│  │                                                 │    │
│  │  Image: kauri/chatbot-api:1.0.0               │    │
│  │  Port: 8001                                    │    │
│  │                                                 │    │
│  │  Resources:                                    │    │
│  │  • Requests: CPU 500m, Memory 1Gi              │    │
│  │  • Limits:   CPU 1000m, Memory 2Gi             │    │
│  │                                                 │    │
│  │  Env Variables:                                │    │
│  │  • DATABASE_URL (from Secret)                  │    │
│  │  • REDIS_URL (from ConfigMap)                  │    │
│  │  • LOG_LEVEL=info                              │    │
│  │                                                 │    │
│  │  Volume Mounts:                                │    │
│  │  • /app/config → config-volume                 │    │
│  │  • /tmp        → emptyDir                      │    │
│  │                                                 │    │
│  │  Probes:                                       │    │
│  │  • Liveness:  GET /health (every 10s)          │    │
│  │  • Readiness: GET /health (every 5s)           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │      SIDECAR: log-forwarder                    │    │
│  │                                                 │    │
│  │  Image: fluentbit:latest                       │    │
│  │  • Forward logs to Elasticsearch               │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │      SIDECAR: metrics-exporter                 │    │
│  │                                                 │    │
│  │  Image: prom/statsd-exporter                   │    │
│  │  • Export metrics to Prometheus                │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

## 7. Observabilité

### 7.1 Métriques (Prometheus + Grafana)

```
┌─────────────────────────────────────────────────────────────┐
│                    GRAFANA DASHBOARD                         │
│                "KAURI Chatbot Overview"                      │
└─────────────────────────────────────────────────────────────┘

┌───────────────────────┐  ┌───────────────────────┐
│   Request Rate        │  │   Latency (p50/p95)   │
│                       │  │                       │
│   ▲ 150 req/s         │  │   p50: 1.2s          │
│   │                   │  │   p95: 2.8s          │
│   │     ████          │  │   p99: 4.5s          │
│   │   ██████          │  │                       │
│   └─────────────►     │  └───────────────────────┘
└───────────────────────┘

┌───────────────────────┐  ┌───────────────────────┐
│   Error Rate          │  │   Cache Hit Rate      │
│                       │  │                       │
│   0.8% (target <2%)   │  │   92% (target >90%)   │
│   ✅ HEALTHY          │  │   ✅ HEALTHY          │
└───────────────────────┘  └───────────────────────┘

┌───────────────────────────────────────────────────────────┐
│   Service Health                                          │
│                                                           │
│   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│   │ Chatbot API  │   │  RAG Engine  │   │ Knowledge   │ │
│   │  ✅ 3/3 UP   │   │  ✅ 2/2 UP   │   │  ✅ 1/1 UP  │ │
│   └──────────────┘   └──────────────┘   └─────────────┘ │
│                                                           │
│   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│   │ PostgreSQL   │   │  Pinecone    │   │   Redis     │ │
│   │  ✅ UP       │   │  ✅ UP       │   │  ✅ UP      │ │
│   └──────────────┘   └──────────────┘   └─────────────┘ │
└───────────────────────────────────────────────────────────┘
```

### 7.2 Distributed Tracing (Jaeger)

```
Trace ID: 7f3a8b2c9d1e4f5g

┌────────────────────────────────────────────────────────────┐
│  User Request                                               │
│  POST /v1/chat/query                                        │
│  Duration: 2.4s                                             │
└────────────────────────────────────────────────────────────┘

    ├─► API Gateway (50ms)
    │   └─► Rate Limit Check (5ms)
    │   └─► Auth Validation (10ms)
    │
    ├─► Chatbot API Service (2200ms)
    │   ├─► Cache Check (2ms) ─► Miss
    │   │
    │   ├─► RAG Engine Service (2100ms) ◄──┐
    │   │   ├─► Intent Classification (300ms) LLM Call
    │   │   ├─► Query Reformulation (200ms)  LLM Call
    │   │   ├─► Generate Embedding (50ms)    Local Model
    │   │   ├─► Hybrid Search (800ms)
    │   │   │   ├─► BM25 Search (100ms)
    │   │   │   ├─► Vector Search (400ms) ◄─ Pinecone
    │   │   │   └─► Reranking (300ms)       Local Model
    │   │   └─► LLM Generation (750ms)       DeepSeek API
    │   │
    │   ├─► Save to DB (80ms) ◄─ PostgreSQL
    │   ├─► Cache Response (5ms) ◄─ Redis
    │   └─► Publish Event (10ms) ◄─ Kafka
    │
    └─► Response to User (100ms)
        └─► SSE Stream
```

---

## 8. Sécurité

### 8.1 Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│                       SECURITY LAYERS                        │
└─────────────────────────────────────────────────────────────┘

Layer 1: Network
┌────────────────────────────────────────┐
│  • WAF (Web Application Firewall)      │
│  • DDoS Protection (CloudFlare)        │
│  • TLS 1.3 (SSL Termination)           │
│  • Firewall Rules (Security Groups)    │
└────────────────────────────────────────┘
                  │
Layer 2: API Gateway
┌────────────────────────────────────────┐
│  • Rate Limiting (100 req/min/IP)      │
│  • IP Whitelist/Blacklist              │
│  • Request Validation                  │
│  • JWT Verification                    │
└────────────────────────────────────────┘
                  │
Layer 3: Application
┌────────────────────────────────────────┐
│  • Input Sanitization                  │
│  • Output Encoding                     │
│  • CSRF Protection                     │
│  • XSS Prevention                      │
│  • SQL Injection Prevention            │
│  • Authentication (JWT)                │
│  • Authorization (RBAC)                │
└────────────────────────────────────────┘
                  │
Layer 4: Data
┌────────────────────────────────────────┐
│  • Encryption at Rest (AES-256)        │
│  • Encryption in Transit (TLS)         │
│  • Secrets Management (Vault)          │
│  • Data Masking (PII)                  │
│  • Audit Logging                       │
└────────────────────────────────────────┘
                  │
Layer 5: Infrastructure
┌────────────────────────────────────────┐
│  • Container Security (Scanning)       │
│  • Least Privilege (IAM Roles)         │
│  • Network Segmentation (VPC)          │
│  • Backup & Disaster Recovery          │
│  • Security Monitoring (SIEM)          │
└────────────────────────────────────────┘
```

---

## 9. CI/CD Pipeline

```
┌──────────┐
│   Dev    │
│ Push Code│
└────┬─────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                  GITHUB ACTIONS                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  1. Lint & Format│
│  • Black         │
│  • Flake8        │
│  • mypy          │
└────────┬────────┘
         │ ✅ Pass
         ▼
┌─────────────────┐
│  2. Unit Tests   │
│  • pytest        │
│  • coverage >80% │
└────────┬────────┘
         │ ✅ Pass
         ▼
┌─────────────────┐
│ 3. Build Image   │
│  • Docker build  │
│  • Tag: git-sha  │
└────────┬────────┘
         │ ✅ Success
         ▼
┌─────────────────┐
│ 4. Security Scan │
│  • Trivy         │
│  • Snyk          │
└────────┬────────┘
         │ ✅ No Critical
         ▼
┌─────────────────┐
│ 5. Push to ECR   │
│  • Tag latest    │
│  • Tag version   │
└────────┬────────┘
         │ ✅ Pushed
         ▼
┌─────────────────────────────────────────┐
│  6. Deploy to Staging                   │
│  • Update Helm values                   │
│  • kubectl apply                        │
│  • Wait for rollout                     │
└────────┬────────────────────────────────┘
         │ ✅ Deployed
         ▼
┌─────────────────────────────────────────┐
│  7. Integration Tests                   │
│  • API Tests                            │
│  • End-to-End Tests                     │
└────────┬────────────────────────────────┘
         │ ✅ Pass
         ▼
┌─────────────────────────────────────────┐
│  8. Manual Approval (Production)        │
│  • Review changes                       │
│  • Approve deployment                   │
└────────┬────────────────────────────────┘
         │ ✅ Approved
         ▼
┌─────────────────────────────────────────┐
│  9. Deploy to Production (Blue/Green)   │
│  • Deploy to Blue environment           │
│  • Run smoke tests                      │
│  • Canary (10% traffic)                 │
│  • Monitor metrics                      │
│  • Gradually increase to 100%           │
└────────┬────────────────────────────────┘
         │ ✅ Success
         ▼
┌─────────────────────────────────────────┐
│  10. Cleanup                            │
│  • Remove old images                    │
│  • Update docs                          │
│  • Notify team                          │
└─────────────────────────────────────────┘
```

---

## 10. Conclusion

Cette architecture microservices offre:

- **Scalabilité**: Chaque service scale indépendamment
- **Résilience**: Isolation des pannes
- **Performance**: Optimisations par service
- **Maintenabilité**: Code modulaire et testable
- **Observabilité**: Monitoring complet
- **Sécurité**: Defense in depth
- **Évolutivité**: Facile d'ajouter de nouveaux services

**Migration estimée**: 12 semaines  
**Coûts infrastructure**: ~$430/mois  
**Gains attendus**: +100x scalabilité, 99.9% disponibilité
