"""
JWT Token Validator for Chatbot Service
Validates tokens from User Service
"""
from typing import Optional, Dict, Any
import httpx
import jwt as pyjwt
import structlog
from fastapi import Header, HTTPException, status

from ..config import settings

logger = structlog.get_logger()


class JWTValidator:
    """Validates JWT tokens and retrieves user info"""

    def __init__(self):
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.user_service_url = settings.user_service_url
        self.timeout = settings.user_service_timeout

    async def validate_token_with_user_service(self, token: str) -> Dict[str, Any]:
        """
        Validate token by calling User Service /me endpoint
        
        Args:
            token: JWT token string
            
        Returns:
            User information dict
            
        Raises:
            HTTPException: If token is invalid or user service is unreachable
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.user_service_url}/api/v1/auth/me",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    user_data = response.json()
                    logger.info("token_validated_via_user_service", user_id=user_data.get("user_id"))
                    return user_data
                elif response.status_code == 401:
                    logger.warning("token_validation_failed_unauthorized")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token invalide ou expiré",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    logger.error("token_validation_failed_unexpected", status_code=response.status_code)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Service d'authentification indisponible"
                    )
                    
        except httpx.TimeoutException:
            logger.error("user_service_timeout")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Timeout lors de la validation du token"
            )
        except httpx.RequestError as e:
            logger.error("user_service_request_error", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Erreur lors de la connexion au service utilisateur"
            )

    def decode_token_local(self, token: str) -> Dict[str, Any]:
        """
        Decode and verify token locally (faster but no revocation check)
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            payload = pyjwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except pyjwt.ExpiredSignatureError:
            logger.warning("token_expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except pyjwt.InvalidTokenError as e:
            logger.warning("token_invalid", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )


# Global instance
jwt_validator = JWTValidator()


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Dependency to get current user from JWT token
    
    Args:
        authorization: Authorization header (Bearer token)
        
    Returns:
        User information dict
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token manquant ou format invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    
    # Validate with User Service (checks revocation)
    user_data = await jwt_validator.validate_token_with_user_service(token)
    
    return user_data


async def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns None if no token provided
    
    Args:
        authorization: Authorization header (Bearer token)
        
    Returns:
        User information dict or None
    """
    if not authorization:
        return None
    
    try:
        return await get_current_user(authorization)
    except HTTPException:
        return None
