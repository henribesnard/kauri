"""
Configuration du User Service
Charge les variables d'environnement avec héritage du .env racine
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuration du User Service avec héritage du .env racine"""

    # Service Info
    service_name: str = Field(default="kauri_user_service", alias="SERVICE_NAME")
    service_version: str = Field(default="1.0.0", alias="SERVICE_VERSION")
    service_port: int = Field(default=8001, alias="SERVICE_PORT")

    # Environment
    kauri_env: str = Field(default="development", alias="KAURI_ENV")
    debug: bool = Field(default=True, alias="DEBUG")

    # Database
    database_url: str = Field(alias="DATABASE_URL")

    # Redis
    redis_host: str = Field(default="redis", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str = Field(alias="REDIS_PASSWORD")
    redis_prefix: str = Field(default="user_service", alias="REDIS_PREFIX")
    cache_ttl: int = Field(default=3600, alias="CACHE_TTL")

    # JWT
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=24, alias="JWT_EXPIRE_HOURS")

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, alias="RATE_LIMIT_PERIOD")

    # Password Policy
    password_min_length: int = Field(default=8, alias="PASSWORD_MIN_LENGTH")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # API Documentation
    api_title: str = Field(default="KAURI User Service API", alias="API_TITLE")
    api_description: str = Field(
        default="Service de gestion des utilisateurs pour KAURI ERP",
        alias="API_DESCRIPTION"
    )
    docs_url: str = Field(default="/api/v1/docs", alias="DOCS_URL")
    openapi_url: str = Field(default="/api/v1/openapi.json", alias="OPENAPI_URL")

    class Config:
        # Cherche d'abord dans .env du service, puis dans .env racine
        env_file = [".env", "../.env", "../../.env"]
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore les variables non définies dans le schéma


# Singleton instance
settings = Settings()
