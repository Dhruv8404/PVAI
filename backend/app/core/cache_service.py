import json
import time
import logging
from typing import Any, Optional, Dict
from app.core.config import settings
from app.core.redis_service import redis_service
from app.core.metrics import (
    HAS_PROMETHEUS,
    CACHE_HITS,
    CACHE_MISSES
)

logger = logging.getLogger("app.ai")


class LocalMemoryCache:
    """In-memory fallback cache utilizing a thread-safe local dictionary."""
    
    def __init__(self):
        # key -> (value_json, expiry_timestamp)
        self._store: Dict[str, tuple] = {}
        self._lock = asyncio_lock_compatible_lock()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        if key in self._store:
            val_json, expiry = self._store[key]
            if expiry > now:
                CACHE_HITS.labels(cache_type="memory").inc()
                return json.loads(val_json)
            else:
                # Evict expired key
                del self._store[key]
        CACHE_MISSES.labels(cache_type="memory").inc()
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else settings.CACHE_DEFAULT_TTL
        expiry = time.time() + duration
        self._store[key] = (json.dumps(value), expiry)

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def clear(self) -> None:
        self._store.clear()


class RedisCache:
    """Distributed response cache utilizing the active Redis service."""
    
    def __init__(self):
        pass

    def _get_client(self):
        return redis_service.get_client()

    def get(self, key: str) -> Optional[Any]:
        client = self._get_client()
        if not client:
            return None
        try:
            val = client.get(key)
            if val is not None:
                CACHE_HITS.labels(cache_type="redis").inc()
                return json.loads(val)
        except Exception as e:
            logger.warning(f"[CACHE] Redis get exception: {e}")
        CACHE_MISSES.labels(cache_type="redis").inc()
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        client = self._get_client()
        if not client:
            return
        duration = ttl if ttl is not None else settings.CACHE_DEFAULT_TTL
        try:
            client.set(key, json.dumps(value), ex=duration)
        except Exception as e:
            logger.warning(f"[CACHE] Redis set exception: {e}")

    def delete(self, key: str) -> None:
        client = self._get_client()
        if not client:
            return
        try:
            client.delete(key)
        except Exception as e:
            logger.warning(f"[CACHE] Redis delete exception: {e}")

    def clear(self) -> None:
        client = self._get_client()
        if not client:
            return
        try:
            # Flushes current DB
            client.flushdb()
        except Exception as e:
            logger.warning(f"[CACHE] Redis flushdb exception: {e}")


def asyncio_lock_compatible_lock():
    import threading
    return threading.Lock()


class CacheService:
    """Delegates cache requests to either Redis or Local Memory providers.
    
    Acts as a unified cache interface, degrading to in-memory on connection loss.
    """
    
    def __init__(self):
        self._local_cache = LocalMemoryCache()
        self._redis_cache = RedisCache()

    def _get_active_provider(self):
        # Env driven selection. Defaults to local if Redis is offline
        use_redis = settings.CACHE_TYPE.lower() == "redis"
        if use_redis and redis_service.is_online():
            return self._redis_cache
        return self._local_cache

    def get(self, key: str) -> Optional[Any]:
        """Retrieves an object from cache by key. Returns None on cache miss."""
        return self._get_active_provider().get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Saves an object to cache, associated with a key and specific TTL (secs)."""
        self._get_active_provider().set(key, value, ttl)

    def delete(self, key: str) -> None:
        """Evicts an object from the cache by key."""
        self._get_active_provider().delete(key)

    def clear(self) -> None:
        """Clears all entries inside the active cache database."""
        self._get_active_provider().clear()

    def get_stats(self) -> dict:
        """Returns statistics on active caching providers."""
        use_redis = settings.CACHE_TYPE.lower() == "redis"
        active = "redis" if (use_redis and redis_service.is_online()) else "memory"
        return {
            "configured_type": settings.CACHE_TYPE,
            "active_type": active,
            "redis_online": redis_service.is_online()
        }


# Global cache service manager singleton
cache_service = CacheService()
