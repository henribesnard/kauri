# Architecture Decision: Schémas PostgreSQL Séparés

## 🎯 Question Posée

> "Vu qu'on a deux schémas différents (user et chatbot), est-ce idéal pour gérer les conversations d'un user ? Ne serait-il pas mieux de créer un seul schéma pour tout le projet ?"

## 📋 Décision Architecture

**DÉCISION : Conserver deux schémas séparés avec mécanismes de cohérence**

```
kauri_users    → users, sessions, profiles (User Service)
kauri_chatbot  → conversations, messages, tags (Chatbot Service)
```

---

## ✅ Justification

### 1. Architecture Microservices
Votre projet KAURI suit déjà un pattern microservices :
- **User Service** (port 3201) - Authentification, gestion utilisateurs
- **Chatbot Service** (port 3202) - RAG, conversations, messages

Avoir deux bases de données séparées **aligne l'architecture data avec l'architecture services**.

### 2. Avantages de la Séparation

#### **Scaling Indépendant**
```
Chatbot Service (haute charge)     → Scale DB chatbot + replicas
User Service (charge modérée)       → DB user reste stable
```

Le chatbot génère **beaucoup plus de requêtes** que l'authentification :
- Authentification : ~100 req/min (login, vérification token)
- Chatbot : ~10,000 req/min (messages, historique, RAG)

#### **Déploiement Indépendant**
```bash
# Déployer nouvelle version chatbot SANS toucher auth
cd backend/kauri_chatbot_service
alembic upgrade head        # Migration chatbot uniquement
docker-compose up -d chatbot_service
```

Pas besoin de redémarrer User Service → **Zero downtime pour auth**.

#### **Isolation des Pannes**
Si la DB chatbot devient lente/tombe :
- ✅ Les utilisateurs peuvent toujours se connecter
- ✅ User Service reste fonctionnel
- ✅ Dégradation gracieuse (chatbot en maintenance)

#### **Sécurité & Permissions**
```
DB kauri_users:    Accès → User Service uniquement
DB kauri_chatbot:  Accès → Chatbot Service uniquement
```

Principe du **moindre privilège** : chaque service n'accède qu'à ses données.

#### **Évolutivité Future**
Architecture extensible pour futurs services :
```
kauri_users       → User Service
kauri_chatbot     → Chatbot Service
kauri_analytics   → Analytics Service (futur)
kauri_admin       → Admin Dashboard (futur)
kauri_mobile      → Mobile API (futur)
```

---

## ⚠️ Inconvénients (et Solutions)

### Problème 1 : Pas de Foreign Key Native

**Problème :**
```sql
-- Impossible de faire ceci entre deux bases
ALTER TABLE chatbot.conversations
  ADD FOREIGN KEY (user_id) REFERENCES users.users(id) ON DELETE CASCADE;
```

**Solutions Implémentées :**

#### ✅ Solution A : Validation à l'écriture (En place)
```python
@router.post("/api/v1/chat/query")
async def chat_query(current_user: Dict = Depends(get_current_user)):
    # get_current_user() appelle User Service pour valider le token
    # Si user n'existe pas → 401 Unauthorized
    user_id = uuid.UUID(current_user.get("user_id"))
    # Impossible de créer conversation pour user inexistant
```

**Garantit :** Aucune conversation orpheline n'est créée.

#### ✅ Solution B : Cleanup Job Automatique (Nouveau)
```python
# src/tasks/cleanup_orphaned_data.py
async def cleanup_orphaned_conversations():
    """
    Tâche quotidienne qui :
    1. Récupère tous les user_ids de conversations
    2. Vérifie via User Service API si chaque user existe
    3. Supprime conversations pour users supprimés
    """
```

**Configuration Cron (Docker):**
```yaml
# docker-compose.yml
chatbot_cleanup:
  image: kauri_chatbot_service
  command: ["python", "-m", "src.tasks.cleanup_orphaned_data"]
  depends_on:
    - postgres
  deploy:
    mode: replicated
    replicas: 0  # Run via cron, not continuously
```

**Crontab:**
```bash
# Cron sur le serveur hôte
0 3 * * * docker run --rm kauri_chatbot_cleanup
# Tous les jours à 3h du matin
```

#### ✅ Solution C : Endpoints Admin (Nouveau)
```bash
# Trigger manuel si besoin urgent
POST /api/v1/admin/cleanup/orphaned-conversations
POST /api/v1/admin/cleanup/soft-deleted-messages?days_old=30
```

Utile pour maintenance immédiate.

---

### Problème 2 : Pas de Transactions Cross-Database

**Problème :**
Impossible de faire une transaction atomique qui touche les deux bases :
```python
# IMPOSSIBLE avec deux bases séparées
with db.begin():
    user = create_user(db_users)
    conversation = create_conversation(db_chatbot, user.id)
    # Si conversation échoue, user déjà créé → incohérence
```

**Solution : Pattern Saga (Compensation)**
```python
async def create_user_with_welcome_conversation():
    try:
        # Step 1: Create user
        user = await user_service.create_user(...)

        # Step 2: Create welcome conversation
        try:
            conv = await chatbot_service.create_conversation(user.id)
        except Exception:
            # Compensation: Delete user if conversation fails
            await user_service.delete_user(user.id)
            raise

    except Exception as e:
        logger.error("user_creation_failed", error=str(e))
        raise
```

**Note :** Ce cas est rare car la création de conversation est optionnelle.

---

## 🔄 Mécanismes de Cohérence Implémentés

### 1. Validation JWT (En Place)
```
User fait requête → JWT validé via User Service → user_id extrait
→ Conversation créée SEULEMENT si user existe
```

### 2. Cleanup Job Quotidien (Nouveau)
```python
# Vérifie et nettoie quotidiennement
- Conversations orphelines (user supprimé)
- Messages soft-deleted anciens (>30 jours)
```

### 3. Endpoints Admin (Nouveau)
```
GET  /api/v1/admin/stats/database          # Monitoring
POST /api/v1/admin/cleanup/orphaned-conversations
POST /api/v1/admin/cleanup/soft-deleted-messages
```

### 4. Logging & Monitoring
```python
logger.warning("user_no_longer_exists", user_id=str(user_id))
# Alerte si incohérence détectée
```

---

## 📊 Comparaison Finale

| Critère                     | Un Schéma | Deux Schémas (Actuel) |
|-----------------------------|-----------|-----------------------|
| **Foreign Keys**            | ✅ Native | ⚠️ Via cleanup jobs    |
| **Transactions ACID**       | ✅ Oui    | ❌ Non (Saga pattern)  |
| **Scaling Indépendant**     | ❌ Non    | ✅ Oui                 |
| **Déploiement Indépendant** | ❌ Non    | ✅ Oui                 |
| **Isolation Pannes**        | ❌ Non    | ✅ Oui                 |
| **Évolutivité Services**    | ❌ Non    | ✅ Oui                 |
| **Complexité**              | ✅ Simple | ⚠️ Moyenne             |
| **Cohérence Données**       | ✅ Immédiate | ⚠️ Éventuelle (avec cleanup) |

---

## 🎯 Recommandation Finale

### ✅ GARDER DEUX SCHÉMAS SÉPARÉS

**Raisons :**
1. ✅ Alignement avec architecture microservices
2. ✅ Scaling indépendant (chatbot ≫ auth en charge)
3. ✅ Déploiement sans downtime
4. ✅ Isolation des pannes
5. ✅ Extensibilité future (nouveaux services)

**Avec mécanismes de cohérence :**
- ✅ Validation JWT (empêche création orphelines)
- ✅ Cleanup jobs automatiques (nettoie incohérences)
- ✅ Endpoints admin (monitoring & maintenance)

---

## 🚀 Quand Passer à Un Seul Schéma ?

**Uniquement si :**
- ❌ Vous fusionnez User + Chatbot en un seul service monolithique
- ❌ Le projet reste petit (<10,000 users, <100,000 messages)
- ❌ Vous n'avez pas besoin de scaler indépendamment
- ❌ Une seule équipe gère tout

**Pour KAURI :**
Deux schémas séparés est la **meilleure architecture** pour croissance et maintenabilité.

---

## 📚 Références

**Microservices Data Patterns :**
- [Database per Service Pattern](https://microservices.io/patterns/data/database-per-service.html)
- [Saga Pattern for Distributed Transactions](https://microservices.io/patterns/data/saga.html)
- [Event-Driven Architecture](https://martinfowler.com/articles/201701-event-driven.html)

**PostgreSQL Multi-Database :**
- [PostgreSQL Multi-Database Best Practices](https://www.postgresql.org/docs/current/managing-databases.html)
- [Schema vs Database in PostgreSQL](https://stackoverflow.com/questions/1152405/postgresql-schemas-vs-databases)

---

## ✅ Action Items

- [x] Modèles SQLAlchemy avec UUID user_id (sans FK native)
- [x] Validation JWT à chaque requête chatbot
- [x] Cleanup job pour conversations orphelines
- [x] Cleanup job pour messages soft-deleted
- [x] Endpoints admin pour monitoring
- [ ] **TODO:** Configurer cron job quotidien (3h du matin)
- [ ] **TODO:** Ajouter alerting si >1000 conversations orphelines détectées
- [ ] **TODO:** Dashboard admin pour visualiser stats DB

---

**Date :** 2025-01-05
**Version :** 1.0
**Statut :** ✅ Approuvé
