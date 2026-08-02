import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("app.startup")


class RedisService:
    """Manages the Redis client connection pool.
    
    Provides graceful fallbacks if Redis is unavailable or unconfigured.
    """
    
    def __init__(self):
        self._client = None
        self._online = False

    def initialize(self):
        """Attempts connection to Redis. Degrades gracefully on failure."""
        logger.info("Initializing Redis service client connection...")
        try:
            import redis
            # Create redis connection pool
            url = settings.REDIS_URL
            logger.info(f"Connecting to Redis at: {settings.REDIS_HOST}:{settings.REDIS_PORT} (DB: {settings.REDIS_DB})")
            
            # 2s connection timeout to avoid hanging startup if Redis is down
            self._client = redis.Redis.from_url(
                url,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
                decode_responses=True
            )
            
            # Ping to verify active connection
            self._client.ping()
            self._online = True
            logger.info("Redis client connected and pinged successfully.")
        except ImportError:
            logger.warning("Redis python package is not installed. Running in degraded mode (No Redis support).")
            self._client = None
            self._online = False
        except Exception as e:
            logger.warning(
                f"Could not connect to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}. "
                f"Error: {e}. Graceful in-memory fallback will be used."
            )
            self._client = None
            self._online = False

    def is_online(self) -> bool:
        """Returns True if the Redis service is online and verified."""
        return self._online and self._client is not None

    def get_client(self):
        """Returns the raw redis client instance, or None if offline."""
        return self._client


# Global Redis service manager singleton
redis_service = RedisService()
