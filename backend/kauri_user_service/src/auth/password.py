"""
Utilitaires pour la gestion des mots de passe
Hashing et vérification avec bcrypt
"""
from passlib.context import CryptContext

# Contexte bcrypt avec configuration sécurisée
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Cost factor (plus élevé = plus sécurisé mais plus lent)
)


def hash_password(password: str) -> str:
    """
    Hash un mot de passe avec bcrypt

    Args:
        password: Mot de passe en clair

    Returns:
        Hash du mot de passe (format: $2b$12$...)
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Vérifie si un mot de passe correspond à son hash

    Args:
        plain_password: Mot de passe en clair
        hashed_password: Hash du mot de passe

    Returns:
        True si le mot de passe correspond, False sinon
    """
    return pwd_context.verify(plain_password, hashed_password)


def needs_update(hashed_password: str) -> bool:
    """
    Vérifie si un hash doit être mis à jour
    (si l'algorithme ou le cost factor a changé)

    Args:
        hashed_password: Hash du mot de passe

    Returns:
        True si le hash doit être régénéré
    """
    return pwd_context.needs_update(hashed_password)
