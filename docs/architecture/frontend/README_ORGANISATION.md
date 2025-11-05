# Organisation du Dossier Frontend KAURI

> **Note importante** : Ce dossier contient à la fois les spécifications frontend ET backend pour des raisons historiques. Une réorganisation est recommandée.

---

## 📁 Structure Actuelle

```
frontend/
├── README_ORGANISATION.md              # Ce fichier
├── KAURI_Frontend_Specifications.md    # ✅ SPECS FRONTEND (Nouveau)
│
├── kauri-app/                          # ✅ APPLICATION REACT PRINCIPALE
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── README.md
│
├── kauri-interface.html                # ⚠️ PROTOTYPE HTML (à archiver)
│
└── Documents Backend (à déplacer):
    ├── KAURI_Chatbot_Resume_Executif.md
    ├── KAURI_Chatbot_Architecture_Ameliorations.md
    └── KAURI_Chatbot_Diagrammes_Architecture.md
```

---

## ✅ Documents Frontend

### 1. **KAURI_Frontend_Specifications.md** (NOUVEAU)
Spécifications complètes du frontend React :
- Architecture frontend
- Design system
- Pages et fonctionnalités
- Composants réutilisables
- Intégration backend
- Tests et déploiement
- Roadmap

### 2. **kauri-app/** (APPLICATION PRINCIPALE)
Application React + TypeScript + Vite :
- Code source dans `src/`
- Configuration dans fichiers racine
- Documentation dans `kauri-app/README.md`

### 3. **kauri-interface.html** (PROTOTYPE)
Prototype HTML statique avec React inline :
- ⚠️ Déprécié - à archiver ou supprimer
- Remplacé par `kauri-app/`
- Conservé pour référence visuelle

---

## ⚠️ Documents Backend (Mal placés)

Ces documents **ne concernent PAS le frontend** mais l'architecture **backend/microservices** :

### 1. KAURI_Chatbot_Resume_Executif.md
- Résumé exécutif pour la direction
- Architecture backend microservices
- Coûts infrastructure
- Plan de migration backend

### 2. KAURI_Chatbot_Architecture_Ameliorations.md
- Analyse détaillée architecture backend
- Stack technique backend
- Recommandations microservices
- Migration ChromaDB → Pinecone
- Découpage en 3 services backend

### 3. KAURI_Chatbot_Diagrammes_Architecture.md
- Diagrammes architecture backend
- Flux de données backend
- Déploiement Kubernetes
- CI/CD pipeline

---

## 🔄 Réorganisation Recommandée

### Structure Proposée

```
kauri/
├── docs/                               # Documentation globale
│   ├── architecture/
│   │   ├── backend/
│   │   │   ├── KAURI_Chatbot_Resume_Executif.md
│   │   │   ├── KAURI_Chatbot_Architecture_Ameliorations.md
│   │   │   └── KAURI_Chatbot_Diagrammes_Architecture.md
│   │   └── frontend/
│   │       └── KAURI_Frontend_Specifications.md
│   └── README.md
│
├── frontend/                           # Code frontend uniquement
│   ├── kauri-app/                      # Application React
│   │   ├── src/
│   │   ├── public/
│   │   └── README.md
│   └── archive/
│       └── kauri-interface-prototype.html
│
└── backend/                            # Code backend
    ├── chatbot-api/
    ├── rag-engine/
    └── knowledge-base/
```

### Commandes de Réorganisation

```bash
# Créer structure docs/
mkdir -p docs/architecture/backend
mkdir -p docs/architecture/frontend

# Déplacer docs backend
mv frontend/KAURI_Chatbot_Resume_Executif.md docs/architecture/backend/
mv frontend/KAURI_Chatbot_Architecture_Ameliorations.md docs/architecture/backend/
mv frontend/KAURI_Chatbot_Diagrammes_Architecture.md docs/architecture/backend/

# Déplacer doc frontend
mv frontend/KAURI_Frontend_Specifications.md docs/architecture/frontend/

# Archiver prototype HTML
mkdir -p frontend/archive
mv frontend/kauri-interface.html frontend/archive/kauri-interface-prototype.html
```

---

## 📋 Actions Recommandées

### Priorité 1 - Urgent

- [ ] **Déplacer les docs backend** vers `docs/architecture/backend/`
- [ ] **Déplacer le doc frontend** vers `docs/architecture/frontend/`
- [ ] **Archiver** `kauri-interface.html` (prototype déprécié)
- [ ] **Mettre à jour les dates** dans les documents (2025-11-03 → 2025-11-04)

### Priorité 2 - Important

- [ ] Corriger les références "OHAD'AI" → "KAURI" dans les documents
- [ ] Vérifier les estimations de coûts dans les docs backend
- [ ] Ajouter des wireframes/maquettes pour le frontend
- [ ] Créer un document "Guide de contribution" pour les devs

### Priorité 3 - Nice to have

- [ ] Créer un design system Figma/Sketch
- [ ] Ajouter des screenshots de l'application dans la doc
- [ ] Créer un changelog
- [ ] Documenter les user stories

---

## 🎯 Pour les Nouveaux Développeurs

### Je veux travailler sur le Frontend
👉 Consultez :
1. `KAURI_Frontend_Specifications.md` (spécifications complètes)
2. `kauri-app/README.md` (guide de démarrage)
3. `kauri-app/src/` (code source)

### Je veux comprendre l'Architecture Backend
👉 Consultez :
1. `KAURI_Chatbot_Resume_Executif.md` (vue d'ensemble)
2. `KAURI_Chatbot_Architecture_Ameliorations.md` (détails techniques)
3. `KAURI_Chatbot_Diagrammes_Architecture.md` (schémas)

### Je veux voir un Prototype Visuel
👉 Ouvrez `kauri-interface.html` dans un navigateur (prototype déprécié)

---

## 📞 Contact

**Questions sur le frontend** : frontend@kauri.com
**Questions sur l'architecture** : architecture@kauri.com
**Questions générales** : tech@kauri.com

---

**Date de création** : 2025-11-04
**Auteur** : Architecture Team
**Version** : 1.0
