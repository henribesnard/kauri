"""
Configuration du Chatbot Service
Charge les variables d'environnement avec héritage du .env racine
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuration du Chatbot Service avec héritage du .env racine"""

    # Service Info
    service_name: str = Field(default="kauri_chatbot_service", alias="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", alias="SERVICE_VERSION")
    service_port: int = Field(default=3202, alias="SERVICE_PORT")

    # Environment
    kauri_env: str = Field(default="development", alias="KAURI_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    # Database (PostgreSQL for conversations and messages)
    database_url: str = Field(alias="CHATBOT_DATABASE_URL")

    # Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str = Field(alias="REDIS_PASSWORD")
    redis_prefix: str = Field(default="chatbot_service", alias="REDIS_PREFIX")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")
    embedding_cache_ttl: int = Field(default=86400, alias="EMBEDDING_CACHE_TTL")

    # Vector Database
    vector_db_type: str = Field(default="chromadb", alias="VECTOR_DB_TYPE")
    vector_db_host: str = Field(default="chromadb", alias="VECTOR_DB_HOST")
    vector_db_port: int = Field(default=8000, alias="VECTOR_DB_PORT")

    # API Keys
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    deepseek_api_key: str = Field(alias="DEEPSEEK_API_KEY")

    # JWT (pour validation)
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")

    # Embeddings
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1024, alias="EMBEDDING_DIMENSION")
    embedding_device: str = Field(default="cpu", alias="EMBEDDING_DEVICE")
    embedding_batch_size: int = Field(default=8, alias="EMBEDDING_BATCH_SIZE")

    # LLM
    llm_provider: str = Field(default="deepseek", alias="LLM_PROVIDER")
    llm_model: str = Field(default="deepseek-chat", alias="LLM_MODEL")
    llm_fallback_provider: str = Field(default="openai", alias="LLM_FALLBACK_PROVIDER")
    llm_fallback_model: str = Field(default="gpt-4o-mini", alias="LLM_FALLBACK_MODEL")
    llm_temperature: float = Field(default=0.1, alias="LLM_TEMPERATURE")  # Déterministe pour réponses cohérentes
    llm_max_tokens: int = Field(default=2500, alias="LLM_MAX_TOKENS")  # Réponses complètes et structurées

    # Intent Classification
    intent_classifier_temperature: float = Field(default=0.0, alias="INTENT_CLASSIFIER_TEMPERATURE")  # Déterministe pour classification
    intent_classifier_max_tokens: int = Field(default=500, alias="INTENT_CLASSIFIER_MAX_TOKENS")  # Classification + réponse directe si nécessaire

    # RAG Configuration
    rag_top_k: int = Field(default=10, alias="RAG_TOP_K")
    rag_rerank_top_k: int = Field(default=5, alias="RAG_RERANK_TOP_K")
    reranker_model: str = Field(default="BAAI/bge-reranker-base", alias="RERANKER_MODEL")

    # BM25 Configuration
    bm25_k1: float = Field(default=1.5, alias="BM25_K1")  # BM25 term frequency saturation parameter
    bm25_b: float = Field(default=0.75, alias="BM25_B")  # BM25 length normalization parameter

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=10, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")

    # User Service Integration
    user_service_url: str = Field(default="http://kauri_user_service:3201", alias="USER_SERVICE_URL")
    user_service_timeout: int = Field(default=5, alias="USER_SERVICE_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API Documentation
    api_title: str = Field(default="KAURI Chatbot Service API", alias="API_TITLE")
    api_description: str = Field(
        default="Service de chatbot RAG expert en comptabilité OHADA",
        alias="API_DESCRIPTION"
    )
    docs_url: str = Field(default="/api/v1/docs", alias="DOCS_URL")
    openapi_url: str = Field(default="/api/v1/openapi.json", alias="OPENAPI_URL")

    class Config:
        # Cherche d'abord dans .env.local (pour dev local), puis .env du service, puis .env racine
        env_file = [".env.local", ".env", "../.env", "../../.env"]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore les variables non définies


# Singleton instance
settings = Settings()
