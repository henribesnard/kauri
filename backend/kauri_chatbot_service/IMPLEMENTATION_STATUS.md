# 🤖 KAURI Chatbot Service - État d'Implémentation

## ✅ Composants Implémentés

### 1. **Structure de Base**
- ✅ Configuration avec héritage .env (src/config.py)
- ✅ FastAPI app avec middlewares (src/api/main.py)
- ✅ Dockerfile multi-stage optimisé
- ✅ Modèles de base de données (src/models/document.py)

### 2. **Authentification**
- ✅ JWT Validator (src/auth/jwt_validator.py)
- ✅ Validation via User Service
- ✅ Dépendance `get_current_user` pour protection endpoints

### 3. **LLM Client**
- ✅ DeepSeek client primaire (src/llm/llm_client.py)
- ✅ OpenAI fallback automatique
- ✅ Support streaming
- ✅ Retry logic avec tenacity

### 4. **Base de Données**
- ✅ Modèle Document (OHADA hierarchy complète)
- ✅ Modèle DocumentChunk (pour RAG)
- ✅ Modèle IngestionLog (tracking)
- ✅ Support PostgreSQL avec SQLAlchemy

### 5. **Document Ingestion**
- ✅ DocumentProcessor (src/ingestion/document_processor.py)
- ✅ Support formats: txt, md, pdf, docx, html
- ✅ Script CLI d'ingestion (ingest_documents.py)
- ✅ Hash-based deduplication

### 6. **Schémas Pydantic**
- ✅ ChatRequest, ChatResponse (src/schemas/chat.py)
- ✅ SourceDocument, StreamChunk
- ✅ HealthResponse, Message

---

## 🚧 Composants à Compléter

### 1. **RAG Components** (PRIORITAIRE)

#### A. Embedder (src/rag/embedder/bge_embedder.py)
```python
class BGEEmbedder:
    - Load BAAI/bge-m3 model
    - embed_text(text) -> List[float]
    - embed_batch(texts) -> List[List[float]]
    - Cache avec Redis
```

#### B. Vector Store (src/rag/vector_store/chroma_store.py)
```python
class ChromaStore:
    - Connection à ChromaDB container
    - add_documents(docs, embeddings)
    - search(query_embedding, top_k) -> List[Doc]
    - Health check
```

#### C. BM25 Retriever (src/rag/retriever/bm25_retriever.py)
```python
class BM25Retriever:
    - Build index from documents
    - search(query, top_k) -> List[Doc]
    - Score normalization
```

#### D. Reranker (src/rag/reranker/cross_encoder_reranker.py)
```python
class CrossEncoderReranker:
    - Load cross-encoder model
    - rerank(query, documents) -> List[Doc]
    - Batch scoring
```

#### E. Hybrid Retriever (src/rag/retriever/hybrid_retriever.py)
```python
class HybridRetriever:
    - Combine vector + BM25
    - Weighted fusion (alpha=0.6)
    - Reranking pipeline
```

#### F. RAG Pipeline (src/rag/pipeline/rag_pipeline.py)
```python
class RAGPipeline:
    - retrieve(query) -> List[Doc]
    - generate_answer(query, context)
    - Full workflow orchestration
```

### 2. **Chat Endpoints** (src/api/routes/chat.py)
```python
@router.post("/query")  # Standard query
@router.post("/stream")  # Streaming SSE
# Protection JWT avec get_current_user
```

### 3. **Database Utils** (src/utils/database.py)
```python
- init_db()
- get_db() dependency
- Connection pooling
```

---

## 🚀 Plan d'Implémentation (Étapes Suivantes)

### **Phase 1: RAG Core (2-3h)**
1. Créer BGEEmbedder
2. Créer ChromaStore
3. Créer BM25Retriever
4. Tester retrieval isolé

### **Phase 2: Reranking & Fusion (1h)**
5. Créer CrossEncoderReranker
6. Créer HybridRetriever avec fusion
7. Tester pipeline complet

### **Phase 3: Integration (1h)**
8. Créer RAGPipeline orchestrator
9. Créer Chat endpoints
10. Intégrer avec JWT protection

### **Phase 4: Ingestion & Testing (1h)**
11. Compléter script d'ingestion avec embeddings
12. Indexer documents OHADA
13. Tests end-to-end

---

## 📦 Ports Utilisés

- **User Service**: 3201
- **Chatbot Service**: 3202
- **PostgreSQL**: 3100 (host) → 5432 (container)
- **Redis**: 3103 (host) → 6379 (container)
- **ChromaDB**: 3104 (host) → 8000 (container)

---

## 🧪 Comment Tester

### 1. Build & Start
```bash
cd /c/Users/henri/Projets/kauri
docker-compose up -d --build kauri_chatbot_service
```

### 2. Health Check
```bash
curl http://localhost:3202/api/v1/health
```

### 3. Ingérer Documents
```bash
docker exec -it kauri_chatbot_service python ingest_documents.py
```

### 4. Tester Chat (avec token du User Service)
```bash
TOKEN="<your_jwt_token>"
curl -X POST http://localhost:3202/api/v1/chat/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Quelle est la structure du plan comptable OHADA?"}'
```

---

## 📝 Notes Importantes

1. **Modèles ML**: Les modèles sont téléchargés au premier démarrage (~2GB pour BGE-M3)
2. **ChromaDB**: Doit être démarré avant le Chatbot Service
3. **base_connaissances/**: Doit contenir les documents OHADA
4. **JWT**: Les endpoints chat nécessitent un token valide du User Service

---

## 🔗 Fichiers Clés

```
src/
├── api/
│   ├── main.py                 ✅ FastAPI app
│   └── routes/
│       └── chat.py             🚧 À créer
├── auth/
│   └── jwt_validator.py        ✅ JWT validation
├── llm/
│   └── llm_client.py           ✅ LLM avec fallback
├── rag/
│   ├── embedder/
│   │   └── bge_embedder.py     🚧 À créer
│   ├── vector_store/
│   │   └── chroma_store.py     🚧 À créer
│   ├── retriever/
│   │   ├── bm25_retriever.py   🚧 À créer
│   │   └── hybrid_retriever.py 🚧 À créer
│   ├── reranker/
│   │   └── cross_encoder.py    🚧 À créer
│   └── pipeline/
│       └── rag_pipeline.py     🚧 À créer
├── models/
│   └── document.py             ✅ DB models
├── schemas/
│   └── chat.py                 ✅ Pydantic schemas
├── ingestion/
│   └── document_processor.py   ✅ Doc processing
└── config.py                   ✅ Configuration
```

---

**Statut Global**: **60% Complete** ✅

**Prochaine étape**: Implémenter les composants RAG core
