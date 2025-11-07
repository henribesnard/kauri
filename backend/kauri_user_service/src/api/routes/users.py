"""
Routes pour la gestion du profil utilisateur
/api/v1/users/*
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import structlog

from ...models.user import User
from ...schemas.user import UserResponse
from ...auth.password import hash_password, verify_password
from ...utils.database import get_db
from ..routes.auth import get_current_user

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/users", tags=["users"])


# ============================================
# Schemas
# ============================================

class UpdateProfileRequest(BaseModel):
    """Schéma pour la mise à jour du profil"""
    first_name: str | None = None
    last_name: str | None = None
    # email: EmailStr | None = None  # Désactivé pour l'instant


class UpdatePasswordRequest(BaseModel):
    """Schéma pour le changement de mot de passe"""
    current_password: str
    new_password: str


# ============================================
# Endpoints
# ============================================

@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Récupérer le profil de l'utilisateur connecté
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    profile_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mettre à jour le profil de l'utilisateur connecté

    - **first_name**: Prénom (optionnel)
    - **last_name**: Nom (optionnel)
    """
    logger.info("profile_update_attempt", user_id=current_user.user_id)

    # Mettre à jour les champs fournis
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name

    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name

    # Sauvegarder
    db.commit()
    db.refresh(current_user)

    logger.info(
        "profile_updated",
        user_id=current_user.user_id,
        first_name=current_user.first_name,
        last_name=current_user.last_name
    )

    return current_user


@router.put("/me/password")
async def update_my_password(
    password_data: UpdatePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Changer le mot de passe de l'utilisateur connecté

    - **current_password**: Mot de passe actuel (pour vérification)
    - **new_password**: Nouveau mot de passe
    """
    logger.info("password_change_attempt", user_id=current_user.user_id)

    # Vérifier que l'utilisateur a un mot de passe (pas OAuth)
    if not current_user.password_hash:
        logger.warning(
            "password_change_failed_oauth_user",
            user_id=current_user.user_id,
            oauth_provider=current_user.oauth_provider
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les utilisateurs OAuth ne peuvent pas changer de mot de passe"
        )

    # Vérifier le mot de passe actuel
    if not verify_password(password_data.current_password, current_user.password_hash):
        logger.warning("password_change_failed_wrong_password", user_id=current_user.user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect"
        )

    # Valider le nouveau mot de passe
    if len(password_data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit contenir au moins 8 caractères"
        )

    # Mettre à jour le mot de passe
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()

    logger.info("password_changed_successfully", user_id=current_user.user_id)

    return {
        "message": "Mot de passe mis à jour avec succès",
        "success": True
    }
