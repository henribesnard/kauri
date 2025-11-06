# 📄 Support PDF et Déduplication Intelligente - Documentation

## Vue d'ensemble des changements

Le système d'ingestion de KAURI a été amélioré pour supporter les documents PDF en plus des DOCX, avec un système de déduplication intelligent basé sur ChromaDB.

---

## ✨ Nouvelles fonctionnalités

### 1. Support complet des PDFs

✅ **Extraction de texte depuis PDFs** avec `pdfplumber`
✅ **Détection et extraction de tableaux** dans les PDFs
✅ **Métadonnées automatiques** (catégorie basée sur le chemin)
✅ **Gestion des PDFs multi-pages**

### 2. Déduplication intelligente

✅ **Chargement des hashes depuis ChromaDB** au démarrage
✅ **Skip automatique des documents déjà ingérés**
✅ **Basé sur le hash SHA-256 du contenu**
✅ **Persistance entre les exécutions**

### 3. Paramètres de chunking optimisés

✅ **Chunk size: 3500 caractères** (taille universelle)
✅ **Overlap: 300 caractères** (sécurise les transitions)

---

## 📁 Structure des dossiers

```
base_connaissances/
├── actes_uniformes/           (existant - DOCX)
├── plan_comptable/             (existant - DOCX)
├── presentation_ohada/         (existant - DOCX)
├── doctrines/                  (nouveau - 974 PDFs déplacés)
└── jurisprudences/             (nouveau - 4034 PDFs déplacés)
```

**Total: 5008 PDFs + documents DOCX existants**

---

## 🔧 Modifications techniques

### Fichier: `src/ingestion/document_processor.py`

**Ajouté:**
- `read_pdf()` - Extraction de texte depuis PDF avec pdfplumber
- `_table_to_text()` - Conversion des tableaux en format texte
- `_infer_category_from_path()` - Détection automatique de catégorie
- Support `.pdf` dans `SUPPORTED_FORMATS`
- Traitement PDF dans `process_file()`

**Fonctionnalités:**
```python
# Extraction de texte page par page
with pdfplumber.open(file_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
```

---

### Fichier: `ingest_documents.py`

**Ajouté:**
- `load_existing_hashes()` - Charge les hashes depuis ChromaDB
- Support des PDFs dans `find_documents()`
- Déduplication au démarrage de l'ingestion

**Logique de déduplication:**
```python
# Avant (❌)
processed_hashes = set()  # Vide à chaque exécution

# Après (✅)
processed_hashes = load_existing_hashes(chroma_store)  # Charge depuis DB
```

**Paramètres de chunking:**
```python
chunk_size = 3500      # Caractères par chunk
chunk_overlap = 300    # Overlap entre chunks
```

---

## 🚀 Utilisation

### Lancer les tests

```bash
# Depuis le host
docker exec kauri_chatbot_service python test_pdf_ingestion.py
```

**Tests effectués:**
1. ✅ Traitement d'un PDF
2. ✅ Système de déduplication
3. ✅ Recherche de fichiers

---

### Lancer l'ingestion complète

```bash
# Ingérer TOUS les documents (DOCX + PDF)
docker exec kauri_chatbot_service python ingest_documents.py
```

**Ce qui se passe:**
1. Connexion à ChromaDB
2. Chargement des hashes existants (déduplication)
3. Recherche de tous les `.docx` et `.pdf` dans `base_connaissances/`
4. Pour chaque fichier:
   - Extraction du contenu
   - Calcul du hash SHA-256
   - **Skip si déjà ingéré** (hash existant)
   - Sinon: chunking → embeddings → ajout à ChromaDB
5. Construction de l'index BM25
6. Affichage des statistiques

---

### Réingérer uniquement les nouveaux documents

```bash
# Ajouter de nouveaux PDFs dans base_connaissances/
cp nouveau_doc.pdf base_connaissances/doctrines/

# Relancer l'ingestion
docker exec kauri_chatbot_service python ingest_documents.py
```

**Résultat:**
- ✅ Documents existants: **skipped** (déduplication)
- ✅ Nouveaux documents: **ingérés**
- ✅ Pas de doublons dans ChromaDB

---

## 📊 Statistiques attendues

### Première ingestion (base vide)

```
==============================================================
✅ Ingestion terminée!
==============================================================
📊 Statistiques:
  • Fichiers trouvés:      5008+
  • Documents créés:       5008+
  • Documents ignorés:     0 (déjà existants)
  • Échecs:                0-10 (fichiers corrompus éventuels)
  • Taux de succès:        99.8%
==============================================================

📦 ChromaDB: ~50000+ chunks indexés
```

### Réingestion (avec documents existants)

```
==============================================================
✅ Ingestion terminée!
==============================================================
📊 Statistiques:
  • Fichiers trouvés:      5008+
  • Documents créés:       5
  • Documents ignorés:     5003+ (déjà existants)
  • Échecs:                0
  • Taux de succès:        100%
==============================================================

📦 ChromaDB: ~50050+ chunks indexés
```

---

## 🔍 Vérification de la persistance

### Vérifier que ChromaDB persiste les données

```bash
# Redémarrer les services
docker-compose restart

# Vérifier le nombre de documents
docker exec kauri_chatbot_service python -c "
from src.rag.vector_store.chroma_store import get_chroma_store
store = get_chroma_store()
print(f'Documents in ChromaDB: {store.count()}')
"
```

**Si le nombre reste identique:** ✅ Persistance active
**Si le nombre = 0:** ❌ Problème de volume Docker

---

## ⚙️ Configuration ChromaDB

Le `docker-compose.yml` est configuré pour la persistance:

```yaml
chromadb:
  environment:
    IS_PERSISTENT: "True"     # ✅ Persistance activée
  volumes:
    - chromadb_data:/chroma/chroma  # ✅ Volume Docker
```

**Volume nommé:**
```yaml
volumes:
  chromadb_data:
    name: kauri_chromadb_data
```

---

## 🐛 Troubleshooting

### Erreur: "Unsupported format: .pdf"

**Cause:** Ancienne version du code
**Solution:**
```bash
docker-compose down
docker-compose build kauri_chatbot_service
docker-compose up -d
```

### Tous les documents sont "skipped"

**Cause:** Documents déjà ingérés
**C'est normal !** Le système de déduplication fonctionne.

**Pour forcer la réingestion:**
```bash
# ATTENTION: Efface TOUTE la base ChromaDB
docker exec kauri_chatbot_service python -c "
from src.rag.vector_store.chroma_store import get_chroma_store
store = get_chroma_store()
store.clear()
print('ChromaDB cleared')
"

# Puis réingérer
docker exec kauri_chatbot_service python ingest_documents.py
```

### PDFs ne sont pas trouvés

**Vérifier:**
```bash
# Depuis le host
ls -la base_connaissances/doctrines/ | head
ls -la base_connaissances/jurisprudences/ | head

# Depuis le conteneur
docker exec kauri_chatbot_service ls -la /app/base_connaissances/doctrines/ | head
```

**Volume mapping dans docker-compose.yml:**
```yaml
volumes:
  - ./base_connaissances:/app/base_connaissances:ro
```

---

## 📈 Performance

### Temps d'ingestion estimés

| Documents | Chunks | Temps estimé |
|-----------|--------|--------------|
| 100 PDFs | ~1000 | 2-5 minutes |
| 1000 PDFs | ~10000 | 20-50 minutes |
| 5008 PDFs | ~50000 | 1.5-3 heures |

**Facteurs d'impact:**
- Taille des PDFs
- CPU disponible
- Vitesse réseau (embeddings API)
- Nombre de tableaux

---

## 🎯 Prochaines étapes

### Optimisations possibles

1. **Batch processing** - Traiter les documents par lots
2. **Parallel ingestion** - Utiliser asyncio pour paralléliser
3. **Embedding cache** - Cacher les embeddings calculés
4. **Index incremental** - Mettre à jour BM25 de façon incrémentale
5. **Monitoring** - Ajouter des métriques Prometheus

### Améliorations fonctionnelles

1. **OCR pour PDFs scannés** - Intégrer le service kauri_ocr_service
2. **Extraction d'entités** - Détecter dates, montants, articles
3. **Classification automatique** - ML pour catégoriser les documents
4. **Résumés automatiques** - Générer des résumés avec LLM
5. **Interface web** - Dashboard pour suivre l'ingestion

---

## 📚 Ressources

- **pdfplumber docs**: https://github.com/jsvine/pdfplumber
- **ChromaDB docs**: https://docs.trychroma.com/
- **KAURI architecture**: `backend/ARCHITECTURE_DECISION.md`

---

## ✅ Checklist de validation

- [x] Support PDF ajouté dans document_processor
- [x] Déduplication depuis ChromaDB implémentée
- [x] find_documents() trouve les PDFs
- [x] Chunk size / overlap configurés (3500/300)
- [x] 974 doctrines déplacées vers base_connaissances/
- [x] 4034 jurisprudences déplacées vers base_connaissances/
- [x] Script de test créé
- [x] Documentation complète
- [ ] Tests exécutés avec succès
- [ ] Ingestion complète lancée
- [ ] Vérification de la persistance

---

**Développé pour KAURI - Expertise comptable OHADA** 🇫🇷🇨🇮
