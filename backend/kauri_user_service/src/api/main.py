"""
KAURI User Service - API Main
Point d'entrée FastAPI pour le service utilisateur
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import structlog
import time

from ..config import settings
from ..utils.database import init_db, check_db_connection
from .routes import auth, oauth, verification

# Configure structured logging
logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.service_version,
    docs_url=settings.docs_url,
    openapi_url=settings.openapi_url,
)

# Session Middleware (required for OAuth)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.oauth_state_secret,
    session_cookie="kauri_session",
    max_age=3600,  # 1 hour
    same_site="lax",
    https_only=False,  # Set to True in production with HTTPS
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(oauth.router)
app.include_router(verification.router)


# Middleware pour logging des requêtes
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log toutes les requêtes avec timing"""
    start_time = time.time()

    # Log requête
    logger.info(
        "request_received",
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
    )

    # Traiter la requête
    response = await call_next(request)

    # Calculer durée
    duration = time.time() - start_time

    # Log réponse
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
    )

    return response


# ====================
# Health Check Endpoint
# ====================
@app.get("/api/v1/health", tags=["health"])
async def health_check():
    """
    Health check endpoint pour Docker et monitoring
    """
    db_ok = check_db_connection()

    return {
        "status": "healthy" if db_ok else "degraded",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.kauri_env,
        "database": "connected" if db_ok else "disconnected",
    }


# ====================
# Root Endpoint
# ====================
@app.get("/", tags=["root"])
async def root():
    """
    Endpoint racine avec informations du service
    """
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "online",
        "docs": settings.docs_url,
        "openapi": settings.openapi_url,
    }


# ====================
# Startup Event
# ====================
@app.on_event("startup")
async def startup_event():
    """
    Événement au démarrage de l'application
    """
    logger.info(
        "service_starting",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.kauri_env,
        port=settings.service_port,
    )

    # Initialiser la base de données
    try:
        init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e), exc_info=True)


# ====================
# Shutdown Event
# ====================
@app.on_event("shutdown")
async def shutdown_event():
    """
    Événement à l'arrêt de l'application
    """
    logger.info(
        "service_stopping",
        service=settings.service_name,
    )


# ====================
# Exception Handlers
# ====================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handler global pour toutes les exceptions non gérées
    """
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred" if not settings.debug else str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
