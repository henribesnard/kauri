# 🎯 Document Sourcing - Guide Complet

## ✅ Statut : OPÉRATIONNEL

La fonctionnalité de **Document Sourcing** est implémentée, testée et prête pour la production.

## 📋 Qu'est-ce que Document Sourcing ?

Cette fonctionnalité permet à Kauri de répondre aux questions du type :
- **"Dans quels documents parle-t-on des amortissements ?"**
- **"Existe-t-il une jurisprudence sur la comptabilité des stocks ?"**
- **"Quels documents traitent des provisions ?"**
- **"Liste-moi les actes uniformes sur le droit commercial"**

Au lieu de donner une réponse directe sur le concept, Kauri **liste les documents** pertinents groupés par catégorie.

## 🚀 Tests Rapides

### Option 1 : Script Python Complet (Recommandé)
```bash
python test_sourcing_complete.py
```

**Ce script teste** :
- ✅ Questions de document sourcing (non-stream)
- ✅ Questions de contrôle RAG/general (non-stream)
- ✅ Questions de document sourcing (stream)
- ✅ Questions de contrôle (stream)

### Option 2 : Script PowerShell (Windows)
```powershell
.\test_sourcing_curl.ps1
```

### Option 3 : Tests manuels avec curl

#### 1. S'authentifier
```bash
TOKEN=$(curl -s --request POST \
  --url http://localhost:3201/api/v1/auth/login \
  --header 'content-type: application/json' \
  --data '{
  "email": "henribesnard@example.com",
  "password": "Harena123456"
}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

echo $TOKEN
```

#### 2. Test Non-Stream
```bash
curl --request POST \
  --url http://localhost:3202/api/v1/chat/query \
  --header "authorization: Bearer $TOKEN" \
  --header 'content-type: application/json' \
  --data '{
  "query": "Dans quels documents parle-t-on des amortissements ?"
}'
```

#### 3. Test Stream
```bash
curl --request POST \
  --url http://localhost:3202/api/v1/chat/stream \
  --header "authorization: Bearer $TOKEN" \
  --header 'content-type: application/json' \
  --data '{
  "query": "Quels documents traitent des provisions ?"
}'
```

## 📊 Résultats Attendus

### Réponse de Document Sourcing

```json
{
  "conversation_id": "...",
  "query": "Dans quels documents parle-t-on des amortissements ?",
  "answer": "J'ai trouvé **4 document(s)** pertinent(s) sur ce sujet :\n\n### 📊 Plan Comptable OHADA (4 document(s))\n1. **Plan Comptable / Partie 2 / chapitre_1** (pertinence: 5.52)\n2. ...",
  "sources": [
    {
      "title": "Plan Comptable / Partie 2 / chapitre_1 Frais de recherche",
      "score": 5.52,
      "category": "plan_comptable",
      "section": "Partie 2",
      "file_path": "plan_comptable/partie_2/chapitre_1.docx",
      "document_type": "plan_comptable",
      "metadata_summary": {}
    }
  ],
  "metadata": {
    "intent_type": "document_sourcing",
    "sourcing_mode": true,
    "num_sources": 4,
    "keywords_used": ["amortissements"],
    "categories_found": ["plan_comptable"]
  }
}
```

### Indicateurs Clés

| Indicateur | Valeur Attendue |
|------------|----------------|
| `intent_type` | `document_sourcing` |
| `sourcing_mode` | `true` |
| `confidence` | > 0.95 |
| Documents groupés | Par catégorie |
| Métadonnées enrichies | Oui |

## 🔍 Différence avec RAG Query

| Type | Question | Comportement |
|------|----------|--------------|
| **Document Sourcing** | "Dans quels documents parle-t-on de X ?" | Liste les documents |
| **RAG Query** | "C'est quoi X ?" | Explique le concept |
| **General** | "Bonjour" | Conversation |

## 📁 Fichiers Modifiés

1. **`src/schemas/chat.py`** - Schema SourceDocument enrichi
2. **`src/rag/agents/intent_classifier.py`** - Nouvel intent document_sourcing
3. **`src/rag/agents/rag_workflow.py`** - Node + routing + streaming
4. **`src/rag/pipeline/rag_pipeline.py`** - Méthode conversion enrichie

## 📚 Documentation Complète

- **Architecture** : `DOCUMENT_SOURCING_FEATURE.md`
- **Résultats Tests** : `TESTS_DOCUMENT_SOURCING_RESULTS.md`
- **Ce guide** : `README_DOCUMENT_SOURCING.md`

## ⚠️ Notes Importantes

### ChromaDB en Ingestion

Si l'ingestion ChromaDB est en cours, vous verrez :
```
[error] chromadb_search_failed: Collection does not exist
[info] bm25_search_complete: results=30 ✅ FALLBACK
```

**C'est normal** : Le système utilise BM25 comme fallback et continue de fonctionner.

### Performance

| Mode | Latence Moyenne |
|------|----------------|
| Stream | ~6-8s |
| Non-Stream | ~18-20s |

**Note** : Les temps seront meilleurs une fois l'ingestion ChromaDB terminée.

## 🎯 Exemples de Questions

### ✅ Questions de Document Sourcing (Intent détecté)

- "Dans quels documents parle-t-on des amortissements ?"
- "Existe-t-il une jurisprudence sur..."
- "Quels documents traitent de..."
- "Liste-moi les actes uniformes sur..."
- "Où puis-je trouver des infos sur..."

### ❌ Questions RAG Query (Intent différent)

- "C'est quoi un amortissement ?"
- "Comment comptabiliser..."
- "Explique-moi..."
- "Quelle est la différence entre..."

## 🔧 Dépannage

### Le système retourne `intent: unknown`

**Cause** : Le workflow n'a pas pu s'exécuter, fallback au pipeline legacy
**Solution** : Vérifier les logs Docker
```bash
docker logs kauri_chatbot_service --tail 50
```

### Pas de documents trouvés

**Cause 1** : Ingestion ChromaDB en cours
**Solution** : Attendre la fin de l'ingestion

**Cause 2** : Pas de documents sur ce sujet
**Solution** : Normal, le système indique 0 documents

### Erreur d'authentification

**Vérifier** : Email et password dans le script de test
**Solution** : Utiliser les credentials corrects

## 📞 Support

Pour toute question sur la fonctionnalité :
1. Consulter `DOCUMENT_SOURCING_FEATURE.md`
2. Vérifier les logs : `docker logs kauri_chatbot_service`
3. Relire ce guide

## ✨ Prochaines Améliorations

- [ ] Filtrage par date de publication
- [ ] Recherche multi-critères
- [ ] Export des listes de documents
- [ ] Visualisation hiérarchique
- [ ] Suggestions de documents liés

---

**Version** : 1.0
**Date** : 2025-11-06
**Status** : ✅ Production Ready
