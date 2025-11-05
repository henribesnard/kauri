# Architecture de Classification d'Intention KAURI

## Vue d'ensemble

Le système KAURI utilise maintenant une architecture avancée basée sur **LangGraph** et **LLM-based intent classification** au lieu de patterns statiques.

## Pourquoi cette approche ?

### Problème des patterns statiques
❌ Ne couvre pas tous les cas possibles
❌ Nécessite maintenance manuelle
❌ Pas d'apprentissage ou d'adaptation
❌ Faux positifs/négatifs fréquents

### Solution : Intent Classifier Agent
✅ Classification dynamique par LLM
✅ S'adapte à toutes les formulations
✅ Haute précision avec raisonnement
✅ Extensible sans code changes

---

## Architecture Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│              CLASSIFY_INTENT NODE                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Intent Classifier Agent (LLM: gpt-4o-mini)          │  │
│  │  ─────────────────────────────────────────────────   │  │
│  │  Prompt: Analyser l'intention de l'utilisateur      │  │
│  │                                                       │  │
│  │  Output: {                                           │  │
│  │    intent_type: "general_conversation" | "rag_query" │  │
│  │                  | "clarification",                  │  │
│  │    confidence: 0.0-1.0,                              │  │
│  │    reasoning: "Explication..."                       │  │
│  │  }                                                    │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│              ROUTE_BY_INTENT (Conditional Edge)            │
└─────┬────────────────┬────────────────────┬────────────────┘
      │                │                    │
      ▼                ▼                    ▼
┌───────────────┐ ┌──────────────────┐ ┌─────────────────┐
│ DIRECT        │ │ RETRIEVE &       │ │ ASK             │
│ RESPONSE      │ │ GENERATE         │ │ CLARIFICATION   │
│               │ │                  │ │                 │
│ • No RAG      │ │ • Hybrid Search  │ │ • Message asking│
│ • LLM only    │ │ • Reranking      │ │   for more      │
│ • Fast        │ │ • Context        │ │   context       │
│               │ │ • LLM with docs  │ │                 │
└───────┬───────┘ └────────┬─────────┘ └────────┬────────┘
        │                  │                    │
        └──────────────────┼────────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Final Answer  │
                  │  + Sources     │
                  │  + Metadata    │
                  └────────────────┘
```

---

## Types d'Intention

### 1. **general_conversation**
Questions qui ne nécessitent PAS de recherche dans la documentation OHADA.

**Exemples:**
- "Bonjour"
- "Qui es-tu ?"
- "Quel est ton rôle ?"
- "Merci beaucoup"
- "Comment ça va ?"

**Traitement:**
- Pas de recherche RAG
- Réponse directe du LLM avec system prompt
- Latence réduite
- `sources: []`

---

### 2. **rag_query**
Questions techniques nécessitant la documentation OHADA.

**Exemples:**
- "C'est quoi un amortissement ?"
- "Comment comptabiliser une créance douteuse ?"
- "Article 15 du SYSCOHADA"
- "Différence entre classe 2 et classe 3 ?"

**Traitement:**
- Recherche hybride (BM25 + Semantic)
- Reranking avec cross-encoder
- Context preparation
- LLM avec documentation
- Sources avec scores

---

### 3. **clarification**
Questions ambiguës nécessitant plus de contexte.

**Exemples:**
- "Qu'est-ce que c'est ?"
- "Peux-tu m'expliquer ?"
- "Et après ?"
- "Comment ça marche ?"

**Traitement:**
- Message demandant des précisions
- Pas de recherche RAG
- Guide l'utilisateur vers une question plus précise

---

## Composants Clés

### 1. Intent Classifier Agent
**Fichier:** `src/rag/agents/intent_classifier.py`

```python
class IntentClassifierAgent:
    def __init__(self):
        # Utilise gpt-4o-mini pour classification rapide
        self.llm = ChatOpenAI(
            model=settings.llm_fallback_model,
            temperature=0  # Déterministe
        )

        # Structured output pour fiabilité
        self.classifier = self.llm.with_structured_output(
            IntentClassification
        )

    async def classify_intent(self, query: str) -> IntentClassification:
        # Classification avec reasoning
        ...
```

**Avantages:**
- Classification précise via LLM
- Structured output (Pydantic)
- Raisonnement explicable
- Fallback automatique en cas d'erreur

---

### 2. RAG Workflow (LangGraph)
**Fichier:** `src/rag/agents/rag_workflow.py`

```python
class RAGWorkflow:
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)

        # Nodes
        workflow.add_node("classify_intent", ...)
        workflow.add_node("direct_response", ...)
        workflow.add_node("retrieve_and_generate", ...)
        workflow.add_node("ask_clarification", ...)

        # Conditional routing
        workflow.add_conditional_edges(
            "classify_intent",
            self._route_by_intent,
            {...}
        )

        return workflow.compile()
```

**Avantages:**
- Graph-based orchestration
- Routing conditionnel
- State management
- Debuggable et traçable

---

### 3. RAG Pipeline (Intégration)
**Fichier:** `src/rag/pipeline/rag_pipeline.py`

```python
class RAGPipeline:
    def __init__(self, use_workflow: bool = True):
        # use_workflow=True : Intent-based routing
        # use_workflow=False : Legacy direct pipeline

        if self.use_workflow:
            self.workflow = RAGWorkflow(rag_pipeline=self)

    async def query(self, query: str, ...) -> Dict[str, Any]:
        if self.use_workflow and self.workflow:
            # Nouveau système avec intent classification
            return await self.workflow.execute(...)
        else:
            # Legacy pipeline (fallback)
            ...
```

---

## Dépendances

```txt
# LangGraph ecosystem
langgraph==0.2.60
langchain-openai==0.2.14
langchain==0.3.20
langchain-core==0.3.42
```

---

## Logs et Debugging

Le système produit des logs structurés à chaque étape :

```json
{
  "event": "intent_classification_complete",
  "query": "Qui es-tu ?",
  "intent_type": "general_conversation",
  "confidence": 0.95,
  "reasoning": "Question sur l'identité de KAURI, ne nécessite pas de documentation"
}
```

```json
{
  "event": "workflow_routing",
  "intent_type": "rag_query",
  "confidence": 0.98
}
```

---

## Metadata dans la Réponse

Chaque réponse contient maintenant :

```json
{
  "conversation_id": "uuid",
  "query": "...",
  "answer": "...",
  "sources": [...],
  "metadata": {
    "intent_type": "rag_query",
    "intent_confidence": 0.98,
    "intent_reasoning": "Question technique sur SYSCOHADA",
    "retrieval_time_ms": 245,
    "generation_time_ms": 1200,
    "num_sources": 5,
    "use_reranking": true,
    "model_used": "gpt-4o"
  }
}
```

---

## Avantages de l'Architecture

### 🎯 Précision
- Classification LLM > patterns statiques
- Confidence scores pour monitoring
- Raisonnement explicable

### ⚡ Performance
- Skip RAG pour questions générales
- Classification rapide (gpt-4o-mini)
- Latence optimisée

### 🔧 Maintenabilité
- Pas de patterns hardcodés
- Workflow visualisable
- Facile à étendre (nouveaux intent types)

### 📊 Observabilité
- Logs structurés
- Metadata riches
- Traçabilité complète

---

## Évolutions Futures

### Phase 1 (Actuel)
✅ Classification 3 types d'intention
✅ Routing conditionnel
✅ Intégration LangGraph

### Phase 2 (Possible)
- Multi-turn conversation support
- Intent history tracking
- Personalization par utilisateur

### Phase 3 (Avancé)
- Fine-tuning du classifier
- Multi-domain routing (comptabilité, juridique, fiscalité)
- Active learning from user feedback

---

## Configuration

Pour activer/désactiver le workflow :

```python
# Dans src/rag/pipeline/rag_pipeline.py
pipeline = RAGPipeline(use_workflow=True)  # Nouveau système
pipeline = RAGPipeline(use_workflow=False)  # Legacy
```

Le système est conçu pour être **backward-compatible** avec fallback automatique en cas d'erreur.

---

## Tests Recommandés

1. **Questions générales**
   - "Bonjour", "Qui es-tu ?", "Merci"
   - Vérifier : `sources: []`, latence < 1s

2. **Questions OHADA**
   - "C'est quoi un amortissement ?"
   - Vérifier : sources présentes, références correctes

3. **Questions ambiguës**
   - "Qu'est-ce que c'est ?"
   - Vérifier : message de clarification

4. **Edge cases**
   - Questions mixtes
   - Typos et variations
   - Questions multi-langues
