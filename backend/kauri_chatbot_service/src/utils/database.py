"""
Database utilities for Chatbot Service
"""
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import structlog

from ..config import settings
from ..models.document import Base

logger = structlog.get_logger()

# Create engine with connection pooling
engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    poolclass=QueuePool
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database - create all tables"""
    logger.info("database_init_start")
    try:
        Base.metadata.create_all(bind=engine)
        
        # Log created tables
        tables = [table.name for table in Base.metadata.sorted_tables]
        logger.info("database_init_success", tables=tables)
    except Exception as e:
        logger.error("database_init_failed", error=str(e), exc_info=True)
        raise


def check_db_connection() -> bool:
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("database_connection_check_failed", error=str(e))
        return False


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
