# KAURI Frontend - Spécifications Complètes

> **Application React pour la Gestion Comptable OHADA**
> **Date**: 2025-11-04
> **Version**: 1.0

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Architecture Frontend](#2-architecture-frontend)
3. [Design System](#3-design-system)
4. [Pages et Fonctionnalités](#4-pages-et-fonctionnalités)
5. [Composants Réutilisables](#5-composants-réutilisables)
6. [Intégration Backend](#6-intégration-backend)
7. [Authentification et Sécurité](#7-authentification-et-sécurité)
8. [Tests et Qualité](#8-tests-et-qualité)
9. [Déploiement](#9-déploiement)
10. [Roadmap](#10-roadmap)

---

## 1. Vue d'Ensemble

### 1.1 Objectif

KAURI Frontend est l'interface utilisateur moderne de la plateforme KAURI, une solution de gestion comptable intelligente conforme aux normes OHADA (Organisation pour l'Harmonisation en Afrique du Droit des Affaires).

### 1.2 Utilisateurs Cibles

- **Comptables** : Gestion quotidienne des opérations comptables
- **Chefs d'entreprise** : Suivi de la santé financière
- **Experts-comptables** : Supervision et validation
- **Assistants comptables** : Saisie et traitement des documents

### 1.3 Stack Technique

```yaml
Framework: React 18.3+
Language: TypeScript 5.5+
Build Tool: Vite 6.0+
Styling: Tailwind CSS 3.4+
Routing: React Router v6
HTTP Client: Axios
State Management: React Context API (+ React Query pour cache)
Icons: Lucide React
Forms: React Hook Form + Zod validation
Charts: Recharts
PDF Generation: jsPDF
Date Management: date-fns
```

---

## 2. Architecture Frontend

### 2.1 Structure du Projet

```
kauri-app/
├── public/                    # Assets statiques
│   ├── logo.svg
│   └── favicon.ico
├── src/
│   ├── assets/               # Images, fonts, etc.
│   ├── components/           # Composants réutilisables
│   │   ├── auth/            # Authentification
│   │   │   ├── ProtectedRoute.tsx
│   │   │   └── LoginForm.tsx
│   │   ├── dashboard/       # Dashboard
│   │   │   ├── Chatbot.tsx
│   │   │   ├── KPICard.tsx
│   │   │   ├── TransactionList.tsx
│   │   │   └── TaskList.tsx
│   │   ├── layout/          # Layout
│   │   │   ├── DashboardLayout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   ├── shared/          # Composants partagés
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Table.tsx
│   │   │   └── Alert.tsx
│   │   └── charts/          # Graphiques
│   │       ├── LineChart.tsx
│   │       └── BarChart.tsx
│   ├── contexts/            # Contextes React
│   │   ├── AuthContext.tsx
│   │   ├── ThemeContext.tsx
│   │   └── NotificationContext.tsx
│   ├── hooks/               # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useApi.ts
│   │   └── useDebounce.ts
│   ├── pages/               # Pages
│   │   ├── auth/
│   │   │   ├── LoginPage.tsx
│   │   │   └── RegisterPage.tsx
│   │   ├── dashboard/
│   │   │   └── DashboardPage.tsx
│   │   ├── accounting/
│   │   │   ├── PurchasesPage.tsx
│   │   │   ├── SalesPage.tsx
│   │   │   ├── BankPage.tsx
│   │   │   └── AssetsPage.tsx
│   │   ├── reports/
│   │   │   ├── BalanceSheetPage.tsx
│   │   │   ├── IncomeStatementPage.tsx
│   │   │   └── GeneralLedgerPage.tsx
│   │   └── settings/
│   │       └── SettingsPage.tsx
│   ├── services/            # Services API
│   │   ├── api.ts           # Configuration Axios
│   │   ├── authService.ts   # Authentification
│   │   ├── chatbotService.ts
│   │   ├── transactionService.ts
│   │   └── reportService.ts
│   ├── types/               # Types TypeScript
│   │   ├── index.ts
│   │   ├── auth.ts
│   │   ├── transaction.ts
│   │   └── report.ts
│   ├── utils/               # Utilitaires
│   │   ├── format.ts        # Formatage (dates, nombres)
│   │   ├── validation.ts    # Validations
│   │   └── constants.ts     # Constantes
│   ├── App.tsx              # Composant principal
│   ├── main.tsx             # Point d'entrée
│   └── index.css            # Styles globaux
├── .env.development         # Variables d'env dev
├── .env.production          # Variables d'env prod
├── Dockerfile               # Docker
├── nginx.conf               # Configuration Nginx
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

### 2.2 Flux de Données

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│  React Components   │
│  (UI Layer)         │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  React Context API  │
│  (State Management) │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Services Layer     │
│  (API Calls)        │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Axios HTTP Client  │
│  (with interceptors)│
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  API Gateway        │
│  (Backend)          │
└─────────────────────┘
```

### 2.3 Routing

```typescript
// Routes principales
/                          → Redirect to /login or /dashboard
/login                     → LoginPage
/register                  → RegisterPage
/dashboard                 → DashboardPage (Protected)
/purchases                 → PurchasesPage (Protected)
/sales                     → SalesPage (Protected)
/bank                      → BankPage (Protected)
/assets                    → AssetsPage (Protected)
/reports                   → ReportsPage (Protected)
  /reports/balance-sheet   → BalanceSheetPage
  /reports/income-statement → IncomeStatementPage
  /reports/general-ledger  → GeneralLedgerPage
/settings                  → SettingsPage (Protected)
```

---

## 3. Design System

### 3.1 Palette de Couleurs

```css
/* Primary Colors (Teal/Green) */
--primary-50:  #f0fdf4;
--primary-100: #dcfce7;
--primary-200: #bbf7d0;
--primary-300: #86efac;
--primary-400: #4ade80;
--primary-500: #0e766e;  /* Main brand color */
--primary-600: #0c6460;
--primary-700: #0a5450;
--primary-800: #084440;
--primary-900: #063630;

/* Gray Scale */
--gray-50:  #f9fafb;
--gray-100: #f3f4f6;
--gray-200: #e5e7eb;
--gray-300: #d1d5db;
--gray-400: #9ca3af;
--gray-500: #6b7280;
--gray-600: #4b5563;
--gray-700: #374151;
--gray-800: #1f2937;
--gray-900: #111827;

/* Semantic Colors */
--success: #10b981;
--warning: #f59e0b;
--error:   #ef4444;
--info:    #3b82f6;
```

### 3.2 Typographie

```css
/* Font Family */
font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;

/* Font Sizes */
text-xs:   0.75rem;   /* 12px */
text-sm:   0.875rem;  /* 14px */
text-base: 1rem;      /* 16px */
text-lg:   1.125rem;  /* 18px */
text-xl:   1.25rem;   /* 20px */
text-2xl:  1.5rem;    /* 24px */
text-3xl:  1.875rem;  /* 30px */
text-4xl:  2.25rem;   /* 36px */

/* Font Weights */
font-normal:   400;
font-medium:   500;
font-semibold: 600;
font-bold:     700;
font-extrabold: 800;
```

### 3.3 Espacements

```css
/* Spacing Scale (Tailwind) */
0:   0px;
1:   0.25rem;  /* 4px */
2:   0.5rem;   /* 8px */
3:   0.75rem;  /* 12px */
4:   1rem;     /* 16px */
5:   1.25rem;  /* 20px */
6:   1.5rem;   /* 24px */
8:   2rem;     /* 32px */
10:  2.5rem;   /* 40px */
12:  3rem;     /* 48px */
16:  4rem;     /* 64px */
```

### 3.4 Composants UI Standards

#### Button

```tsx
// Variants: primary, secondary, outline, ghost
<Button variant="primary" size="md">
  Valider
</Button>
```

#### Input

```tsx
<Input
  label="Email"
  type="email"
  placeholder="exemple@kauri.com"
  error="Email invalide"
/>
```

#### Card

```tsx
<Card title="Transactions récentes">
  {content}
</Card>
```

#### Modal

```tsx
<Modal
  isOpen={isOpen}
  onClose={handleClose}
  title="Confirmation"
>
  {content}
</Modal>
```

---

## 4. Pages et Fonctionnalités

### 4.1 Page de Connexion (`/login`)

**Objectif** : Authentifier l'utilisateur

**Composants** :
- Formulaire de connexion (email + password)
- Lien "Mot de passe oublié"
- Lien vers inscription
- Logo et branding KAURI

**Validation** :
- Email valide (format)
- Password minimum 8 caractères

**API Endpoint** :
```
POST /api/v1/auth/login
Body: { email, password }
Response: { access_token, refresh_token, user }
```

---

### 4.2 Page Tableau de Bord (`/dashboard`)

**Objectif** : Vue d'ensemble de l'activité comptable

**Sections** :

1. **KPIs (Indicateurs Clés)**
   - Chiffre d'affaires du mois
   - Dépenses du mois
   - Trésorerie actuelle
   - Factures en attente

2. **Transactions Récentes**
   - Liste des 10 dernières transactions
   - Filtres : date, type (achat/vente)
   - Actions : voir détail, modifier, supprimer

3. **Tâches à Faire**
   - Liste des tâches prioritaires
   - Badges de priorité (urgent, moyen, faible)
   - Actions : marquer comme fait

4. **Chatbot Kauri**
   - Bouton d'ouverture fixe
   - Modal de chat
   - Streaming SSE pour les réponses

**API Endpoints** :
```
GET /api/v1/dashboard/kpis
GET /api/v1/transactions?limit=10
GET /api/v1/tasks?status=pending
```

---

### 4.3 Page Achats (`/purchases`)

**Objectif** : Gérer les factures d'achat

**Fonctionnalités** :
- Liste des factures fournisseurs
- Création nouvelle facture
- Import depuis fichier (PDF, Excel)
- Validation et comptabilisation
- Export vers comptabilité

**Composants** :
- Tableau avec pagination
- Formulaire de saisie
- Upload de fichiers
- Prévisualisation PDF

---

### 4.4 Page Ventes (`/sales`)

**Objectif** : Gérer les factures de vente

**Fonctionnalités** :
- Liste des factures clients
- Création devis → facture
- Envoi par email au client
- Suivi des paiements
- Relances automatiques

---

### 4.5 Page Banque (`/bank`)

**Objectif** : Rapprochement bancaire

**Fonctionnalités** :
- Import relevés bancaires (CSV, OFX)
- Rapprochement automatique
- Validation manuelle
- Gestion des écarts
- Visualisation soldes

---

### 4.6 Page Immobilisations (`/assets`)

**Objectif** : Suivi des immobilisations

**Fonctionnalités** :
- Liste des immobilisations
- Calcul amortissements OHADA
- Plan d'amortissement
- Cessions et mises au rebut

---

### 4.7 Page Rapports (`/reports`)

**Objectif** : Génération états financiers OHADA

**Rapports Disponibles** :

1. **Bilan Comptable** (SYSCOHADA)
   - Actif / Passif
   - Conforme modèle OHADA
   - Export PDF

2. **Compte de Résultat**
   - Charges / Produits
   - Résultat net
   - Export PDF

3. **Grand Livre**
   - Tous les comptes
   - Mouvements détaillés
   - Filtres par période

4. **Balance Générale**
   - Soldes de tous les comptes
   - Débit / Crédit
   - Export Excel

---

## 5. Composants Réutilisables

### 5.1 Chatbot

**Fichier** : `src/components/dashboard/Chatbot.tsx`

**Props** :
```typescript
interface ChatbotProps {
  isOpen: boolean;
  onClose: () => void;
}
```

**Fonctionnalités** :
- Envoi de questions
- Réponses en streaming (SSE)
- Historique des conversations
- Upload de documents pour analyse
- Citations des sources OHADA

**État** :
```typescript
const [messages, setMessages] = useState<Message[]>([]);
const [isLoading, setIsLoading] = useState(false);
const [inputValue, setInputValue] = useState('');
```

---

### 5.2 KPICard

**Fichier** : `src/components/dashboard/KPICard.tsx`

**Props** :
```typescript
interface KPICardProps {
  label: string;
  value: string | number;
  change?: string;
  trend?: 'up' | 'down' | 'warning';
  icon: React.ReactNode;
}
```

**Exemple** :
```tsx
<KPICard
  label="Chiffre d'affaires"
  value="45 250 000 FCFA"
  change="+12.5%"
  trend="up"
  icon={<TrendingUp />}
/>
```

---

### 5.3 TransactionList

**Fichier** : `src/components/dashboard/TransactionList.tsx`

**Props** :
```typescript
interface TransactionListProps {
  transactions: Transaction[];
  onViewDetails: (id: string) => void;
}
```

**Features** :
- Affichage des transactions
- Tri par colonne
- Filtres date/type
- Actions rapides

---

### 5.4 Table (Composant Générique)

**Fichier** : `src/components/shared/Table.tsx`

**Props** :
```typescript
interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  onRowClick?: (row: T) => void;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  };
}
```

**Utilisation** :
```tsx
<Table
  columns={purchaseColumns}
  data={purchases}
  pagination={paginationConfig}
  onRowClick={handleRowClick}
/>
```

---

## 6. Intégration Backend

### 6.1 Services Microservices Backend

```
┌──────────────────────┐
│   API Gateway        │
│   (Port 80/443)      │
│   • Routing          │
│   • Auth             │
│   • Rate Limiting    │
└──────────┬───────────┘
           │
    ┌──────┼──────┬────────┐
    │      │      │        │
    ▼      ▼      ▼        ▼
┌───────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
│ Auth  │ │Chatbot │ │Accounting│ │Documents │
│Service│ │Service │ │ Service  │ │ Service  │
│:8001  │ │:8002   │ │:8003     │ │:8004     │
└───────┘ └────────┘ └─────────┘ └──────────┘
```

### 6.2 Configuration API

**Fichier** : `src/services/api.ts`

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (ajouter token)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor (gérer erreurs)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expiré → refresh
      // Si refresh échoue → redirect /login
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 6.3 Services API

#### authService.ts

```typescript
import api from './api';

export const authService = {
  login: async (email: string, password: string) => {
    const response = await api.post('/api/v1/auth/login', {
      email,
      password,
    });
    return response.data;
  },

  register: async (userData: RegisterData) => {
    const response = await api.post('/api/v1/auth/register', userData);
    return response.data;
  },

  me: async () => {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/api/v1/auth/logout');
    return response.data;
  },
};
```

#### chatbotService.ts

```typescript
import api from './api';

export const chatbotService = {
  sendQuery: async (query: string) => {
    const response = await api.post('/api/v1/chat/query', { query });
    return response.data;
  },

  streamQuery: (query: string, onMessage: (data: any) => void) => {
    const eventSource = new EventSource(
      `${import.meta.env.VITE_CHATBOT_SERVICE_URL}/api/v1/chat/stream?query=${encodeURIComponent(query)}`,
      { withCredentials: true }
    );

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return eventSource;
  },
};
```

---

## 7. Authentification et Sécurité

### 7.1 Flux d'Authentification

```
User → Login Form → POST /api/v1/auth/login → Backend
                                                  ↓
                                            JWT Tokens
                                            (access + refresh)
                                                  ↓
                                          Store in localStorage
                                                  ↓
                                          Redirect to /dashboard
```

### 7.2 Protection des Routes

**Fichier** : `src/components/auth/ProtectedRoute.tsx`

```typescript
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
};
```

### 7.3 Gestion des Tokens

```typescript
// Stockage
localStorage.setItem('access_token', accessToken);
localStorage.setItem('refresh_token', refreshToken);

// Récupération
const token = localStorage.getItem('access_token');

// Refresh automatique (dans interceptor)
if (error.response?.status === 401) {
  const refreshToken = localStorage.getItem('refresh_token');
  const newTokens = await refreshAccessToken(refreshToken);
  // Retry original request
}
```

### 7.4 Sécurité

**Mesures** :
- ✅ HTTPS uniquement en production
- ✅ JWT avec expiration courte (15 min)
- ✅ Refresh token avec expiration longue (7 jours)
- ✅ CORS configuré strictement
- ✅ Sanitization des inputs (XSS prevention)
- ✅ Content Security Policy headers
- ✅ Rate limiting sur API

---

## 8. Tests et Qualité

### 8.1 Stack de Tests

```yaml
Unit Tests: Vitest
Component Tests: React Testing Library
E2E Tests: Playwright
Coverage: vitest coverage
Linting: ESLint
Formatting: Prettier
Type Checking: TypeScript strict mode
```

### 8.2 Structure des Tests

```
src/
├── components/
│   ├── Button.tsx
│   └── Button.test.tsx
├── services/
│   ├── authService.ts
│   └── authService.test.ts
└── pages/
    ├── DashboardPage.tsx
    └── DashboardPage.test.tsx
```

### 8.3 Exemples de Tests

#### Test Composant

```typescript
// Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from './Button';

describe('Button', () => {
  it('renders button with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    fireEvent.click(screen.getByText('Click'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

#### Test Service

```typescript
// authService.test.ts
import { authService } from './authService';
import api from './api';

vi.mock('./api');

describe('authService', () => {
  it('should login successfully', async () => {
    const mockResponse = { access_token: 'token123' };
    vi.mocked(api.post).mockResolvedValue({ data: mockResponse });

    const result = await authService.login('test@kauri.com', 'password');

    expect(result).toEqual(mockResponse);
    expect(api.post).toHaveBeenCalledWith('/api/v1/auth/login', {
      email: 'test@kauri.com',
      password: 'password',
    });
  });
});
```

### 8.4 Commandes

```bash
# Tests unitaires
npm run test

# Tests avec coverage
npm run test:coverage

# Tests E2E
npm run test:e2e

# Linting
npm run lint

# Format code
npm run format
```

---

## 9. Déploiement

### 9.1 Build de Production

```bash
# Build
npm run build

# Résultat dans dist/
dist/
├── assets/
│   ├── index-abc123.js
│   └── index-def456.css
└── index.html
```

### 9.2 Docker

**Fichier** : `Dockerfile`

```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 9.3 Configuration Nginx

**Fichier** : `nginx.conf`

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/css application/javascript application/json;

    # SPA routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://api-gateway:80;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 9.4 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy Frontend

on:
  push:
    branches: [main]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm run test:coverage

      - name: Build
        run: npm run build

      - name: Build Docker image
        run: docker build -t kauri-frontend:${{ github.sha }} .

      - name: Push to registry
        run: docker push kauri-frontend:${{ github.sha }}

      - name: Deploy to Kubernetes
        run: kubectl set image deployment/kauri-frontend app=kauri-frontend:${{ github.sha }}
```

---

## 10. Roadmap

### Phase 1 (Actuelle) - MVP ✅

- [x] Pages Login / Register
- [x] Dashboard avec KPIs
- [x] Chatbot intégré
- [x] Transactions récentes
- [x] Authentification JWT
- [x] Layout responsive

### Phase 2 - Fonctionnalités Comptables (4 semaines)

- [ ] Page Achats complète
- [ ] Page Ventes complète
- [ ] Page Banque (rapprochement)
- [ ] Page Immobilisations
- [ ] Import fichiers (PDF, Excel)
- [ ] Export PDF des rapports

### Phase 3 - Rapports OHADA (2 semaines)

- [ ] Bilan comptable SYSCOHADA
- [ ] Compte de résultat
- [ ] Grand Livre
- [ ] Balance générale
- [ ] TVA et déclarations

### Phase 4 - Optimisations (2 semaines)

- [ ] React Query pour cache
- [ ] Optimistic updates
- [ ] Offline mode (PWA)
- [ ] Notifications push
- [ ] Multi-langue (FR/EN)

### Phase 5 - Tests et Qualité (2 semaines)

- [ ] Tests unitaires (80%+ coverage)
- [ ] Tests E2E (Playwright)
- [ ] Performance audits
- [ ] Accessibility (WCAG AA)
- [ ] Security audit

---

## 📞 Support et Contact

**Équipe Frontend** : frontend@kauri.com
**Documentation** : https://docs.kauri.com/frontend
**Repository** : https://github.com/kauri/frontend

---

**Document créé par** : Architecture Team
**Date** : 2025-11-04
**Version** : 1.0
**Statut** : Specification complète
