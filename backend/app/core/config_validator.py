import os
import logging
from app.core.config import settings

logger = logging.getLogger("app.startup")

DEFAULT_SECRET_KEY = "7aef83b519c2f6d90d8a4362b2e8a1c97f6c3d9e8b7a6e5d4c3b2a10f9e8d7c6"


def validate_config():
    """Validates configuration parameters at application startup.
    
    Fails startup on critical dependencies (DB, Security Keys).
    Logs warnings on optional/AI services if missing or offline.
    """
    logger.info("Validating application environment configuration...")
    
    critical_errors = []
    warnings = []
    
    # 1. CRITICAL: Verify Database Connection String
    if not settings.ASYNC_DATABASE_URL or "postgresql" not in settings.ASYNC_DATABASE_URL:
        critical_errors.append("DATABASE_URL is not set or is not a valid PostgreSQL connection string.")
        
    # 2. CRITICAL: Security Keys & Algorithms
    # If in production, ensure the secret key is NOT the default one
    is_prod = settings.ENV.lower() == "production"
    
    if not settings.SECRET_KEY:
        critical_errors.append("SECRET_KEY must be configured.")
    elif is_prod and settings.SECRET_KEY == DEFAULT_SECRET_KEY:
        critical_errors.append("SECRET_KEY must be changed from the default value in production.")
        
    if not settings.JWT_ALGORITHM:
        critical_errors.append("JWT_ALGORITHM must be configured.")
        
    # Check if there are any critical errors. If so, raise an exception to halt startup
    if critical_errors:
        error_msg = "Application startup aborted due to critical configuration errors:\n" + "\n".join(f"- {err}" for err in critical_errors)
        logger.critical(error_msg)
        raise ValueError(error_msg)
        
    # 3. OPTIONAL: Cloudinary configuration
    if settings.STORAGE_TYPE == "cloudinary":
        missing_cloudinary = []
        if not settings.CLOUDINARY_CLOUD_NAME:
            missing_cloudinary.append("CLOUDINARY_CLOUD_NAME")
        if not settings.CLOUDINARY_API_KEY:
            missing_cloudinary.append("CLOUDINARY_API_KEY")
        if not settings.CLOUDINARY_API_SECRET:
            missing_cloudinary.append("CLOUDINARY_API_SECRET")
            
        if missing_cloudinary:
            warnings.append(f"Cloudinary media storage is enabled, but the following settings are missing: {', '.join(missing_cloudinary)}")
            
    # 4. OPTIONAL: LLM Provider selection and keys
    supported_providers = ["omniroute", "openai", "gemini", "ollama", "deepseek"]
    if not settings.LLM_PROVIDER:
        warnings.append(f"LLM_PROVIDER is not configured. Supported values: {supported_providers}")
    elif settings.LLM_PROVIDER.lower() not in supported_providers:
        warnings.append(f"LLM_PROVIDER '{settings.LLM_PROVIDER}' is not supported. Supported values: {supported_providers}")
    else:
        provider = settings.LLM_PROVIDER.lower()
        if provider == "omniroute" and not settings.OMNIROUTE_API_KEY:
            warnings.append("LLM_PROVIDER is 'omniroute' but OMNIROUTE_API_KEY is not configured.")
        elif provider == "openai" and not (settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")):
            warnings.append("LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not configured.")
        elif provider == "gemini" and not (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")):
            warnings.append("LLM_PROVIDER is 'gemini' but GEMINI_API_KEY is not configured.")
        elif provider == "deepseek" and not (settings.DEEPSEEK_API_KEY or os.getenv("DEEPSEEK_API_KEY")):
            warnings.append("LLM_PROVIDER is 'deepseek' but DEEPSEEK_API_KEY is not configured.")
            
    # 5. OPTIONAL: Embedding model
    if not settings.EMBEDDING_MODEL:
        warnings.append("EMBEDDING_MODEL is not configured.")

    # 6. OPTIONAL: Redis & Cache Configs
    if settings.CACHE_TYPE == "redis":
        if not settings.REDIS_HOST:
            warnings.append("CACHE_TYPE is 'redis' but REDIS_HOST is missing.")
        if not settings.REDIS_PORT:
            warnings.append("CACHE_TYPE is 'redis' but REDIS_PORT is missing.")
            
    # 7. OPTIONAL: Storage provider S3/Azure checking
    if settings.STORAGE_TYPE.lower() == "s3":
        if not settings.S3_BUCKET_NAME:
            warnings.append("STORAGE_TYPE is 's3' but S3_BUCKET_NAME is missing.")
            
    # 8. OPTIONAL: Background Queue & Workers validation
    from app.core import task_queue
    if not hasattr(task_queue, "MAX_CONCURRENT_WORKERS") or task_queue.MAX_CONCURRENT_WORKERS <= 0:
        warnings.append("Worker configuration MAX_CONCURRENT_WORKERS is invalid or missing.")
        
    # 9. OPTIONAL: Metrics library loading validation
    from app.core.metrics import HAS_PROMETHEUS
    if not HAS_PROMETHEUS:
        warnings.append("Prometheus Client library ('prometheus-client') is missing. Exporter will run in degraded mock format.")
        
    # Log warnings
    for warn in warnings:
        logger.warning(f"[CONFIG WARNING] {warn}")
        
    logger.info("Configuration validation check completed successfully.")
