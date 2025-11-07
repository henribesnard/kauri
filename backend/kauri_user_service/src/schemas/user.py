"""
Schémas Pydantic pour validation des données User
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, validator


# ============================================
# Schémas pour Authentification
# ============================================

class UserRegister(BaseModel):
    """Schéma pour l'enregistrement d'un utilisateur"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        """Valider la complexité du mot de passe"""
        if len(v) < 8:
            raise ValueError('Le mot de passe doit contenir au moins 8 caractères')
        if not any(char.isdigit() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins un chiffre')
        if not any(char.isupper() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une majuscule')
        if not any(char.islower() for char in v):
            raise ValueError('Le mot de passe doit contenir au moins une minuscule')
        return v


class UserLogin(BaseModel):
    """Schéma pour la connexion"""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schéma pour la réponse contenant le token"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Durée en secondes
    user: 'UserLoginResponse'  # Forward reference - schéma sécurisé sans is_superuser/is_verified


class TokenData(BaseModel):
    """Schéma pour les données contenues dans le token"""
    user_id: str
    email: str


# ============================================
# Schémas pour User
# ============================================

class UserBase(BaseModel):
    """Schéma de base pour User"""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    """Schéma pour créer un User"""
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schéma pour mettre à jour un User"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserResponse(UserBase):
    """Schéma pour la réponse User (sans password)"""
    user_id: str
    is_active: bool
    is_verified: bool
    is_superuser: bool

    # Subscription fields
    subscription_tier: str
    subscription_status: str
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    trial_end_date: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2 (anciennement orm_mode)


class UserLoginResponse(UserBase):
    """Schéma sécurisé pour la réponse login (sans is_superuser, is_verified)"""
    user_id: str

    # Subscription fields (for frontend to know user's plan)
    subscription_tier: str
    subscription_status: str

    # Removed for security: is_superuser, is_verified, created_at, updated_at, last_login

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """Schéma pour User en base de données (avec password_hash)"""
    password_hash: Optional[str] = None


# ============================================
# Schémas pour Messages
# ============================================

class Message(BaseModel):
    """Schéma générique pour messages"""
    message: str


class ErrorResponse(BaseModel):
    """Schéma pour réponses d'erreur"""
    error: str
    detail: Optional[str] = None
