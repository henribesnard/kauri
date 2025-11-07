"""
Routes d'authentification
/api/v1/auth/*
"""
from datetime import datetime
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
import structlog

from ...models.user import User, RevokedToken
from ...schemas.user import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    UserLoginResponse,
    Message
)
from ...auth.password import hash_password, verify_password
from ...auth.jwt_manager import jwt_manager
from ...utils.database import get_db
from ...services.verification_service import verification_service
from ...services.email_service import email_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# ============================================
# Helper Functions
# ============================================

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Dépendance pour obtenir l'utilisateur courant depuis le token JWT

    Args:
        authorization: Header Authorization (format: "Bearer <token>")
        db: Session de base de données

    Returns:
        User: Utilisateur courant

    Raises:
        HTTPException: Si token invalide ou utilisateur introuvable
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant ou format invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]

    # Vérifier si token révoqué
    revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
    if revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token révoqué",
        )

    # Décoder token
    try:
        user_data = jwt_manager.get_user_from_token(token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
            )
    except Exception as e:
        logger.error("token_decode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
        )

    # Récupérer utilisateur
    user = db.query(User).filter(User.user_id == user_data["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )

    return user


# ============================================
# Endpoints
# ============================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """
    Enregistrer un nouvel utilisateur

    - **email**: Email unique
    - **password**: Mot de passe (min 8 caractères, 1 majuscule, 1 chiffre)
    - **first_name**: Prénom (optionnel)
    - **last_name**: Nom (optionnel)
    """
    logger.info("user_registration_attempt", email=user_data.email)

    # Vérifier si email existe déjà
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning("user_registration_failed_email_exists", email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un compte avec cet email existe déjà"
        )

    # Créer utilisateur
    user_id = str(uuid.uuid4())
    password_hash = hash_password(user_data.password)

    new_user = User(
        user_id=user_id,
        email=user_data.email,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        is_verified=False,
        is_superuser=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("user_registration_success", user_id=user_id, email=user_data.email)

    # Generer et envoyer le token de verification d'email
    try:
        token = verification_service.create_verification_token(db, new_user)
        verification_url = verification_service.get_verification_url(token)

        user_name = f"{new_user.first_name} {new_user.last_name}".strip() if new_user.first_name or new_user.last_name else None

        email_sent = email_service.send_verification_email(
            to_email=new_user.email,
            verification_url=verification_url,
            user_name=user_name
        )

        if email_sent:
            logger.info(
                "verification_email_sent",
                user_id=user_id,
                email=user_data.email
            )
        else:
            logger.warning(
                "verification_email_not_sent",
                user_id=user_id,
                email=user_data.email,
                message="SMTP not configured or email failed"
            )
    except Exception as e:
        logger.error(
            "verification_email_error",
            user_id=user_id,
            email=user_data.email,
            error=str(e)
        )
        # Ne pas faire echouer l'inscription si l'email ne part pas

    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Connexion utilisateur

    - **email**: Email de l'utilisateur
    - **password**: Mot de passe
    """
    logger.info("user_login_attempt", email=credentials.email)

    # Récupérer utilisateur
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user:
        logger.warning("user_login_failed_user_not_found", email=credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    # Vérifier mot de passe
    if not user.password_hash or not verify_password(credentials.password, user.password_hash):
        logger.warning("user_login_failed_invalid_password", user_id=user.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect"
        )

    # Vérifier si compte actif
    if not user.is_active:
        logger.warning("user_login_failed_account_inactive", user_id=user.user_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé"
        )

    # Vérifier si l'email est vérifié (sauf pour les utilisateurs OAuth)
    if not user.is_verified and not user.oauth_provider:
        logger.warning("user_login_failed_email_not_verified", user_id=user.user_id, email=user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez vérifier votre adresse email avant de vous connecter. Consultez votre boite de réception."
        )

    # Mettre à jour last_login
    user.last_login = datetime.utcnow()
    db.commit()

    logger.info("user_login_success", user_id=user.user_id, email=user.email)

    # Créer token
    token_data = jwt_manager.create_access_token(
        user_id=user.user_id,
        email=user.email
    )

    # Créer réponse avec token et utilisateur (schéma sécurisé)
    return TokenResponse(
        **token_data,
        user=UserLoginResponse.from_orm(user)
    )


@router.post("/logout", response_model=Message)
async def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Déconnexion utilisateur (révocation du token)

    Nécessite un token JWT valide dans le header Authorization
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant"
        )

    token = authorization.split(" ")[1]

    # Récupérer expiration du token
    expires_at = jwt_manager.get_token_expiry(token)
    if not expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide"
        )

    # Ajouter token à la liste des révoqués
    revoked_token = RevokedToken(
        token_id=str(uuid.uuid4()),
        token=token,
        expires_at=expires_at
    )

    db.add(revoked_token)
    db.commit()

    logger.info("user_logout_success", token_id=revoked_token.token_id)

    return Message(message="Déconnexion réussie")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Obtenir les informations de l'utilisateur courant

    Nécessite un token JWT valide dans le header Authorization
    """
    logger.info("user_info_retrieved", user_id=current_user.user_id)
    return current_user
