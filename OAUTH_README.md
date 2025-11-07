# 🔐 Authentification OAuth - Kauri

## 🎯 Vue d'ensemble

Kauri supporte maintenant l'authentification OAuth avec **4 providers populaires** :

| Provider | Status | Gratuit | Scopes |
|----------|--------|---------|--------|
| 🔵 **Google** | ✅ Supporté | Oui | openid, email, profile |
| 🔵 **Facebook** | ✅ Supporté | Oui | email, public_profile |
| 🔵 **LinkedIn** | ✅ Supporté | Oui | openid, profile, email |
| 🔵 **Twitter** | ✅ Supporté | Oui | tweet.read, users.read |

## ✨ Fonctionnalités

- ✅ **4 providers OAuth** intégrés avec Authlib
- ✅ **100% gratuit** - Pas de coûts cachés, Authlib est open-source
- ✅ **Configuration flexible** - Activez seulement les providers dont vous avez besoin
- ✅ **Détection automatique** - Les boutons s'affichent uniquement si le provider est configuré
- ✅ **Liaison de comptes** - Si l'email existe déjà, les comptes sont automatiquement liés
- ✅ **Multi-providers** - Un utilisateur peut avoir plusieurs providers liés
- ✅ **Protection CSRF** - State tokens sécurisés pour chaque flux OAuth
- ✅ **Gestion d'erreurs** - Messages d'erreur clairs pour l'utilisateur
- ✅ **UI moderne** - Boutons responsive avec icônes

## 📁 Fichiers créés/modifiés

### Backend
```
backend/kauri_user_service/
├── requirements.txt                          (modifié - authlib, itsdangerous)
├── alembic_migration_oauth.sql              (nouveau - migration SQL)
├── test_oauth_config.py                     (nouveau - script de test)
└── src/
    ├── config.py                            (modifié - config OAuth)
    ├── models/user.py                       (modifié - champs OAuth)
    ├── auth/
    │   └── oauth_manager.py                 (nouveau - gestionnaire OAuth)
    └── api/
        ├── main.py                          (modifié - router OAuth)
        └── routes/
            └── oauth.py                     (nouveau - endpoints OAuth)
```

### Frontend
```
frontend/kauri-app/src/
├── App.tsx                                   (modifié - route callback)
├── components/auth/
│   └── OAuthButtons.tsx                     (nouveau - boutons OAuth)
└── pages/
    ├── LoginPage.tsx                        (modifié - intégration OAuth)
    ├── RegisterPage.tsx                     (modifié - intégration OAuth)
    └── OAuthCallbackPage.tsx                (nouveau - page callback)
```

### Documentation
```
├── OAUTH_SETUP.md                           (guide de configuration)
├── OAUTH_IMPLEMENTATION_SUMMARY.md          (résumé technique)
├── OAUTH_README.md                          (ce fichier)
└── .env.oauth.example                       (exemple configuration)
```

## 🚀 Quick Start

### 1. Installation

```bash
# Backend
cd backend/kauri_user_service
pip install -r requirements.txt

# Frontend (aucune dépendance supplémentaire)
cd frontend/kauri-app
npm install
```

### 2. Migration base de données

```bash
# Via psql
psql -U kauri_user -d kauri_db -f backend/kauri_user_service/alembic_migration_oauth.sql

# Ou via Docker
docker exec -i kauri-postgres psql -U kauri_user -d kauri_db < backend/kauri_user_service/alembic_migration_oauth.sql
```

### 3. Configuration

Ajoutez ces variables dans votre `.env` :

```bash
# OAuth State Secret (générez une clé aléatoire)
OAUTH_STATE_SECRET=votre-secret-tres-securise-32-chars-minimum

# Frontend URL
FRONTEND_URL=http://localhost:5173

# Google OAuth (exemple)
GOOGLE_CLIENT_ID=votre-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=votre-google-client-secret

# Facebook OAuth (optionnel)
FACEBOOK_CLIENT_ID=votre-facebook-app-id
FACEBOOK_CLIENT_SECRET=votre-facebook-app-secret

# LinkedIn OAuth (optionnel)
LINKEDIN_CLIENT_ID=votre-linkedin-client-id
LINKEDIN_CLIENT_SECRET=votre-linkedin-client-secret

# Twitter OAuth (optionnel)
TWITTER_CLIENT_ID=votre-twitter-client-id
TWITTER_CLIENT_SECRET=votre-twitter-client-secret
```

**Note**: Consultez `OAUTH_SETUP.md` pour obtenir les credentials de chaque provider.

### 4. Test de la configuration

```bash
cd backend/kauri_user_service
python test_oauth_config.py
```

Output attendu :
```
🔍 Test de la configuration OAuth...

1️⃣  Test des imports...
   ✅ Tous les imports sont OK

2️⃣  Test de la configuration...
   Frontend URL: http://localhost:5173
   OAuth State Secret défini: ✅

3️⃣  Providers OAuth configurés:
   Google: ✅ Configuré
   Facebook: ⚠️  Non configuré
   Linkedin: ⚠️  Non configuré
   Twitter: ⚠️  Non configuré

   Total configurés: 1/4

==================================================
✅ Configuration OAuth prête !
   1 provider(s) configuré(s)
==================================================
```

### 5. Démarrage

```bash
# Backend
cd backend/kauri_user_service
python -m src.api.main

# Frontend (nouveau terminal)
cd frontend/kauri-app
npm run dev
```

### 6. Test manuel

1. Ouvrez http://localhost:5173/login
2. Vous devriez voir les boutons OAuth
3. Cliquez sur "Continuer avec Google"
4. Authentifiez-vous
5. Vous serez redirigé vers /chat

## 🔗 Endpoints API

### GET `/api/v1/oauth/providers`
Liste les providers OAuth disponibles et configurés.

**Réponse:**
```json
{
  "providers": {
    "google": true,
    "facebook": false,
    "linkedin": false,
    "twitter": false
  },
  "enabled_providers": ["google"]
}
```

### GET `/api/v1/oauth/login/{provider}`
Initie le flux OAuth pour le provider spécifié.

**Paramètres:**
- `provider`: google | facebook | linkedin | twitter

**Réponse:** Redirection vers la page d'authentification du provider

### GET `/api/v1/oauth/callback/{provider}`
Callback OAuth - Reçoit le code d'autorisation.

**Paramètres query:**
- `code`: Code d'autorisation
- `state`: Token de protection CSRF

**Réponse:** Redirection vers le frontend avec le token JWT

## 📱 Interface utilisateur

### Page de connexion
![Login with OAuth](docs/oauth-login.png)

Les boutons OAuth apparaissent automatiquement après le séparateur "Ou continuer avec".

### Page d'inscription
Les mêmes boutons sont disponibles sur la page d'inscription pour créer un compte via OAuth.

## 🔒 Sécurité

### Protection CSRF
Chaque flux OAuth utilise un **state token** :
- Signé cryptographiquement avec `OAUTH_STATE_SECRET`
- Expire après 10 minutes
- Vérifié obligatoirement au callback

### Gestion des données
- Les passwords sont optionnels pour les comptes OAuth
- Les emails OAuth sont vérifiés par défaut
- Les tokens JWT suivent les mêmes règles que l'authentification classique

### Liaison de comptes
Si un utilisateur :
1. S'inscrit avec email/password : `henri@example.com`
2. Puis se connecte via Google avec : `henri@example.com`

→ Les comptes sont **automatiquement liés** (pas de duplication)

## 🔧 Dépannage

### "Provider non configuré"
**Cause**: Credentials manquants dans `.env`

**Solution**:
1. Vérifiez que `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` sont définis
2. Redémarrez le backend après modification
3. Testez avec `python test_oauth_config.py`

### "Invalid redirect URI"
**Cause**: URL de callback incorrecte dans la console du provider

**Solution**:
- Format exact : `http://localhost:8001/api/v1/oauth/callback/{provider}`
- Doit correspondre exactement à l'URL configurée dans la console

### "State invalide"
**Cause**: `OAUTH_STATE_SECRET` non défini ou expiré

**Solution**:
1. Définissez `OAUTH_STATE_SECRET` dans `.env`
2. Générez une clé aléatoire : `openssl rand -hex 32`

### Aucun bouton OAuth visible
**Cause**: Aucun provider configuré

**Solution**:
1. Exécutez `python test_oauth_config.py`
2. Configurez au moins un provider
3. Redémarrez le backend

## 📚 Documentation complète

- **Configuration détaillée**: Consultez `OAUTH_SETUP.md`
- **Détails techniques**: Consultez `OAUTH_IMPLEMENTATION_SUMMARY.md`
- **Exemple .env**: Consultez `.env.oauth.example`

## 🌐 URLs de redirection par environnement

### Développement
```
Backend: http://localhost:8001
Frontend: http://localhost:5173
Redirect URIs: http://localhost:8001/api/v1/oauth/callback/{provider}
```

### Production
```
Backend: https://api.votre-domaine.com
Frontend: https://votre-domaine.com
Redirect URIs: https://api.votre-domaine.com/api/v1/oauth/callback/{provider}
```

**Important**: Mettez à jour les redirect URIs dans chaque console de provider lors du déploiement en production.

## 💡 Conseils

1. **Commencez avec Google** - Plus simple à configurer
2. **Un provider suffit** - Pas besoin de tous les configurer
3. **Testez en local** - Utilisez localhost pour le développement
4. **HTTPS en production** - Obligatoire pour OAuth en production
5. **Gardez vos secrets privés** - Ne commitez jamais les credentials

## 📞 Support

Pour toute question sur :
- **Configuration des providers** → Consultez `OAUTH_SETUP.md`
- **Problèmes techniques** → Consultez `OAUTH_IMPLEMENTATION_SUMMARY.md`
- **Authlib** → [Documentation Authlib](https://docs.authlib.org/)

## 🎉 C'est tout !

Votre application Kauri supporte maintenant l'authentification OAuth avec 4 providers majeurs, le tout gratuitement et avec une configuration flexible.

Bon développement ! 🚀
