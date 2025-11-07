# 🚀 Ingestion en cours - Guide de suivi

## ✅ Statut : LANCÉE EN ARRIÈRE-PLAN

L'ingestion complète de **5264 documents** (256 DOCX + 5008 PDF) a été lancée avec succès !

### Paramètres appliqués à TOUS les documents :
- ✅ **Chunk size : 3500 caractères**
- ✅ **Overlap : 300 caractères**
- ✅ **ChromaDB vidé** : Pas de documents avec anciens paramètres

---

## 📊 Suivre la progression

### Commande principale (à relancer régulièrement)

```bash
docker exec kauri_chatbot_service python check_ingestion_progress.py
```

**Affiche :**
- Nombre de documents traités
- Nombre de chunks créés
- Pourcentage de progression
- Temps restant estimé
- Barre de progression visuelle

**Exemple de sortie :**
```
📁 Fichiers à traiter:
   • Total:        5264 fichiers
   • DOCX:         256
   • PDF:          5008

✅ Documents ingérés:
   • Uniques:      250 documents
   • Restants:     5014 documents
   • Progression:  4.7%

📦 Chunks dans ChromaDB:
   • Total:        1250 chunks
   • Moyenne:      5.0 chunks/doc

[██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░] 4.7%

⏱️  Temps restant estimé:
   • ~8.4 heures (43 minutes)
```

---

## 📝 Voir les logs en direct

```bash
docker exec kauri_chatbot_service tail -f /app/logs/ingestion.log
```

**Sortir avec :** `Ctrl+C`

**Ce que vous verrez :**
```
2025-11-06 14:24:35 [info] processing_file path=...
2025-11-06 14:24:35 [info] document_chunked num_chunks=5
2025-11-06 14:24:35 [info] embedding_batch_start count=5
2025-11-06 14:24:50 [info] embedding_batch_complete
2025-11-06 14:24:50 [info] document_ingested
```

---

## ⏱️ Temps estimé

### Total : **1.5 à 3 heures** pour 5264 documents

| Étape | Documents | Temps |
|-------|-----------|-------|
| DOCX (256) | rapides | ~15-20 min |
| PDFs petits (3000) | moyens | ~45-60 min |
| PDFs gros (2008) | lents | ~60-120 min |

**Facteurs :**
- Taille des PDFs
- Nombre de tableaux
- Vitesse API embeddings (BGE-M3)

---

## 🔍 Vérifications pendant l'ingestion

### 1. Vérifier que le processus tourne

```bash
docker exec kauri_chatbot_service ps aux | grep python
```

**Doit afficher :** `python ingest_documents.py`

### 2. Vérifier l'augmentation des chunks

```bash
docker exec kauri_chatbot_service python -c "
from src.rag.vector_store.chroma_store import get_chroma_store
print(f'Chunks: {get_chroma_store().count()}')
"
```

**Doit augmenter** à chaque appel (attendre 30s entre les appels)

### 3. Vérifier les erreurs dans les logs

```bash
docker exec kauri_chatbot_service grep -i error /app/logs/ingestion.log | tail -10
```

**Doit être vide** ou contenir uniquement des warnings sans gravité

---

## 🎯 Une fois l'ingestion terminée

L'ingestion affichera automatiquement un résumé final dans les logs :

```
============================================================
✅ Ingestion terminée!
============================================================
📊 Statistiques:
  • Fichiers trouvés:      5264
  • Documents créés:       5264
  • Documents ignorés:     0 (déjà existants)
  • Échecs:                0-10 (fichiers corrompus)
  • Taux de succès:        99.8%
============================================================

📦 ChromaDB: ~52000 chunks indexés
```

### Vérification finale

```bash
# 1. Compter les chunks finaux
docker exec kauri_chatbot_service python check_ingestion_progress.py

# 2. Vérifier la fin des logs
docker exec kauri_chatbot_service tail -50 /app/logs/ingestion.log

# 3. Tester une requête
docker exec kauri_chatbot_service python -c "
from src.rag.vector_store.chroma_store import get_chroma_store
store = get_chroma_store()
print(f'✅ {store.count()} chunks prêts pour les requêtes')
"
```

---

## 📈 Statistiques attendues

### Résultat final attendu

| Métrique | Valeur estimée |
|----------|----------------|
| Documents totaux | 5264 |
| Chunks totaux | ~50000-60000 |
| Moyenne chunks/doc | ~10-12 |
| Taille moyenne chunk | ~3000-3500 chars |
| Overlap | 300 chars |

### Distribution par catégorie

```
actes_uniformes:     198 docs  →  ~2000 chunks
doctrines:           974 docs  →  ~10000 chunks
jurisprudences:     4034 docs  →  ~35000 chunks
plan_comptable:       56 docs  →  ~500 chunks
presentation_ohada:    2 docs  →  ~20 chunks
```

---

## 🐛 Troubleshooting

### L'ingestion semble bloquée

**Vérifier :**
```bash
# Dernière activité dans les logs (doit être < 5min)
docker exec kauri_chatbot_service bash -c "ls -lh /app/logs/ingestion.log"

# Processus actif
docker exec kauri_chatbot_service ps aux | grep python
```

**Si bloqué :**
```bash
# Arrêter le processus
docker exec kauri_chatbot_service pkill -f ingest_documents.py

# Relancer
docker exec -d kauri_chatbot_service bash -c "python ingest_documents.py > /app/logs/ingestion.log 2>&1"
```

### Erreurs d'embeddings

Si vous voyez beaucoup d'erreurs liées aux embeddings :
- Vérifier la connexion internet
- Vérifier que le modèle BGE-M3 est téléchargé
- Les erreurs temporaires sont normales (retry automatique)

### Mémoire insuffisante

Si le conteneur plante (Out of Memory) :
```bash
# Augmenter la mémoire Docker à 8GB minimum
# Dans Docker Desktop : Settings → Resources → Memory → 8GB

# Redémarrer les services
docker-compose restart
```

---

## 💡 Commandes utiles

```bash
# Progression rapide
docker exec kauri_chatbot_service python check_ingestion_progress.py

# Logs en direct
docker exec kauri_chatbot_service tail -f /app/logs/ingestion.log

# Nombre de chunks actuel
docker exec kauri_chatbot_service python -c "from src.rag.vector_store.chroma_store import get_chroma_store; print(get_chroma_store().count())"

# Logs complets (historique)
docker exec kauri_chatbot_service cat /app/logs/ingestion.log

# Arrêter l'ingestion
docker exec kauri_chatbot_service pkill -f ingest_documents.py
```

---

## 📞 Support

Si problème persistant :
1. Copier les dernières lignes de `/app/logs/ingestion.log`
2. Noter le nombre de documents traités
3. Vérifier les logs Docker : `docker logs kauri_chatbot_service`

---

## 🎉 Après l'ingestion

Une fois terminée, vous pourrez :
- ✅ Poser des questions au chatbot
- ✅ Rechercher dans les 5264+ documents OHADA
- ✅ Bénéficier de chunks optimisés (3500/300)
- ✅ Ajouter de nouveaux documents (déduplication automatique)

---

**Lancement :** 2025-11-06 14:23:00
**Documents :** 5264 fichiers (256 DOCX + 5008 PDF)
**Paramètres :** Chunk 3500 / Overlap 300
**Persistance :** ChromaDB volume Docker
