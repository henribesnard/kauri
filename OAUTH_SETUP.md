# Configuration OAuth - Kauri

Ce guide explique comment configurer l'authentification OAuth avec Google, Facebook, LinkedIn et Twitter pour Kauri.

## 📋 Table des matières

- [Prérequis](#prérequis)
- [Configuration des providers](#configuration-des-providers)
  - [Google OAuth](#google-oauth)
  - [Facebook OAuth](#facebook-oauth)
  - [LinkedIn OAuth](#linkedin-oauth)
  - [Twitter OAuth](#twitter-oauth)
- [Configuration du backend](#configuration-du-backend)
- [Migration de la base de données](#migration-de-la-base-de-données)
- [Installation des dépendances](#installation-des-dépendances)
- [Test de l'intégration](#test-de-lintégration)

## Prérequis

- Compte développeur pour chaque provider que vous souhaitez utiliser
- Backend Kauri User Service installé
- Frontend Kauri App installé
- PostgreSQL configuré

## Configuration des providers

### Google OAuth

1. **Créer un projet Google Cloud**
   - Allez sur [Google Cloud Console](https://console.cloud.google.com/)
   - Créez un nouveau projet ou sélectionnez un projet existant

2. **Activer l'API Google+**
   - Dans le menu, allez dans "APIs & Services" > "Library"
   - Recherchez "Google+ API" et activez-la

3. **Créer des credentials OAuth 2.0**
   - Allez dans "APIs & Services" > "Credentials"
   - Cliquez sur "Create Credentials" > "OAuth client ID"
   - Type d'application: "Web application"
   - Nom: "Kauri App"
   - Authorized redirect URIs:
     - `http://localhost:8001/api/v1/oauth/callback/google` (développement)
     - `https://votre-domaine.com/api/v1/oauth/callback/google` (production)

4. **Récupérer les credentials**
   - Copiez le `Client ID` et `Client Secret`
   - Ajoutez-les dans votre `.env`

### Facebook OAuth

1. **Créer une application Facebook**
   - Allez sur [Facebook Developers](https://developers.facebook.com/)
   - Cliquez sur "My Apps" > "Create App"
   - Type: "Consumer"
   - Nom de l'app: "Kauri"

2. **Configurer Facebook Login**
   - Dans le tableau de bord de l'app, ajoutez "Facebook Login"
   - Allez dans "Facebook Login" > "Settings"
   - Valid OAuth Redirect URIs:
     - `http://localhost:8001/api/v1/oauth/callback/facebook`
     - `https://votre-domaine.com/api/v1/oauth/callback/facebook`

3. **Récupérer les credentials**
   - Allez dans "Settings" > "Basic"
   - Copiez "App ID" (Client ID) et "App Secret" (Client Secret)
   - Ajoutez-les dans votre `.env`

### LinkedIn OAuth

1. **Créer une application LinkedIn**
   - Allez sur [LinkedIn Developers](https://www.linkedin.com/developers/apps)
   - Cliquez sur "Create app"
   - Remplissez les informations requises

2. **Configurer OAuth 2.0**
   - Dans "Auth" tab
   - Redirect URLs:
     - `http://localhost:8001/api/v1/oauth/callback/linkedin`
     - `https://votre-domaine.com/api/v1/oauth/callback/linkedin`
   - OAuth 2.0 scopes: `openid`, `profile`, `email`

3. **Récupérer les credentials**
   - Dans "Auth" tab
   - Copiez "Client ID" et "Client Secret"
   - Ajoutez-les dans votre `.env`

### Twitter OAuth

1. **Créer une application Twitter**
   - Allez sur [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
   - Créez un nouveau projet et une app

2. **Configurer OAuth 2.0**
   - Dans les paramètres de l'app, activez OAuth 2.0
   - Type: "Web App"
   - Callback URLs:
     - `http://localhost:8001/api/v1/oauth/callback/twitter`
     - `https://votre-domaine.com/api/v1/oauth/callback/twitter`

3. **Récupérer les credentials**
   - Dans "Keys and tokens"
   - Copiez "OAuth 2.0 Client ID" et "Client Secret"
   - Ajoutez-les dans votre `.env`

## Configuration du backend

### Variables d'environnement

Ajoutez ces variables dans votre fichier `.env` à la racine du projet :

```bash
# ============================================
# OAuth Configuration
# ============================================

# OAuth State Secret (pour protection CSRF)
OAUTH_STATE_SECRET=votre-secret-tres-securise-changez-moi

# Frontend URL (pour les redirections)
FRONTEND_URL=http://localhost:5173

# Google OAuth
GOOGLE_CLIENT_ID=votre-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre-google-client-secret

# Facebook OAuth
FACEBOOK_CLIENT_ID=votre-facebook-app-id
FACEBOOK_CLIENT_SECRET=votre-facebook-app-secret

# LinkedIn OAuth
LINKEDIN_CLIENT_ID=votre-linkedin-client-id
LINKEDIN_CLIENT_SECRET=votre-linkedin-client-secret

# Twitter OAuth
TWITTER_CLIENT_ID=votre-twitter-client-id
TWITTER_CLIENT_SECRET=votre-twitter-client-secret
```

### Notes importantes

- **OAUTH_STATE_SECRET**: Générez une clé secrète aléatoire et sécurisée (minimum 32 caractères)
- **FRONTEND_URL**: URL de votre application frontend (change en production)
- Vous n'êtes pas obligé de configurer tous les providers. Les providers non configurés ne seront simplement pas affichés.

## Migration de la base de données

Exécutez la migration SQL pour ajouter les champs OAuth :

```bash
# Depuis la racine du projet
cd backend/kauri_user_service

# Exécutez la migration SQL
psql -U kauri_user -d kauri_db -f alembic_migration_oauth.sql

# Ou via Docker
docker exec -i kauri-postgres psql -U kauri_user -d kauri_db < alembic_migration_oauth.sql
```

La migration ajoute les colonnes suivantes à la table `users` :
- `avatar_url` - URL de la photo de profil
- `facebook_id` - ID utilisateur Facebook
- `linkedin_id` - ID utilisateur LinkedIn
- `twitter_id` - ID utilisateur Twitter
- `oauth_provider` - Provider utilisé pour l'inscription

## Installation des dépendances

### Backend

```bash
cd backend/kauri_user_service
pip install -r requirements.txt
```

Les nouvelles dépendances ajoutées :
- `authlib==1.3.2` - Bibliothèque OAuth
- `itsdangerous==2.2.0` - Pour la génération de tokens state sécurisés

### Frontend

Aucune dépendance supplémentaire n'est nécessaire. Les icônes OAuth utilisent `lucide-react` qui est déjà installé.

## Test de l'intégration

### 1. Démarrer les services

```bash
# Backend
cd backend/kauri_user_service
python -m src.api.main

# Frontend (dans un autre terminal)
cd frontend/kauri-app
npm run dev
```

### 2. Tester l'authentification

1. Ouvrez votre navigateur sur `http://localhost:5173/login`
2. Vous devriez voir les boutons OAuth pour les providers configurés
3. Cliquez sur un bouton OAuth
4. Vous serez redirigé vers la page de connexion du provider
5. Après autorisation, vous serez redirigé vers l'application

### 3. Vérifier les endpoints

```bash
# Lister les providers disponibles
curl http://localhost:8001/api/v1/oauth/providers

# Réponse attendue :
{
  "providers": {
    "google": true,
    "facebook": true,
    "linkedin": false,
    "twitter": false
  },
  "enabled_providers": ["google", "facebook"]
}
```

## Flux OAuth

```
1. Utilisateur clique sur "Continuer avec Google"
   ↓
2. Redirection vers /api/v1/oauth/login/google
   ↓
3. Backend génère un state token (protection CSRF)
   ↓
4. Redirection vers Google OAuth
   ↓
5. Utilisateur s'authentifie sur Google
   ↓
6. Google redirige vers /api/v1/oauth/callback/google?code=...&state=...
   ↓
7. Backend vérifie le state token
   ↓
8. Backend échange le code contre un access token
   ↓
9. Backend récupère les infos utilisateur depuis Google
   ↓
10. Backend crée ou récupère l'utilisateur en DB
    ↓
11. Backend génère un JWT token Kauri
    ↓
12. Redirection vers frontend avec le token
    ↓
13. Frontend stocke le token et redirige vers /chat
```

## Sécurité

### Protection CSRF avec State Token
Chaque flux OAuth génère un state token unique qui :
- Est signé cryptographiquement avec `OAUTH_STATE_SECRET`
- Expire après 10 minutes
- Doit correspondre lors du callback

### Gestion des comptes
- Si un utilisateur s'inscrit avec email/password puis se connecte via OAuth avec le même email, les comptes sont automatiquement liés
- Un utilisateur peut avoir plusieurs providers liés (Google + Facebook par exemple)
- Le champ `oauth_provider` indique le provider utilisé pour l'inscription initiale

### Tokens JWT
- Les tokens JWT Kauri sont utilisés pour toutes les requêtes API après authentification OAuth
- Même durée de vie que les tokens classiques (configuré dans `JWT_EXPIRE_HOURS`)

## Dépannage

### "Provider non configuré"
- Vérifiez que vous avez bien défini `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` dans `.env`
- Redémarrez le backend après modification du `.env`

### "Invalid redirect URI"
- Vérifiez que l'URL de callback est exactement la même dans la console du provider et dans votre configuration
- Format: `http://localhost:8001/api/v1/oauth/callback/{provider}`

### "Token invalide" ou "State invalide"
- Vérifiez que `OAUTH_STATE_SECRET` est bien défini
- Assurez-vous que l'horloge du serveur est correcte

### Twitter ne fournit pas d'email
- Twitter nécessite une permission spéciale pour accéder à l'email
- Si non disponible, un email temporaire est généré: `twitter_{id}@kauri-oauth.local`
- L'utilisateur peut mettre à jour son email dans les paramètres

## Support

Pour plus d'informations :
- [Documentation Authlib](https://docs.authlib.org/)
- [Google OAuth Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Facebook Login Documentation](https://developers.facebook.com/docs/facebook-login)
- [LinkedIn OAuth Documentation](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [Twitter OAuth Documentation](https://developer.twitter.com/en/docs/authentication/oauth-2-0)
