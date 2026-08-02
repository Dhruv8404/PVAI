# Production Security Configuration & Hardening

This document outlines the security controls, policies, and hardening configurations implemented for the **PVAI** backend.

---

## 1. API Protection & Middlewares

### TrustedHostMiddleware
Restricts incoming requests to explicitly configured Host header values to prevent HTTP Host Header Poisoning attacks.
* **Settings Key:** `ALLOWED_HOSTS`
* **Default:** `*` (Override with specific production domains, e.g. `api.pvai.com,pvai-backend.onrender.com`).

### Rate Limiting
Endpoints are protected from brute-force and Denial-of-Service (DoS) abuse via an in-memory sliding token bucket algorithm.
* **Settings Keys:** `RATE_LIMIT_REQUESTS=100`, `RATE_LIMIT_WINDOW=60` (100 requests per minute).
* Bypasses internal endpoints like `/health` and `/metrics` to prevent monitoring scrapers from getting blocked.
* Returns `HTTP 429 Too Many Requests` on breach.

### Security Response Headers Middleware
Injects modern security headers to enforce browser-side isolation policies:

| Header | Value | Purpose |
|---|---|---|
| `X-Frame-Options` | `DENY` | Prevents Clickjacking attacks (stops rendering inside frames/iframes). |
| `X-Content-Type-Options` | `nosniff` | Disables MIME type sniffing, forcing stylesheet and script MIME matching. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limits referrer leakage during cross-origin navigations. |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=()` | Blocks access to physical hardware sensors. |
| `Content-Security-Policy` | Curated Directives | Limits source origins of script, style, media, connect, and image requests. |

---

## 2. Request Identification & Audit Correlation

Every HTTP transaction generates a unique UUID `X-Request-ID` correlation token.
* Propagated automatically through request-response headers.
* Bound to execution context variables (`contextvars`), ensuring all application logs, database queries, and system errors record the request correlation key.
* Used to trace exceptions from client-side errors directly to server log lines.

---

## 3. Structured Secrets Scrubbing

Application logs use a structured JSON layout, passing through regex-based string redact filters.
* Redacts:
  * HTTP Bearer authorization tokens (`Authorization: Bearer [REDACTED]`).
  * API Keys (`api_key=[REDACTED]`, `GEMINI_API_KEY`, `OPENAI_API_KEY`).
  * User credentials (`password=[REDACTED]`).
  * Internal Settings secrets (`SECRET_KEY`, `JWT_SECRET`).
