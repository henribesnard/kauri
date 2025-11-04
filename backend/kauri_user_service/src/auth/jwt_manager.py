"""
Gestionnaire de tokens JWT
Génération, validation et révocation de tokens
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError
import uuid

from ..config import settings


class JWTManager:
    """Gestionnaire de tokens JWT"""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_hours = settings.jwt_expire_hours

    def create_access_token(
        self,
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """
        Crée un token JWT pour un utilisateur

        Args:
            user_id: ID de l'utilisateur
            email: Email de l'utilisateur
            expires_delta: Durée avant expiration (par défaut: settings.jwt_expire_hours)

        Returns:
            Dict contenant le token et les infos d'expiration
        """
        # Calculer expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.expire_hours)

        # Créer payload
        to_encode = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "exp": expire,  # Expiration
            "iat": datetime.utcnow(),  # Issued at
            "jti": str(uuid.uuid4()),  # JWT ID (unique)
            "type": "access"
        }

        # Encoder le token
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm
        )

        return {
            "access_token": encoded_jwt,
            "token_type": "bearer",
            "expires_in": int((expire - datetime.utcnow()).total_seconds()),
            "expires_at": expire.isoformat()
        }

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Décode et valide un token JWT

        Args:
            token: Token JWT à décoder

        Returns:
            Dict contenant les données du token

        Raises:
            InvalidTokenError: Si le token est invalide
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise InvalidTokenError("Token expiré")
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Token invalide: {str(e)}")

    def verify_token(self, token: str) -> bool:
        """
        Vérifie si un token est valide

        Args:
            token: Token JWT à vérifier

        Returns:
            True si valide, False sinon
        """
        try:
            self.decode_token(token)
            return True
        except InvalidTokenError:
            return False

    def get_user_from_token(self, token: str) -> Optional[Dict[str, str]]:
        """
        Extrait les informations utilisateur d'un token

        Args:
            token: Token JWT

        Returns:
            Dict avec user_id et email, ou None si invalide
        """
        try:
            payload = self.decode_token(token)
            return {
                "user_id": payload.get("sub"),
                "email": payload.get("email")
            }
        except InvalidTokenError:
            return None

    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """
        Récupère la date d'expiration d'un token

        Args:
            token: Token JWT

        Returns:
            Datetime d'expiration ou None si invalide
        """
        try:
            payload = self.decode_token(token)
            exp_timestamp = payload.get("exp")
            if exp_timestamp:
                return datetime.fromtimestamp(exp_timestamp)
            return None
        except InvalidTokenError:
            return None


# Singleton instance
jwt_manager = JWTManager()
