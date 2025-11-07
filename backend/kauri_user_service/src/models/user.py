"""
Modèles SQLAlchemy pour le User Service
"""
from datetime import datetime, date
from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, BigInteger, Date, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """
    Modèle User pour l'authentification et la gestion des utilisateurs
    """
    __tablename__ = "users"

    # Identifiant unique
    user_id = Column(String(36), primary_key=True, index=True)

    # Informations de base
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable pour OAuth

    # Profil
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)  # Photo de profil OAuth

    # OAuth Providers (optionnel)
    google_id = Column(String(255), unique=True, nullable=True, index=True)

    # OAuth metadata
    oauth_provider = Column(String(50), nullable=True)  # 'google', None pour local

    # Email verification
    email_verification_token = Column(String(255), nullable=True, index=True)
    email_verification_token_expires = Column(DateTime, nullable=True)
    email_verified_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Subscription fields (added via migration 7dc92d559294)
    subscription_tier = Column(String(20), nullable=False, default='free', server_default='free', index=True)
    subscription_status = Column(String(20), nullable=False, default='active', server_default='active', index=True)
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)
    trial_end_date = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(user_id={self.user_id}, email={self.email})>"


class RevokedToken(Base):
    """
    Modèle pour les tokens JWT révoqués (logout)
    """
    __tablename__ = "revoked_tokens"

    token_id = Column(String(36), primary_key=True)
    token = Column(Text, unique=True, nullable=False, index=True)
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<RevokedToken(token_id={self.token_id})>"


class SubscriptionTier(Base):
    """
    Modèle pour les plans d'abonnement (reference table)
    """
    __tablename__ = "subscription_tiers"

    tier_id = Column(String(20), primary_key=True)
    tier_name = Column(String(50), nullable=False)
    tier_name_fr = Column(String(50), nullable=False)
    tier_description = Column(Text, nullable=True)
    tier_description_fr = Column(Text, nullable=True)

    # Quotas (NULL = illimité)
    messages_per_day = Column(Integer, nullable=True)
    messages_per_month = Column(Integer, nullable=True)
    tokens_per_month = Column(BigInteger, nullable=True)

    # Pricing (FCFA)
    price_monthly = Column(Integer, nullable=False, default=0)
    price_annual = Column(Integer, nullable=True)

    # Features
    has_document_sourcing = Column(Boolean, nullable=False, default=False)
    has_pdf_generation = Column(Boolean, nullable=False, default=False)
    has_priority_support = Column(Boolean, nullable=False, default=False)
    has_custom_training = Column(Boolean, nullable=False, default=False)
    has_api_access = Column(Boolean, nullable=False, default=False)

    # Display
    display_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    is_visible = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<SubscriptionTier(tier_id={self.tier_id}, tier_name={self.tier_name})>"


class UserUsage(Base):
    """
    Modèle pour le suivi de l'utilisation des quotas par utilisateur
    """
    __tablename__ = "user_usage"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    usage_date = Column(Date, nullable=False, index=True)

    # Daily counters
    messages_today = Column(Integer, nullable=False, default=0)

    # Monthly counters
    messages_this_month = Column(Integer, nullable=False, default=0)
    tokens_this_month = Column(BigInteger, nullable=False, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UserUsage(user_id={self.user_id}, usage_date={self.usage_date})>"


class UsageLog(Base):
    """
    Modèle pour les logs d'audit d'utilisation
    """
    __tablename__ = "usage_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # 'message_sent', 'quota_exceeded', etc.
    event_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Usage details
    messages_count = Column(Integer, nullable=True)
    tokens_count = Column(BigInteger, nullable=True)

    # Context
    quota_tier = Column(String(20), nullable=True)
    quota_status = Column(String(20), nullable=True)  # 'allowed', 'exceeded', 'warning'
    request_ip = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    # Additional metadata (JSON) - renamed to avoid SQLAlchemy conflict
    event_metadata = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<UsageLog(user_id={self.user_id}, event_type={self.event_type})>"
