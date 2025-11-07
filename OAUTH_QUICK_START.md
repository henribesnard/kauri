# ⚡ OAuth Quick Start - 5 minutes

Guide ultra-rapide pour activer OAuth sur Kauri.

## 🎯 Objectif

Activer Google OAuth en moins de 5 minutes.

## 📋 Prérequis

- Compte Google
- Backend et frontend Kauri déjà installés
- PostgreSQL qui tourne

## 🚀 Étapes

### 1️⃣ Migration base de données (30 secondes)

```bash
cd backend/kauri_user_service
psql -U kauri_user -d kauri_db -f alembic_migration_oauth.sql
```

### 2️⃣ Installer dépendances (1 minute)

```bash
cd backend/kauri_user_service
pip install authlib itsdangerous
```

### 3️⃣ Obtenir credentials Google (2 minutes)

1. Allez sur https://console.cloud.google.com/
2. Créez un projet "Kauri"
3. "APIs & Services" → "Credentials" → "Create Credentials" → "OAuth client ID"
4. Type: Web application
5. Authorized redirect URIs: `http://localhost:8001/api/v1/oauth/callback/google`
6. Copiez Client ID et Client Secret

### 4️⃣ Configuration .env (1 minute)

Ajoutez dans votre `.env` :

```bash
OAUTH_STATE_SECRET=change-moi-par-une-cle-aleatoire-de-32-caracteres-minimum
FRONTEND_URL=http://localhost:5173
GOOGLE_CLIENT_ID=votre-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre-client-secret
```

### 5️⃣ Test (30 secondes)

```bash
# Tester la config
cd backend/kauri_user_service
python test_oauth_config.py

# Démarrer
python -m src.api.main
```

Dans un autre terminal :

```bash
cd frontend/kauri-app
npm run dev
```

### 6️⃣ Vérification

Ouvrez http://localhost:5173/login

Vous devriez voir un bouton "Continuer avec Google" ✅

## 🎉 C'est tout !

Cliquez sur le bouton pour tester.

## ❌ En cas de problème

### Pas de bouton Google visible ?

```bash
# Vérifiez la config
python test_oauth_config.py

# Le résultat doit montrer:
# Google: ✅ Configuré
```

### "Provider non configuré" ?

Vérifiez que votre `.env` contient bien :
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

Puis redémarrez le backend.

### "Invalid redirect URI" ?

Vérifiez dans Google Cloud Console que l'URL est exactement :
```
http://localhost:8001/api/v1/oauth/callback/google
```

## 📚 Pour aller plus loin

- Guide complet : `OAUTH_SETUP.md`
- Documentation : `OAUTH_README.md`
- Prochaines étapes : `OAUTH_NEXT_STEPS.md`

---

**Temps total estimé : 5 minutes** ⏱️
