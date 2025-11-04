# KAURI - Architecture Backend OHAD'AI
## Documentation Complète pour Reproduction du Système Backend

> **Date de création**: 2025-11-03
> **Projet source**: OHAD'AI Expert-Comptable
> **Objectif**: Documentation exhaustive de l'architecture backend pour reproduction dans le projet KAURI

---

## Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Architecture Globale](#2-architecture-globale)
3. [Structure des Répertoires](#3-structure-des-répertoires)
4. [Modules Principaux](#4-modules-principaux)
5. [Configuration des Modèles LLM](#5-configuration-des-modèles-llm)
6. [Système de Recherche Hybride](#6-système-de-recherche-hybride)
7. [Base de Données Vectorielle](#7-base-de-données-vectorielle)
8. [API FastAPI](#8-api-fastapi)
9. [Authentification et Sécurité](#9-authentification-et-sécurité)
10. [Optimisations et Cache](#10-optimisations-et-cache)
11. [Dépendances Python](#11-dépendances-python)
12. [Configuration et Environnements](#12-configuration-et-environnements)
13. [Scripts d'Ingestion](#13-scripts-dingestion)
14. [Guide de Reproduction](#14-guide-de-reproduction)

---

## 1. Vue d'Ensemble

### 1.1 Description

Le backend OHAD'AI est un système RAG (Retrieval-Augmented Generation) expert en comptabilité OHADA qui combine:

- **Recherche hybride** (BM25 + Vectorielle + Reranking)
- **Embeddings locaux** avec BGE-M3 (1024 dimensions)
- **LLM DeepSeek** pour génération de réponses
- **API FastAPI** avec streaming SSE
- **Cache distribué Redis** (optionnel)
- **Base vectorielle ChromaDB**
- **Authentification JWT** avec gestion d'utilisateurs

### 1.2 Technologies Clés

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Framework API | FastAPI | 0.115.11 |
| Base Vectorielle | ChromaDB | 0.5.23 |
| Embeddings | BGE-M3 (local) | BAAI/bge-m3 |
| LLM Principal | DeepSeek | deepseek-chat |
| Reranking | Cross-Encoder | ms-marco-MiniLM-L-6-v2 |
| Cache | Redis | 5.2.1 (optionnel) |
| Base SQL | SQLite/PostgreSQL | psycopg2-binary 2.9.10 |
| Serveur ASGI | Uvicorn | 0.34.0 |

---

## 2. Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT (HTTP/SSE)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                  FASTAPI SERVER (Port 8000)                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ API Endpoints: /query, /stream, /auth, /conversations│   │
│  │ - Authentification JWT (optionnelle)                 │   │
│  │ - Gestion des conversations                          │   │
│  │ - Streaming SSE                                       │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│              OHADA HYBRID RETRIEVER                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Intent    │  │    Query     │  │   Context    │       │
│  │ Classifier  │  │ Reformulator │  │  Processor   │       │
│  └─────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │         HYBRID SEARCH (Parallel)                   │     │
│  │  ┌──────────────┐        ┌──────────────┐         │     │
│  │  │ BM25 Search  │        │Vector Search │         │     │
│  │  │ (Keyword)    │        │ (BGE-M3)     │         │     │
│  │  └──────┬───────┘        └───────┬──────┘         │     │
│  │         └─────────┬──────────────┘                 │     │
│  │                   ▼                                │     │
│  │         ┌─────────────────┐                        │     │
│  │         │ Cross-Encoder   │                        │     │
│  │         │   Reranking     │                        │     │
│  │         └────────┬────────┘                        │     │
│  └──────────────────┼───────────────────────────────┘      │
└───────────────────┼─┼───────────────────────────────────────┘
                    │ │
        ┌───────────┘ └──────────┐
        ▼                        ▼
┌───────────────┐        ┌──────────────┐
│   ChromaDB    │        │  LLM Client  │
│ (Vector Store)│        │  (DeepSeek)  │
│  - 7 Collections       │ - Response   │
│  - BGE-M3 (1024)       │   Generation │
└───────────────┘        └──────────────┘
        │
        ▼
┌───────────────┐
│ Redis Cache   │
│  (Optional)   │
│ - Embeddings  │
│ - Queries     │
└───────────────┘
```

---

## 3. Structure des Répertoires

```
backend/
├── src/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── ohada_api_server.py        # Point d'entrée FastAPI principal
│   │   ├── auth_routes.py             # Routes d'authentification
│   │   ├── conversations_api.py       # Routes gestion conversations
│   │   └── v1/
│   │       └── documents.py           # Routes documents (API v1)
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── auth_manager.py            # Gestionnaire authentification
│   │   ├── auth_models.py             # Modèles Pydantic auth
│   │   ├── jwt_manager.py             # Gestion tokens JWT
│   │   └── password_utils.py          # Utilitaires mots de passe
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── ohada_config.py            # Configuration LLM centralisée
│   │   ├── llm_config_test.yaml      # Config environnement test
│   │   └── llm_config_production.yaml # Config environnement prod
│   │
│   ├── db/
│   │   ├── base.py                    # Base SQLAlchemy
│   │   └── db_manager.py              # Gestionnaire base SQL
│   │
│   ├── document_parser/
│   │   ├── __init__.py
│   │   ├── parser.py                  # Parser PDF universel
│   │   └── extractor.py               # Extraction texte/métadonnées
│   │
│   ├── generation/
│   │   ├── __init__.py
│   │   ├── intent_classifier.py       # Classification intention LLM
│   │   ├── query_reformulator.py      # Reformulation requêtes
│   │   ├── response_generator.py      # Génération réponses
│   │   └── streaming_generator.py     # Génération streaming
│   │
│   ├── models/
│   │   ├── document.py                # Modèles SQLAlchemy documents
│   │   └── user.py                    # Modèles SQLAlchemy users
│   │
│   ├── retrieval/
│   │   ├── __init__.py
│   │   ├── ohada_hybrid_retriever.py  # Orchestrateur recherche hybride
│   │   ├── bm25_retriever.py          # Recherche BM25 (keyword)
│   │   ├── vector_retriever.py        # Recherche vectorielle
│   │   ├── cross_encoder_reranker.py  # Reranking cross-encoder
│   │   ├── context_processor.py       # Traitement contexte
│   │   └── postgres_metadata_enricher.py # Enrichissement métadonnées
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py              # Configuration Celery
│   │   └── document_tasks.py          # Tâches asynchrones
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── ohada_cache.py             # Cache embeddings local
│   │   ├── ohada_clients.py           # Client LLM unifié
│   │   ├── ohada_streaming.py         # Utilitaires streaming
│   │   ├── ohada_utils.py             # Utilitaires généraux
│   │   └── redis_cache.py             # Cache Redis distribué
│   │
│   ├── vector_db/
│   │   ├── __init__.py
│   │   └── ohada_vector_db_structure.py # Gestion ChromaDB + BGE-M3
│   │
│   └── main.py                         # Point d'entrée alternatif
│
├── scripts/
│   ├── import_document.py              # Import document unique
│   ├── import_all_documents.py         # Import batch documents
│   ├── ingest_to_chromadb.py          # Ingestion ChromaDB
│   ├── migrate_all_documents.py       # Migration documents
│   ├── test_workflow.py               # Test workflow complet
│   └── test_simple_workflow.py        # Test workflow simple
│
├── chroma_db/                          # Stockage ChromaDB (persisté)
│   └── [collections vectorielles]
│
├── data/                               # Données application
│   └── ohada_users.db                 # Base SQLite utilisateurs
│
├── start.bat                           # Script démarrage Windows
├── restart_server.bat                 # Script redémarrage
└── requirements.txt                   # Dépendances Python (racine)
```

---

## 4. Modules Principaux

### 4.1 API Server (`src/api/ohada_api_server.py`)

**Rôle**: Point d'entrée FastAPI, orchestration des requêtes.

**Fonctionnalités principales**:
- Démarrage serveur avec warm-up (préchargement modèles)
- Endpoints RESTful + SSE streaming
- Middleware CORS
- Gestion authentification JWT optionnelle
- Cache Redis pour requêtes répétées
- Analyse d'intention avec LLM
- Gestion conversations utilisateur

**Endpoints clés**:

```python
GET  /                  # Status API
GET  /status            # Status détaillé (modèles, BDD, collections)
POST /query             # Requête standard (avec/sans streaming)
GET  /stream            # Requête streaming SSE
GET  /history           # Historique requêtes

# Authentification
POST /auth/register     # Enregistrement utilisateur
POST /auth/login        # Connexion (JWT)
POST /auth/logout       # Déconnexion
GET  /auth/me           # Info utilisateur courant

# Conversations
GET  /conversations                     # Liste conversations
POST /conversations                     # Créer conversation
GET  /conversations/{conversation_id}  # Détails conversation
DELETE /conversations/{conversation_id}# Supprimer conversation

# Admin
GET /admin/stats        # Statistiques système
GET /admin/cache-stats  # Statistiques cache Redis
GET /admin/cleanup      # Nettoyage BDD
GET /admin/models       # Info modèles configurés

# Test
POST /test/intent       # Tester classification intention
POST /test/search       # Tester recherche seule
```

**Workflow d'une requête `/query`**:

```python
1. Réception requête POST avec QueryRequest (query, n_results, partie, chapitre)
2. Authentification utilisateur (optionnelle via JWT)
3. Vérification cache Redis (si activé) → retour immédiat si HIT
4. Analyse intention avec LLMIntentAnalyzer
   - Si intention = conversational/greeting → réponse directe
   - Si intention = technical → continuer workflow
5. Reformulation requête (QueryReformulator)
6. Recherche hybride (OhadaHybridRetriever.search_hybrid)
   - BM25 + Vectoriel en parallèle
   - Reranking cross-encoder
7. Traitement contexte (ContextProcessor)
8. Génération réponse (ResponseGenerator)
9. Mise en cache Redis (TTL 1h)
10. Sauvegarde conversation (si utilisateur authentifié)
11. Retour JSON avec réponse + sources + performance
```

**Fichier de référence**: `backend/src/api/ohada_api_server.py:1-1171`

---

### 4.2 Configuration LLM (`src/config/ohada_config.py`)

**Rôle**: Gestion centralisée des modèles LLM et embeddings.

**Classe principale**: `LLMConfig`

**Chargement de configuration**:
- Détecte environnement via `OHADA_ENV` (test/production)
- Charge fichier YAML correspondant (`llm_config_test.yaml` ou `llm_config_production.yaml`)
- Fallback sur configuration par défaut si fichier manquant

**Providers supportés**:
```yaml
- deepseek      # LLM principal (deepseek-chat)
- openai        # LLM + Embeddings API (text-embedding-3-small, gpt-3.5/4)
- local_embedding # BGE-M3 local pour embeddings (BAAI/bge-m3)
- local         # Ollama pour LLM local (désactivé en test)
```

**Méthodes clés**:

```python
get_embedding_model(provider=None)
# → Retourne (provider_name, model_name, params)
# Exemple: ("local_embedding", "BAAI/bge-m3", {"dimensions": 1024})

get_response_model(provider=None)
# → Retourne (provider_name, model_name, params)
# Exemple: ("deepseek", "deepseek-chat", {"temperature": 0.3, "max_tokens": 1500})

get_assistant_personality()
# → Retourne config personnalité assistant
# {name, expertise, region, language, tone, capabilities, knowledge_domains}
```

**Fichier de référence**: `backend/src/config/ohada_config.py:1-302`

---

### 4.3 Hybrid Retriever (`src/retrieval/ohada_hybrid_retriever.py`)

**Rôle**: Orchestrateur central de la recherche hybride.

**Classe principale**: `OhadaHybridRetriever`

**Composants intégrés**:
```python
- bm25_retriever        # Recherche keyword
- vector_retriever      # Recherche vectorielle
- reranker             # Cross-encoder reranking
- context_processor    # Traitement contexte
- query_reformulator   # Reformulation requêtes
- response_generator   # Génération réponses
- streaming_generator  # Génération streaming
- llm_client          # Client LLM unifié
```

**Méthode principale**: `search_hybrid()`

**Workflow**:
```python
1. Détermination collections cibles (ohada_documents)
2. Parallélisation:
   a. Génération embedding requête (BGE-M3)
   b. Recherche BM25 (pour chaque collection)
   c. Recherche vectorielle (pour chaque collection)
3. Agrégation résultats (BM25 + Vector)
4. Déduplication par document_id (meilleur score)
5. Calcul score combiné: combined_score = 0.5*bm25 + 0.5*vector
6. Boosting selon type document:
   - presentation_ohada × 1.5 si "traité" dans query
   - chapitre × 1.2 si mots-clés comptables
7. Tri par score combiné
8. Reranking cross-encoder (top 2×n_results)
9. Sélection top n_results
10. Enrichissement métadonnées PostgreSQL (optionnel)
```

**Point d'entrée API**:
```python
create_ohada_query_api(config_path)
# → Crée instance OhadaHybridRetriever configurée
# → Utilisé au démarrage FastAPI
```

**Fichier de référence**: `backend/src/retrieval/ohada_hybrid_retriever.py:1-655`

---

### 4.4 Vector Database (`src/vector_db/ohada_vector_db_structure.py`)

**Rôle**: Gestion base vectorielle ChromaDB et embeddings BGE-M3.

**Classes principales**:

#### 4.4.1 `OhadaEmbedder` (Singleton)

**Modèles supportés**:
- **Test**: `BAAI/bge-m3` (1024 dimensions, 8192 tokens)
- **Production**: `Alibaba-NLP/gte-Qwen2-1.5B-instruct` (1536 dimensions)

**Méthodes**:
```python
generate_embedding(text: str) → List[float]
# Génère embedding pour texte unique

generate_embeddings(texts: List[str], batch_size=8) → List[List[float]]
# Génère embeddings par batch (optimisé)

evaluate_embedding_quality(corpus, queries, relevant_docs)
# Évalue qualité avec métriques Precision@5, Recall@5, MAP@5
```

**Optimisations**:
- Pattern Singleton (modèle chargé une seule fois)
- Cache global `_model_cache`
- Détection GPU automatique
- Troncature textes longs (8192 tokens max)
- Batch processing avec barre de progression

#### 4.4.2 `OhadaVectorDB`

**Collections ChromaDB**:
```python
1. syscohada_plan_comptable  # Structure et fonctionnement
2. partie_1                  # Opérations courantes
3. partie_2                  # Opérations spécifiques
4. partie_3                  # États financiers annuels
5. partie_4                  # Comptes consolidés
6. chapitres                 # Chapitres (incluant sections/applications)
7. presentation_ohada        # Présentation OHADA et traité
```

**Méthodes clés**:
```python
add_document(collection_name, document, embedding=None)
# Ajoute document avec embedding (génère si None)

query(collection_name, query_text=None, query_embedding=None,
      filter_dict=None, n_results=5)
# Recherche vectorielle avec filtres

get_collection_stats()
# Statistiques toutes collections (count, metadata, title)

reset_database()
# Réinitialise toutes collections (DANGER)
```

**Fichier de référence**: `backend/src/vector_db/ohada_vector_db_structure.py:1-725`

---

### 4.5 LLM Client (`src/utils/ohada_clients.py`)

**Rôle**: Interface unifiée pour LLM et embeddings multi-providers.

**Classe principale**: `LLMClient`

**Préchargement**:
```python
# Au __init__, précharge embedder local pour éviter latence
embedder = OhadaEmbedder(model_name="BAAI/bge-m3")
# → Gain ~200-500ms sur première requête
```

**Méthodes principales**:

```python
generate_embedding(text: str) → List[float]
# Cascade: local_embedding → openai → fallback vecteur zéro
# Utilise pattern Singleton OhadaEmbedder

generate_response(system_prompt, user_prompt, max_tokens, temperature) → str
# Cascade: deepseek → openai → local → erreur
# Retourne réponse textuelle complète

generate_response_streaming(system_prompt, user_prompt, ...) → AsyncGenerator
# Version async streaming (pour SSE)
# Retourne objet stream OpenAI
```

**Gestion multi-providers**:
```python
# Essaye chaque provider selon provider_priority
for provider in ["deepseek", "openai", "local"]:
    try:
        client = self._get_client(provider, params)
        response = client.chat.completions.create(...)
        return response.choices[0].message.content
    except Exception:
        continue  # Essayer provider suivant
```

**Fichier de référence**: `backend/src/utils/ohada_clients.py:1-380`

---

### 4.6 Response Generator (`src/generation/response_generator.py`)

**Rôle**: Génération réponses finales avec contexte.

**Optimisation majeure**: Génération en 1 étape au lieu de 2

**Ancienne méthode** (2 étapes, ~1800-3200ms):
1. Analyse contexte (800 tokens, ~800-1200ms)
2. Génération réponse (1200 tokens, ~1000-2000ms)

**Nouvelle méthode** (1 étape, ~1000-2000ms):
- Prompt unifié avec instructions d'analyse intégrées
- Économie ~800-1200ms et 1 appel réseau

**Contraintes de formatage**:
```
- Interdit notation LaTeX (\frac, \times, etc.)
- Interdit formules entre crochets
- Formules en texte: "Montant = Base × Taux"
- Fractions: "A divisé par B" ou "A / B"
```

**Fichier de référence**: `backend/src/generation/response_generator.py:1-135`

---

### 4.7 Intent Classifier (`src/generation/intent_classifier.py`)

**Rôle**: Classification intention requête avec LLM.

**Classe principale**: `LLMIntentAnalyzer`

**Intentions détectées**:
```
- greeting              # Salutations, présentations
- help                  # Demande d'aide
- conversational        # Discussion générale
- off_topic            # Hors sujet (non comptabilité)
- technical            # Question technique OHADA (défaut)
```

**Workflow**:
```python
1. Analyse avec LLM (prompt classification)
2. Parsing JSON réponse:
   {
     "intent": "greeting",
     "confidence": 0.95,
     "subcategory": "presentation",
     "needs_knowledge_base": false,
     "explanation": "..."
   }
3. Génération réponse directe si needs_knowledge_base=false
4. Sinon, continue vers recherche hybride
```

**Avantage**: Évite recherche inutile pour requêtes non techniques (gain ~2-3s).

---

## 5. Configuration des Modèles LLM

### 5.1 Fichier `llm_config_test.yaml`

```yaml
# Priorités providers
provider_priority:
  - "deepseek"      # LLM principal
  - "openai"        # LLM fallback
  - "local"         # Ollama (désactivé)

embedding_provider_priority:
  - "local_embedding"  # BGE-M3 (prioritaire)
  - "openai"           # text-embedding-3-small (fallback)

default_provider: "deepseek"
default_embedding_provider: "local_embedding"

providers:
  # DeepSeek - LLM Principal
  deepseek:
    api_key_env: "DEEPSEEK_API_KEY"
    base_url: "https://api.deepseek.com/v1"
    models:
      default: "deepseek-chat"
      analysis: "deepseek-chat"
      response: "deepseek-chat"
    parameters:
      temperature: 0.3
      top_p: 0.9
      max_tokens: 1500

  # OpenAI - Embeddings + LLM Fallback
  openai:
    api_key_env: "OPENAI_API_KEY"
    models:
      default: "gpt-3.5-turbo-0125"
      embedding: "text-embedding-3-small"  # 1536 dimensions
      analysis: "gpt-3.5-turbo-0125"
      response: "gpt-4-turbo-preview"
    parameters:
      temperature: 0.3
      top_p: 0.9
      max_tokens: 1500
      dimensions: 1536

  # BGE-M3 Local - Embeddings Principal
  local_embedding:
    enabled: true
    local: true  # Flag important
    models:
      embedding: "BAAI/bge-m3"  # 8192 tokens context
    parameters:
      dimensions: 1024

  # Ollama Local - Désactivé en test
  local:
    enabled: false
    api_key_env: "OLLAMA_API_KEY"
    base_url: "http://localhost:11434/api"
    models:
      default: "mistral:7b-instruct-v0.2"
      analysis: "mistral:7b-instruct-v0.2"
      response: "llama3:8b"
    parameters:
      temperature: 0.3
      top_p: 0.9
      max_tokens: 1500
      local: true

# Personnalité Assistant
assistant_personality:
  name: "Expert OHADA"
  expertise: "comptabilité et normes SYSCOHADA"
  region: "zone OHADA (Afrique)"
  language: "fr"
  tone: "professionnel"
  capabilities:
    - "réponse aux questions sur le plan comptable OHADA"
    - "explication des règles comptables SYSCOHADA"
    - "aide à la préparation des états financiers"
    - "conseils en matière de fiscalité des entreprises"
    - "aide à l'analyse des opérations comptables"
    - "interprétation des actes uniformes OHADA"
    - "génération d'écritures comptables conformes"
  knowledge_domains:
    - "Plan comptable OHADA"
    - "Normes SYSCOHADA"
    - "Comptabilité des entreprises dans la zone OHADA"
    - "Audit et contrôle des comptes"
    - "Fiscalité des entreprises dans la zone OHADA"
    - "Gestion financière et trésorerie"
    - "Analyse financière et ratios"
    - "États financiers et rapports annuels"
    - "Réglementation comptable dans l'espace OHADA"
```

**Fichier de référence**: `backend/src/config/llm_config_test.yaml:1-96`

### 5.2 Différences Production

`llm_config_production.yaml`:
- **Embedding model**: `Alibaba-NLP/gte-Qwen2-1.5B-instruct` (1536 dim)
- **LLM response**: `gpt-4-turbo-preview` (au lieu de deepseek)
- **Max tokens**: 2000 (au lieu de 1500)
- **Local enabled**: false (tout via API)

---

## 6. Système de Recherche Hybride

### 6.1 Vue d'Ensemble

Le système combine **3 techniques** de recherche:

```
Query: "Comment calculer l'amortissement linéaire?"
    │
    ├─► BM25 Retriever (Keyword-based)
    │   - Tokenization
    │   - TF-IDF scoring
    │   - Score: 0.0 - 1.0
    │
    ├─► Vector Retriever (Semantic)
    │   - BGE-M3 embedding (1024 dim)
    │   - Cosine similarity
    │   - Score: 0.0 - 1.0
    │
    └─► Combined Results
        - Deduplication by doc_id
        - Combined score = 0.5*bm25 + 0.5*vector
        - Document type boosting
        │
        ▼
    Cross-Encoder Reranker
        - ms-marco-MiniLM-L-6-v2
        - Pairwise (query, document)
        - Final score: 0.0 - 1.0
        │
        ▼
    Top N Results (sorted by final_score)
```

### 6.2 BM25 Retriever (`src/retrieval/bm25_retriever.py`)

**Algorithme**: Okapi BM25 (keyword-based search)

**Paramètres**:
```python
k1 = 1.5   # Term frequency saturation
b = 0.75   # Length normalization
```

**Workflow**:
```python
1. Document provider récupère tous documents de collection
2. Construction index BM25 (rank-bm25 library)
3. Tokenization query
4. Scoring BM25 pour chaque document
5. Application filtres (partie, chapitre)
6. Tri par score descendant
7. Retour top n_results candidats
```

**Format candidat**:
```python
{
    "document_id": "doc_123",
    "text": "Le calcul de l'amortissement...",
    "metadata": {"partie": 1, "chapitre": 5, ...},
    "bm25_score": 0.87,
    "vector_score": 0.0,
    "combined_score": 0.435  # 0.87 * 0.5
}
```

### 6.3 Vector Retriever (`src/retrieval/vector_retriever.py`)

**Modèle**: BGE-M3 (BAAI/bge-m3, 1024 dimensions)

**Cache cascade**:
```python
1. Redis cache (distribué, ~1-2ms)
2. Local cache (mémoire, ~0.1ms)
3. Génération embedding (~50-150ms API, ~10-30ms local)
```

**Workflow**:
```python
1. get_embedding(query) avec cascade cache
2. ChromaDB collection.query(query_embeddings=[embedding])
3. Conversion distance → score: score = 1 - (distance/2)
4. Application filtres (where clause)
5. Retour candidats avec vector_score
```

**Optimisation Redis**:
```python
# Mise en cache embedding
redis_cache.set_embedding(text, embedding, ttl=86400)  # 24h

# Récupération
cached = redis_cache.get_embedding(text)
if cached:
    return cached  # Gain ~50-150ms
```

### 6.4 Cross-Encoder Reranker (`src/retrieval/cross_encoder_reranker.py`)

**Modèle**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

**Différence vs Bi-Encoder**:
- **Bi-encoder**: encode query et document séparément, calcule similarité
- **Cross-encoder**: encode paire (query, document) ensemble, plus précis

**Workflow**:
```python
1. Préparation paires: [(query, doc1.text), (query, doc2.text), ...]
2. Scoring par batch (optimisé GPU)
3. Normalisation scores: sigmoid(score)
4. Mise à jour candidates avec final_score
5. Tri par final_score descendant
```

**Gain de précision**: +15-25% sur métriques NDCG@10

### 6.5 Context Processor (`src/retrieval/context_processor.py`)

**Rôle**: Traitement et formatage du contexte pour LLM.

**Méthodes**:

```python
summarize_context(query, search_results) → str
# Agrège résultats en texte structuré pour LLM
# Format:
# """
# Source 1 (score: 0.95):
# [Texte pertinent...]
#
# Source 2 (score: 0.87):
# [Texte pertinent...]
# """

prepare_sources(search_results) → List[Dict]
# Formate sources pour frontend
# [
#   {
#     "document_id": "...",
#     "preview": "...",  # Premiers 200 chars
#     "metadata": {...},
#     "relevance_score": 0.95
#   }
# ]
```

---

## 7. Base de Données Vectorielle

### 7.1 ChromaDB Collections

**Localisation**: `backend/chroma_db/`

**Collections créées**:

| Nom Collection | Description | Nombre de docs (exemple) |
|----------------|-------------|--------------------------|
| `syscohada_plan_comptable` | Structure et fonctionnement | ~500 |
| `partie_1` | Opérations courantes | ~1200 |
| `partie_2` | Opérations spécifiques | ~800 |
| `partie_3` | États financiers annuels | ~600 |
| `partie_4` | Comptes consolidés | ~400 |
| `chapitres` | Chapitres (sections + applications) | ~2500 |
| `presentation_ohada` | Présentation OHADA et traité | ~300 |

**Total**: ~6300 documents vectorisés

### 7.2 Structure Document

**Classe Pydantic**:
```python
class OhadaDocument(BaseModel):
    id: str                    # Unique identifier
    text: str                  # Contenu textuel
    metadata: Dict[str, Any]   # Métadonnées
    reference: OhadaReference  # Référence hiérarchique
    pdf_path: Optional[str]    # Chemin PDF source
```

**Métadonnées typiques**:
```python
{
    "partie": 1,
    "chapitre": 5,
    "title": "L'amortissement des immobilisations",
    "document_type": "chapitre",
    "parent_id": "partie_1",
    "page_debut": 142,
    "page_fin": 158,
    "pdf_path": "./plan_comptable/partie_1/chapitre_5.pdf"
}
```

### 7.3 Embeddings

**Modèle**: BGE-M3 (BAAI/bge-m3)

**Caractéristiques**:
- **Dimensions**: 1024
- **Context window**: 8192 tokens
- **Multilingue**: Oui (optimisé chinois/anglais, bon français)
- **Type**: Dense retrieval
- **Performance**: NDCG@10 = 0.651 sur BEIR

**Génération**:
```python
embedder = OhadaEmbedder(model_name="BAAI/bge-m3")
embedding = embedder.generate_embedding(text)
# → List[float] de longueur 1024
```

**Stockage ChromaDB**:
```python
collection.add(
    ids=[doc.id],
    documents=[doc.text],
    metadatas=[doc.metadata],
    embeddings=[embedding]  # Vector 1024D
)
```

---

## 8. API FastAPI

### 8.1 Structure Routes

```python
# Routes principales
@app.get("/")                      # Status API
@app.get("/status")                # Status détaillé
@app.post("/query")                # Requête principale
@app.get("/stream")                # Streaming SSE
@app.get("/history")               # Historique

# Authentification (src/api/auth_routes.py)
@router.post("/auth/register")     # Enregistrement
@router.post("/auth/login")        # Connexion
@router.post("/auth/logout")       # Déconnexion
@router.get("/auth/me")            # Info utilisateur

# Conversations (src/api/conversations_api.py)
@router.get("/conversations")                      # Liste
@router.post("/conversations")                     # Créer
@router.get("/conversations/{id}")                 # Détails
@router.put("/conversations/{id}")                 # Mettre à jour
@router.delete("/conversations/{id}")              # Supprimer
@router.get("/conversations/{id}/messages")        # Messages
@router.post("/conversations/{id}/messages")       # Ajouter message
@router.delete("/conversations/{id}/messages/{msg_id}") # Supprimer message

# Admin
@router.get("/admin/stats")        # Statistiques
@router.get("/admin/cache-stats")  # Stats cache
@router.get("/admin/cleanup")      # Nettoyage
@router.get("/admin/models")       # Info modèles

# Test
@router.post("/test/intent")       # Test classification
@router.post("/test/search")       # Test recherche
```

### 8.2 Modèles Pydantic

```python
class QueryRequest(BaseModel):
    query: str
    partie: Optional[int] = None
    chapitre: Optional[int] = None
    n_results: int = Field(default=5, ge=1, le=20)
    include_sources: bool = True
    stream: bool = False
    save_to_conversation: Optional[str] = None
    create_conversation: bool = True

class QueryResponse(BaseModel):
    id: str
    query: str
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    performance: Dict[str, float]
    timestamp: float
    conversation_id: Optional[str] = None
    user_message_id: Optional[str] = None
    ia_message_id: Optional[str] = None
```

### 8.3 Streaming SSE

**Endpoint**: `GET /stream?query=...&_token=...`

**Format événements**:
```
event: start
data: {"id": "uuid", "query": "...", "timestamp": 1234567890.123}

event: progress
data: {"status": "analyzing_intent", "completion": 0.05}

event: progress
data: {"status": "retrieving", "completion": 0.1}

event: chunk
data: {"text": "Le calcul de l'amortissement", "completion": 0.45}

event: chunk
data: {"text": " linéaire se fait", "completion": 0.50}

event: complete
data: {"id": "uuid", "query": "...", "answer": "...", "sources": [...], ...}
```

**Authentification streaming**:
```
GET /stream?query=...&_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 9. Authentification et Sécurité

### 9.1 JWT Manager (`src/auth/jwt_manager.py`)

**Algorithme**: HS256 (HMAC + SHA-256)

**Secret Key**: Variable env `JWT_SECRET_KEY` (auto-générée si absente)

**Structure token**:
```python
payload = {
    "sub": user_id,          # Subject (user ID)
    "email": user.email,     # Email utilisateur
    "exp": now + 24h,        # Expiration 24h
    "iat": now,              # Issued at
    "type": "access"         # Type de token
}
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
```

**Méthodes**:
```python
create_access_token(user_id, expires_delta=timedelta(hours=24)) → str
decode_token(token: str) → Dict
revoke_token(token: str) → bool
is_token_revoked(token: str) → bool
```

### 9.2 Database Manager (`src/db/db_manager.py`)

**Backend**: SQLite (développement) ou PostgreSQL (production)

**Tables**:

```sql
-- Utilisateurs
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,          -- Hashed avec bcrypt
    google_id TEXT UNIQUE,       -- OAuth Google
    created_at TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN
);

-- Conversations
CREATE TABLE conversations (
    conversation_id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(user_id),
    title TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Messages
CREATE TABLE messages (
    message_id TEXT PRIMARY KEY,
    conversation_id TEXT REFERENCES conversations(conversation_id),
    user_id TEXT REFERENCES users(user_id),
    content TEXT,
    is_user BOOLEAN,             -- True = user, False = IA
    metadata JSON,               -- Performance, sources, intent
    created_at TIMESTAMP
);

-- Tokens révoqués
CREATE TABLE revoked_tokens (
    token_id TEXT PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    revoked_at TIMESTAMP,
    expires_at TIMESTAMP
);
```

**Méthodes principales**:
```python
# Utilisateurs
create_user(email, password=None, google_id=None) → str
get_user(user_id) → Dict
get_user_by_email(email) → Dict
verify_password(user_id, password) → bool

# Conversations
create_conversation(user_id, title) → str
get_conversations(user_id) → List[Dict]
update_conversation(conversation_id) → bool
delete_conversation(conversation_id) → bool

# Messages
add_message(conversation_id, user_id, content, is_user, metadata=None) → str
get_messages(conversation_id) → List[Dict]

# Stats
get_statistics() → Dict
```

### 9.3 Password Utils (`src/auth/password_utils.py`)

**Algorithme**: bcrypt (cost factor 12)

```python
hash_password(password: str) → str
# → "$2b$12$..."

verify_password(password: str, hashed: str) → bool
# → True/False
```

---

## 10. Optimisations et Cache

### 10.1 Redis Cache (`src/utils/redis_cache.py`)

**Classe**: `RedisCache`

**Configuration**:
```python
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6382")
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=False)
```

**Caches implémentés**:

#### Query Cache
```python
set_query_cache(query, response, filters, ttl=3600)
# Key: "query:hash(query+filters)"
# Value: JSON response
# TTL: 1 heure

get_query_cache(query, filters) → Dict
# Retourne réponse cachée ou None
```

**Gain**: 95-98% réduction latence sur requêtes répétées (~2500ms → ~50ms)

#### Embedding Cache
```python
set_embedding(text, embedding, ttl=86400)
# Key: "embedding:hash(text)"
# Value: pickle(embedding)
# TTL: 24 heures

get_embedding(text) → List[float]
# Retourne embedding caché ou None
```

**Gain**: ~50-150ms par embedding (API) ou ~10-30ms (local)

**Métriques**:
```python
get_stats() → Dict
# {
#   "enabled": True,
#   "total_queries": 1234,
#   "cache_hits": 567,
#   "cache_misses": 667,
#   "hit_rate": 45.9  # %
# }
```

### 10.2 Local Embedding Cache (`src/utils/ohada_cache.py`)

**Classe**: `EmbeddingCache` (dict avec FIFO)

```python
class EmbeddingCache:
    def __init__(self, max_size=100):
        self.cache = {}  # {hash(text): embedding}
        self.max_size = max_size

    def get(text_hash) → List[float]
    def set(text_hash, embedding) → None
    # Éviction FIFO si taille > max_size
```

**Cascade cache** (dans `VectorRetriever.get_embedding`):
```python
1. Redis cache (~1-2ms)
2. Local cache (~0.1ms)
3. Génération (~50-150ms API, ~10-30ms local)
```

### 10.3 Warm-up Startup

**Dans `ohada_api_server.py`**:

```python
@app.on_event("startup")
async def startup_event():
    """Préchargement modèles au démarrage"""

    # 1. Charger retriever (charge index BM25)
    retriever = get_retriever()

    # 2. Précharger cross-encoder
    retriever.reranker.load_model()

    # 3. Warm-up query de test
    retriever.search_hybrid(
        query="test warmup syscohada",
        n_results=1,
        rerank=True
    )
    # → Première requête utilisateur aussi rapide que suivantes
```

**Gain**: Évite latence ~200-500ms sur première requête.

---

## 11. Dépendances Python

### 11.1 Core Framework

```
fastapi==0.115.11           # Framework API
uvicorn==0.34.0             # Serveur ASGI
pydantic==2.10.6            # Validation données
python-dotenv==1.0.1        # Variables environnement
```

### 11.2 LLM & Embeddings

```
openai==1.65.4              # Client OpenAI API
litellm==1.60.2             # Multi-provider LLM
sentence-transformers==3.4.1 # BGE-M3, cross-encoder
transformers==4.49.0        # HuggingFace models
torch==2.6.0                # PyTorch backend
```

### 11.3 Recherche & Retrieval

```
chromadb==0.5.23            # Base vectorielle
rank-bm25==0.2.2            # BM25 algorithm
langchain==0.3.20           # Framework RAG
langchain-community==0.3.19 # Intégrations
langchain-core==0.3.42      # Core langchain
```

### 11.4 Base de Données

```
psycopg2-binary==2.9.10     # PostgreSQL driver
SQLAlchemy==2.0.38          # ORM
alembic==1.15.1             # Migrations
redis==5.2.1                # Cache Redis
```

### 11.5 Authentification

```
PyJWT==2.10.1               # JSON Web Tokens
bcrypt==4.3.0               # Password hashing
cryptography==44.0.2        # Cryptographie
```

### 11.6 Document Processing

```
pypdf==5.3.1                # Parsing PDF
pdfplumber==0.11.5          # Extraction PDF
beautifulsoup4==4.13.3      # Parsing HTML
python-docx==1.1.2          # Parsing Word
openpyxl==3.1.5             # Parsing Excel
```

### 11.7 Utilities

```
numpy==2.2.3                # Calculs numériques
pandas==2.2.3               # DataFrames
scikit-learn==1.6.1         # ML utils
tqdm==4.67.1                # Progress bars
requests==2.32.3            # HTTP client
```

**Fichier complet**: `requirements.txt` (242 lignes, voir fichier source)

---

## 12. Configuration et Environnements

### 12.1 Variables d'Environnement

**Fichier**: `.env` (à la racine projet)

```bash
# Environnement (test ou production)
OHADA_ENV=test

# Clés API LLM
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...

# JWT
JWT_SECRET_KEY=votre_secret_jwt_aleatoire

# OAuth Google (optionnel)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Base de données (optionnel, SQLite par défaut)
DATABASE_URL=postgresql://user:pass@localhost:5432/ohada

# Redis (optionnel)
REDIS_URL=redis://localhost:6382

# Serveur
HOST=0.0.0.0
PORT=8000
RELOAD=true

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Admin
ADMIN_EMAILS=admin@example.com

# Paths (optionnel)
OHADA_DB_PATH=./data/ohada_users.db
OHADA_CONFIG_PATH=./src/config
```

### 12.2 Différences Test vs Production

| Aspect | Test (OHADA_ENV=test) | Production (OHADA_ENV=production) |
|--------|----------------------|----------------------------------|
| **LLM principal** | deepseek-chat | gpt-4-turbo-preview |
| **Embedding model** | BAAI/bge-m3 (local) | Alibaba-NLP/gte-Qwen2-1.5B-instruct |
| **Embedding dim** | 1024 | 1536 |
| **Max tokens** | 1500 | 2000 |
| **Temperature** | 0.3 | 0.2 |
| **Log level** | DEBUG | INFO |
| **Base de données** | SQLite | PostgreSQL |
| **Redis** | Optionnel | Recommandé |
| **Reload** | true | false |

### 12.3 Configuration ChromaDB

**Localisation**: `backend/chroma_db/` (persisté sur disque)

**Initialisation**:
```python
import chromadb
client = chromadb.PersistentClient(path="backend/chroma_db")
```

**Settings implicites**:
- `anonymized_telemetry`: false
- `allow_reset`: true (développement)
- `is_persistent`: true

---

## 13. Scripts d'Ingestion

### 13.1 `scripts/import_document.py`

**Usage**: Import document PDF unique dans ChromaDB

```bash
python scripts/import_document.py \
    --pdf path/to/document.pdf \
    --partie 1 \
    --chapitre 5 \
    --title "L'amortissement des immobilisations" \
    --env test
```

**Workflow**:
```python
1. Parser PDF (pdfplumber)
2. Extraction texte par page
3. Chunking intelligent (512 tokens, overlap 50)
4. Génération métadonnées
5. Génération embeddings BGE-M3
6. Stockage ChromaDB (collection selon partie/type)
```

### 13.2 `scripts/import_all_documents.py`

**Usage**: Import batch de tous documents

```bash
cd backend
python scripts/import_all_documents.py --env test
```

**Structure attendue**:
```
plan_comptable/
├── presentation/
│   ├── presentation_ohada.pdf
│   └── traite_relatif.pdf
├── partie_1/
│   ├── chapitre_1.pdf
│   ├── chapitre_2.pdf
│   └── ...
├── partie_2/
│   └── ...
└── ohada_toc.json  # Table des matières
```

**Workflow**:
```python
1. Scan répertoires partie_1/ à partie_4/
2. Pour chaque PDF:
   a. Extraction texte
   b. Enrichissement métadonnées (depuis TOC)
   c. Chunking adaptatif
   d. Génération embeddings
   e. Stockage collection appropriée
3. Logs détaillés + statistiques finales
```

### 13.3 `scripts/ingest_to_chromadb.py`

**Usage**: Ingestion spécialisée avec options avancées

```bash
python scripts/ingest_to_chromadb.py \
    --source ./documents \
    --collection chapitres \
    --chunk-size 512 \
    --overlap 50 \
    --batch-size 8 \
    --env test
```

**Options**:
- `--chunk-size`: Taille chunks (tokens)
- `--overlap`: Recouvrement entre chunks
- `--batch-size`: Taille batch embeddings
- `--collection`: Collection cible
- `--reset`: Réinitialiser collection avant import

---

## 14. Guide de Reproduction

### 14.1 Prérequis

**Système**:
- Python 3.10+
- 8 GB RAM minimum (16 GB recommandé pour BGE-M3)
- 10 GB espace disque (modèles + ChromaDB)

**Logiciels**:
- Git
- Python venv ou conda
- PostgreSQL 15+ (production, optionnel en test)
- Redis 7+ (optionnel)

### 14.2 Installation Étape par Étape

#### Étape 1: Cloner la structure

```bash
# Créer projet KAURI
mkdir kauri
cd kauri

# Créer structure backend
mkdir -p backend/src/{api,auth,config,db,document_parser,generation,models,retrieval,tasks,utils,vector_db}
mkdir -p backend/scripts
mkdir -p backend/chroma_db
mkdir -p backend/data
mkdir -p backend/plan_comptable/{presentation,partie_1,partie_2,partie_3,partie_4}
```

#### Étape 2: Copier les fichiers sources

**Depuis OHAD'AI, copier**:

```bash
# Modules Python
cp -r ohada/backend/src/* kauri/backend/src/

# Scripts
cp -r ohada/backend/scripts/* kauri/backend/scripts/

# Configurations
cp ohada/backend/src/config/*.yaml kauri/backend/src/config/

# Scripts de démarrage
cp ohada/backend/start.bat kauri/backend/  # Windows
cp ohada/backend/start.sh kauri/backend/   # Linux

# Requirements
cp ohada/requirements.txt kauri/
```

#### Étape 3: Environnement virtuel

```bash
cd kauri/backend

# Créer venv
python -m venv venv

# Activer
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer dépendances
pip install -r ../requirements.txt
```

**⏱️ Durée**: ~10-15 minutes (téléchargement PyTorch, transformers, etc.)

#### Étape 4: Configuration environnement

```bash
# Créer .env
cat > .env << EOF
# Environnement
OHADA_ENV=test

# Clés API (OBLIGATOIRES)
OPENAI_API_KEY=sk-votre-cle-openai
DEEPSEEK_API_KEY=sk-votre-cle-deepseek

# JWT (généré automatiquement si absent)
JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Serveur
HOST=0.0.0.0
PORT=8000
RELOAD=true

# CORS
CORS_ORIGINS=*

# Paths
OHADA_DB_PATH=./data/ohada_users.db
OHADA_CONFIG_PATH=./src/config
EOF
```

#### Étape 5: Initialisation base vectorielle

```bash
# Test modèle BGE-M3
python -c "from src.vector_db.ohada_vector_db_structure import OhadaEmbedder; e = OhadaEmbedder('BAAI/bge-m3'); print(f'Dim: {e.embedding_dimension}')"

# Expected output:
# Chargement du modèle d'embedding: BAAI/bge-m3
# Modèle chargé: dimension 1024
# Dim: 1024
```

**⏱️ Durée première fois**: ~2-5 minutes (téléchargement BGE-M3, ~2GB)

#### Étape 6: Initialisation base SQL

```bash
# La base SQLite sera créée automatiquement au premier démarrage
# Pas de migration nécessaire
```

#### Étape 7: Ingestion documents (optionnel)

```bash
# Si vous avez des PDFs OHADA:
python scripts/import_all_documents.py

# Sinon, créer quelques documents de test:
python scripts/ingest_to_chromadb.py --source ./test_docs --env test
```

**⏱️ Durée**: Variable selon nombre de documents (exemple: 100 PDFs = ~20-30 min)

#### Étape 8: Démarrage serveur

```bash
# Windows
.\start.bat

# Linux/Mac
chmod +x start.sh
./start.sh

# Ou directement:
set PYTHONPATH=%CD%  # Windows
export PYTHONPATH=$(pwd)  # Linux/Mac

python -m uvicorn src.api.ohada_api_server:app --host 0.0.0.0 --port 8000 --reload
```

**Logs de démarrage attendus**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Démarrage du serveur API en environnement: test
INFO:     Environnement test: utilisation du modèle d'embedding BAAI/bge-m3 (provider: local_embedding)
INFO:     ============================================================
INFO:     Démarrage du warm-up du serveur...
INFO:     ============================================================
INFO:     1/3 - Chargement du retriever hybride...
INFO:     ✓ Retriever hybride chargé
INFO:     2/3 - Chargement du cross-encoder...
INFO:     ✓ Cross-encoder chargé
INFO:     3/3 - Warm-up avec requête de test...
INFO:     ✓ Warm-up query réussi
INFO:     ============================================================
INFO:     ✓ Serveur prêt à traiter les requêtes
INFO:     ============================================================
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

#### Étape 9: Test endpoints

```bash
# Test status
curl http://localhost:8000/status

# Test query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Comment calculer l amortissement?", "n_results": 3}'

# Test streaming (dans navigateur)
http://localhost:8000/stream?query=Comment+calculer+amortissement&n_results=3
```

**Réponse attendue `/status`**:
```json
{
  "status": "online",
  "environment": "test",
  "timestamp": "2025-11-03T10:30:45.123456",
  "databases": {
    "vector_db": {
      "status": "online",
      "collections": {
        "syscohada_plan_comptable": 500,
        "partie_1": 1200,
        ...
      }
    },
    "sql": {
      "status": "online",
      "total_users": 0,
      "total_conversations": 0
    }
  },
  "models": {
    "llm": {
      "provider": "deepseek",
      "model": "deepseek-chat"
    },
    "embedding": {
      "provider": "local_embedding",
      "model": "BAAI/bge-m3"
    }
  }
}
```

### 14.3 Configuration Production

**Différences clés**:

```bash
# .env production
OHADA_ENV=production
DATABASE_URL=postgresql://user:pass@localhost:5432/kauri
REDIS_URL=redis://localhost:6379
RELOAD=false
CORS_ORIGINS=https://kauri.example.com

# llm_config_production.yaml
# → Embedding: gte-Qwen2-1.5B-instruct (1536 dim)
# → LLM: gpt-4-turbo-preview
# → Max tokens: 2000
```

**Services additionnels**:

```bash
# PostgreSQL
docker run -d \
  --name kauri-postgres \
  -e POSTGRES_USER=kauri_user \
  -e POSTGRES_PASSWORD=secure_password \
  -e POSTGRES_DB=kauri \
  -p 5432:5432 \
  postgres:15

# Redis
docker run -d \
  --name kauri-redis \
  -p 6379:6379 \
  redis:7-alpine
```

**Démarrage production**:

```bash
# Avec Gunicorn + Uvicorn workers
pip install gunicorn

gunicorn src.api.ohada_api_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --log-level info \
  --access-logfile /var/log/kauri/access.log \
  --error-logfile /var/log/kauri/error.log
```

### 14.4 Vérification Installation

**Checklist**:

- [ ] Serveur démarre sans erreur
- [ ] `/status` retourne 200 avec infos modèles
- [ ] BGE-M3 chargé (dimension 1024)
- [ ] Collections ChromaDB créées (7 collections)
- [ ] `/query` retourne réponse + sources
- [ ] `/stream` fonctionne (SSE)
- [ ] Warm-up query réussie au startup
- [ ] Cache Redis actif (si configuré)
- [ ] Authentification fonctionne (si activée)
- [ ] Conversations sauvegardées (si auth activée)

**Tests unitaires** (si disponibles):

```bash
cd backend
pytest tests/ -v
```

---

## 15. Métriques de Performance

### 15.1 Latences Typiques

**Sans cache** (première requête):
```
Reformulation query:     ~500-800ms    (LLM)
Recherche hybride:       ~800-1200ms   (BM25 + Vector + Reranking)
  - BM25:                ~100-200ms
  - Vector search:       ~200-400ms    (embedding inclus)
  - Dedup + combine:     ~50-100ms
  - Reranking:           ~300-500ms    (cross-encoder)
Traitement contexte:     ~100-200ms
Génération réponse:      ~1000-2000ms  (DeepSeek LLM)
─────────────────────────────────────
TOTAL:                   ~2400-4200ms
```

**Avec cache Redis** (requête répétée):
```
Vérification cache:      ~1-5ms
Retour réponse cachée:   ~10-50ms
─────────────────────────────────────
TOTAL:                   ~11-55ms      (gain 99%)
```

**Avec embedding cache**:
```
Embedding depuis Redis:  ~1-2ms        (vs ~50-150ms API ou ~10-30ms local)
```

### 15.2 Optimisations Implémentées

| Optimisation | Gain | Localisation |
|--------------|------|--------------|
| Warm-up startup | ~200-500ms première requête | `ohada_api_server.py:97` |
| Cache Redis queries | 95-98% latence | `redis_cache.py`, `ohada_api_server.py:389` |
| Cache embeddings | ~50-150ms par embedding | `vector_retriever.py:48` |
| Génération 1 étape | ~800-1200ms | `response_generator.py:23` |
| Parallel search | ~400-600ms | `ohada_hybrid_retriever.py:169` |
| BGE-M3 local | ~40-120ms vs API | `ohada_vector_db_structure.py:42` |
| Batch embeddings | ~30% vs séquentiel | `ohada_vector_db_structure.py:116` |
| Singleton embedder | ~200-500ms | `ohada_vector_db_structure.py:46` |

---

## 16. Troubleshooting

### 16.1 Problèmes Courants

#### Backend ne démarre pas

**Symptôme**: Erreur au démarrage

**Solutions**:
```bash
# 1. Vérifier clés API
echo $DEEPSEEK_API_KEY  # Doit être défini

# 2. Vérifier PYTHONPATH
set PYTHONPATH=%CD%  # Windows
export PYTHONPATH=$(pwd)  # Linux

# 3. Vérifier port libre
netstat -an | findstr 8000  # Windows
lsof -i :8000  # Linux

# 4. Logs détaillés
python -m uvicorn src.api.ohada_api_server:app --log-level debug
```

#### ChromaDB vide

**Symptôme**: `/status` montre 0 documents

**Solutions**:
```bash
# 1. Vérifier répertoire ChromaDB
ls backend/chroma_db/

# 2. Réimporter documents
cd backend
python scripts/import_all_documents.py

# 3. Vérifier collections
python -c "from src.vector_db.ohada_vector_db_structure import OhadaVectorDB; db = OhadaVectorDB(); print(db.get_collection_stats())"
```

#### BGE-M3 ne se charge pas

**Symptôme**: Erreur "Failed to load model"

**Solutions**:
```bash
# 1. Téléchargement manuel
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

# 2. Vérifier espace disque
df -h  # Linux
dir  # Windows

# 3. Fallback OpenAI embeddings
# Dans llm_config_test.yaml, mettre:
embedding_provider_priority:
  - "openai"
  - "local_embedding"
```

#### Redis non disponible

**Symptôme**: Warning "Redis connection refused"

**Action**: C'est normal, Redis est optionnel. Pour activer:

```bash
# Docker
docker run -d -p 6382:6379 redis:7-alpine

# Variable env
export REDIS_URL=redis://localhost:6382
```

### 16.2 Logs Utiles

```bash
# Logs API
tail -f backend/ohada_api_test.log

# Logs Uvicorn
python -m uvicorn src.api.ohada_api_server:app --log-level debug 2>&1 | tee server.log

# Logs par module
import logging
logging.getLogger("ohada_hybrid_retriever").setLevel(logging.DEBUG)
```

---

## 17. Références Techniques

### 17.1 Modèles Utilisés

| Modèle | Usage | Source | Taille |
|--------|-------|--------|--------|
| BGE-M3 | Embeddings | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) | ~2 GB |
| Cross-Encoder | Reranking | [ms-marco-MiniLM-L-6-v2](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L-6-v2) | ~90 MB |
| DeepSeek-Chat | LLM | [DeepSeek API](https://platform.deepseek.com) | API |
| GPT-3.5/4 | LLM | [OpenAI API](https://platform.openai.com) | API |

### 17.2 Algorithmes Clés

**BM25**:
- Okapi BM25 (Robertson et al., 1995)
- k1=1.5, b=0.75
- Library: `rank-bm25`

**Embeddings**:
- Dense retrieval (Karpukhin et al., 2020)
- BGE-M3: RetroMAE + Multi-stage training
- Dimension: 1024 (test), 1536 (prod)

**Reranking**:
- Cross-encoder (Nogueira & Cho, 2019)
- Fine-tuned on MS MARCO
- Pairwise scoring

**Hybrid Search**:
- Score combiné: α×BM25 + (1-α)×Vector (α=0.5)
- Fusion tardive (late fusion)
- Reranking final

### 17.3 Métriques d'Évaluation

**NDCG@10**: Normalized Discounted Cumulative Gain
- BGE-M3 sur BEIR: 0.651
- Baseline BM25: 0.45-0.50
- Hybrid + Rerank: 0.70-0.75 (estimé)

**Precision@5**: Parmi top 5, % pertinents
- Cible: > 80%

**Recall@10**: Parmi tous pertinents, % dans top 10
- Cible: > 70%

**MRR**: Mean Reciprocal Rank
- Cible: > 0.85

---

## Conclusion

Ce document constitue la **documentation exhaustive de l'architecture backend OHAD'AI** pour reproduction dans le projet **KAURI**.

**Points clés**:
- ✅ Architecture RAG hybride (BM25 + Vector + Reranking)
- ✅ Embeddings locaux BGE-M3 (1024 dim, 8192 tokens)
- ✅ LLM DeepSeek + OpenAI fallback
- ✅ API FastAPI avec streaming SSE
- ✅ Authentification JWT optionnelle
- ✅ Cache Redis distribué (95-98% gain latence)
- ✅ 7 collections ChromaDB
- ✅ Optimisations multiples (~2-4s → ~0.05s avec cache)

**Prochaines étapes pour KAURI**:
1. Adapter domaine métier (remplacer comptabilité OHADA par votre domaine)
2. Réimporter corpus de documents spécifiques
3. Ajuster prompts et personnalité assistant
4. Tester et affiner paramètres de recherche
5. Développer nouveau frontend adapté

---

**Date de dernière mise à jour**: 2025-11-03
**Version**: 1.0
**Auteur**: Documentation générée depuis OHAD'AI Expert-Comptable
