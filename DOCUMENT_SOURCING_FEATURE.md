# Feature: Document Sourcing pour Kauri

## Résumé

Cette fonctionnalité permet à Kauri de répondre à des questions de type "sourcing" où l'utilisateur cherche à savoir **quels documents** traitent d'un sujet particulier, plutôt que d'obtenir une réponse directe sur le sujet.

## Exemples de Questions Supportées

- "Dans quels documents parle-t-on des amortissements ?"
- "Existe-t-il une jurisprudence sur la comptabilité des stocks ?"
- "Quels documents traitent des provisions ?"
- "Liste-moi les actes uniformes sur le droit commercial"
- "Où puis-je trouver des infos sur les immobilisations ?"

## Architecture Technique

### 1. Nouveau Intent: `document_sourcing`

**Fichier**: `backend/kauri_chatbot_service/src/rag/agents/intent_classifier.py`

- Ajout du type d'intent `document_sourcing` aux Literal types
- Mise à jour du system prompt pour détecter les questions de sourcing
- Le classifier retourne les keywords et category_filter au format JSON dans `direct_answer`

### 2. Schema Enrichi pour SourceDocument

**Fichier**: `backend/kauri_chatbot_service/src/schemas/chat.py`

Nouveaux champs ajoutés:
```python
category: Optional[str]          # Type de document (plan_comptable, acte_uniforme, etc.)
section: Optional[str]           # Section/subsection
file_path: Optional[str]         # Chemin du fichier source
document_type: Optional[str]     # Alias pour category
metadata_summary: Optional[Dict] # Métadonnées additionnelles (livre, titre, article)
```

### 3. Node document_sourcing dans le Workflow

**Fichier**: `backend/kauri_chatbot_service/src/rag/agents/rag_workflow.py`

Le node `_document_sourcing_node()` :
1. Extrait les keywords du direct_answer de l'intent
2. Récupère plus de documents que d'habitude (top_k * 3)
3. Filtre par catégorie si spécifié
4. Déduplique par file_path
5. Groupe les documents par catégorie
6. Formate une réponse structurée listant les documents trouvés

### 4. Méthode de Conversion Enrichie

**Fichier**: `backend/kauri_chatbot_service/src/rag/pipeline/rag_pipeline.py`

Nouvelle méthode `_convert_to_source_documents_enriched()` qui inclut toutes les métadonnées enrichies dans les objets SourceDocument retournés.

## Format de Réponse

Quand l'intent `document_sourcing` est détecté, Kauri répond avec :

```
J'ai trouvé **12 document(s)** pertinent(s) sur ce sujet :

### 📊 Plan Comptable OHADA (5 document(s))
1. **Plan Comptable / Partie 4 / Chapitre 7 : Comptes d'amortissements** (pertinence: 0.95)
2. **Plan Comptable / Partie 1 / Chapitre 5 : Opérations d'investissement** (pertinence: 0.89)
...

### 📜 Actes Uniformes (3 documents)
1. **Actes Uniformes / Droit Comptable / Titre 2 : Amortissements** (pertinence: 0.92)
...

### 📚 Doctrine (2 documents)
...

### ⚖️ Jurisprudence (2 documents)
...

💡 *Tu peux me demander des détails sur un document spécifique ou poser une question précise sur le sujet.*
```

## Métadonnées Retournées

La réponse inclut les métadonnées suivantes:
```json
{
  "intent_type": "document_sourcing",
  "sourcing_mode": true,
  "num_sources": 12,
  "keywords_used": ["amortissements"],
  "categories_found": ["plan_comptable", "acte_uniforme", "doctrine"],
  "retrieval_performed": true
}
```

## Support Streaming

La fonctionnalité est également disponible en mode streaming via `/api/v1/chat/stream`.

## Tests

### Tests de Classification d'Intent

Le classifier détecte correctement:
- ✅ "Dans quels documents..." → `document_sourcing` (confidence: 0.98)
- ✅ "Existe-t-il une jurisprudence..." → `document_sourcing` (confidence: 0.95)
- ✅ "C'est quoi un amortissement ?" → `rag_query` (confidence: 0.98)
- ✅ "Bonjour" → `general_conversation` (confidence: 1.0)

### Logs de Succès

```
[info] intent_classification_complete
       confidence=0.98
       intent_type=document_sourcing
       query=Dans quels documents parle-t-on des amortissements ?

[info] workflow_routing
       confidence=0.98
       intent_type=document_sourcing

[info] workflow_document_sourcing_complete
       num_categories=1
       num_documents=4

[info] workflow_execute_complete
       has_error=False
       intent_type=document_sourcing
```

## Fichiers Modifiés

1. `backend/kauri_chatbot_service/src/schemas/chat.py` - Enrichissement SourceDocument
2. `backend/kauri_chatbot_service/src/rag/agents/intent_classifier.py` - Nouveau intent
3. `backend/kauri_chatbot_service/src/rag/agents/rag_workflow.py` - Node + routing + streaming
4. `backend/kauri_chatbot_service/src/rag/pipeline/rag_pipeline.py` - Méthode enrichie

## Notes d'Implémentation

### Gestion du direct_answer

Le champ `direct_answer` dans `IntentClassification` accepte maintenant:
- `str` pour general_conversation et clarification
- `dict` pour document_sourcing (contenant keywords et category_filter)
- `None` pour rag_query

### Filtre par Catégorie

Le classifier peut extraire la catégorie de document demandée:
```json
{
  "keywords": ["stocks"],
  "category_filter": "jurisprudence"
}
```

Catégories supportées:
- `doctrine`
- `jurisprudence`
- `acte_uniforme`
- `plan_comptable`

### Performance

- Récupération de plus de documents (top_k * 3) pour avoir une vue exhaustive
- Déduplication par file_path pour éviter les doublons
- Limitation à 30 documents maximum dans la réponse
- Maximum 10 documents affichés par catégorie

## Améliorations Futures Possibles

1. **Filtrage avancé** : Par date, par article spécifique, etc.
2. **Recherche multi-critères** : Combiner plusieurs keywords
3. **Suggestions de documents liés** : "Les utilisateurs qui ont consulté ce document ont également consulté..."
4. **Export des listes** : Permettre d'exporter la liste des documents en PDF/CSV
5. **Hiérarchie de documents** : Afficher la structure complète (Livre > Titre > Chapitre > Article)

## Status

✅ **Implémenté et Testé** - La fonctionnalité est opérationnelle en production.
