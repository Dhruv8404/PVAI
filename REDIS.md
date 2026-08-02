# Redis Integration & HA Guide

This document describes the Redis setup, failover logic, and configurations implemented in **PVAI**.

---

## 1. Role of Redis in PVAI

Redis is integrated as an optional enterprise infrastructure layer used for:
1. **Distributed Caching:** Caching API responses, AI matched templates, embedding metadata, and heavy report queries.
2. **Rate Limiting Backend:** Storing sliding rate-limit buckets across multiple scaling nodes.
3. **Background Queue State:** Inter-thread or inter-process task message queuing (future broker support).

---

## 2. Environment Configurations

Define the following environment variables to configure the Redis client:

```ini
# Redis Connection parameters
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=secret_redis_pass  # Optional
REDIS_DB=0

# Caching Strategy
CACHE_TYPE=redis  # Options: memory, redis
CACHE_DEFAULT_TTL=300  # Default eviction: 5 minutes
```

---

## 3. High Availability & Graceful Fallback

The backend implements automatic connection probing and graceful degradation.

### Startup Isolation
* A `2.0 seconds` connection socket timeout is enforced during startup.
* If Redis is offline or unreachable, the application logs a warning and proceeds starting up:
  ```text
  [WARNING] Could not connect to Redis at localhost:6379. Graceful in-memory fallback will be used.
  ```

### Caching Fallback
* If `CACHE_TYPE=redis` but Redis goes offline during runtime, requests automatically fall back to the thread-safe `LocalMemoryCache` dictionary without throwing 500 errors to the client.
* Active monitoring metrics (`/metrics`) increment `cache_misses_total` for memory while reporting degraded status on `/api/v1/ops/diagnostics`.
