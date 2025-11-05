"""
Configuration management using Pydantic Settings
"""
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "KAURI OCR Service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # API
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8003

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 2
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_TTL: int = 604800  # 7 days
    REDIS_STATS_TTL: int = 3600    # 1 hour

    # RabbitMQ
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "kauri"
    RABBITMQ_PASSWORD: str
    RABBITMQ_VHOST: str = "/kauri"
    OCR_QUEUE_NAME: str = "ocr_processing"
    OCR_PRIORITY_QUEUE: str = "ocr_priority"
    OCR_RESULTS_QUEUE: str = "ocr_results"

    # MinIO/S3 Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "kauri-ocr"
    MINIO_SECURE: bool = False

    # OCR Configuration
    OCR_DEFAULT_ENGINE: str = "paddleocr"
    OCR_LANG: str = "fr,en"
    OCR_USE_ANGLE_CLS: bool = True
    OCR_USE_GPU: bool = False
    OCR_DET_MODEL_DIR: Optional[str] = None
    OCR_REC_MODEL_DIR: Optional[str] = None
    OCR_CLS_MODEL_DIR: Optional[str] = None

    # OCR Quality Thresholds
    OCR_MIN_CONFIDENCE: float = 0.6
    OCR_MIN_QUALITY_SCORE: float = 0.7
    OCR_REQUIRES_REVIEW_THRESHOLD: float = 0.8

    # Worker Configuration
    WORKER_CONCURRENCY: int = 4
    WORKER_PREFETCH_COUNT: int = 1
    WORKER_MAX_RETRIES: int = 3
    WORKER_RETRY_DELAY: int = 60  # seconds

    # Document Processing
    MAX_FILE_SIZE: int = 52428800  # 50MB
    ALLOWED_EXTENSIONS: str = "pdf,png,jpg,jpeg,tiff,bmp"
    MAX_PAGES_PER_DOCUMENT: int = 100
    IMAGE_MAX_DIMENSION: int = 4096

    # OHADA Validation
    OHADA_COUNTRIES: str = "BJ,BF,CI,GW,ML,NE,SN,TG,CM,CF,TD,CG,GQ,GA"
    DEFAULT_CURRENCY: str = "XOF"
    VAT_RATES: str = "0.18,0.19"

    # Rate Limiting
    RATE_LIMIT_PER_TENANT_PER_HOUR: int = 100
    RATE_LIMIT_PER_TENANT_PER_DAY: int = 1000

    # External Services
    DOCUMENT_MANAGEMENT_SERVICE_URL: str = "http://localhost:8001"
    ACCOUNTING_CORE_SERVICE_URL: str = "http://localhost:8002"
    NOTIFICATION_SERVICE_URL: str = "http://localhost:8005"

    # Security
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Monitoring
    PROMETHEUS_PORT: int = 9090
    SENTRY_DSN: Optional[str] = None

    # Feature Flags
    ENABLE_TABLE_DETECTION: bool = True
    ENABLE_SIGNATURE_DETECTION: bool = True
    ENABLE_HANDWRITING_DETECTION: bool = False
    ENABLE_LAYOUT_ANALYSIS: bool = True
    ENABLE_ENTITY_EXTRACTION: bool = True
    ENABLE_OHADA_VALIDATION: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    @property
    def ocr_languages(self) -> List[str]:
        """Get list of OCR languages"""
        return [lang.strip() for lang in self.OCR_LANG.split(",")]

    @property
    def allowed_extensions_list(self) -> List[str]:
        """Get list of allowed file extensions"""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def ohada_countries_list(self) -> List[str]:
        """Get list of OHADA countries"""
        return [country.strip() for country in self.OHADA_COUNTRIES.split(",")]

    @property
    def vat_rates_list(self) -> List[float]:
        """Get list of VAT rates"""
        return [float(rate.strip()) for rate in self.VAT_RATES.split(",")]

    @property
    def rabbitmq_url(self) -> str:
        """Get RabbitMQ connection URL"""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}{self.RABBITMQ_VHOST}"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# Global settings instance
settings = Settings()
