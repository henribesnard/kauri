# KAURI Frontend

Application React moderne pour la gestion comptable OHADA.

## 🚀 Technologies

- **React 18** avec TypeScript
- **Vite** - Build tool ultra-rapide
- **Tailwind CSS** - Framework CSS utility-first
- **React Router v6** - Routing
- **Axios** - Client HTTP
- **Lucide React** - Icônes

## 📁 Structure du projet

```
src/
├── components/          # Composants réutilisables
│   ├── auth/           # Composants d'authentification
│   ├── dashboard/      # Composants du dashboard
│   └── layout/         # Composants de mise en page
├── contexts/           # Contextes React (AuthContext)
├── pages/              # Pages de l'application
├── services/           # Services API (axios)
├── types/              # Types TypeScript
└── utils/              # Utilitaires
```

## 🛠️ Développement local

### Prérequis

- Node.js 20+
- npm ou yarn

### Installation

```bash
npm install
```

### Lancer le serveur de développement

```bash
npm run dev
```

L'application sera accessible sur `http://localhost:5173`

### Build de production

```bash
npm run build
```

Les fichiers compilés seront dans le dossier `dist/`

## 🐳 Docker

### Build de l'image Docker

```bash
docker build -t kauri-frontend .
```

### Lancer avec docker-compose

À la racine du projet :

```bash
docker-compose up kauri_frontend
```

L'application sera accessible sur `http://localhost:3000`

## 🔐 Authentification

L'application utilise JWT pour l'authentification :

1. **Login/Register** - Les tokens sont stockés dans localStorage
2. **Protected Routes** - Routes automatiquement protégées
3. **API Interceptors** - Ajout automatique du token aux requêtes

## 🌐 Variables d'environnement

Créez un fichier `.env` pour le développement :

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USER_SERVICE_URL=http://localhost:8001
VITE_CHATBOT_SERVICE_URL=http://localhost:8002
```

En production (Docker), les requêtes API passent par le proxy nginx.

## 📦 Services API disponibles

- **User Service** (port 8001/3201)
  - `/api/v1/auth/login` - Connexion
  - `/api/v1/auth/register` - Inscription
  - `/api/v1/auth/me` - Profil utilisateur

- **Chatbot Service** (port 8002/3202)
  - `/api/v1/chat/query` - Envoyer une question
  - `/api/v1/chat/stream` - Chat en streaming (SSE)

## 🎨 Composants principaux

### Layout
- `Sidebar` - Navigation latérale
- `Header` - En-tête avec recherche et profil utilisateur
- `DashboardLayout` - Layout principal avec sidebar + header

### Dashboard
- `KPICard` - Carte d'indicateur de performance
- `TransactionList` - Liste des transactions récentes
- `TaskList` - Liste des tâches à faire
- `Chatbot` - Assistant IA intégré

### Pages
- `LoginPage` - Page de connexion
- `RegisterPage` - Page d'inscription
- `DashboardPage` - Tableau de bord principal
- `PlaceholderPage` - Page placeholder pour les routes en développement

## 🔄 Prochaines étapes

- [ ] Implémenter les pages Achats, Ventes, Banque
- [ ] Ajouter React Query pour la gestion du cache
- [ ] Implémenter les vrais appels API pour les KPIs
- [ ] Ajouter les tests (Vitest + React Testing Library)
- [ ] Implémenter le téléchargement de fichiers pour le chatbot
- [ ] Ajouter la génération de PDF pour les rapports

## 📝 Notes de développement

- Le chatbot supporte le streaming SSE pour les réponses en temps réel
- Toutes les requêtes API incluent automatiquement le token JWT
- Le proxy nginx gère le routing API en production
- Les routes sont protégées automatiquement par `ProtectedRoute`
