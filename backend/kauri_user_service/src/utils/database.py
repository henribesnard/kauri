"""
Utilitaires pour la base de données
Connexion, sessions et dépendances FastAPI
"""
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import structlog

from ..config import settings
from ..models.user import Base

logger = structlog.get_logger()

# Créer engine SQLAlchemy
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log SQL queries en mode debug
    pool_pre_ping=True,  # Vérifier connexion avant utilisation
    pool_size=5,  # Nombre de connexions dans le pool
    max_overflow=10,  # Nombre max de connexions supplémentaires
)

# Créer SessionLocal class
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def init_db():
    """
    Initialise la base de données (crée les tables)
    À appeler au démarrage de l'application
    """
    try:
        logger.info("database_init_start")
        Base.metadata.create_all(bind=engine)
        logger.info("database_init_success", tables=list(Base.metadata.tables.keys()))
    except Exception as e:
        logger.error("database_init_failed", error=str(e), exc_info=True)
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Dépendance FastAPI pour obtenir une session de base de données

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users

    Yields:
        Session SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_connection() -> bool:
    """
    Vérifie la connexion à la base de données

    Returns:
        True si connexion OK, False sinon
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception as e:
        logger.error("database_connection_check_failed", error=str(e))
        return False
