# 📚 Documentation Technique Complète - KAURI Chatbot Service

**Version:** 2.1.0
**Date:** 08/11/2025
**Service:** kauri_chatbot_service
**Port:** 3202

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#vue-densemble)
2. [Architecture Générale](#architecture-générale)
3. [Pipeline RAG Conversationnel](#pipeline-rag-conversationnel)
4. [Workflow LangGraph](#workflow-langgraph)
5. [Classification d'Intent](#classification-dintent)
6. [Retrieval Hybride](#retrieval-hybride)
7. [Métadonnées Enrichies](#métadonnées-enrichies)
8. [Endpoints API](#endpoints-api)
9. [Configuration](#configuration)
10. [Base de Données](#base-de-données)
11. [Flux de Données](#flux-de-données)
12. [Fichiers Clés](#fichiers-clés)

---

## 🎯 Vue d'Ensemble

### Objectif

KAURI Chatbot Service est un système RAG (Retrieval-Augmented Generation) conversationnel spécialisé en **droit et comptabilité OHADA**. Il permet aux juristes et comptables d'interroger une base documentaire structurée (Actes Uniformes, Plan Comptable, Jurisprudences, Doctrines) via une interface conversationnelle intelligente.

### Spécificités OHADA

- **Domaine juridique** : Droit des affaires harmonisé (17 États membres)
- **Domaine comptable** : SYSCOHADA (Système Comptable OHADA)
- **Types de documents** : Actes Uniformes, Plan Comptable, Jurisprudences CCJA, Doctrines
- **Références précises** : Articles, Comptes, Chapitres, Juridictions

### Fonctionnalités Principales

1. **RAG Conversationnel** : Réponses basées sur documents avec historique
2. **Classification d'Intent Intelligente** : 6 types d'intentions détectées
3. **Retrieval Hybride** : Vector Search + BM25 + Cross-Encoder Reranking
4. **Recherches Spécialisées** : Par référence (Article X), par juridiction (CCJA), par type de document
5. **Métadonnées Enrichies** : Category, Section, File Path pour chaque source
6. **Mode Streaming** : Réponses progressives via Server-Sent Events (SSE)
7. **Persistance Conversations** : Historique sauvegardé en base PostgreSQL

---

## 🏗️ Architecture Générale

### Stack Technologique

```
┌─────────────────────────────────────────────────────────────┐
│                    KAURI CHATBOT SERVICE                    │
│                     (FastAPI - Python 3.11)                 │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
        ┌───────▼──────┐ ┌───▼────┐ ┌─────▼──────┐
        │   ChromaDB   │ │ DeepSeek│ │ PostgreSQL │
        │  (Vectors)   │ │  (LLM)  │ │(Convs/Msgs)│
        └──────────────┘ └─────────┘ └────────────┘
```

**Composants Externes :**
- **ChromaDB** (port 8000) : Base vectorielle pour embeddings + métadonnées
- **DeepSeek API** : LLM principal (deepseek-chat) via OpenRouter
- **PostgreSQL** (via kauri_user_service) : Stockage conversations et messages
- **User Service** (port 3201) : Authentification JWT

**Modèles ML :**
- **Embeddings** : `BAAI/bge-m3` (multilingual, 1024 dimensions)
- **Reranking** : `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **LLM Principal** : `deepseek/deepseek-chat` (via OpenRouter)
- **LLM Fallback** : `openai/gpt-4o-mini`

---

## 🔄 Pipeline RAG Conversationnel

### Architecture en 3 Couches

```
┌──────────────────────────────────────────────────────────────┐
│                    1. API LAYER (FastAPI)                    │
│  ┌─────────────────┐              ┌─────────────────┐       │
│  │  /chat/query    │              │  /chat/stream   │       │
│  │  (non-stream)   │              │  (SSE stream)   │       │
│  └────────┬────────┘              └────────┬────────┘       │
└───────────┼──────────────────────────────┼──────────────────┘
            │                              │
┌───────────▼──────────────────────────────▼──────────────────┐
│            2. CONVERSATION LAYER                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │        ConversationAwareRAG                      │       │
│  │  - Récupère historique conversation             │       │
│  │  - Augmente query avec contexte                 │       │
│  │  - Sauvegarde messages (user + assistant)       │       │
│  │  - Auto-génère titre conversation               │       │
│  └─────────────────────┬────────────────────────────┘       │
└────────────────────────┼─────────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────────┐
│            3. RAG PIPELINE LAYER                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │              RAGWorkflow (LangGraph)             │       │
│  │                                                  │       │
│  │  Node 1: classify_intent                        │       │
│  │         ↓                                        │       │
│  │  Node 2: routing (6 types)                      │       │
│  │         ↓                                        │       │
│  │  Nodes 3-8: Spécialisés par intent              │       │
│  │    - general_conversation                       │       │
│  │    - rag_query                                  │       │
│  │    - clarification                              │       │
│  │    - document_sourcing                          │       │
│  │    - legal_reference_search                     │       │
│  │    - case_law_research                          │       │
│  │         ↓                                        │       │
│  │  Node Final: Format response                    │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### Fichiers Clés

| Fichier | Rôle |
|---------|------|
| `src/api/routes/chat.py` | API endpoints (query, stream, health) |
| `src/rag/pipeline/conversation_aware_rag.py` | Couche conversationnelle + persistence |
| `src/rag/pipeline/rag_pipeline.py` | Pipeline RAG de base (retrieval + generation) |
| `src/rag/agents/rag_workflow.py` | Workflow LangGraph (classification + routing) |

### Gestion robuste des sources (2025-11-10)

- Chaque message assistant sauvegarde désormais les sources **enrichies** (titre, score, catégorie, `file_path`,
  résumé de métadonnées). Ces objets JSON restent disponibles pour les conversations suivantes.
- Le `ContextManager` maintient un buffer FIFO de références dédupliquées (`get_recent_sources`) par conversation :
  on peut réutiliser automatiquement jusqu’à 5 sources récentes sans solliciter à nouveau Chroma si elles couvrent déjà
  la question de suivi.
- Dans le workflow RAG, un retrieval hybride est toujours exécuté. Lorsque moins de `RAG_MIN_DOCUMENTS` (3) documents
  pertinents sont trouvés, les sources sont complétées avec celles du buffer afin de garantir qu’au moins trois
  références soient renvoyées au frontend.
- Le buffer limite aussi la pollution du contexte : seules les références utiles sont conservées et envoyées au LLM,
  ce qui évite de saturer rapidement les 8 000 tokens réservés au contexte conversationnel.

---

## 🧠 Workflow LangGraph

### Architecture du Workflow

Le workflow utilise **LangGraph** pour orchestrer le traitement des requêtes via un graphe de nœuds spécialisés.

```
                    ┌─────────────────┐
                    │  START (Query)  │
                    └────────┬────────┘
                             │
                    ┌────────▼─────────┐
                    │ classify_intent  │
                    │  (IntentNode)    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │     ROUTING      │
                    │  (6 branches)    │
                    └─┬─┬─┬─┬─┬─┬─────┘
                      │ │ │ │ │ │
        ┌─────────────┘ │ │ │ │ └──────────────┐
        │               │ │ │ │                │
   ┌────▼────┐  ┌──────▼─▼─▼─▼──────┐   ┌─────▼──────┐
   │general_ │  │     rag_query      │   │case_law_   │
   │convers. │  │   (retrieval +     │   │research    │
   └─────────┘  │    generation)     │   └────────────┘
                └────────────────────┘
                         │
                    ┌────▼─────┐
                    │  RESPONSE│
                    └──────────┘
```

### Types d'Intentions (6)

| Intent | Description | Workflow Node | Retrieval |
|--------|-------------|---------------|-----------|
| **general_conversation** | Questions générales hors OHADA | `_general_conversation_node` | ❌ Non |
| **rag_query** | Questions nécessitant documentation OHADA | `_rag_query_node` | ✅ Oui (standard) |
| **clarification** | Demandes de clarification/reformulation | `_clarification_node` | ❌ Non |
| **document_sourcing** | Recherche de documents sources | `_document_sourcing_node` | ✅ Oui (enriched metadata) |
| **legal_reference_search** | Recherche par référence (Article X, Compte Y) | `_legal_reference_search_node` | ✅ Oui (by reference) |
| **case_law_research** | Recherche jurisprudentielle (CCJA, etc.) | `_case_law_research_node` | ✅ Oui (by jurisdiction) |

### Classification d'Intent

**Fichier** : `src/rag/agents/intent_classifier.py`

**Processus** :
1. Query utilisateur → LLM DeepSeek (température=0.0 pour déterminisme)
2. Prompt spécialisé OHADA avec exemples
3. Parsing JSON de la réponse
4. Enrichissement avec `LegalReferenceParser` si références détectées

**Exemple de Prompt** :
```
Tu es un classificateur d'intentions pour un assistant juridique OHADA.
Analyse la question et détermine l'intention parmi : [6 types]

Question : "Que dit l'Article 15 de l'AU-OHADA ?"
→ Intent: legal_reference_search
→ Legal Metadata: { reference: "Article 15", source: "AU-OHADA" }
```

**Output** :
```python
IntentClassification(
    intent_type="legal_reference_search",
    confidence=0.95,
    reasoning="Question ciblée sur un article précis",
    direct_answer=None,
    legal_metadata=LegalMetadata(
        document_type="acte_uniforme",
        legal_references=[LegalReference(type="article", number="15")]
    )
)
```

---

## 🔍 Retrieval Hybride

### Architecture 3-Stages

Le système combine **3 méthodes de retrieval** pour maximiser la pertinence :

```
┌──────────────────────────────────────────────────────────┐
│              STAGE 1: PARALLEL RETRIEVAL                 │
│                                                          │
│  ┌─────────────────┐          ┌─────────────────┐      │
│  │ Vector Search   │          │   BM25 Search   │      │
│  │ (Semantic)      │          │   (Keyword)     │      │
│  │                 │          │                 │      │
│  │ Query Embedding │          │ Token Matching  │      │
│  │      ↓          │          │      ↓          │      │
│  │ ChromaDB        │          │ BM25 Index      │      │
│  │ (top_k=20)      │          │ (top_k=20)      │      │
│  └────────┬────────┘          └────────┬────────┘      │
└───────────┼──────────────────────────────┼──────────────┘
            │                              │
            └──────────┬───────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│              STAGE 2: FUSION                             │
│                                                          │
│  Reciprocal Rank Fusion (RRF)                           │
│  - Combine scores from both retrievers                  │
│  - Deduplicate documents                                │
│  - Rerank by fused score                                │
│  - Output: top_k candidates (default: 10)               │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│              STAGE 3: RERANKING                          │
│                                                          │
│  Cross-Encoder Reranking                                │
│  Model: ms-marco-MiniLM-L-6-v2                          │
│  - Rescore each (query, document) pair                  │
│  - Deep semantic understanding                          │
│  - Output: top_k final (default: 5)                     │
└──────────────────────────────────────────────────────────┘
```

### Fichier Principal

**`src/rag/retriever/hybrid_retriever.py`**

**Méthodes** :
- `retrieve()` : Retrieval hybride standard (Vector + BM25 + Reranking)
- `retrieve_by_metadata()` : Retrieval avec filtrage par métadonnées (category, jurisdiction)

### Paramètres de Configuration

```python
# Vector Search
rag_top_k = 20  # Nombre de docs récupérés par vector search

# Reranking
rag_rerank_top_k = 10  # Candidats avant reranking
rag_final_top_k = 5    # Documents finaux après reranking

# BM25
bm25_k1 = 1.5  # Saturation term frequency
bm25_b = 0.75  # Document length normalization
```

### Retrieval Spécialisé (Legal)

**Fichier** : `src/rag/retriever/legal_retriever.py`

**Méthodes Spécialisées** :

1. **`retrieve_by_reference(reference: LegalReference)`**
   - Recherche ciblée par Article, Compte, Chapitre
   - Utilise métadonnées enrichies (`article`, `compte`, `section`)
   - Combine filtrage metadata + vector search

2. **`retrieve_case_law(topic: str, jurisdiction: str)`**
   - Recherche jurisprudentielle par juridiction (CCJA, Cour Suprême, etc.)
   - Filtre `category="jurisprudence"` + `jurisdiction="CCJA"`

3. **`retrieve_by_document_type(type: str)`**
   - Filtre par type : acte_uniforme, plan_comptable, jurisprudence, doctrine

4. **`retrieve_related(reference_doc: Dict)`**
   - Trouve documents similaires/liés à un document de référence

---

## 📊 Métadonnées Enrichies

### Extraction Automatique à l'Ingestion

**Fichier** : `src/ingestion/metadata_extractor.py`

Lors de l'ingestion de documents, le système extrait automatiquement :

```python
{
    # Type de document (détecté du path + contenu)
    "category": "plan_comptable" | "acte_uniforme" | "jurisprudence" | "doctrine",

    # Structure documentaire
    "section": "partie_1",  # Extrait du path
    "title": "Chapitre 5 Opérations d'investissement",
    "file_path": "/app/base_connaissances/plan_comptable/partie_1/...",

    # Références juridiques/comptables
    "articles_references": ["Article 15", "Article 42"],
    "article": "15",  # Article principal
    "comptes_references": ["Compte 6012", "Compte 601"],
    "compte": "6012",
    "classes": ["Classe 6"],
    "classe": "6",

    # Métadonnées jurisprudentielles
    "jurisdiction": "CCJA",
    "case_number": "056/2023",
    "date": "2023-05-15",

    # Thématiques juridiques
    "legal_topics": ["amortissement", "immobilisation"],

    # Statistiques
    "content_length": 15420,
    "word_count": 2500
}
```

### Patterns Reconnus

```python
# Articles
Article 15
Art. 42
Art 35 de l'AU-OHADA

# Comptes
Compte 6012
Compte 601
Classe 6

# Jurisprudences
CCJA/2023/056
Arrêt n°056/2023
CCJA, Arrêt n°056/2023 du 15 mai 2023

# Juridictions
CCJA (Cour Commune de Justice et d'Arbitrage)
Cour Suprême
Cour d'Appel
Tribunal de Commerce

# Dates
15 mai 2023
8 mars 2022
2023-05-15
```

### Sources Enrichies dans Réponse API

**Avant (Phase 1)** :
```json
{
  "title": "Plan Comptable / Partie 1 / chapitre_5...",
  "score": 3.04,
  "category": null,
  "section": null,
  "file_path": null,
  "document_type": null
}
```

**Après (Phase 2 - Actuel)** :
```json
{
  "title": "Plan Comptable / Partie 1 / chapitre_5 Opérations d'investissement",
  "score": 3.039626359939575,
  "category": "plan_comptable",
  "section": "partie_1",
  "file_path": "/app/base_connaissances/plan_comptable/partie_1/chapitre_5.docx",
  "document_type": "plan_comptable",
  "metadata_summary": null
}
```

**Note** : `metadata_summary` est un objet contenant des métadonnées additionnelles spécifiques (articles, comptes) quand disponibles.

---

## 🌐 Endpoints API

### Base URL
```
http://localhost:3202/api/v1
```

### 1. POST `/chat/query` - Query Non-Stream

**Description** : Requête RAG standard avec réponse complète d'un seul coup.

**Headers** :
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body** :
```json
{
  "query": "Qu'est-ce qu'un acte uniforme OHADA ?",
  "conversation_id": "uuid-optional"
}
```

**Response** :
```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "query": "Qu'est-ce qu'un acte uniforme OHADA ?",
  "answer": "Un Acte uniforme OHADA est...",
  "sources": [
    {
      "title": "Acte Uniforme / Traité / Article 1",
      "score": 0.92,
      "category": "acte_uniforme",
      "section": "traite",
      "file_path": "/app/.../acte_uniforme_traite.pdf",
      "document_type": "acte_uniforme",
      "metadata_summary": {
        "article": "1"
      }
    }
  ],
  "model_used": "deepseek/deepseek-chat",
  "tokens_used": 1234,
  "latency_ms": 2450,
  "metadata": {
    "intent_type": "rag_query",
    "intent_confidence": 0.98,
    "num_sources": 4,
    "retrieval_performed": true,
    "use_reranking": true
  },
  "timestamp": "2025-11-08T06:30:00Z"
}
```

**Codes de Statut** :
- `200 OK` : Succès
- `401 Unauthorized` : JWT invalide/expiré
- `500 Internal Server Error` : Erreur serveur

---

### 2. POST `/chat/stream` - Query Stream (SSE)

**Description** : Requête RAG avec streaming progressif via Server-Sent Events.

**Headers** :
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body** :
```json
{
  "query": "Comment comptabiliser un amortissement ?",
  "conversation_id": "uuid-optional"
}
```

**Response** : Stream SSE (`text/event-stream`)

**Événements** :

1. **`sources`** - Sources récupérées (envoyé en premier)
```
data: {"type":"sources","sources":[...],"metadata":{"num_sources":4}}
```

2. **`token`** - Tokens de réponse (streamés progressivement)
```
data: {"type":"token","content":"Un "}
data: {"type":"token","content":"amortissement "}
data: {"type":"token","content":"est..."}
```

3. **`done`** - Métadonnées finales
```
data: {"type":"done","metadata":{"conversation_id":"uuid","model_used":"deepseek/deepseek-chat","tokens_used":345,"latency_ms":1890,"intent_type":"rag_query"}}
```

4. **`message_id`** - ID du message assistant (pour feedback)
```
data: {"type":"message_id","message_id":"uuid"}
```

5. **`error`** - En cas d'erreur
```
data: {"type":"error","content":"Erreur: ..."}
```

---

### 3. GET `/chat/health` - Health Check

**Description** : Vérification de l'état du service.

**Response** :
```json
{
  "status": "ok",
  "service": "chat",
  "endpoints": {
    "query": "/api/v1/chat/query",
    "stream": "/api/v1/chat/stream"
  }
}
```

---

## ⚙️ Configuration

### Fichier de Configuration

**`src/config.py`** - Configuration via Pydantic Settings

### Variables d'Environnement Principales

#### LLM Configuration
```bash
LLM_PROVIDER=deepseek                    # Provider principal
LLM_MODEL=deepseek-chat                  # Modèle principal
LLM_TEMPERATURE=0.1                      # Température génération (0-1, 0.1=déterministe)
LLM_MAX_TOKENS=2500                      # Max tokens par réponse

LLM_FALLBACK_PROVIDER=openai             # Provider de secours
LLM_FALLBACK_MODEL=gpt-4o-mini          # Modèle de secours

INTENT_CLASSIFIER_TEMPERATURE=0.0        # Température classification (0=ultra-déterministe)
INTENT_CLASSIFIER_MAX_TOKENS=500         # Max tokens classification
```

#### Embeddings & Retrieval
```bash
EMBEDDER_MODEL=BAAI/bge-m3              # Modèle embeddings
EMBEDDER_DEVICE=cpu                      # cpu ou cuda
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2

RAG_TOP_K=20                             # Docs récupérés (vector + bm25)
RAG_RERANK_TOP_K=10                      # Candidats avant reranking
RAG_FINAL_TOP_K=5                        # Docs finaux après reranking
```

#### ChromaDB
```bash
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=kauri_ohada_knowledge
```

#### PostgreSQL (via User Service)
```bash
DATABASE_URL=postgresql://user:pass@host:5432/kauri
```

#### Workflow & Features
```bash
USE_RAG_WORKFLOW=true                    # Activer workflow LangGraph
ENABLE_LEGAL_REPORTS=false               # Rapports structurés (désactivé par défaut)
REPORT_AUTO_GENERATE_THRESHOLD=3         # Seuil auto-génération rapport
```

#### API Keys
```bash
OPENROUTER_API_KEY=sk-or-...            # OpenRouter (DeepSeek)
OPENAI_API_KEY=sk-...                    # OpenAI (fallback)
```

---

## 💾 Base de Données

### PostgreSQL (via User Service)

**Tables Utilisées** :

#### `conversations`
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `messages`
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    role VARCHAR(50) NOT NULL,  -- 'user' | 'assistant'
    content TEXT NOT NULL,
    sources JSONB,              -- Array of sources for assistant messages
    metadata JSONB,             -- model_used, tokens_used, intent_type, etc.
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Service** : `src/services/conversation_service.py`

**Méthodes Principales** :
- `get_or_create_conversation()` : Récupère ou crée conversation
- `save_message()` : Sauvegarde message (user ou assistant)
- `get_conversation_messages()` : Récupère historique (limit=10 derniers)
- `auto_generate_title()` : Génère titre conversation automatiquement

---

### ChromaDB (Vector Database)

**Collection** : `kauri_ohada_knowledge`

**Documents Stockés** : 10,190+ chunks

**Structure d'un Document** :
```python
{
    "id": "uuid",
    "embedding": [1024 floats],  # BAAI/bge-m3
    "document": "contenu textuel du chunk",
    "metadata": {
        # Métadonnées de base
        "source": "file_path",
        "category": "plan_comptable",
        "section": "partie_1",
        "title": "Chapitre 5...",
        "file_path": "/app/.../file.docx",

        # Métadonnées enrichies (Phase 2)
        "article": "15",
        "articles_references": ["Article 15", "Article 18"],
        "compte": "6012",
        "comptes_references": ["Compte 6012"],
        "jurisdiction": "CCJA",
        "case_number": "056/2023",
        "date": "2023-05-15",
        "legal_topics": ["amortissement"],

        # Stats
        "content_length": 1500,
        "word_count": 250
    }
}
```

---

## 📂 Flux de Données

### Flux Complet - Query Non-Stream

```
┌─────────────────────────────────────────────────────────────┐
│                    1. CLIENT REQUEST                        │
│  POST /api/v1/chat/query                                    │
│  Headers: { Authorization: Bearer JWT }                     │
│  Body: { query, conversation_id }                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              2. AUTHENTICATION (JWT)                        │
│  - Validate JWT with User Service                          │
│  - Extract user_id from token                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│         3. CONVERSATION LAYER (ConversationAwareRAG)        │
│  a) Get/Create conversation (PostgreSQL)                   │
│  b) Retrieve last 10 messages (PostgreSQL)                 │
│  c) Save user message (PostgreSQL)                         │
│  d) Build conversation context (format history)            │
│  e) Augment query with context                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│            4. RAG WORKFLOW (LangGraph)                      │
│  a) classify_intent (LLM DeepSeek, temp=0.0)               │
│     → Output: intent_type + legal_metadata                 │
│  b) routing (based on intent_type)                         │
│     → Route to specialized node                            │
│  c) Execute node (example: rag_query)                      │
│     → Hybrid Retrieval (see next section)                  │
│     → LLM Generation                                        │
│  d) Format response                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│          5. HYBRID RETRIEVAL (if needed)                    │
│  a) Parallel Retrieval:                                     │
│     - Vector Search (ChromaDB, top_k=20)                   │
│     - BM25 Search (in-memory index, top_k=20)              │
│  b) Fusion (RRF, deduplicate)                              │
│  c) Reranking (Cross-Encoder, top_k=5)                     │
│  → Output: 5 most relevant documents + metadata            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              6. LLM GENERATION                              │
│  a) Format context from documents                          │
│  b) Build system prompt (OHADA specialist)                 │
│  c) Build user prompt (context + query + rules)            │
│  d) Call LLM DeepSeek (temp=0.1, max_tokens=2500)          │
│  → Output: Generated answer                                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│          7. SAVE ASSISTANT MESSAGE                          │
│  - Save to PostgreSQL messages table                       │
│  - Include: content, sources, metadata                     │
│  - Auto-generate conversation title (if first message)     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              8. FORMAT & RETURN RESPONSE                    │
│  {                                                          │
│    conversation_id, message_id, query, answer,             │
│    sources (enriched), model_used, tokens_used,            │
│    latency_ms, metadata, timestamp                         │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### Flux Complet - Query Stream

**Identique jusqu'à l'étape 6**, puis :

```
┌─────────────────────────────────────────────────────────────┐
│              6. LLM STREAMING GENERATION                    │
│  a) Yield sources event                                     │
│     data: {"type":"sources","sources":[...]}               │
│  b) Stream tokens progressively                            │
│     data: {"type":"token","content":"Un "}                 │
│     data: {"type":"token","content":"amortissement "}      │
│     ...                                                     │
│  c) Yield message_id event                                 │
│     data: {"type":"message_id","message_id":"uuid"}        │
│  d) Yield done event with metadata                         │
│     data: {"type":"done","metadata":{...}}                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 Fichiers Clés

### Structure du Projet

```
backend/kauri_chatbot_service/
│
├── src/
│   ├── api/
│   │   └── routes/
│   │       └── chat.py                    # Endpoints API (/query, /stream, /health)
│   │
│   ├── rag/
│   │   ├── pipeline/
│   │   │   ├── conversation_aware_rag.py  # Couche conversationnelle + persistence
│   │   │   └── rag_pipeline.py            # Pipeline RAG de base
│   │   │
│   │   ├── agents/
│   │   │   ├── rag_workflow.py            # LangGraph workflow (6 nodes)
│   │   │   ├── intent_classifier.py       # Classification d'intent
│   │   │   ├── reference_parser.py        # Parsing références juridiques
│   │   │   └── legal_report_generator.py  # Génération rapports structurés
│   │   │
│   │   └── retriever/
│   │       ├── hybrid_retriever.py        # Retrieval hybride (Vector+BM25+Rerank)
│   │       ├── legal_retriever.py         # Retrieval spécialisé juridique
│   │       ├── vector_retriever.py        # Vector search (ChromaDB)
│   │       ├── bm25_retriever.py          # BM25 keyword search
│   │       └── reranker.py                # Cross-encoder reranking
│   │
│   ├── llm/
│   │   └── llm_client.py                  # Client LLM (DeepSeek via OpenRouter)
│   │
│   ├── embedder/
│   │   └── embedder.py                    # Embeddings (BAAI/bge-m3)
│   │
│   ├── ingestion/
│   │   ├── document_processor.py          # Ingestion documents (PDF, DOCX)
│   │   └── metadata_extractor.py          # Extraction métadonnées juridiques
│   │
│   ├── services/
│   │   └── conversation_service.py        # Persistence conversations (PostgreSQL)
│   │
│   ├── schemas/
│   │   └── chat.py                        # Schémas Pydantic (Request/Response)
│   │
│   ├── auth/
│   │   └── jwt_validator.py               # Validation JWT (User Service)
│   │
│   ├── models/
│   │   └── database.py                    # Modèles SQLAlchemy
│   │
│   └── config.py                          # Configuration (Pydantic Settings)
│
├── main.py                                # Application FastAPI
├── Dockerfile
├── requirements.txt
└── .env.example
```

### Fichiers de Documentation

```
DOCUMENTATION_TECHNIQUE_COMPLETE.md       # Ce fichier
PHASE1_DOCUMENTATION.md                   # Phase 1: Classification enrichie
PHASE2_DOCUMENTATION.md                   # Phase 2: Rapports + Métadonnées
RESUME_AMELIORATIONS.md                   # Résumé des améliorations
GUIDE_UTILISATEUR_JURISTE.md              # Guide utilisateur final
ANALYSE_STREAM_VS_NONSTREAM.md            # Analyse tests stream/non-stream
```

---

## 🔐 Sécurité & Authentification

### JWT Validation

**Fichier** : `src/auth/jwt_validator.py`

**Processus** :
1. Extraction du token depuis header `Authorization: Bearer <token>`
2. Validation du token avec User Service (HTTP request)
3. Vérification expiration + signature
4. Extraction user_id, email, subscription info
5. Injection dans request state

**Protection Endpoints** :
- ✅ `/chat/query` : Protégé (JWT requis)
- ✅ `/chat/stream` : Protégé (JWT requis)
- ❌ `/chat/health` : Public (pas de JWT)

---

## 📊 Métriques & Performance

### Latences Typiques

| Endpoint | Mode | Latence Moyenne | Détails |
|----------|------|-----------------|---------|
| `/chat/query` | Non-stream | ~20-25s | Retrieval (2-3s) + Generation (15-20s) |
| `/chat/stream` | Stream | ~18-20s | Même mais perception plus rapide |

**Breakdown Latence** :
- Classification intent : ~1-2s
- Retrieval (vector + BM25) : ~1s
- Reranking : ~0.5-1s
- LLM Generation : ~15-20s (dépend longueur réponse)
- Persistence DB : ~0.5s

### Optimisations Appliquées

1. **Lazy Loading** : Embeddings et reranker chargés à la première utilisation
2. **Caching** : BM25 index reconstruit au démarrage puis gardé en mémoire
3. **Parallel Retrieval** : Vector et BM25 en parallèle
4. **Temperature Optimization** : 0.1 pour génération, 0.0 pour classification (déterminisme)
5. **Streaming** : Permet UI responsive pendant génération

---

## 🚀 Déploiement

### Docker Compose

**Service** : `kauri_chatbot_service`

```yaml
kauri_chatbot_service:
  build: ./backend/kauri_chatbot_service
  container_name: kauri_chatbot_service
  ports:
    - "3202:3202"
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - CHROMA_HOST=chromadb
    - CHROMA_PORT=8000
    - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
  depends_on:
    - chromadb
    - kauri_user_service
  volumes:
    - ./base_connaissances:/app/base_connaissances:ro
```

### Commandes Utiles

```bash
# Redémarrer le service
docker-compose restart kauri_chatbot_service

# Voir les logs
docker logs kauri_chatbot_service --tail 100 -f

# Health check
curl http://localhost:3202/api/v1/chat/health
```

---

## 🧪 Tests

### Scripts de Test

```
test_stream_vs_nonstream.py          # Compare stream vs non-stream
test_sources_metadata.py              # Vérifie métadonnées enrichies
test_phase1_enhancements.py           # Tests Phase 1 (classification)
```

### Test Manuel

```bash
# Obtenir token JWT
TOKEN=$(curl -s --request POST \
  --url http://localhost:3201/api/v1/auth/login \
  --header 'content-type: application/json' \
  --data '{"email":"user@example.com","password":"pass"}' \
  | jq -r '.access_token')

# Test query non-stream
curl --request POST \
  --url http://localhost:3202/api/v1/chat/query \
  --header "Authorization: Bearer $TOKEN" \
  --header 'content-type: application/json' \
  --data '{"query":"Qu'\''est-ce qu'\''un acte uniforme OHADA ?"}'
```

---

## 📈 Améliorations Futures

### Phase 3 (Optionnel)

1. **Export PDF/DOCX** : Rapports juridiques exportables
2. **Templates Personnalisables** : Cabinets peuvent définir formats
3. **Analyse Comparative Automatique** : Comparer jurisprudences/doctrines
4. **Cache Intelligent** : Rapports fréquents pré-générés
5. **Fine-tuning Reranker** : Spécialisé sur corpus OHADA
6. **API Dédiée Rapports** : Endpoint `/api/v1/reports/generate`
7. **Multi-langue** : Support Anglais pour OHADA anglophone

---

## 📞 Support & Contact

**Projet** : KAURI - Assistant Juridique et Comptable OHADA
**Version** : 2.1.0
**Dernière Mise à Jour** : 08/11/2025
**Développé avec** : Claude Code (Anthropic)

---

**Fin de la Documentation Technique Complète**
