# Response Caching and TTL Architecture

This document describes the caching layers, invalidation methods, and eviction keys.

---

## 1. Cache Layer Specifications

We implement a dual-mode cache strategy:
1. **Redis Cache:** Distributed Key-Value store. Used when `CACHE_TYPE=redis` and the Redis client is online.
2. **Local Memory Cache:** Fast, concurrent thread-safe dictionary. Used as a fallback when Redis is unavailable.

---

## 2. Configured Cache Lifetimes (TTL)

| Target Cache Objects | Default TTL | Purpose |
|---|---|---|
| AI matched headers | 600 seconds | Speeds up dataset standardization mappings. |
| Embedding metadata | 3600 seconds | Avoids recalculating static embeddings. |
| Operational diagnostics | 15 seconds | Limits load on database from monitoring tools. |
| Rendered report drafts | 300 seconds | Speeds up repeat downloads from clients. |

---

## 3. Cache Invalidation Utilities

To invalidate cache entries:
* Call `cache_service.delete(key)` to clear a single key (e.g. invalidating matched headers when a new template field is added).
* Call `cache_service.clear()` to clear the entire cache store.
* Operational endpoints `/ops/diagnostics` expose stats (`cache`) detailing the hit and miss counts.
