"""
Service de gestion des tokens de verification email
"""
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog
from sqlalchemy.orm import Session

from ..models.user import User
from ..config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class VerificationService:
    """Service pour gerer les tokens de verification d'email"""

    TOKEN_LENGTH = 32  # Longueur du token en bytes (64 caracteres hex)
    TOKEN_VALIDITY_HOURS = 24  # Validite du token en heures

    @staticmethod
    def generate_verification_token() -> str:
        """
        Genere un token de verification securise

        Returns:
            Token de verification (hex string)
        """
        return secrets.token_urlsafe(VerificationService.TOKEN_LENGTH)

    @staticmethod
    def create_verification_token(db: Session, user: User) -> str:
        """
        Cree et stocke un nouveau token de verification pour un utilisateur

        Args:
            db: Session de base de donnees
            user: Utilisateur pour lequel creer le token

        Returns:
            Le token de verification genere
        """
        token = VerificationService.generate_verification_token()
        expires_at = datetime.utcnow() + timedelta(
            hours=VerificationService.TOKEN_VALIDITY_HOURS
        )

        user.email_verification_token = token
        user.email_verification_token_expires = expires_at
        user.is_verified = False

        db.commit()

        logger.info(
            "verification_token_created",
            user_id=user.user_id,
            email=user.email,
            expires_at=expires_at.isoformat()
        )

        return token

    @staticmethod
    def get_verification_url(token: str) -> str:
        """
        Construit l'URL complete de verification

        Args:
            token: Token de verification

        Returns:
            URL complete de verification
        """
        frontend_url = settings.frontend_url.rstrip('/')
        return f"{frontend_url}/verify-email?token={token}"

    @staticmethod
    def verify_email_token(
        db: Session,
        token: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """
        Verifie un token de verification d'email

        Args:
            db: Session de base de donnees
            token: Token de verification

        Returns:
            Tuple (success, error_message, user)
            - success: True si la verification a reussi
            - error_message: Message d'erreur si la verification a echoue
            - user: L'utilisateur verifie (None si echec)
        """
        # Chercher l'utilisateur avec ce token
        user = db.query(User).filter(
            User.email_verification_token == token
        ).first()

        if not user:
            logger.warning("verification_token_not_found", token=token[:10] + "...")
            return False, "Token de verification invalide", None

        # Verifier si le token a expire
        if user.email_verification_token_expires < datetime.utcnow():
            logger.warning(
                "verification_token_expired",
                user_id=user.user_id,
                email=user.email,
                expired_at=user.email_verification_token_expires.isoformat()
            )
            return False, "Le lien de verification a expire. Veuillez demander un nouveau lien.", None

        # Marquer l'email comme verifie
        user.is_verified = True
        user.email_verified_at = datetime.utcnow()
        user.email_verification_token = None
        user.email_verification_token_expires = None

        db.commit()

        logger.info(
            "email_verified_successfully",
            user_id=user.user_id,
            email=user.email
        )

        return True, None, user

    @staticmethod
    def resend_verification_email(
        db: Session,
        email: str
    ) -> Tuple[bool, Optional[str], Optional[User]]:
        """
        Renvoie un email de verification

        Args:
            db: Session de base de donnees
            email: Email de l'utilisateur

        Returns:
            Tuple (success, error_message, user)
        """
        # Chercher l'utilisateur
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.warning("resend_verification_user_not_found", email=email)
            return False, "Utilisateur non trouve", None

        # Verifier si l'email est deja verifie
        if user.is_verified:
            logger.info("resend_verification_already_verified", email=email)
            return False, "Cet email est deja verifie", None

        # Generer un nouveau token
        token = VerificationService.create_verification_token(db, user)

        logger.info(
            "verification_email_resent",
            user_id=user.user_id,
            email=user.email
        )

        return True, None, user


# Instance globale du service
verification_service = VerificationService()
