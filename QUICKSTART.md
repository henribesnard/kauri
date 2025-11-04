# ⚡ KAURI - Guide de Démarrage Rapide

> **5 minutes pour lancer l'architecture complète !**

---

## 🎯 Prérequis

```bash
# Vérifier Docker
docker --version
# ✅ Doit afficher: Docker version 20.x ou supérieur

# Vérifier Docker Compose
docker-compose --version
# ✅ Doit afficher: Docker Compose version 2.x ou supérieur
```

---

## 🚀 Démarrage en 3 Étapes

### Étape 1️⃣ : Cloner le Projet

```bash
cd /chemin/vers/kauri
```

### Étape 2️⃣ : Configurer les Secrets (Optionnel pour dev)

Le fichier `.env` contient déjà des valeurs par défaut pour le développement.

**Pour la production**, éditez `.env` et changez :
```bash
JWT_SECRET_KEY=votre_secret_aleatoire_super_long
POSTGRES_PASSWORD=votre_mot_de_passe_secure
REDIS_PASSWORD=votre_mot_de_passe_redis
```

### Étape 3️⃣ : Lancer !

#### 🪟 Windows
```bash
start.bat
```

#### 🐧 Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

#### 🛠️ Avec Make (si installé)
```bash
make up
```

---

## ✅ Vérification

### 1. Vérifier les Services

```bash
# Status Docker
docker-compose ps

# Doit afficher 5 services "Up (healthy)":
# - kauri_postgres
# - kauri_redis
# - kauri_chromadb
# - kauri_user_service
# - kauri_chatbot_service
```

### 2. Health Checks

```bash
# User Service
curl http://localhost:8001/api/v1/health

# Chatbot Service
curl http://localhost:8002/api/v1/health

# Ou avec Make
make health
```

### 3. Ouvrir la Documentation

- **User Service** : http://localhost:8001/api/v1/docs
- **Chatbot Service** : http://localhost:8002/api/v1/docs

---

## 📖 URLs des Services

| Service | URL | Documentation |
|---------|-----|---------------|
| **PostgreSQL** | `localhost:5432` | - |
| **Redis** | `localhost:6379` | - |
| **ChromaDB** | http://localhost:8000 | API vectorielle |
| **User Service** | http://localhost:8001 | http://localhost:8001/api/v1/docs |
| **Chatbot Service** | http://localhost:8002 | http://localhost:8002/api/v1/docs |

---

## 🧪 Tester l'API

### User Service

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Response attendue:
{
  "status": "healthy",
  "service": "kauri_user_service",
  "version": "1.0.0",
  "environment": "development"
}
```

### Chatbot Service

```bash
# Health check
curl http://localhost:8002/api/v1/health

# Response attendue:
{
  "status": "healthy",
  "service": "kauri_chatbot_service",
  "version": "1.0.0",
  "environment": "development",
  "llm_provider": "deepseek",
  "embedding_model": "BAAI/bge-m3"
}
```

---

## 📊 Voir les Logs

```bash
# Tous les services (temps réel)
docker-compose logs -f

# User Service uniquement
docker-compose logs -f kauri_user_service

# Chatbot Service uniquement
docker-compose logs -f kauri_chatbot_service

# PostgreSQL
docker-compose logs -f postgres

# Ou avec Make
make logs
make logs-user
make logs-chat
```

---

## 🛑 Arrêter les Services

```bash
# Arrêter proprement
docker-compose down

# Ou avec Make
make down
```

---

## 🔄 Redémarrer

```bash
# Redémarrer tous les services
docker-compose restart

# Ou avec Make
make restart
```

---

## 🧹 Nettoyer Complètement

```bash
# ⚠️ ATTENTION: Supprime TOUS les volumes (données perdues)
docker-compose down -v

# Ou avec Make
make clean
```

---

## 🐛 Résolution de Problèmes

### Problème : Les services ne démarrent pas

```bash
# 1. Vérifier les logs
docker-compose logs

# 2. Vérifier les ports disponibles
netstat -an | findstr "5432 6379 8000 8001 8002"  # Windows
lsof -i :5432,6379,8000,8001,8002                  # Linux/Mac

# 3. Rebuild les images
docker-compose build --no-cache
docker-compose up -d
```

### Problème : Health check échoue

```bash
# Attendre 60 secondes (warm-up)
sleep 60

# Vérifier les logs du service
docker-compose logs kauri_user_service
docker-compose logs kauri_chatbot_service

# Redémarrer le service spécifique
docker-compose restart kauri_user_service
```

### Problème : "Permission denied" sur scripts

```bash
# Linux/Mac
chmod +x start.sh
chmod +x scripts/init-databases.sh

# Windows: Lancer en tant qu'administrateur
```

---

## 📚 Commandes Utiles

```bash
# Voir status
docker-compose ps

# Voir logs
docker-compose logs -f

# Entrer dans un container
docker exec -it kauri_user_service bash
docker exec -it kauri_chatbot_service bash

# Vérifier santé
make health

# Voir URLs
make urls

# Stats ressources
docker stats
# ou
make stats
```

---

## 🎓 Prochaines Étapes

1. ✅ **Services lancés** - Architecture opérationnelle
2. 📖 **Lire README.md** - Documentation complète
3. 📊 **Explorer Swagger UI** - Tester les endpoints
4. 🔧 **Développer** - Implémenter auth & RAG
5. 🧪 **Tester** - Écrire les tests unitaires

---

## 💡 Aide Rapide

| Besoin | Commande |
|--------|----------|
| Démarrer | `make up` ou `./start.sh` |
| Arrêter | `make down` |
| Logs | `make logs` |
| Status | `make ps` |
| Health | `make health` |
| Shell | `make shell-user` ou `make shell-chat` |
| Clean | `make clean` |
| Aide | `make help` |

---

## 📞 Support

- **Documentation** : Voir `README.md` et `ARCHITECTURE_SUMMARY.md`
- **Issues** : https://github.com/votre-org/kauri/issues
- **Email** : support@kauri.com

---

**Bon développement ! 🚀**
