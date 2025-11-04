# KAURI - ERP de Gestion Comptable OHADA

> **Architecture microservices moderne pour la comptabilité d'entreprise**

## 📋 Table des Matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Démarrage](#démarrage)
- [Services](#services)
- [Documentation API](#documentation-api)
- [Développement](#développement)
- [Tests](#tests)
- [Déploiement](#déploiement)

---

## 🎯 Vue d'ensemble

KAURI est une solution ERP complète de gestion comptable conforme aux normes OHADA (Organisation pour l'Harmonisation en Afrique du Droit des Affaires).

### Fonctionnalités Principales

- 🤖 **Chatbot RAG Intelligent** - Assistant virtuel expert en comptabilité OHADA
- 👥 **Gestion Utilisateurs** - Authentification, autorisation et gestion des profils
- 📊 **Comptabilité OHADA** - Gestion conforme au plan comptable SYSCOHADA
- 🔍 **Recherche Hybride** - BM25 + Vector Search + Reranking pour résultats pertinents
- 📄 **Base de Connaissances** - Documentation OHADA complète et indexée

---

## 🏗️ Architecture

### Services Déployés

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
└─────────────────────────────────────────────────────────────┘
        │
        ├──► PostgreSQL (Port 5432)
        │    ├── kauri_users (User Service DB)
        │    └── kauri_chatbot (Chatbot Service DB)
        │
        ├──► Redis (Port 6379)
        │    ├── Cache queries & embeddings
        │    └── Session management
        │
        ├──► ChromaDB (Port 8000)
        │    └── Vector database (développement)
        │
        ├──► User Service (Port 8001)
        │    ├── API REST: /api/v1/*
        │    ├── Auth JWT
        │    └── CRUD utilisateurs
        │
        └──► Chatbot Service (Port 8002)
             ├── API REST: /api/v1/*
             ├── RAG Engine (BM25 + Vector + Reranking)
             ├── LLM: DeepSeek / GPT-4
             └── Embeddings: BGE-M3 (1024 dim)
```

### Stack Technique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| **Backend Framework** | FastAPI | 0.115.11 |
| **Base SQL** | PostgreSQL | 15 |
| **Cache** | Redis | 7 |
| **Vector DB** | ChromaDB (dev) / Pinecone (prod) | 0.5.23 |
| **Embeddings** | BGE-M3 (local) | 1024 dim |
| **LLM** | DeepSeek + OpenAI | API |
| **Containerisation** | Docker + Docker Compose | - |

---

## 📦 Prérequis

### Logiciels Requis

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Git**
- **Python** >= 3.11 (pour développement local)

### Ressources Système Recommandées

- **RAM**: 8 GB minimum (16 GB recommandé)
- **Disque**: 20 GB libre
- **CPU**: 4 cores minimum

---

## 🚀 Installation

### 1. Cloner le Repository

```bash
git clone https://github.com/votre-org/kauri.git
cd kauri
```

### 2. Configurer les Variables d'Environnement

Le fichier `.env` à la racine contient les variables partagées entre tous les services.

```bash
# Vérifier que .env existe et contient les clés API
cat .env
```

**Variables obligatoires à configurer** :

```bash
# API Keys
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...

# JWT Secret (générer une clé aléatoire)
JWT_SECRET_KEY=votre_secret_super_long_et_aleatoire

# Passwords (changer en production)
POSTGRES_PASSWORD=kauri_password_2024
REDIS_PASSWORD=redis_password_2024
```

### 3. Configurer les Services Individuels

Chaque service a son propre fichier `.env` qui **hérite** du `.env` racine :

- `backend/kauri_user_service/.env` - Configuration User Service
- `backend/kauri_chatbot_service/.env` - Configuration Chatbot Service

Ces fichiers contiennent les variables **spécifiques** à chaque service.

---

## ⚙️ Configuration

### Héritage des Variables

Le système utilise un mécanisme d'héritage à 3 niveaux :

```
1. .env racine (variables globales partagées)
   ↓ hérite
2. backend/<service>/.env (variables spécifiques service)
   ↓ hérite
3. Variables d'environnement Docker Compose
```

**Exemple** :

```bash
# Dans .env racine
POSTGRES_USER=kauri_user
POSTGRES_PASSWORD=kauri_password_2024

# Dans backend/kauri_user_service/.env
USER_DB_NAME=kauri_users
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${USER_DB_NAME}
```

### Variables Importantes

#### .env Racine (Partagées)

```bash
# Environnement
KAURI_ENV=development  # development | staging | production

# PostgreSQL
POSTGRES_USER=kauri_user
POSTGRES_PASSWORD=kauri_password_2024

# Redis
REDIS_PASSWORD=redis_password_2024

# JWT (partagé entre services)
JWT_SECRET_KEY=secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# API Keys
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=sk-...
```

#### User Service (.env spécifique)

```bash
SERVICE_PORT=8001
USER_DB_NAME=kauri_users
RATE_LIMIT_REQUESTS=100
PASSWORD_MIN_LENGTH=8
```

#### Chatbot Service (.env spécifique)

```bash
SERVICE_PORT=8002
CHATBOT_DB_NAME=kauri_chatbot
EMBEDDING_MODEL=BAAI/bge-m3
LLM_PROVIDER=deepseek
RAG_TOP_K=10
RATE_LIMIT_REQUESTS=10
```

---

## 🎬 Démarrage

### Méthode 1 : Script de Démarrage (Recommandé)

#### Windows
```bash
start.bat
```

#### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

### Méthode 2 : Docker Compose Manuellement

```bash
# Construction des images
docker-compose build

# Démarrage des services
docker-compose up -d

# Vérifier les logs
docker-compose logs -f

# Vérifier le status
docker-compose ps
```

### Vérification du Démarrage

```bash
# Health checks
curl http://localhost:8001/api/v1/health  # User Service
curl http://localhost:8002/api/v1/health  # Chatbot Service

# Logs
docker-compose logs kauri_user_service
docker-compose logs kauri_chatbot_service
```

---

## 🔧 Services

### 1️⃣ User Service (Port 8001)

**Responsabilités** :
- Authentification JWT
- Gestion des utilisateurs (CRUD)
- Gestion des sessions
- Validation des tokens

**Endpoints Principaux** :
```
GET  /api/v1/health            # Health check
POST /api/v1/auth/register     # Enregistrement
POST /api/v1/auth/login        # Connexion
GET  /api/v1/auth/me           # Info utilisateur courant
POST /api/v1/auth/logout       # Déconnexion
```

**Documentation** : http://localhost:8001/api/v1/docs

### 2️⃣ Chatbot Service (Port 8002)

**Responsabilités** :
- Chatbot RAG expert OHADA
- Recherche hybride (BM25 + Vector)
- Génération de réponses avec LLM
- Gestion des conversations

**Endpoints Principaux** :
```
GET  /api/v1/health            # Health check
POST /api/v1/chat/query        # Query synchrone
GET  /api/v1/chat/stream       # Query streaming SSE
GET  /api/v1/chat/conversations # Liste conversations
```

**Documentation** : http://localhost:8002/api/v1/docs

---

## 📚 Documentation API

### Swagger UI (Interactive)

- **User Service** : http://localhost:8001/api/v1/docs
- **Chatbot Service** : http://localhost:8002/api/v1/docs

### OpenAPI Spec (JSON)

- **User Service** : http://localhost:8001/api/v1/openapi.json
- **Chatbot Service** : http://localhost:8002/api/v1/openapi.json

### Exemples d'Utilisation

#### 1. Authentification

```bash
# Enregistrement
curl -X POST "http://localhost:8001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'

# Connexion
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
# Retourne: {"access_token": "eyJhbGc...", "token_type": "bearer"}
```

#### 2. Query Chatbot

```bash
# Query standard
curl -X POST "http://localhost:8002/api/v1/chat/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Comment enregistrer un achat de matériel en OHADA ?",
    "n_results": 5
  }'

# Query streaming (SSE)
curl "http://localhost:8002/api/v1/chat/stream?query=Comment%20calculer%20amortissement&_token=<token>"
```

---

## 🛠️ Développement

### Structure du Projet

```
kauri/
├── .env                                 # Variables globales
├── docker-compose.yml                   # Orchestration services
├── start.sh / start.bat                 # Scripts démarrage
│
├── backend/
│   ├── kauri_user_service/
│   │   ├── .env                        # Variables spécifiques user
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── src/
│   │       ├── api/
│   │       │   └── main.py            # Point d'entrée FastAPI
│   │       ├── auth/                   # Logique authentification
│   │       ├── models/                 # Modèles SQLAlchemy
│   │       ├── schemas/                # Schémas Pydantic
│   │       ├── utils/                  # Utilitaires
│   │       └── config.py              # Configuration (hérite .env)
│   │
│   └── kauri_chatbot_service/
│       ├── .env                        # Variables spécifiques chatbot
│       ├── Dockerfile
│       ├── requirements.txt
│       └── src/
│           ├── api/
│           │   └── main.py            # Point d'entrée FastAPI
│           ├── rag/                    # Logique RAG
│           ├── models/                 # Modèles SQLAlchemy
│           ├── schemas/                # Schémas Pydantic
│           ├── utils/                  # Utilitaires
│           └── config.py              # Configuration (hérite .env)
│
├── scripts/
│   └── init-databases.sh               # Init PostgreSQL DBs
│
└── base_connaissances/                 # Documents OHADA sources
```

### Développement Local (Sans Docker)

#### User Service

```bash
cd backend/kauri_user_service

# Créer venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt

# Démarrer service
python -m uvicorn src.api.main:app --reload --port 8001
```

#### Chatbot Service

```bash
cd backend/kauri_chatbot_service

# Créer venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt

# Précharger modèle BGE-M3 (optionnel, ~2GB)
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"

# Démarrer service
python -m uvicorn src.api.main:app --reload --port 8002
```

### Logs et Debugging

```bash
# Logs en temps réel (tous services)
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f kauri_user_service
docker-compose logs -f kauri_chatbot_service

# Logs PostgreSQL
docker-compose logs -f postgres

# Inspecter un container
docker exec -it kauri_user_service bash
docker exec -it kauri_chatbot_service bash
```

---

## 🧪 Tests

### Tests Unitaires

```bash
# User Service
cd backend/kauri_user_service
pytest tests/ -v --cov=src

# Chatbot Service
cd backend/kauri_chatbot_service
pytest tests/ -v --cov=src
```

### Tests d'Intégration

```bash
# Tous les services doivent être lancés
docker-compose up -d

# Exécuter tests
pytest tests/integration/ -v
```

---

## 🚢 Déploiement

### Production avec Docker

```bash
# Build images de production
docker-compose -f docker-compose.prod.yml build

# Démarrer
docker-compose -f docker-compose.prod.yml up -d
```

### Production avec Kubernetes

```bash
# Déployer avec Helm
helm install kauri ./helm/kauri -f values.prod.yaml

# Vérifier status
kubectl get pods -n kauri
kubectl get services -n kauri
```

---

## 📊 Monitoring

### Health Checks

```bash
# User Service
curl http://localhost:8001/api/v1/health

# Chatbot Service
curl http://localhost:8002/api/v1/health
```

### Métriques Prometheus

```bash
# User Service Metrics
curl http://localhost:8001/metrics

# Chatbot Service Metrics
curl http://localhost:8002/metrics
```

---

## 🔒 Sécurité

### Best Practices Implémentées

- ✅ **JWT Authentication** avec expiration
- ✅ **Rate Limiting** (10 req/min pour chatbot, 100 req/min pour user)
- ✅ **Input Validation** avec Pydantic
- ✅ **Password Hashing** avec bcrypt
- ✅ **CORS** configuré strictement
- ✅ **Non-root Docker users**
- ✅ **Secrets dans variables d'environnement** (pas dans code)

### À Configurer en Production

- [ ] HTTPS/TLS sur tous les endpoints
- [ ] Secrets management (Vault, AWS Secrets Manager)
- [ ] IP Whitelisting
- [ ] WAF (Web Application Firewall)
- [ ] DDoS Protection
- [ ] Audit Logging

---

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📄 Licence

Ce projet est sous licence MIT. Voir `LICENSE` pour plus de détails.

---

## 📞 Support

- **Documentation** : Voir `/docs`
- **Issues** : https://github.com/votre-org/kauri/issues
- **Email** : support@kauri.com

---

## 🙏 Remerciements

- **OHADA** - Organisation pour l'Harmonisation en Afrique du Droit des Affaires
- **BGE-M3** - BAAI General Embedding Model
- **DeepSeek** - LLM Provider
- **ChromaDB** - Vector Database
- **FastAPI** - Modern Python Web Framework

---

**Version** : 1.0.0
**Date** : 2025-11-03
**Auteur** : Équipe KAURI
