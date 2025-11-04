# 🔐 KAURI User Service

> Service d'authentification et gestion des utilisateurs pour l'écosystème KAURI

---

## ✅ Statut: **Complet et Fonctionnel**

Tous les endpoints sont implémentés et testés :
- ✅ `POST /api/v1/auth/register` - Enregistrement
- ✅ `POST /api/v1/auth/login` - Connexion
- ✅ `POST /api/v1/auth/logout` - Déconnexion
- ✅ `GET  /api/v1/auth/me` - Info utilisateur courant

---

## 🏗️ Architecture

```
src/
├── api/
│   ├── main.py                 # Point d'entrée FastAPI
│   └── routes/
│       └── auth.py             # Routes authentification
├── auth/
│   ├── jwt_manager.py          # Gestion JWT tokens
│   └── password.py             # Hashing bcrypt
├── models/
│   └── user.py                 # Modèles SQLAlchemy (User, RevokedToken)
├── schemas/
│   └── user.py                 # Schémas Pydantic (validation)
├── utils/
│   └── database.py             # Connexion DB
└── config.py                   # Configuration (hérite .env)
```

---

## 🚀 Démarrage

### Avec Docker Compose (Recommandé)

```bash
# À la racine du projet
docker-compose up -d kauri_user_service

# Vérifier les logs
docker-compose logs -f kauri_user_service
```

### Local (Développement)

```bash
cd backend/kauri_user_service

# Créer venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installer dépendances
pip install -r requirements.txt

# Démarrer
python -m uvicorn src.api.main:app --reload --port 8001
```

---

## 📚 Documentation API

### Swagger UI (Interactive)
http://localhost:8001/api/v1/docs

### OpenAPI Spec (JSON)
http://localhost:8001/api/v1/openapi.json

---

## 🧪 Tester les Endpoints

### Option 1: Script de Test Automatique

```bash
cd backend/kauri_user_service
python test_auth_endpoints.py
```

**Résultat attendu** :
```
✓ Health Check
✓ Register
✓ Get User Info
✓ Logout
✓ Token Revoked
✓ Login
✓ Get User Info (after login)

Tests réussis: 7/7
```

### Option 2: cURL Manuellement

#### 1. Health Check
```bash
curl http://localhost:8001/api/v1/health
```

**Response** :
```json
{
  "status": "healthy",
  "service": "kauri_user_service",
  "version": "1.0.0",
  "environment": "development",
  "database": "connected"
}
```

#### 2. Register
```bash
curl -X POST "http://localhost:8001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@kauri.com",
    "password": "TestPass123!",
    "first_name": "Test",
    "last_name": "User"
  }'
```

**Response** :
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### 3. Login
```bash
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@kauri.com",
    "password": "TestPass123!"
  }'
```

#### 4. Get Current User (me)
```bash
TOKEN="<votre_token>"

curl -X GET "http://localhost:8001/api/v1/auth/me" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** :
```json
{
  "user_id": "uuid-123",
  "email": "test@kauri.com",
  "first_name": "Test",
  "last_name": "User",
  "is_active": true,
  "is_verified": false,
  "is_superuser": false,
  "created_at": "2025-11-03T20:00:00",
  "updated_at": "2025-11-03T20:00:00",
  "last_login": "2025-11-03T20:00:00"
}
```

#### 5. Logout
```bash
curl -X POST "http://localhost:8001/api/v1/auth/logout" \
  -H "Authorization: Bearer $TOKEN"
```

**Response** :
```json
{
  "message": "Déconnexion réussie"
}
```

---

## 🔐 Sécurité

### JWT Tokens

- **Algorithme**: HS256 (HMAC + SHA-256)
- **Expiration**: 24 heures (configurable)
- **Secret**: Variable `JWT_SECRET_KEY` dans .env
- **Révocation**: Tokens stockés dans table `revoked_tokens` après logout

### Passwords

- **Hashing**: bcrypt avec cost factor 12
- **Validation**:
  - Minimum 8 caractères
  - Au moins 1 majuscule
  - Au moins 1 minuscule
  - Au moins 1 chiffre

### Rate Limiting

- **Limite**: 100 requêtes/minute par utilisateur (configurable)
- **Implémenté via**: Middleware FastAPI

---

## 🗄️ Base de Données

### Modèle User

```sql
CREATE TABLE users (
    user_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    google_id VARCHAR(255) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Modèle RevokedToken

```sql
CREATE TABLE revoked_tokens (
    token_id VARCHAR(36) PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

---

## ⚙️ Configuration

### Variables d'Environnement

Hérite du `.env` racine + `.env` local du service.

**Variables importantes** :

```bash
# Service
SERVICE_PORT=8001
SERVICE_NAME=kauri_user_service

# Database
DATABASE_URL=postgresql://kauri_user:password@postgres:5432/kauri_users

# JWT
JWT_SECRET_KEY=votre_secret_super_long
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Password Policy
PASSWORD_MIN_LENGTH=8
```

---

## 🧩 Intégration avec Autres Services

### Chatbot Service

Le Chatbot Service utilise le User Service pour :
1. **Valider les tokens JWT** avant chaque requête
2. **Récupérer les infos utilisateur** pour personnaliser les réponses
3. **Associer les conversations** à un utilisateur

**Exemple de validation de token** :

```python
import requests

def validate_token(token: str) -> dict:
    """Valide un token JWT via le User Service"""
    response = requests.get(
        "http://kauri_user_service:8001/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:
        return response.json()  # Infos utilisateur
    else:
        raise Exception("Token invalide")
```

---

## 🛠️ Développement

### Ajouter un Nouvel Endpoint

1. **Créer la route** dans `src/api/routes/`
2. **Ajouter les schémas Pydantic** dans `src/schemas/`
3. **Créer le modèle SQLAlchemy** si nécessaire dans `src/models/`
4. **Inclure le router** dans `src/api/main.py`

**Exemple** :

```python
# src/api/routes/users.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..utils.database import get_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])

@router.get("/{user_id}")
async def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

---

## 📊 Logs

Les logs sont structurés avec **structlog** :

```json
{
  "event": "user_registration_success",
  "user_id": "uuid-123",
  "email": "test@kauri.com",
  "timestamp": "2025-11-03T20:00:00",
  "level": "info"
}
```

**Voir les logs** :

```bash
# Tous les logs
docker-compose logs -f kauri_user_service

# Filtrer par mot-clé
docker-compose logs kauri_user_service | grep "user_login"
```

---

## ❓ FAQ

### Comment changer la durée d'expiration des tokens ?

Modifier `JWT_EXPIRE_HOURS` dans `.env` :
```bash
JWT_EXPIRE_HOURS=48  # 48 heures au lieu de 24
```

### Comment ajouter OAuth Google ?

1. Configurer `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` dans `.env`
2. Implémenter la route `/api/v1/auth/google` dans `auth.py`
3. Utiliser `google-auth-library-python`

### Comment activer l'email de vérification ?

Modifier `EMAIL_VERIFICATION_REQUIRED=true` dans `.env` et implémenter :
1. Endpoint `/api/v1/auth/send-verification`
2. Endpoint `/api/v1/auth/verify-email`

---

## 🔗 Liens Utiles

- **Documentation API** : http://localhost:8001/api/v1/docs
- **Health Check** : http://localhost:8001/api/v1/health
- **Architecture Globale** : `../../ARCHITECTURE_SUMMARY.md`
- **Guide Quickstart** : `../../QUICKSTART.md`

---

## 📝 Changelog

### v1.0.0 (2025-11-03)

- ✅ Implémentation complète authentification JWT
- ✅ Endpoints: register, login, logout, me
- ✅ Modèles User + RevokedToken
- ✅ Password hashing bcrypt
- ✅ Validation Pydantic
- ✅ Tests automatisés
- ✅ Documentation Swagger

---

**Version** : 1.0.0
**Date** : 2025-11-03
**Statut** : ✅ Production Ready
