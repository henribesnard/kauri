"""
Modèles SQLAlchemy pour le User Service
"""
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
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
