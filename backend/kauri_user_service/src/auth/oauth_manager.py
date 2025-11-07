"""
OAuth Manager avec Authlib
Gestion centralisée de l'authentification OAuth pour Google, Facebook, LinkedIn, Twitter
"""
from typing import Optional, Dict, Any
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import structlog

from ..config import settings

logger = structlog.get_logger()

# Configuration OAuth
config = Config(environ={
    "GOOGLE_CLIENT_ID": settings.google_client_id,
    "GOOGLE_CLIENT_SECRET": settings.google_client_secret,
    "FACEBOOK_CLIENT_ID": settings.facebook_client_id,
    "FACEBOOK_CLIENT_SECRET": settings.facebook_client_secret,
    "LINKEDIN_CLIENT_ID": settings.linkedin_client_id,
    "LINKEDIN_CLIENT_SECRET": settings.linkedin_client_secret,
    "TWITTER_CLIENT_ID": settings.twitter_client_id,
    "TWITTER_CLIENT_SECRET": settings.twitter_client_secret,
})

# Instance OAuth
oauth = OAuth(config)


# ============================================
# Configuration des Providers
# ============================================

# Google OAuth 2.0
oauth.register(
    name='google',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Facebook OAuth 2.0
oauth.register(
    name='facebook',
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    api_base_url='https://graph.facebook.com/',
    client_kwargs={
        'scope': 'email public_profile'
    }
)

# LinkedIn OAuth 2.0
oauth.register(
    name='linkedin',
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    api_base_url='https://api.linkedin.com/v2/',
    client_kwargs={
        'scope': 'openid profile email'
    }
)

# Twitter OAuth 2.0 (nouvelle API OAuth 2.0 avec PKCE)
oauth.register(
    name='twitter',
    api_base_url='https://api.twitter.com/2/',
    access_token_url='https://api.twitter.com/2/oauth2/token',
    authorize_url='https://twitter.com/i/oauth2/authorize',
    client_kwargs={
        'scope': 'tweet.read users.read',
        'code_challenge_method': 'S256'  # PKCE
    }
)


# ============================================
# Helper Functions
# ============================================

def get_oauth_client(provider: str):
    """
    Récupérer le client OAuth pour un provider donné

    Args:
        provider: Nom du provider ('google', 'facebook', 'linkedin', 'twitter')

    Returns:
        OAuth client configuré

    Raises:
        ValueError: Si le provider n'est pas supporté
    """
    if provider not in ['google', 'facebook', 'linkedin', 'twitter']:
        raise ValueError(f"Provider OAuth non supporté: {provider}")

    return getattr(oauth, provider)


async def get_user_info_from_provider(provider: str, token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Récupérer les informations utilisateur depuis le provider OAuth

    Args:
        provider: Nom du provider
        token: Token OAuth reçu

    Returns:
        Dictionnaire avec les informations utilisateur normalisées
    """
    try:
        client = get_oauth_client(provider)

        if provider == 'google':
            # Google utilise OpenID Connect - userinfo endpoint
            resp = await client.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            resp.raise_for_status()
            profile = resp.json()

            return {
                'provider_id': profile.get('sub'),
                'email': profile.get('email'),
                'first_name': profile.get('given_name'),
                'last_name': profile.get('family_name'),
                'avatar_url': profile.get('picture'),
                'email_verified': profile.get('email_verified', False)
            }

        elif provider == 'facebook':
            # Facebook Graph API
            resp = await client.get(
                'me?fields=id,email,first_name,last_name,picture.width(200).height(200)',
                token=token
            )
            resp.raise_for_status()
            profile = resp.json()

            return {
                'provider_id': profile.get('id'),
                'email': profile.get('email'),
                'first_name': profile.get('first_name'),
                'last_name': profile.get('last_name'),
                'avatar_url': profile.get('picture', {}).get('data', {}).get('url'),
                'email_verified': True  # Facebook vérifie toujours les emails
            }

        elif provider == 'linkedin':
            # LinkedIn API v2
            # Récupérer le profil
            profile_resp = await client.get('me', token=token)
            profile_resp.raise_for_status()
            profile = profile_resp.json()

            # Récupérer l'email
            email_resp = await client.get(
                'emailAddress?q=members&projection=(elements*(handle~))',
                token=token
            )
            email_resp.raise_for_status()
            email_data = email_resp.json()

            email = None
            if 'elements' in email_data and len(email_data['elements']) > 0:
                email = email_data['elements'][0].get('handle~', {}).get('emailAddress')

            first_name = profile.get('localizedFirstName')
            last_name = profile.get('localizedLastName')

            # Photo de profil
            avatar_url = None
            if 'profilePicture' in profile:
                display_image = profile['profilePicture'].get('displayImage~')
                if display_image and 'elements' in display_image and len(display_image['elements']) > 0:
                    avatar_url = display_image['elements'][0].get('identifiers', [{}])[0].get('identifier')

            return {
                'provider_id': profile.get('id'),
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'avatar_url': avatar_url,
                'email_verified': True
            }

        elif provider == 'twitter':
            # Twitter API v2
            resp = await client.get(
                'users/me?user.fields=profile_image_url',
                token=token
            )
            resp.raise_for_status()
            data = resp.json()
            user = data.get('data', {})

            # Twitter ne donne pas l'email par défaut, il faut une permission spéciale
            # On utilise le username comme identifiant
            return {
                'provider_id': user.get('id'),
                'email': None,  # Twitter ne fournit pas l'email par défaut
                'first_name': user.get('name', '').split()[0] if user.get('name') else None,
                'last_name': ' '.join(user.get('name', '').split()[1:]) if user.get('name') and len(user.get('name', '').split()) > 1 else None,
                'avatar_url': user.get('profile_image_url'),
                'email_verified': False
            }

    except Exception as e:
        logger.error(
            "oauth_get_user_info_failed",
            provider=provider,
            error=str(e),
            exc_info=True
        )
        return None


def is_provider_configured(provider: str) -> bool:
    """
    Vérifier si un provider OAuth est configuré

    Args:
        provider: Nom du provider

    Returns:
        True si configuré, False sinon
    """
    if provider == 'google':
        return bool(settings.google_client_id and settings.google_client_secret)
    elif provider == 'facebook':
        return bool(settings.facebook_client_id and settings.facebook_client_secret)
    elif provider == 'linkedin':
        return bool(settings.linkedin_client_id and settings.linkedin_client_secret)
    elif provider == 'twitter':
        return bool(settings.twitter_client_id and settings.twitter_client_secret)
    return False
