"""
Routes pour la verification d'email
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import structlog

from ...utils.database import get_db
from ...services.verification_service import verification_service
from ...services.email_service import email_service

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])


class VerifyEmailRequest(BaseModel):
    """Request pour verifier un email"""
    token: str


class ResendVerificationRequest(BaseModel):
    """Request pour renvoyer un email de verification"""
    email: EmailStr


class VerificationResponse(BaseModel):
    """Response apres verification"""
    message: str
    success: bool


@router.post("/verify-email", response_model=VerificationResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verifie un email avec le token recu

    Args:
        request: Token de verification
        db: Session de base de donnees

    Returns:
        Message de confirmation ou d'erreur

    Raises:
        HTTPException: Si le token est invalide ou expire
    """
    logger.info("verify_email_attempt", token_prefix=request.token[:10])

    success, error_message, user = verification_service.verify_email_token(
        db=db,
        token=request.token
    )

    if not success:
        logger.warning(
            "verify_email_failed",
            error=error_message,
            token_prefix=request.token[:10]
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    logger.info(
        "verify_email_success",
        user_id=user.user_id,
        email=user.email
    )

    return VerificationResponse(
        message="Votre email a ete verifie avec succes! Vous pouvez maintenant vous connecter.",
        success=True
    )


@router.post("/resend-verification", response_model=VerificationResponse)
async def resend_verification_email(
    request: ResendVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Renvoie un email de verification

    Args:
        request: Email de l'utilisateur
        db: Session de base de donnees

    Returns:
        Message de confirmation ou d'erreur

    Raises:
        HTTPException: Si l'utilisateur n'existe pas ou est deja verifie
    """
    logger.info("resend_verification_attempt", email=request.email)

    success, error_message, user = verification_service.resend_verification_email(
        db=db,
        email=request.email
    )

    if not success:
        logger.warning(
            "resend_verification_failed",
            email=request.email,
            error=error_message
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )

    # Generer l'URL de verification
    token = user.email_verification_token
    verification_url = verification_service.get_verification_url(token)

    # Envoyer l'email
    user_name = f"{user.first_name} {user.last_name}".strip() if user.first_name or user.last_name else None

    email_sent = email_service.send_verification_email(
        to_email=user.email,
        verification_url=verification_url,
        user_name=user_name
    )

    if not email_sent:
        logger.warning(
            "resend_verification_email_failed",
            user_id=user.user_id,
            email=user.email
        )
        # Note: On ne leve pas d'exception ici car le token a ete cree
        # L'utilisateur pourra reessayer plus tard

    logger.info(
        "resend_verification_success",
        user_id=user.user_id,
        email=user.email,
        email_sent=email_sent
    )

    return VerificationResponse(
        message="Un nouvel email de verification a ete envoye. Veuillez verifier votre boite de reception.",
        success=True
    )


@router.get("/check-status/{email}")
async def check_verification_status(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Verifie le statut de verification d'un email

    Args:
        email: Email a verifier
        db: Session de base de donnees

    Returns:
        Statut de verification

    Raises:
        HTTPException: Si l'utilisateur n'existe pas
    """
    from ...models.user import User

    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouve"
        )

    return {
        "email": user.email,
        "is_verified": user.is_verified,
        "verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
        "has_pending_verification": bool(user.email_verification_token)
    }
