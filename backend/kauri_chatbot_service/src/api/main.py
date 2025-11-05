"""
KAURI Chatbot Service - API Main
Point d'entrée FastAPI pour le service chatbot
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import time

from ..config import settings
from .routes import chat

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

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1")


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
    Basic health check endpoint pour Docker et monitoring
    """
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "environment": settings.kauri_env,
        "llm_provider": settings.llm_provider,
        "embedding_model": settings.embedding_model,
    }


@app.get("/api/v1/health/detailed", tags=["health"])
async def detailed_health_check():
    """
    Detailed health check - vérifie tous les composants RAG
    - ChromaDB (recherche sémantique)
    - BM25 (recherche lexicale)
    - Embedder
    - Reranker (cross-encoder)
    """
    from ..rag.vector_store.chroma_store import get_chroma_store
    from ..rag.retriever.bm25_retriever import get_bm25_retriever
    from ..rag.embedder.bge_embedder import get_embedder
    from ..rag.reranker.cross_encoder_reranker import get_reranker

    health_status = {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "healthy",
        "components": {}
    }

    # Test ChromaDB (Vector Search)
    try:
        chroma_store = get_chroma_store()
        doc_count = chroma_store.count()

        # Test a simple search
        embedder = get_embedder()
        test_embedding = embedder.embed_text("test")
        test_results = chroma_store.search(test_embedding, top_k=1)

        health_status["components"]["chromadb"] = {
            "status": "healthy",
            "document_count": doc_count,
            "search_test": "passed" if test_results else "no_results"
        }
    except Exception as e:
        health_status["components"]["chromadb"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Test BM25 (Lexical Search)
    try:
        bm25_retriever = get_bm25_retriever()

        if bm25_retriever.bm25 is None:
            health_status["components"]["bm25"] = {
                "status": "unhealthy",
                "error": "BM25 index not built"
            }
            health_status["status"] = "degraded"
        else:
            # Test search
            test_results = bm25_retriever.search("test", top_k=1)
            health_status["components"]["bm25"] = {
                "status": "healthy",
                "document_count": len(bm25_retriever.documents),
                "search_test": "passed" if test_results else "no_results"
            }
    except Exception as e:
        health_status["components"]["bm25"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Test Embedder (Semantic Search)
    try:
        embedder = get_embedder()
        test_embedding = embedder.embed_text("test comptabilité")

        health_status["components"]["embedder"] = {
            "status": "healthy",
            "model": settings.embedding_model,
            "embedding_dimension": len(test_embedding),
            "test": "passed"
        }
    except Exception as e:
        health_status["components"]["embedder"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Test Reranker (Cross-Encoder)
    try:
        reranker = get_reranker()

        # Test reranking with dummy data
        test_docs = [
            {"content": "test document 1", "score": 0.5},
            {"content": "test document 2", "score": 0.6}
        ]
        reranked = reranker.rerank("test query", test_docs, top_k=2)

        health_status["components"]["reranker"] = {
            "status": "healthy",
            "model": settings.reranker_model,
            "test": "passed" if reranked else "no_results"
        }
    except Exception as e:
        health_status["components"]["reranker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Test LLM Client
    try:
        from ..llm.llm_client import get_llm_client
        llm_client = get_llm_client()

        health_status["components"]["llm"] = {
            "status": "healthy",
            "primary_provider": settings.llm_provider,
            "primary_model": settings.llm_model,
            "fallback_provider": settings.llm_fallback_provider,
            "fallback_model": settings.llm_fallback_model
        }
    except Exception as e:
        health_status["components"]["llm"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    return health_status


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
    Initialise la base de données et warm-up des modèles
    """
    logger.info(
        "service_starting",
        service=settings.service_name,
        version=settings.service_version,
        environment=settings.kauri_env,
        port=settings.service_port,
        llm_provider=settings.llm_provider,
        embedding_model=settings.embedding_model,
    )

    # Warm-up ML models (lazy loading will trigger on first use)
    try:
        logger.info("warming_up_ml_models")
        from ..rag.embedder.bge_embedder import get_embedder
        from ..rag.reranker.cross_encoder_reranker import get_reranker

        # Get instances (will load models)
        embedder = get_embedder()
        reranker = get_reranker()

        # Warm-up with test queries
        _ = embedder.embed_text("test")
        logger.info("ml_models_warmed_up")
    except Exception as e:
        logger.warning("ml_model_warmup_error", error=str(e))

    # Rebuild BM25 index from ChromaDB at startup
    try:
        logger.info("rebuilding_bm25_index_from_chromadb")
        from ..rag.vector_store.chroma_store import get_chroma_store
        from ..rag.retriever.bm25_retriever import get_bm25_retriever

        chroma_store = get_chroma_store()
        bm25_retriever = get_bm25_retriever()

        # Get all documents from ChromaDB
        collection = chroma_store.collection
        all_data = collection.get()

        if all_data and all_data['documents']:
            # Build documents list for BM25
            documents = []
            for doc_id, content, metadata in zip(
                all_data['ids'],
                all_data['documents'],
                all_data['metadatas']
            ):
                documents.append({
                    "id": doc_id,
                    "content": content,
                    "metadata": metadata
                })

            # Build BM25 index
            bm25_retriever.build_index(documents)
            logger.info("bm25_index_rebuilt_at_startup", num_documents=len(documents))
        else:
            logger.warning("no_documents_in_chromadb_skipping_bm25_build")
    except Exception as e:
        logger.error("bm25_index_rebuild_error", error=str(e))


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
