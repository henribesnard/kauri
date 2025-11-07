# 🎯 PLAN D'IMPLÉMENTATION - SYSTÈME DE QUOTAS KAURI

**Version** : 1.0
**Date** : Janvier 2025
**Objectif** : Implémenter un système complet de gestion des quotas et abonnements

---

## 📋 TABLE DES MATIÈRES

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture technique](#architecture-technique)
3. [Modèles de données](#modèles-de-données)
4. [Backend - User Service](#backend---user-service)
5. [Backend - Chatbot Service](#backend---chatbot-service)
6. [Intégration paiements (CinetPay)](#intégration-paiements-cinetpay)
7. [Frontend](#frontend)
8. [Tests](#tests)
9. [Déploiement](#déploiement)
10. [Roadmap et priorisation](#roadmap-et-priorisation)

---

## 🎯 VUE D'ENSEMBLE

### Objectifs du Système

1. **Limiter l'usage gratuit** : 5 questions/jour pour utilisateurs Free
2. **Gérer les abonnements** : PRO, MAX, ENTERPRISE avec quotas différenciés
3. **Intégrer les paiements** : CinetPay pour Mobile Money + cartes bancaires
4. **Tracking de l'usage** : Métriques en temps réel pour analytics et facturation
5. **Upsell intelligent** : Notifier utilisateurs quand ils approchent des limites

### Périmètre Phase 1 (MVP - 6 semaines)

**Inclus** :
- ✅ Modèles de données (subscriptions, usage, quotas)
- ✅ API endpoints gestion abonnements
- ✅ Middleware rate limiting (quotas questions)
- ✅ Intégration CinetPay (paiement one-time)
- ✅ Dashboard utilisateur (usage en cours)
- ✅ Notifications limites atteintes
- ✅ Admin panel basique (monitoring)

**Exclus (Phase 2)** :
- ⬜ Upload documents personnels (feature MAX)
- ⬜ Génération PDF (feature MAX)
- ⬜ API publique avec rate limiting
- ⬜ Multi-utilisateurs (feature MAX/ENTERPRISE)
- ⬜ Webhooks avancés

---

## 🏗️ ARCHITECTURE TECHNIQUE

### Flux Global

```
┌─────────────┐         ┌──────────────┐         ┌───────────────┐
│   Frontend  │────────>│ User Service │────────>│  PostgreSQL   │
│  (React)    │<────────│   (FastAPI)  │<────────│  kauri_users  │
└─────────────┘         └──────────────┘         └───────────────┘
       │                        │
       │                        │
       │                        v
       │                ┌──────────────┐
       │                │   CinetPay   │
       │                │   Payment    │
       │                │   Gateway    │
       │                └──────────────┘
       │
       v
┌─────────────┐         ┌──────────────┐         ┌───────────────┐
│   Frontend  │────────>│Chatbot Service│────────>│  PostgreSQL   │
│  (React)    │<────────│   (FastAPI)  │<────────│kauri_chatbot  │
└─────────────┘         └──────────────┘         └───────────────┘
                                │
                                v
                        ┌──────────────┐
                        │    Redis     │
                        │ Rate Limiting│
                        └──────────────┘
```

### Stack Technologique

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Backend** | FastAPI (Python 3.11+) | Déjà utilisé, async, performant |
| **Database** | PostgreSQL 15+ | Relationnel, ACID, support JSON |
| **Cache** | Redis 7+ | Rate limiting rapide, compteurs atomiques |
| **Paiements** | CinetPay API v2 | Mobile Money + CB, zone OHADA |
| **Auth** | JWT (HS256) | Déjà implémenté |
| **Frontend** | React 18 + TypeScript | Déjà utilisé |
| **State Mgmt** | React Context API | Simple, pas besoin Redux pour MVP |

---

## 📊 MODÈLES DE DONNÉES

### 1. Table `subscription_plans` (Référentiel)

**Localisation** : `kauri_users` database

```sql
CREATE TYPE plan_tier AS ENUM ('free', 'pro', 'max', 'enterprise');
CREATE TYPE billing_period AS ENUM ('monthly', 'yearly');

CREATE TABLE subscription_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier plan_tier NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL,
    description TEXT,
    price_monthly_fcfa INT NOT NULL,  -- Prix en FCFA
    price_yearly_fcfa INT,  -- Prix annuel (si applicable)

    -- Quotas
    questions_per_day INT,  -- NULL = illimité
    questions_per_month INT,  -- NULL = illimité
    max_conversations INT,  -- NULL = illimité
    max_sources_per_query INT DEFAULT 5,
    max_context_tokens INT DEFAULT 4000,
    max_storage_mb INT DEFAULT 0,  -- Pour upload documents

    -- Features flags
    can_export_conversations BOOLEAN DEFAULT FALSE,
    can_upload_documents BOOLEAN DEFAULT FALSE,
    can_generate_pdf BOOLEAN DEFAULT FALSE,
    has_api_access BOOLEAN DEFAULT FALSE,
    api_calls_per_day INT DEFAULT 0,
    has_priority_queue BOOLEAN DEFAULT FALSE,
    max_team_members INT DEFAULT 1,

    -- Support
    support_level VARCHAR(50) DEFAULT 'community',  -- community, email, priority, dedicated
    support_response_hours INT,  -- SLA en heures

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexation
CREATE INDEX idx_subscription_plans_tier ON subscription_plans(tier);
CREATE INDEX idx_subscription_plans_active ON subscription_plans(is_active);
```

**Données initiales** :

```sql
INSERT INTO subscription_plans (tier, name, description, price_monthly_fcfa, price_yearly_fcfa,
    questions_per_day, questions_per_month, max_conversations, max_sources_per_query,
    max_context_tokens, can_export_conversations, has_priority_queue, support_level, display_order)
VALUES
    ('free', 'Gratuit', 'Découvrez Kauri avec 5 questions par jour', 0, 0,
     5, 150, 3, 5, 4000, FALSE, FALSE, 'community', 0),

    ('pro', 'Professionnel', 'Pour comptables et experts-comptables indépendants', 9900, 106920,
     NULL, 500, NULL, 10, 8000, TRUE, TRUE, 'email', 1),

    ('max', 'Business', 'Pour cabinets moyens avec besoins avancés', 29900, 322920,
     NULL, 2000, NULL, 15, 12000, TRUE, TRUE, 'priority', 2),

    ('enterprise', 'Enterprise', 'Solutions sur-mesure pour grandes structures', 99000, NULL,
     NULL, NULL, NULL, NULL, 16000, TRUE, TRUE, 'dedicated', 3);
```

---

### 2. Table `user_subscriptions` (Abonnements actifs)

**Localisation** : `kauri_users` database

```sql
CREATE TYPE subscription_status AS ENUM ('active', 'past_due', 'cancelled', 'expired');

CREATE TABLE user_subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(plan_id),

    -- Status et période
    status subscription_status DEFAULT 'active',
    billing_period billing_period DEFAULT 'monthly',
    current_period_start TIMESTAMP NOT NULL,
    current_period_end TIMESTAMP NOT NULL,

    -- Paiement
    last_payment_date TIMESTAMP,
    next_payment_date TIMESTAMP,
    payment_method VARCHAR(50),  -- 'orange_money', 'mtn_momo', 'moov_money', 'wave', 'card'

    -- Intégrations externes
    cinetpay_transaction_id VARCHAR(255),
    cinetpay_payment_token VARCHAR(255),

    -- Metadata
    auto_renew BOOLEAN DEFAULT FALSE,  -- Mobile Money = FALSE, Card = TRUE possible
    cancellation_date TIMESTAMP,
    cancellation_reason TEXT,
    metadata JSONB,  -- Champs custom (réductions, promo codes, etc.)

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Contrainte : un seul abonnement actif par utilisateur
    CONSTRAINT unique_active_subscription UNIQUE (user_id, status)
        WHERE status = 'active'
);

-- Indexation
CREATE INDEX idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_status ON user_subscriptions(status);
CREATE INDEX idx_user_subscriptions_end_date ON user_subscriptions(current_period_end);
```

---

### 3. Table `usage_tracking` (Consommation en temps réel)

**Localisation** : `kauri_chatbot` database (proche des conversations)

```sql
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    date DATE NOT NULL,  -- YYYY-MM-DD pour agrégation

    -- Compteurs quotidiens
    questions_today INT DEFAULT 0,
    api_calls_today INT DEFAULT 0,

    -- Compteurs mensuels (même mois que date)
    questions_this_month INT DEFAULT 0,
    tokens_consumed_this_month BIGINT DEFAULT 0,
    api_calls_this_month INT DEFAULT 0,

    -- Metadata
    last_question_at TIMESTAMP,
    last_api_call_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Contrainte unicité par user + date
    CONSTRAINT unique_user_date UNIQUE (user_id, date)
);

-- Indexation (crucial pour perfs)
CREATE INDEX idx_usage_tracking_user_date ON usage_tracking(user_id, date DESC);
CREATE INDEX idx_usage_tracking_date ON usage_tracking(date);

-- Partition par mois (optionnel, pour scalabilité)
-- CREATE TABLE usage_tracking_2025_01 PARTITION OF usage_tracking
--     FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

---

### 4. Table `payment_transactions` (Historique paiements)

**Localisation** : `kauri_users` database

```sql
CREATE TYPE transaction_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
CREATE TYPE transaction_type AS ENUM ('subscription', 'renewal', 'upgrade', 'refund');

CREATE TABLE payment_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    subscription_id UUID REFERENCES user_subscriptions(subscription_id),

    -- Détails transaction
    type transaction_type NOT NULL,
    status transaction_status DEFAULT 'pending',
    amount_fcfa INT NOT NULL,
    currency VARCHAR(3) DEFAULT 'XOF',  -- XOF = Franc CFA

    -- Intégration CinetPay
    cinetpay_transaction_id VARCHAR(255) UNIQUE,
    cinetpay_payment_url TEXT,
    cinetpay_payment_token VARCHAR(255),
    payment_method VARCHAR(50),  -- 'ORANGE_MONEY_CI', 'MTN_MONEY_BF', etc.

    -- Statut paiement
    payment_date TIMESTAMP,
    failure_reason TEXT,

    -- Metadata
    metadata JSONB,  -- Réponse complète CinetPay, logs, etc.

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexation
CREATE INDEX idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX idx_payment_transactions_status ON payment_transactions(status);
CREATE INDEX idx_payment_transactions_cinetpay_id ON payment_transactions(cinetpay_transaction_id);
CREATE INDEX idx_payment_transactions_created ON payment_transactions(created_at DESC);
```

---

### 5. Modification Table `users` (Ajout champ subscription)

**Localisation** : `kauri_users` database

```sql
-- Ajouter colonne pour jointure rapide (dénormalisation)
ALTER TABLE users ADD COLUMN current_subscription_id UUID REFERENCES user_subscriptions(subscription_id);
ALTER TABLE users ADD COLUMN current_plan_tier plan_tier DEFAULT 'free';

-- Index pour requêtes fréquentes
CREATE INDEX idx_users_subscription_id ON users(current_subscription_id);
CREATE INDEX idx_users_plan_tier ON users(current_plan_tier);
```

---

## 🔧 BACKEND - USER SERVICE

### Structure de Fichiers

```
backend/kauri_user_service/
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py  (existant)
│   │   │   ├── oauth.py  (existant)
│   │   │   ├── subscriptions.py  (NOUVEAU)
│   │   │   └── payments.py  (NOUVEAU)
│   │   └── main.py
│   ├── models/
│   │   ├── user.py  (existant)
│   │   ├── subscription.py  (NOUVEAU)
│   │   ├── payment.py  (NOUVEAU)
│   │   └── usage.py  (NOUVEAU)
│   ├── services/
│   │   ├── auth_service.py  (existant)
│   │   ├── subscription_service.py  (NOUVEAU)
│   │   └── payment_service.py  (NOUVEAU)
│   ├── integrations/
│   │   └── cinetpay.py  (NOUVEAU)
│   └── config.py
├── alembic/  (migrations DB)
└── requirements.txt
```

---

### 1. Modèle Pydantic - `src/models/subscription.py`

```python
from datetime import datetime, date
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID

class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"
    ENTERPRISE = "enterprise"

class BillingPeriod(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class SubscriptionPlanSchema(BaseModel):
    plan_id: UUID
    tier: PlanTier
    name: str
    description: Optional[str]
    price_monthly_fcfa: int
    price_yearly_fcfa: Optional[int]

    # Quotas
    questions_per_day: Optional[int]
    questions_per_month: Optional[int]
    max_conversations: Optional[int]
    max_sources_per_query: int = 5
    max_context_tokens: int = 4000
    max_storage_mb: int = 0

    # Features
    can_export_conversations: bool = False
    can_upload_documents: bool = False
    can_generate_pdf: bool = False
    has_api_access: bool = False
    api_calls_per_day: int = 0
    has_priority_queue: bool = False
    max_team_members: int = 1

    support_level: str
    support_response_hours: Optional[int]

    class Config:
        from_attributes = True

class UserSubscriptionSchema(BaseModel):
    subscription_id: UUID
    user_id: UUID
    plan: SubscriptionPlanSchema
    status: SubscriptionStatus
    billing_period: BillingPeriod
    current_period_start: datetime
    current_period_end: datetime
    last_payment_date: Optional[datetime]
    next_payment_date: Optional[datetime]
    payment_method: Optional[str]
    auto_renew: bool

    class Config:
        from_attributes = True

class CreateSubscriptionRequest(BaseModel):
    plan_tier: PlanTier
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    payment_method: str = Field(..., description="orange_money, mtn_momo, moov_money, wave, card")

class UpgradeSubscriptionRequest(BaseModel):
    new_plan_tier: PlanTier
    billing_period: Optional[BillingPeriod] = BillingPeriod.MONTHLY

class CancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = None
    immediate: bool = False  # Si False, expire à la fin de période
```

---

### 2. Service Abonnements - `src/services/subscription_service.py`

```python
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.subscription import (
    PlanTier, BillingPeriod, SubscriptionStatus,
    SubscriptionPlanSchema, UserSubscriptionSchema
)
from ..database.models import (
    SubscriptionPlan, UserSubscription, User
)

class SubscriptionService:

    @staticmethod
    def get_all_plans(db: Session, active_only: bool = True) -> list[SubscriptionPlanSchema]:
        """Récupère tous les plans d'abonnement"""
        query = db.query(SubscriptionPlan)
        if active_only:
            query = query.filter(SubscriptionPlan.is_active == True)

        plans = query.order_by(SubscriptionPlan.display_order).all()
        return [SubscriptionPlanSchema.from_orm(plan) for plan in plans]

    @staticmethod
    def get_plan_by_tier(db: Session, tier: PlanTier) -> Optional[SubscriptionPlan]:
        """Récupère un plan par son tier"""
        return db.query(SubscriptionPlan).filter(
            SubscriptionPlan.tier == tier
        ).first()

    @staticmethod
    def get_user_subscription(db: Session, user_id: UUID) -> Optional[UserSubscriptionSchema]:
        """Récupère l'abonnement actif d'un utilisateur"""
        subscription = db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        ).first()

        if not subscription:
            return None

        return UserSubscriptionSchema.from_orm(subscription)

    @staticmethod
    def create_free_subscription(db: Session, user_id: UUID) -> UserSubscription:
        """Crée un abonnement gratuit pour un nouvel utilisateur"""
        free_plan = SubscriptionService.get_plan_by_tier(db, PlanTier.FREE)

        if not free_plan:
            raise ValueError("Free plan not found in database")

        now = datetime.utcnow()

        subscription = UserSubscription(
            user_id=user_id,
            plan_id=free_plan.plan_id,
            status=SubscriptionStatus.ACTIVE,
            billing_period=BillingPeriod.MONTHLY,
            current_period_start=now,
            current_period_end=now + timedelta(days=36500),  # 100 ans (illimité)
            auto_renew=False
        )

        db.add(subscription)

        # Mettre à jour l'utilisateur
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.current_subscription_id = subscription.subscription_id
            user.current_plan_tier = PlanTier.FREE

        db.commit()
        db.refresh(subscription)

        return subscription

    @staticmethod
    def create_paid_subscription(
        db: Session,
        user_id: UUID,
        plan_tier: PlanTier,
        billing_period: BillingPeriod,
        payment_method: str,
        cinetpay_transaction_id: str
    ) -> UserSubscription:
        """Crée un abonnement payant après paiement validé"""

        # Annuler l'abonnement actuel
        current_sub = db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        ).first()

        if current_sub:
            current_sub.status = SubscriptionStatus.CANCELLED
            current_sub.cancellation_date = datetime.utcnow()

        # Récupérer le nouveau plan
        plan = SubscriptionService.get_plan_by_tier(db, plan_tier)
        if not plan:
            raise ValueError(f"Plan {plan_tier} not found")

        # Calculer les dates
        now = datetime.utcnow()
        if billing_period == BillingPeriod.MONTHLY:
            period_end = now + timedelta(days=30)
            next_payment = period_end
        else:  # YEARLY
            period_end = now + timedelta(days=365)
            next_payment = period_end

        # Créer le nouvel abonnement
        new_subscription = UserSubscription(
            user_id=user_id,
            plan_id=plan.plan_id,
            status=SubscriptionStatus.ACTIVE,
            billing_period=billing_period,
            current_period_start=now,
            current_period_end=period_end,
            last_payment_date=now,
            next_payment_date=next_payment,
            payment_method=payment_method,
            cinetpay_transaction_id=cinetpay_transaction_id,
            auto_renew=False  # Mobile Money = manuel par défaut
        )

        db.add(new_subscription)

        # Mettre à jour l'utilisateur
        user = db.query(User).filter(User.user_id == user_id).first()
        if user:
            user.current_subscription_id = new_subscription.subscription_id
            user.current_plan_tier = plan_tier

        db.commit()
        db.refresh(new_subscription)

        return new_subscription

    @staticmethod
    def upgrade_subscription(
        db: Session,
        user_id: UUID,
        new_plan_tier: PlanTier,
        billing_period: BillingPeriod
    ) -> dict:
        """
        Calcule le montant pour un upgrade (prorata)
        Retourne: {"amount_to_pay": int, "plan": SubscriptionPlanSchema}
        """

        current_sub = SubscriptionService.get_user_subscription(db, user_id)
        if not current_sub:
            raise ValueError("No active subscription")

        new_plan = SubscriptionService.get_plan_by_tier(db, new_plan_tier)
        if not new_plan:
            raise ValueError(f"Plan {new_plan_tier} not found")

        # Calculer prorata
        now = datetime.utcnow()
        days_remaining = (current_sub.current_period_end - now).days
        days_total = (current_sub.current_period_end - current_sub.current_period_start).days

        # Crédit restant sur abonnement actuel
        current_price = (
            current_sub.plan.price_yearly_fcfa if current_sub.billing_period == BillingPeriod.YEARLY
            else current_sub.plan.price_monthly_fcfa
        )
        credit = int((days_remaining / days_total) * current_price)

        # Prix nouveau plan
        new_price = (
            new_plan.price_yearly_fcfa if billing_period == BillingPeriod.YEARLY
            else new_plan.price_monthly_fcfa
        )

        amount_to_pay = max(0, new_price - credit)

        return {
            "amount_to_pay": amount_to_pay,
            "credit_applied": credit,
            "new_plan": SubscriptionPlanSchema.from_orm(new_plan),
            "days_remaining": days_remaining
        }

    @staticmethod
    def cancel_subscription(
        db: Session,
        user_id: UUID,
        reason: Optional[str] = None,
        immediate: bool = False
    ) -> UserSubscription:
        """Annule un abonnement"""

        subscription = db.query(UserSubscription).filter(
            and_(
                UserSubscription.user_id == user_id,
                UserSubscription.status == SubscriptionStatus.ACTIVE
            )
        ).first()

        if not subscription:
            raise ValueError("No active subscription to cancel")

        subscription.cancellation_date = datetime.utcnow()
        subscription.cancellation_reason = reason
        subscription.auto_renew = False

        if immediate:
            # Annulation immédiate -> retour au Free
            subscription.status = SubscriptionStatus.CANCELLED
            SubscriptionService.create_free_subscription(db, user_id)
        else:
            # Annulation à la fin de période
            subscription.status = SubscriptionStatus.ACTIVE  # Reste actif jusqu'à expiration
            # Note: un CRON job vérifiera current_period_end pour expirer

        db.commit()
        db.refresh(subscription)

        return subscription

    @staticmethod
    def check_expiring_subscriptions(db: Session) -> list[UserSubscription]:
        """
        Tâche CRON quotidienne : récupère les abonnements qui expirent dans 3 jours
        Pour envoyer des rappels de renouvellement
        """
        three_days = datetime.utcnow() + timedelta(days=3)

        expiring = db.query(UserSubscription).filter(
            and_(
                UserSubscription.status == SubscriptionStatus.ACTIVE,
                UserSubscription.current_period_end <= three_days,
                UserSubscription.current_period_end > datetime.utcnow()
            )
        ).all()

        return expiring

    @staticmethod
    def expire_subscriptions(db: Session) -> int:
        """
        Tâche CRON quotidienne : expire les abonnements passés
        Retourne vers Free
        """
        now = datetime.utcnow()

        expired = db.query(UserSubscription).filter(
            and_(
                UserSubscription.status == SubscriptionStatus.ACTIVE,
                UserSubscription.current_period_end <= now
            )
        ).all()

        count = 0
        for sub in expired:
            sub.status = SubscriptionStatus.EXPIRED
            SubscriptionService.create_free_subscription(db, sub.user_id)
            count += 1

        if count > 0:
            db.commit()

        return count
```

---

### 3. Intégration CinetPay - `src/integrations/cinetpay.py`

```python
import os
import hmac
import hashlib
import requests
from typing import Optional, Dict
from datetime import datetime
from uuid import uuid4

class CinetPayClient:

    BASE_URL = "https://api-checkout.cinetpay.com/v2"

    def __init__(self):
        self.api_key = os.getenv("CINETPAY_API_KEY")
        self.site_id = os.getenv("CINETPAY_SITE_ID")
        self.secret_key = os.getenv("CINETPAY_SECRET_KEY")

        if not all([self.api_key, self.site_id, self.secret_key]):
            raise ValueError("CinetPay credentials not configured in environment")

    def create_payment(
        self,
        amount: int,  # En FCFA
        customer_email: str,
        customer_name: str,
        description: str,
        transaction_id: Optional[str] = None,
        notify_url: Optional[str] = None,
        return_url: Optional[str] = None,
        channels: str = "ALL"  # ALL, MOBILE_MONEY, CREDIT_CARD
    ) -> Dict:
        """
        Crée un paiement CinetPay

        Returns:
            {
                "code": "00",
                "message": "SUCCESS",
                "data": {
                    "payment_url": "https://checkout.cinetpay.com/payment/...",
                    "payment_token": "abc123...",
                    "transaction_id": "..."
                }
            }
        """

        if not transaction_id:
            transaction_id = f"kauri_{uuid4().hex[:16]}"

        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "transaction_id": transaction_id,
            "amount": amount,
            "currency": "XOF",  # Franc CFA
            "description": description,
            "customer_name": customer_name,
            "customer_surname": "",  # Optionnel
            "customer_email": customer_email,
            "customer_phone_number": "",  # Optionnel mais recommandé
            "customer_address": "",
            "customer_city": "",
            "customer_country": "CI",  # ISO code (Côte d'Ivoire par défaut)
            "customer_state": "",
            "customer_zip_code": "",
            "notify_url": notify_url or f"{os.getenv('API_BASE_URL')}/webhooks/cinetpay",
            "return_url": return_url or f"{os.getenv('FRONTEND_URL')}/subscription/success",
            "channels": channels,
            "metadata": f"user_email:{customer_email}",
            "lang": "fr"  # Interface en français
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/payment",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if result.get("code") == "00":  # Succès
                return {
                    "success": True,
                    "payment_url": result["data"]["payment_url"],
                    "payment_token": result["data"]["payment_token"],
                    "transaction_id": transaction_id
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Unknown error"),
                    "code": result.get("code")
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"CinetPay API error: {str(e)}"
            }

    def check_payment_status(self, transaction_id: str) -> Dict:
        """
        Vérifie le statut d'un paiement

        Returns:
            {
                "code": "00",
                "message": "SUCCES",
                "data": {
                    "status": "ACCEPTED",  # ou REFUSED, PENDING
                    "payment_method": "ORANGE_MONEY_CI",
                    "payment_date": "2025-01-15 10:30:00",
                    "amount": 9900,
                    ...
                }
            }
        """

        payload = {
            "apikey": self.api_key,
            "site_id": self.site_id,
            "transaction_id": transaction_id
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/payment/check",
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            if result.get("code") == "00":
                data = result["data"]
                return {
                    "success": True,
                    "status": data["status"],  # ACCEPTED, REFUSED, PENDING
                    "payment_method": data.get("payment_method"),
                    "payment_date": data.get("payment_date"),
                    "amount": data.get("amount"),
                    "metadata": data.get("metadata")
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message"),
                    "code": result.get("code")
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"CinetPay API error: {str(e)}"
            }

    def verify_webhook_signature(self, payload: Dict, signature: str) -> bool:
        """
        Vérifie la signature d'un webhook CinetPay (sécurité)

        Args:
            payload: Données du webhook
            signature: Signature envoyée dans header X-CinetPay-Signature
        """

        # CinetPay envoie HMAC-SHA256 du payload
        payload_string = str(sorted(payload.items()))
        expected_signature = hmac.new(
            self.secret_key.encode(),
            payload_string.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

# Instance globale
cinetpay_client = CinetPayClient()
```

---

### 4. API Routes Subscriptions - `src/api/routes/subscriptions.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from ...database.session import get_db
from ...auth.dependencies import get_current_user
from ...models.user import UserSchema
from ...models.subscription import (
    SubscriptionPlanSchema,
    UserSubscriptionSchema,
    CreateSubscriptionRequest,
    UpgradeSubscriptionRequest,
    CancelSubscriptionRequest,
    PlanTier
)
from ...services.subscription_service import SubscriptionService
from ...services.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])

@router.get("/plans", response_model=List[SubscriptionPlanSchema])
async def get_subscription_plans(
    db: Session = Depends(get_db)
):
    """Récupère tous les plans d'abonnement disponibles"""
    plans = SubscriptionService.get_all_plans(db)
    return plans

@router.get("/current", response_model=UserSubscriptionSchema)
async def get_current_subscription(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Récupère l'abonnement actif de l'utilisateur connecté"""
    subscription = SubscriptionService.get_user_subscription(db, current_user.user_id)

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found"
        )

    return subscription

@router.post("/create")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initie le processus de création d'abonnement
    Retourne l'URL de paiement CinetPay
    """

    # Vérifier que l'utilisateur n'a pas déjà un abonnement payant actif
    current_sub = SubscriptionService.get_user_subscription(db, current_user.user_id)
    if current_sub and current_sub.plan.tier != PlanTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active paid subscription. Use /upgrade instead."
        )

    # Récupérer le plan demandé
    plan = SubscriptionService.get_plan_by_tier(db, request.plan_tier)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {request.plan_tier} not found"
        )

    # Calculer le montant
    amount = (
        plan.price_yearly_fcfa if request.billing_period == "yearly"
        else plan.price_monthly_fcfa
    )

    if amount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create payment for free plan"
        )

    # Créer le paiement via PaymentService
    payment_result = await PaymentService.create_payment(
        db=db,
        user_id=current_user.user_id,
        plan_tier=request.plan_tier,
        billing_period=request.billing_period,
        amount=amount,
        payment_method=request.payment_method
    )

    if not payment_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=payment_result["error"]
        )

    return {
        "payment_url": payment_result["payment_url"],
        "transaction_id": payment_result["transaction_id"],
        "amount": amount,
        "plan": plan.name,
        "billing_period": request.billing_period
    }

@router.post("/upgrade")
async def upgrade_subscription(
    request: UpgradeSubscriptionRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Calcule le montant pour un upgrade (prorata)
    Retourne l'URL de paiement
    """

    # Calculer le montant avec prorata
    upgrade_info = SubscriptionService.upgrade_subscription(
        db,
        current_user.user_id,
        request.new_plan_tier,
        request.billing_period or "monthly"
    )

    if upgrade_info["amount_to_pay"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Downgrade not supported via this endpoint. Please cancel and subscribe."
        )

    # Créer le paiement
    payment_result = await PaymentService.create_payment(
        db=db,
        user_id=current_user.user_id,
        plan_tier=request.new_plan_tier,
        billing_period=request.billing_period or "monthly",
        amount=upgrade_info["amount_to_pay"],
        payment_method="card",  # Par défaut, peut être overridé
        is_upgrade=True
    )

    if not payment_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=payment_result["error"]
        )

    return {
        "payment_url": payment_result["payment_url"],
        "transaction_id": payment_result["transaction_id"],
        "amount_to_pay": upgrade_info["amount_to_pay"],
        "credit_applied": upgrade_info["credit_applied"],
        "new_plan": upgrade_info["new_plan"].name,
        "billing_period": request.billing_period
    }

@router.post("/cancel")
async def cancel_subscription(
    request: CancelSubscriptionRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Annule l'abonnement actif"""

    subscription = SubscriptionService.cancel_subscription(
        db,
        current_user.user_id,
        request.reason,
        request.immediate
    )

    return {
        "message": "Subscription cancelled successfully",
        "effective_date": subscription.current_period_end if not request.immediate else "immediately",
        "refund": None  # TODO: Politique de remboursement
    }
```

---

### 5. API Routes Payments - `src/api/routes/payments.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from typing import Optional

from ...database.session import get_db
from ...auth.dependencies import get_current_user
from ...models.user import UserSchema
from ...services.payment_service import PaymentService
from ...integrations.cinetpay import cinetpay_client

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

@router.get("/history")
async def get_payment_history(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """Récupère l'historique des paiements de l'utilisateur"""
    payments = PaymentService.get_user_payments(
        db,
        current_user.user_id,
        limit=limit,
        offset=offset
    )
    return payments

@router.get("/check/{transaction_id}")
async def check_payment_status(
    transaction_id: str,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Vérifie le statut d'un paiement (polling après redirection)
    Utilisé par frontend pour savoir si paiement validé
    """

    # Vérifier que la transaction appartient bien à l'utilisateur
    payment = PaymentService.get_payment_by_transaction_id(db, transaction_id)

    if not payment or payment.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Check auprès de CinetPay
    status_result = cinetpay_client.check_payment_status(transaction_id)

    if not status_result["success"]:
        return {
            "status": "error",
            "error": status_result["error"]
        }

    # Mettre à jour le paiement si nécessaire
    if status_result["status"] == "ACCEPTED" and payment.status != "completed":
        await PaymentService.process_successful_payment(db, transaction_id, status_result)

    return {
        "status": status_result["status"],
        "payment_method": status_result.get("payment_method"),
        "payment_date": status_result.get("payment_date")
    }

@router.post("/webhooks/cinetpay")
async def cinetpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_cinetpay_signature: Optional[str] = Header(None)
):
    """
    Webhook CinetPay pour notifications de paiement
    Appelé automatiquement par CinetPay après paiement
    """

    payload = await request.json()

    # Vérifier la signature (sécurité)
    if x_cinetpay_signature:
        if not cinetpay_client.verify_webhook_signature(payload, x_cinetpay_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    # Traiter le webhook
    transaction_id = payload.get("cpm_trans_id")
    status = payload.get("cpm_result")  # "00" = success

    if status == "00":
        # Paiement accepté
        await PaymentService.process_successful_payment(
            db,
            transaction_id,
            {
                "status": "ACCEPTED",
                "payment_method": payload.get("payment_method"),
                "payment_date": payload.get("cpm_trans_date"),
                "amount": int(payload.get("cpm_amount", 0))
            }
        )

        return {"code": "00", "message": "Webhook processed"}

    else:
        # Paiement refusé
        await PaymentService.mark_payment_failed(
            db,
            transaction_id,
            payload.get("cpm_error_message", "Payment refused")
        )

        return {"code": "01", "message": "Payment failed"}
```

---

## 🔧 BACKEND - CHATBOT SERVICE

### Middleware Rate Limiting - `src/middleware/quota_middleware.py`

```python
from fastapi import Request, HTTPException, status
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional
import redis

from ..database.session import get_db
from ..models.usage import UsageTracking
from ..services.subscription_service import SubscriptionService

# Redis client pour rate limiting rapide
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=1,  # DB séparée pour rate limiting
    decode_responses=True
)

class QuotaMiddleware:
    """
    Middleware pour vérifier les quotas avant chaque requête chat
    """

    @staticmethod
    async def check_quota(
        user_id: str,
        db: Session,
        endpoint: str = "chat"
    ) -> dict:
        """
        Vérifie si l'utilisateur a atteint ses quotas

        Returns:
            {
                "allowed": bool,
                "remaining_today": int,
                "remaining_month": int,
                "plan": str,
                "reset_date": str
            }

        Raises:
            HTTPException 429 si quota dépassé
        """

        # 1. Récupérer l'abonnement de l'utilisateur
        subscription = SubscriptionService.get_user_subscription(db, user_id)

        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active subscription"
            )

        plan = subscription.plan

        # 2. Récupérer ou créer l'entrée usage du jour
        today = date.today()
        usage = db.query(UsageTracking).filter(
            UsageTracking.user_id == user_id,
            UsageTracking.date == today
        ).first()

        if not usage:
            usage = UsageTracking(
                user_id=user_id,
                date=today,
                questions_today=0,
                questions_this_month=0
            )
            db.add(usage)
            db.commit()
            db.refresh(usage)

        # 3. Vérifier les quotas

        # Quota quotidien
        if plan.questions_per_day is not None:
            if usage.questions_today >= plan.questions_per_day:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Daily quota exceeded",
                        "quota": plan.questions_per_day,
                        "used": usage.questions_today,
                        "reset_at": str(today + timedelta(days=1)),
                        "upgrade_url": "/subscriptions/plans"
                    }
                )

        # Quota mensuel
        if plan.questions_per_month is not None:
            if usage.questions_this_month >= plan.questions_per_month:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Monthly quota exceeded",
                        "quota": plan.questions_per_month,
                        "used": usage.questions_this_month,
                        "reset_at": str(date(today.year, today.month + 1, 1)),
                        "upgrade_url": "/subscriptions/plans"
                    }
                )

        # 4. Calculer les remainings
        remaining_today = (
            plan.questions_per_day - usage.questions_today
            if plan.questions_per_day is not None
            else float('inf')
        )

        remaining_month = (
            plan.questions_per_month - usage.questions_this_month
            if plan.questions_per_month is not None
            else float('inf')
        )

        return {
            "allowed": True,
            "remaining_today": remaining_today,
            "remaining_month": remaining_month,
            "plan": plan.tier,
            "reset_date": str(today + timedelta(days=1))
        }

    @staticmethod
    async def increment_usage(
        user_id: str,
        db: Session,
        tokens_consumed: int = 0
    ):
        """
        Incrémente les compteurs d'usage après une requête réussie
        """

        today = date.today()

        # Utiliser UPSERT pour éviter race conditions
        usage = db.query(UsageTracking).filter(
            UsageTracking.user_id == user_id,
            UsageTracking.date == today
        ).with_for_update().first()

        if not usage:
            usage = UsageTracking(
                user_id=user_id,
                date=today,
                questions_today=1,
                questions_this_month=1,
                tokens_consumed_this_month=tokens_consumed,
                last_question_at=datetime.utcnow()
            )
            db.add(usage)
        else:
            usage.questions_today += 1
            usage.questions_this_month += 1
            usage.tokens_consumed_this_month += tokens_consumed
            usage.last_question_at = datetime.utcnow()

        db.commit()

        # Optionnel : Incrémenter aussi dans Redis pour stats temps réel
        redis_key_day = f"usage:{user_id}:{today}"
        redis_key_month = f"usage:{user_id}:{today.strftime('%Y-%m')}"

        redis_client.incr(redis_key_day)
        redis_client.expire(redis_key_day, 86400)  # Expire après 24h

        redis_client.incr(redis_key_month)
        redis_client.expire(redis_key_month, 2678400)  # Expire après 31 jours
```

---

### Modification Route Chat - `src/api/routes/chat.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database.session import get_db
from ...auth.dependencies import get_current_user
from ...middleware.quota_middleware import QuotaMiddleware
from ...models.user import UserSchema

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Streaming chat avec vérification quotas
    """

    # 1. VÉRIFIER LES QUOTAS AVANT DE TRAITER
    quota_check = await QuotaMiddleware.check_quota(
        user_id=str(current_user.user_id),
        db=db
    )

    # 2. TRAITEMENT NORMAL DU CHAT
    # ... (code existant)

    # 3. INCRÉMENTER L'USAGE APRÈS SUCCÈS
    await QuotaMiddleware.increment_usage(
        user_id=str(current_user.user_id),
        db=db,
        tokens_consumed=total_tokens  # Calculé pendant génération
    )

    return StreamingResponse(...)

@router.get("/quota")
async def get_user_quota(
    current_user: UserSchema = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint pour frontend : récupère l'état des quotas
    """

    quota_info = await QuotaMiddleware.check_quota(
        user_id=str(current_user.user_id),
        db=db
    )

    # Ajouter des infos sur l'abonnement
    subscription = SubscriptionService.get_user_subscription(db, current_user.user_id)

    return {
        **quota_info,
        "subscription": {
            "plan": subscription.plan.name,
            "tier": subscription.plan.tier,
            "expires_at": subscription.current_period_end
        }
    }
```

---

## 🎨 FRONTEND

### Composant Dashboard Quota - `frontend/kauri-app/src/components/QuotaDisplay.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { Progress } from './ui/progress';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { useNavigate } from 'react-router-dom';

interface QuotaInfo {
  allowed: boolean;
  remaining_today: number;
  remaining_month: number;
  plan: string;
  reset_date: string;
  subscription: {
    plan: string;
    tier: string;
    expires_at: string;
  };
}

export const QuotaDisplay: React.FC = () => {
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchQuotaInfo();
  }, []);

  const fetchQuotaInfo = async () => {
    try {
      const response = await fetch('/api/v1/chat/quota', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setQuotaInfo(data);
      }
    } catch (error) {
      console.error('Failed to fetch quota info:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Chargement...</div>;
  if (!quotaInfo) return null;

  const dailyUsagePercent = quotaInfo.remaining_today === Infinity
    ? 0
    : ((100 - (quotaInfo.remaining_today / (quotaInfo.remaining_today + 1) * 100)));

  const monthlyUsagePercent = quotaInfo.remaining_month === Infinity
    ? 0
    : ((100 - (quotaInfo.remaining_month / (quotaInfo.remaining_month + 1) * 100)));

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Votre utilisation</span>
          <span className="text-sm font-normal text-blue-600">
            Plan {quotaInfo.subscription.plan}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Quota quotidien */}
        {quotaInfo.remaining_today !== Infinity && (
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>Questions aujourd'hui</span>
              <span className="font-semibold">
                {quotaInfo.remaining_today} restantes
              </span>
            </div>
            <Progress value={dailyUsagePercent} className="h-2" />
            <p className="text-xs text-gray-500 mt-1">
              Renouvellement: {new Date(quotaInfo.reset_date).toLocaleDateString()}
            </p>
          </div>
        )}

        {/* Quota mensuel */}
        {quotaInfo.remaining_month !== Infinity && (
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>Questions ce mois-ci</span>
              <span className="font-semibold">
                {quotaInfo.remaining_month} restantes
              </span>
            </div>
            <Progress value={monthlyUsagePercent} className="h-2" />
          </div>
        )}

        {/* Warning si proche de la limite */}
        {quotaInfo.remaining_today < 2 && quotaInfo.remaining_today !== Infinity && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
            <p className="text-sm text-yellow-800">
              ⚠️ Vous approchez de votre limite quotidienne.
              <Button
                variant="link"
                className="ml-2 p-0 h-auto"
                onClick={() => navigate('/pricing')}
              >
                Passer à PRO
              </Button>
            </p>
          </div>
        )}

        {/* Upsell pour Free users */}
        {quotaInfo.subscription.tier === 'free' && (
          <Button
            variant="default"
            className="w-full"
            onClick={() => navigate('/pricing')}
          >
            🚀 Passer à PRO - 9 900 FCFA/mois
          </Button>
        )}
      </CardContent>
    </Card>
  );
};
```

---

### Page Pricing - `frontend/kauri-app/src/pages/PricingPage.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Check, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface Plan {
  plan_id: string;
  tier: string;
  name: string;
  description: string;
  price_monthly_fcfa: number;
  price_yearly_fcfa: number;
  questions_per_day: number | null;
  questions_per_month: number | null;
  max_sources_per_query: number;
  can_export_conversations: boolean;
  can_upload_documents: boolean;
  has_api_access: boolean;
  has_priority_queue: boolean;
  support_level: string;
}

export const PricingPage: React.FC = () => {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const navigate = useNavigate();

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await fetch('/api/v1/subscriptions/plans');
      if (response.ok) {
        const data = await response.json();
        setPlans(data);
      }
    } catch (error) {
      console.error('Failed to fetch plans:', error);
    }
  };

  const handleSubscribe = async (planTier: string) => {
    if (planTier === 'free') {
      return; // Déjà Free par défaut
    }

    try {
      const response = await fetch('/api/v1/subscriptions/create', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          plan_tier: planTier,
          billing_period: billingPeriod,
          payment_method: 'orange_money' // Par défaut, sera choisi sur page paiement
        })
      });

      if (response.ok) {
        const data = await response.json();
        // Rediriger vers CinetPay
        window.location.href = data.payment_url;
      } else {
        const error = await response.json();
        alert(`Erreur: ${error.detail}`);
      }
    } catch (error) {
      console.error('Subscription error:', error);
      alert('Erreur lors de la création de l\'abonnement');
    }
  };

  return (
    <div className="container mx-auto px-4 py-12">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">
          Choisissez votre plan
        </h1>
        <p className="text-gray-600 mb-6">
          Des solutions adaptées à tous les professionnels de la comptabilité OHADA
        </p>

        {/* Toggle Monthly/Yearly */}
        <div className="inline-flex rounded-lg border p-1">
          <button
            className={`px-4 py-2 rounded ${
              billingPeriod === 'monthly'
                ? 'bg-blue-600 text-white'
                : 'text-gray-700'
            }`}
            onClick={() => setBillingPeriod('monthly')}
          >
            Mensuel
          </button>
          <button
            className={`px-4 py-2 rounded ${
              billingPeriod === 'yearly'
                ? 'bg-blue-600 text-white'
                : 'text-gray-700'
            }`}
            onClick={() => setBillingPeriod('yearly')}
          >
            Annuel <span className="text-green-600 text-sm">(-10%)</span>
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
        {plans.map((plan) => {
          const price = billingPeriod === 'monthly'
            ? plan.price_monthly_fcfa
            : Math.floor(plan.price_yearly_fcfa / 12);

          const isPopular = plan.tier === 'pro';

          return (
            <Card
              key={plan.plan_id}
              className={`relative ${
                isPopular ? 'border-blue-600 border-2 shadow-lg' : ''
              }`}
            >
              {isPopular && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                  Plus populaire
                </div>
              )}

              <CardHeader>
                <CardTitle className="text-2xl">{plan.name}</CardTitle>
                <p className="text-gray-600 text-sm">{plan.description}</p>

                <div className="mt-4">
                  <span className="text-4xl font-bold">
                    {price.toLocaleString()}
                  </span>
                  <span className="text-gray-600"> FCFA/mois</span>
                </div>
              </CardHeader>

              <CardContent>
                <ul className="space-y-3 mb-6">
                  <li className="flex items-start">
                    <Check className="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
                    <span>
                      {plan.questions_per_day
                        ? `${plan.questions_per_day} questions/jour`
                        : `${plan.questions_per_month || 'Illimité'} questions/mois`}
                    </span>
                  </li>

                  <li className="flex items-start">
                    <Check className="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
                    <span>{plan.max_sources_per_query} sources par réponse</span>
                  </li>

                  <li className="flex items-start">
                    {plan.can_export_conversations ? (
                      <Check className="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
                    ) : (
                      <X className="w-5 h-5 text-gray-400 mr-2 flex-shrink-0" />
                    )}
                    <span>Export conversations</span>
                  </li>

                  <li className="flex items-start">
                    {plan.has_priority_queue ? (
                      <Check className="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
                    ) : (
                      <X className="w-5 h-5 text-gray-400 mr-2 flex-shrink-0" />
                    )}
                    <span>File d'attente prioritaire</span>
                  </li>

                  <li className="flex items-start">
                    {plan.can_upload_documents ? (
                      <Check className="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
                    ) : (
                      <X className="w-5 h-5 text-gray-400 mr-2 flex-shrink-0" />
                    )}
                    <span>Upload documents personnels</span>
                  </li>

                  <li className="flex items-start">
                    <Check className="w-5 h-5 text-green-600 mr-2 flex-shrink-0" />
                    <span>Support {plan.support_level}</span>
                  </li>
                </ul>

                <Button
                  variant={isPopular ? 'default' : 'outline'}
                  className="w-full"
                  onClick={() => handleSubscribe(plan.tier)}
                  disabled={plan.tier === 'free'}
                >
                  {plan.tier === 'free'
                    ? 'Plan actuel'
                    : plan.tier === 'enterprise'
                    ? 'Nous contacter'
                    : 'Souscrire'}
                </Button>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
```

---

## ✅ TESTS

### Tests Unitaires - `backend/kauri_user_service/tests/test_subscription_service.py`

```python
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.services.subscription_service import SubscriptionService
from src.models.subscription import PlanTier, BillingPeriod

def test_create_free_subscription(db_session, test_user):
    """Test création abonnement gratuit"""
    sub = SubscriptionService.create_free_subscription(db_session, test_user.user_id)

    assert sub.user_id == test_user.user_id
    assert sub.plan.tier == PlanTier.FREE
    assert sub.status == "active"

def test_upgrade_subscription_prorata(db_session, test_user_with_pro):
    """Test calcul prorata lors upgrade"""
    # User a un abonnement PRO depuis 15 jours (sur 30)
    upgrade_info = SubscriptionService.upgrade_subscription(
        db_session,
        test_user_with_pro.user_id,
        PlanTier.MAX,
        BillingPeriod.MONTHLY
    )

    # Crédit = 50% du prix PRO (15 jours restants / 30)
    expected_credit = 9900 / 2
    assert upgrade_info["credit_applied"] == pytest.approx(expected_credit, abs=100)
    assert upgrade_info["amount_to_pay"] == 29900 - expected_credit

def test_quota_enforcement(db_session, test_user_free):
    """Test que quotas sont bien enforc és"""
    from src.middleware.quota_middleware import QuotaMiddleware

    # Utilisateur Free : 5 questions/jour
    for i in range(5):
        await QuotaMiddleware.increment_usage(test_user_free.user_id, db_session)

    # 6ème question doit échouer
    with pytest.raises(HTTPException) as exc_info:
        await QuotaMiddleware.check_quota(test_user_free.user_id, db_session)

    assert exc_info.value.status_code == 429
    assert "Daily quota exceeded" in str(exc_info.value.detail)
```

---

## 🚀 DÉPLOIEMENT

### Variables d'Environnement - `.env.production`

```bash
# CinetPay
CINETPAY_API_KEY=your_api_key_here
CINETPAY_SITE_ID=your_site_id_here
CINETPAY_SECRET_KEY=your_secret_key_here

# URLs
API_BASE_URL=https://api.kauri.com
FRONTEND_URL=https://app.kauri.com

# Database
DATABASE_URL=postgresql://user:pass@db:5432/kauri_users

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
```

---

## 📅 ROADMAP ET PRIORISATION

### Sprint 1 (Semaines 1-2) : Fondations
**Objectif** : Modèles de données + API subscriptions

- [x] Migrations Alembic (tables subscription_plans, user_subscriptions, usage_tracking, payment_transactions)
- [x] Modèles Pydantic (SubscriptionPlanSchema, UserSubscriptionSchema, etc.)
- [x] Service SubscriptionService (CRUD abonnements)
- [x] API routes /subscriptions/plans, /subscriptions/current
- [x] Tests unitaires services

### Sprint 2 (Semaines 3-4) : Paiements
**Objectif** : Intégration CinetPay + webhooks

- [x] Client CinetPay (create_payment, check_status)
- [x] Service PaymentService
- [x] API routes /subscriptions/create, /payments/webhooks/cinetpay
- [x] Tests d'intégration paiements (sandbox CinetPay)
- [x] Monitoring erreurs paiements (Sentry)

### Sprint 3 (Semaines 5-6) : Quotas
**Objectif** : Rate limiting + Frontend

- [x] Middleware QuotaMiddleware
- [x] Modification routes chat pour vérification quotas
- [x] API /chat/quota pour frontend
- [x] Composant React QuotaDisplay
- [x] Page PricingPage
- [x] Tests end-to-end quotas

### Post-MVP (Backlog)
- [ ] Tâche CRON : expiration abonnements
- [ ] Tâche CRON : rappels renouvellement (J-3)
- [ ] Admin panel : dashboard stats abonnements
- [ ] Emails transactionnels (confirmation, renouvellement)
- [ ] Feature MAX : Upload documents personnels
- [ ] Feature MAX : Génération PDF

---

## ✅ CHECKLIST FINALE

**Backend User Service** :
- [ ] Migrations DB appliquées en production
- [ ] Seeds subscription_plans insérés
- [ ] Variables environnement CinetPay configurées
- [ ] Tests unitaires passent (>80% coverage)
- [ ] Endpoints documentés (Swagger)

**Backend Chatbot Service** :
- [ ] Middleware quotas activé sur routes /chat
- [ ] Table usage_tracking créée
- [ ] Redis configuré pour rate limiting
- [ ] Tests d'intégration passent

**Frontend** :
- [ ] Page /pricing déployée
- [ ] Composant QuotaDisplay intégré au dashboard
- [ ] Redirection CinetPay testée (sandbox)
- [ ] Page /subscription/success créée

**Monitoring** :
- [ ] Sentry configuré pour erreurs paiements
- [ ] Logs CinetPay webhooks (CloudWatch)
- [ ] Alertes quotas atteints (metrics)

**Documentation** :
- [ ] README mis à jour avec instructions quotas
- [ ] Guide utilisateur paiement Mobile Money
- [ ] Runbook support client (problèmes paiements)

---

## 📞 SUPPORT ET MAINTENANCE

**Problèmes fréquents** :

1. **Paiement bloqué** : Vérifier logs webhooks CinetPay, resynchroniser via /payments/check/{transaction_id}
2. **Quota incorrect** : Reset manuel via SQL `UPDATE usage_tracking SET questions_today = 0 WHERE user_id = '...'`
3. **Abonnement expiré** : Vérifier CRON job `expire_subscriptions` s'exécute quotidiennement

**Commandes utiles** :

```bash
# Vérifier abonnements actifs
psql kauri_users -c "SELECT u.email, s.plan_id, s.current_period_end FROM user_subscriptions s JOIN users u ON s.user_id = u.user_id WHERE s.status = 'active';"

# Reset usage quotidien (support client)
psql kauri_chatbot -c "UPDATE usage_tracking SET questions_today = 0 WHERE user_id = '<UUID>';"

# Lister paiements en attente
psql kauri_users -c "SELECT * FROM payment_transactions WHERE status = 'pending' AND created_at > NOW() - INTERVAL '24 hours';"
```

---

**FIN DU DOCUMENT**

Version : 1.0
Date dernière mise à jour : 2025-01-15
