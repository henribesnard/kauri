# Guide de Contribution - KAURI

> **Bienvenue dans le projet KAURI !** 🎉
>
> Ce guide vous aidera à contribuer efficacement au projet.

---

## 📋 Table des Matières

1. [Code de Conduite](#code-de-conduite)
2. [Comment Contribuer](#comment-contribuer)
3. [Workflow Git](#workflow-git)
4. [Standards de Code](#standards-de-code)
5. [Conventions de Commit](#conventions-de-commit)
6. [Processus de Code Review](#processus-de-code-review)
7. [Tests](#tests)
8. [Documentation](#documentation)

---

## Code de Conduite

### Nos Valeurs

- **Respect** : Traitez tous les contributeurs avec respect et courtoisie
- **Collaboration** : Travaillez ensemble pour atteindre les objectifs
- **Qualité** : Maintenez des standards élevés de qualité du code
- **Transparence** : Communiquez ouvertement et honnêtement

### Comportements Acceptables

✅ Utiliser un langage accueillant et inclusif
✅ Respecter les points de vue et expériences différents
✅ Accepter gracieusement les critiques constructives
✅ Se concentrer sur ce qui est meilleur pour la communauté

### Comportements Inacceptables

❌ Langage ou images sexualisés, inappropriés
❌ Commentaires insultants ou désobligeants
❌ Harcèlement public ou privé
❌ Publication d'informations privées sans permission

---

## Comment Contribuer

### Types de Contributions

Nous acceptons différents types de contributions :

1. **Code** : Nouvelles fonctionnalités, corrections de bugs
2. **Documentation** : Amélioration de la documentation
3. **Tests** : Ajout de tests unitaires, d'intégration, E2E
4. **Design** : Wireframes, maquettes, design system
5. **Revues** : Code reviews, revues de documentation
6. **Signalement** : Rapport de bugs, suggestions d'amélioration

### Avant de Contribuer

1. **Consultez les issues** existantes pour éviter les doublons
2. **Créez une issue** pour discuter des changements majeurs
3. **Lisez la documentation** du projet
4. **Configurez votre environnement** de développement

---

## Workflow Git

### Structure des Branches

```
main                          # Production, toujours stable
  ├── develop                 # Développement, intégration continue
  │   ├── feature/*          # Nouvelles fonctionnalités
  │   ├── fix/*              # Corrections de bugs
  │   ├── docs/*             # Documentation
  │   ├── refactor/*         # Refactoring
  │   └── test/*             # Tests
  └── hotfix/*               # Corrections urgentes en production
```

### Nommage des Branches

**Format** : `type/description-courte`

**Types** :
- `feature/` : Nouvelle fonctionnalité
- `fix/` : Correction de bug
- `docs/` : Documentation
- `refactor/` : Refactoring
- `test/` : Tests
- `hotfix/` : Correction urgente
- `chore/` : Maintenance, config

**Exemples** :
```bash
feature/chatbot-streaming
fix/login-validation-error
docs/api-documentation
refactor/dashboard-components
test/add-unit-tests-auth
```

### Processus de Contribution

#### 1. Fork et Clone

```bash
# Fork le repository sur GitHub
# Cloner votre fork
git clone https://github.com/VOTRE-USERNAME/kauri.git
cd kauri

# Ajouter le remote upstream
git remote add upstream https://github.com/henribesnard/kauri.git
```

#### 2. Créer une Branche

```bash
# Mettre à jour develop
git checkout develop
git pull upstream develop

# Créer votre branche
git checkout -b feature/ma-nouvelle-fonctionnalite
```

#### 3. Développer

```bash
# Faire vos modifications
# ...

# Ajouter les fichiers modifiés
git add .

# Committer (voir conventions ci-dessous)
git commit -m "feat(chatbot): add streaming support for responses"
```

#### 4. Tester

```bash
# Frontend
cd frontend/kauri-app
npm test
npm run lint

# Backend
cd backend
pytest tests/
```

#### 5. Push et Pull Request

```bash
# Push vers votre fork
git push origin feature/ma-nouvelle-fonctionnalite

# Créer une Pull Request sur GitHub
# Remplir le template de PR
```

#### 6. Code Review

- Répondre aux commentaires de review
- Apporter les modifications demandées
- Pusher les updates (même branche)

#### 7. Merge

- Une fois approuvée, la PR sera mergée par un mainteneur
- Votre branche sera supprimée automatiquement

---

## Standards de Code

### Frontend (React/TypeScript)

#### Conventions de Nommage

```typescript
// Composants : PascalCase
export const DashboardPage = () => { ... }

// Fonctions/variables : camelCase
const handleSubmit = () => { ... }
const isLoading = true;

// Constantes : UPPER_SNAKE_CASE
const API_BASE_URL = 'http://localhost:8000';

// Types/Interfaces : PascalCase
interface UserProfile {
  id: string;
  email: string;
}

// Fichiers composants : PascalCase.tsx
// DashboardPage.tsx, Button.tsx

// Fichiers utilitaires : camelCase.ts
// formatDate.ts, validation.ts
```

#### Structure des Composants

```typescript
import React, { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

// 1. Types/Interfaces
interface DashboardPageProps {
  userId: string;
}

// 2. Composant
export const DashboardPage: React.FC<DashboardPageProps> = ({ userId }) => {
  // 3. Hooks
  const { user } = useAuth();
  const [data, setData] = useState<Data[]>([]);

  // 4. Effects
  useEffect(() => {
    fetchData();
  }, [userId]);

  // 5. Handlers
  const handleRefresh = () => {
    fetchData();
  };

  // 6. Helpers
  const fetchData = async () => {
    // ...
  };

  // 7. Render
  return (
    <div className="dashboard">
      {/* JSX */}
    </div>
  );
};
```

#### Règles ESLint

```json
{
  "extends": [
    "eslint:recommended",
    "plugin:react/recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "no-console": "warn",
    "prefer-const": "error",
    "react/prop-types": "off",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

#### Style Guide

- **Indentation** : 2 espaces
- **Quotes** : Single quotes `'` pour strings
- **Semicolons** : Toujours utiliser `;`
- **Max line length** : 100 caractères
- **Trailing commas** : Toujours (sauf JSON)

### Backend (Python/FastAPI)

#### Conventions de Nommage

```python
# Classes : PascalCase
class UserService:
    pass

# Fonctions/variables : snake_case
def get_user_by_id(user_id: str):
    pass

# Constantes : UPPER_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3

# Fichiers : snake_case.py
# user_service.py, auth_utils.py
```

#### Structure des Modules

```python
"""
Module docstring explaining the purpose.
"""
from typing import List, Optional
from pydantic import BaseModel

# 1. Constants
DEFAULT_PAGE_SIZE = 20

# 2. Models/Types
class UserResponse(BaseModel):
    id: str
    email: str

# 3. Functions
def get_users(page: int = 1) -> List[UserResponse]:
    """
    Get paginated list of users.

    Args:
        page: Page number (1-indexed)

    Returns:
        List of users
    """
    # Implementation
    pass
```

#### Règles Flake8/Black

```ini
[flake8]
max-line-length = 100
exclude = .git,__pycache__,venv

[tool:black]
line-length = 100
target-version = ['py311']
```

---

## Conventions de Commit

### Format Conventional Commits

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

### Types

| Type | Description | Exemple |
|------|-------------|---------|
| `feat` | Nouvelle fonctionnalité | `feat(chatbot): add streaming support` |
| `fix` | Correction de bug | `fix(auth): resolve login validation error` |
| `docs` | Documentation | `docs(api): update authentication guide` |
| `style` | Formatage, style | `style(frontend): fix linting errors` |
| `refactor` | Refactoring | `refactor(dashboard): simplify KPI logic` |
| `test` | Tests | `test(auth): add unit tests for login` |
| `chore` | Maintenance | `chore(deps): update dependencies` |
| `perf` | Performance | `perf(search): optimize vector search` |
| `ci` | CI/CD | `ci(github): add automated tests` |
| `build` | Build system | `build(docker): optimize image size` |

### Scopes

**Frontend** :
- `auth` : Authentification
- `dashboard` : Tableau de bord
- `chatbot` : Chatbot
- `ui` : Composants UI
- `api` : Services API

**Backend** :
- `api` : API endpoints
- `db` : Base de données
- `auth` : Authentification
- `rag` : RAG engine
- `knowledge` : Knowledge base

**Global** :
- `docs` : Documentation
- `config` : Configuration
- `deps` : Dépendances

### Exemples de Commits

```bash
# Feature
feat(chatbot): add SSE streaming for real-time responses

Implement Server-Sent Events (SSE) for chatbot responses to provide
real-time streaming experience to users.

- Add EventSource in frontend
- Update backend endpoint to support streaming
- Add retry logic for connection failures

Closes #123

# Fix
fix(auth): prevent duplicate user registration

Check if email already exists before creating new user account.

Fixes #456

# Documentation
docs(frontend): add component documentation

Add comprehensive documentation for all reusable components
with props, examples, and usage guidelines.

# Refactor
refactor(dashboard): extract KPI logic to custom hook

Move KPI calculation logic to useKPIData hook for better
reusability and testability.

# Test
test(auth): add e2e tests for login flow

Add Playwright E2E tests covering:
- Successful login
- Invalid credentials
- Password reset flow

# Breaking change
feat(api)!: change authentication endpoint structure

BREAKING CHANGE: Auth endpoints moved from /auth/* to /api/v1/auth/*

Migrate your API calls to use the new endpoint structure.
```

### Règles des Messages de Commit

✅ **À faire** :
- Utiliser l'impératif ("add" pas "added")
- Première ligne < 72 caractères
- Corps du message ligne < 100 caractères
- Référencer les issues (#123)
- Expliquer le "pourquoi" pas le "quoi"

❌ **À éviter** :
- Messages vagues ("fix bug", "update")
- Commits trop gros (diviser en commits atomiques)
- Commits WIP (work in progress) sur main/develop
- Mélanger plusieurs types de changements

---

## Processus de Code Review

### Pour l'Auteur de la PR

#### Avant de Soumettre

- [ ] Le code compile sans erreur
- [ ] Tous les tests passent
- [ ] Pas de warnings linter
- [ ] Documentation à jour
- [ ] Commits bien formatés
- [ ] Branche à jour avec develop

#### Template de Pull Request

```markdown
## Description

Brief description of the changes.

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Related Issue

Closes #(issue number)

## Changes Made

- Change 1
- Change 2
- Change 3

## Testing

Describe the tests that you ran to verify your changes.

- [ ] Unit tests
- [ ] Integration tests
- [ ] E2E tests
- [ ] Manual testing

## Screenshots (if applicable)

Add screenshots to help explain your changes.

## Checklist

- [ ] My code follows the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
```

### Pour les Reviewers

#### Checklist de Review

**Code Quality** :
- [ ] Le code est lisible et maintenable
- [ ] Pas de code dupliqué
- [ ] Nommage des variables/fonctions clair
- [ ] Complexité raisonnable
- [ ] Pas de code mort (commenté)

**Fonctionnalité** :
- [ ] Le code fait ce qu'il est censé faire
- [ ] Gestion des edge cases
- [ ] Gestion des erreurs appropriée
- [ ] Performance acceptable

**Tests** :
- [ ] Tests appropriés ajoutés
- [ ] Tests passent
- [ ] Coverage suffisant (> 80%)

**Sécurité** :
- [ ] Pas de secrets hardcodés
- [ ] Validation des inputs
- [ ] Sanitization appropriée
- [ ] Pas de vulnérabilités évidentes

**Documentation** :
- [ ] Code commenté si nécessaire
- [ ] Documentation mise à jour
- [ ] README à jour si nécessaire

#### Types de Commentaires

**Prefix** : Utilisez des préfixes pour clarifier vos commentaires

- `nit:` : Détail mineur, non bloquant
- `question:` : Question pour clarification
- `suggestion:` : Suggestion d'amélioration
- `issue:` : Problème à corriger (bloquant)
- `praise:` : Bon travail !

**Exemples** :
```
nit: Consider renaming 'data' to 'userData' for clarity

question: Why are we using Promise.all here instead of sequential calls?

suggestion: This could be simplified using array.reduce()

issue: This creates a security vulnerability - user input is not sanitized

praise: Great use of the useMemo hook here!
```

#### Répondre aux Commentaires

- Répondre à **tous** les commentaires
- Marquer comme "résolu" une fois traité
- Si vous n'êtes pas d'accord, expliquez pourquoi
- Demander des clarifications si nécessaire

---

## Tests

### Frontend

#### Structure des Tests

```
src/
├── components/
│   ├── Button.tsx
│   └── Button.test.tsx        # Test du composant
├── services/
│   ├── authService.ts
│   └── authService.test.ts    # Test du service
└── __tests__/
    └── e2e/
        └── login.spec.ts      # Tests E2E
```

#### Tests Unitaires (Vitest)

```typescript
// Button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button } from './Button';

describe('Button', () => {
  it('should render with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('should call onClick when clicked', () => {
    const handleClick = vi.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    fireEvent.click(screen.getByText('Click'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('should be disabled when disabled prop is true', () => {
    render(<Button disabled>Click</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

#### Tests E2E (Playwright)

```typescript
// login.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Login Flow', () => {
  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'test@kauri.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.fill('input[name="email"]', 'test@kauri.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    await expect(page.locator('.error')).toContainText('Invalid credentials');
  });
});
```

### Backend

#### Tests Unitaires (pytest)

```python
# test_auth_service.py
import pytest
from src.services.auth_service import AuthService

def test_login_success():
    """Test successful login."""
    service = AuthService()
    result = service.login("test@kauri.com", "password123")

    assert result.success is True
    assert result.token is not None

def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    service = AuthService()

    with pytest.raises(InvalidCredentialsError):
        service.login("test@kauri.com", "wrongpassword")

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation."""
    service = AuthService()
    result = await service.async_login("test@kauri.com", "password123")

    assert result.success is True
```

### Commandes

```bash
# Frontend
npm test                    # Run all tests
npm run test:watch         # Watch mode
npm run test:coverage      # With coverage
npm run test:e2e          # E2E tests

# Backend
pytest                     # Run all tests
pytest tests/unit/        # Only unit tests
pytest --cov=src          # With coverage
pytest -v                 # Verbose
```

### Coverage Requirements

- **Minimum** : 80% de coverage
- **Objectif** : 90% de coverage
- **Critique** : 100% pour auth, payment, security

---

## Documentation

### Types de Documentation

1. **Code Comments** : Expliquer le "pourquoi"
2. **Docstrings** : Documenter fonctions/classes
3. **README** : Guide de démarrage
4. **API Docs** : Documentation OpenAPI/Swagger
5. **Architecture Docs** : Décisions, diagrammes

### Docstrings

#### TypeScript (JSDoc)

```typescript
/**
 * Authenticate user and return JWT token.
 *
 * @param email - User email address
 * @param password - User password
 * @returns Authentication result with token
 * @throws {InvalidCredentialsError} If credentials are invalid
 *
 * @example
 * ```typescript
 * const result = await authService.login('user@example.com', 'pass123');
 * console.log(result.token);
 * ```
 */
async function login(email: string, password: string): Promise<AuthResult> {
  // Implementation
}
```

#### Python

```python
def login(email: str, password: str) -> AuthResult:
    """
    Authenticate user and return JWT token.

    Args:
        email: User email address
        password: User password

    Returns:
        AuthResult: Authentication result with token

    Raises:
        InvalidCredentialsError: If credentials are invalid

    Example:
        >>> result = login('user@example.com', 'pass123')
        >>> print(result.token)
        'eyJhbGc...'
    """
    # Implementation
    pass
```

### README Structure

Chaque module/package devrait avoir un README avec :

```markdown
# Module Name

Brief description

## Installation

## Usage

## API Reference

## Examples

## Testing

## Contributing

## License
```

---

## Questions et Support

### Obtenir de l'Aide

- **Issues GitHub** : Pour bugs et feature requests
- **Discussions** : Pour questions générales
- **Email** : tech@kauri.com
- **Slack** : #kauri-dev (pour l'équipe interne)

### Ressources

- [Documentation Officielle](https://docs.kauri.com)
- [Guide d'Architecture](docs/architecture/)
- [API Reference](https://api.kauri.com/docs)
- [Changelog](CHANGELOG.md)

---

## Remerciements

Merci de contribuer à KAURI ! 🎉

Chaque contribution, grande ou petite, nous aide à améliorer le projet.

---

**Document créé par** : Architecture Team
**Date** : 2025-11-04
**Version** : 1.0
