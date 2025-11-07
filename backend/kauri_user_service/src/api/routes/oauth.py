"""
Routes OAuth pour authentification avec providers externes
/api/v1/oauth/*
"""
from datetime import datetime
import uuid
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from itsdangerous import URLSafeTimedSerializer, BadSignature
import structlog

from ...config import settings
from ...models.user import User
from ...schemas.user import TokenResponse, UserLoginResponse
from ...auth.jwt_manager import jwt_manager
from ...auth.oauth_manager import oauth, get_user_info_from_provider, is_provider_configured
from ...utils.database import get_db

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1/oauth", tags=["oauth"])

# Serializer pour state token (protection CSRF)
state_serializer = URLSafeTimedSerializer(settings.oauth_state_secret)


# ============================================
# Helper Functions
# ============================================

def generate_state_token() -> str:
    """Générer un token state pour protection CSRF"""
    return state_serializer.dumps(str(uuid.uuid4()))


def verify_state_token(token: str, max_age: int = 600) -> bool:
    """
    Vérifier un token state

    Args:
        token: Token à vérifier
        max_age: Durée de validité en secondes (défaut: 10 minutes)

    Returns:
        True si valide, False sinon
    """
    try:
        state_serializer.loads(token, max_age=max_age)
        return True
    except BadSignature:
        return False


async def get_or_create_oauth_user(
    db: Session,
    provider: str,
    user_info: dict
) -> Optional[User]:
    """
    Récupérer ou créer un utilisateur OAuth

    Args:
        db: Session de base de données
        provider: Nom du provider
        user_info: Informations utilisateur du provider

    Returns:
        User object ou None
    """
    provider_id = user_info.get('provider_id')
    email = user_info.get('email')

    if not provider_id:
        logger.error("oauth_missing_provider_id", provider=provider)
        return None

    # Chercher utilisateur par provider_id
    provider_field = f"{provider}_id"
    user = db.query(User).filter(getattr(User, provider_field) == provider_id).first()

    if user:
        # Utilisateur existant - mettre à jour last_login
        user.last_login = datetime.utcnow()
        # Mettre à jour l'avatar si disponible
        if user_info.get('avatar_url'):
            user.avatar_url = user_info['avatar_url']
        db.commit()
        db.refresh(user)
        logger.info("oauth_user_login", user_id=user.user_id, provider=provider)
        return user

    # Nouvel utilisateur OAuth
    # Si email existe déjà, lier le compte OAuth au compte existant
    if email:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            # Lier le compte OAuth au compte existant
            setattr(existing_user, provider_field, provider_id)
            existing_user.last_login = datetime.utcnow()
            if user_info.get('avatar_url') and not existing_user.avatar_url:
                existing_user.avatar_url = user_info['avatar_url']
            db.commit()
            db.refresh(existing_user)
            logger.info(
                "oauth_account_linked",
                user_id=existing_user.user_id,
                provider=provider
            )
            return existing_user

    # Créer un nouvel utilisateur
    user_id = str(uuid.uuid4())

    # Twitter ne fournit pas l'email - générer un email temporaire
    if not email:
        email = f"{provider}_{provider_id}@kauri-oauth.local"
        logger.warning("oauth_no_email_provided", provider=provider, user_id=user_id)

    new_user = User(
        user_id=user_id,
        email=email,
        password_hash=None,  # Pas de password pour OAuth
        first_name=user_info.get('first_name'),
        last_name=user_info.get('last_name'),
        avatar_url=user_info.get('avatar_url'),
        is_active=True,
        is_verified=user_info.get('email_verified', True),  # OAuth emails are verified
        is_superuser=False,
        oauth_provider=provider,
    )

    # Définir le provider_id
    setattr(new_user, provider_field, provider_id)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("oauth_user_created", user_id=user_id, provider=provider, email=email)
    return new_user


# ============================================
# Endpoints
# ============================================

@router.get("/providers")
async def get_available_providers():
    """
    Liste des providers OAuth disponibles et configurés
    """
    providers = {
        'google': is_provider_configured('google'),
        'facebook': is_provider_configured('facebook'),
        'linkedin': is_provider_configured('linkedin'),
        'twitter': is_provider_configured('twitter'),
    }

    return {
        'providers': providers,
        'enabled_providers': [name for name, enabled in providers.items() if enabled]
    }


@router.get("/login/{provider}")
async def oauth_login(provider: str, request: Request):
    """
    Initier le flux OAuth avec un provider

    Args:
        provider: Nom du provider (google, facebook, linkedin, twitter)
    """
    # Vérifier si provider est supporté et configuré
    if provider not in ['google', 'facebook', 'linkedin', 'twitter']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Provider non supporté: {provider}"
        )

    if not is_provider_configured(provider):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider non configuré: {provider}"
        )

    # Générer state token pour protection CSRF
    state = generate_state_token()

    # URL de callback - utiliser backend_url explicite
    redirect_uri = f"{settings.backend_url}/api/v1/oauth/callback/{provider}"

    logger.info("oauth_login_initiated", provider=provider, redirect_uri=redirect_uri)

    # Rediriger vers le provider OAuth
    oauth_client = getattr(oauth, provider)
    return await oauth_client.authorize_redirect(request, redirect_uri, state=state)


@router.get("/callback/{provider}")
async def oauth_callback(provider: str, request: Request, db: Session = Depends(get_db)):
    """
    Callback OAuth - Recevoir le code d'autorisation et créer/connecter l'utilisateur

    Args:
        provider: Nom du provider
        request: Request FastAPI
        db: Session de base de données
    """
    logger.info("oauth_callback_received", provider=provider)

    # Vérifier si provider est supporté
    if provider not in ['google', 'facebook', 'linkedin', 'twitter']:
        logger.error("oauth_callback_invalid_provider", provider=provider)
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=invalid_provider",
            status_code=status.HTTP_302_FOUND
        )

    # Vérifier state token (protection CSRF)
    state = request.query_params.get('state')
    if not state or not verify_state_token(state):
        logger.error("oauth_callback_invalid_state", provider=provider)
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=invalid_state",
            status_code=status.HTTP_302_FOUND
        )

    try:
        # Échanger le code contre un token
        oauth_client = getattr(oauth, provider)
        token = await oauth_client.authorize_access_token(request)

        if not token:
            logger.error("oauth_callback_no_token", provider=provider)
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=no_token",
                status_code=status.HTTP_302_FOUND
            )

        # Récupérer les informations utilisateur
        user_info = await get_user_info_from_provider(provider, token)

        if not user_info:
            logger.error("oauth_callback_no_user_info", provider=provider)
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=no_user_info",
                status_code=status.HTTP_302_FOUND
            )

        # Créer ou récupérer l'utilisateur
        user = await get_or_create_oauth_user(db, provider, user_info)

        if not user:
            logger.error("oauth_callback_user_creation_failed", provider=provider)
            return RedirectResponse(
                url=f"{settings.frontend_url}/login?error=user_creation_failed",
                status_code=status.HTTP_302_FOUND
            )

        # Créer JWT token
        token_data = jwt_manager.create_access_token(
            user_id=user.user_id,
            email=user.email
        )

        # Rediriger vers le frontend avec le token
        redirect_url = (
            f"{settings.frontend_url}/oauth/callback"
            f"?token={token_data['access_token']}"
            f"&expires_in={token_data['expires_in']}"
        )

        logger.info("oauth_callback_success", provider=provider, user_id=user.user_id)

        return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)

    except Exception as e:
        logger.error(
            "oauth_callback_exception",
            provider=provider,
            error=str(e),
            exc_info=True
        )
        return RedirectResponse(
            url=f"{settings.frontend_url}/login?error=oauth_failed",
            status_code=status.HTTP_302_FOUND
        )
