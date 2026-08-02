import time
import uuid
import logging
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import settings
from app.core.request_context import request_id_var, user_id_var
from app.core.metrics import ACTIVE_REQUESTS, HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS, HAS_PROMETHEUS

# Setup request logger
logger = logging.getLogger("app_request_log")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Track active request gauge
        ACTIVE_REQUESTS.inc()
        try:
            # Process request
            response = await call_next(request)
        finally:
            ACTIVE_REQUESTS.dec()
        
        process_time = (time.time() - start_time) * 1000
        client_ip = request.client.host if request.client else "unknown"
        user_id = user_id_var.get()
        req_id = request_id_var.get()
        
        # Track active user metric
        if user_id:
            from app.core.metrics import record_active_user
            record_active_user(str(user_id))

        # Observe Content-Length response size
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                from app.core.metrics import HTTP_RESPONSE_SIZE_BYTES
                HTTP_RESPONSE_SIZE_BYTES.observe(int(content_length))
            except ValueError:
                pass
        
        # Update Prometheus metrics
        HTTP_REQUESTS_TOTAL.labels(method=request.method, endpoint=request.url.path, status=str(response.status_code)).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(method=request.method, endpoint=request.url.path).observe(process_time / 1000.0)

        # Attach request_details to record for JSONFormatter structured logging
        details = {
            "endpoint": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration_ms": round(process_time, 2),
            "client_ip": client_ip,
            "user_id": user_id,
            "request_id": req_id
        }
        
        # Log details (structured formatter will parse 'request_details')
        extra = {"request_details": details}
        logger.info(
            f"Client: {client_ip} | User: {user_id} | ReqID: {req_id} | Method: {request.method} | "
            f"Path: {request.url.path} | Status: {response.status_code} | Duration: {process_time:.2f}ms",
            extra=extra
        )
        
        # Add response time header
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        
        # Bind to ContextVar
        token = request_id_var.set(req_id)
        
        # Try to extract user email/ID from JWT early for request context logging
        try:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                jwt_token = auth_header.split(" ")[1]
                from app.core.security import decode_token
                payload = decode_token(jwt_token)
                user_email = payload.get("sub")
                if user_email:
                    user_id_var.set(user_email)
        except Exception:
            pass
            
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security response headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        
        # Environment-aware CSP directives
        is_prod = settings.ENV.lower() == "production"
        csp_connect = f"connect-src 'self' {settings.FRONTEND_URL} https://api.cloudinary.com https://res.cloudinary.com"
        if not is_prod:
            csp_connect += " http://localhost:* http://127.0.0.1:*"
            
        csp_directives = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob: https://res.cloudinary.com; "
            f"{csp_connect}; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp_directives
        return response


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_limit: int = 100, window_secs: int = 60):
        super().__init__(app)
        self.requests_limit = requests_limit
        self.window_secs = window_secs
        # Simple in-memory sliding token bucket: ip -> [tokens_float, last_updated_timestamp]
        self.buckets = defaultdict(lambda: [float(requests_limit), time.time()])

    async def dispatch(self, request: Request, call_next):
        # Client IP extraction
        client_ip = request.client.host if request.client else "unknown"
        
        # Exclude internal/system endpoints from rate limit tracking
        path = request.url.path
        if path.startswith("/health") or path == "/metrics":
            return await call_next(request)
            
        now = time.time()
        tokens, last_update = self.buckets[client_ip]
        
        # Token calculation
        elapsed = now - last_update
        refill_rate = self.requests_limit / self.window_secs
        new_tokens = min(float(self.requests_limit), tokens + elapsed * refill_rate)
        
        if new_tokens >= 1.0:
            self.buckets[client_ip] = [new_tokens - 1.0, now]
            response = await call_next(request)
            return response
        else:
            self.buckets[client_ip] = [new_tokens, now]
            logger.warning(f"[RATE LIMIT] Limit exceeded for client: {client_ip} on path: {path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."}
            )


def setup_middlewares(app: FastAPI) -> None:
    # 1. Request logging & tracking (Runs inner-most, measures exact route execution time)
    app.add_middleware(RequestLoggingMiddleware)
    
    # 2. Request Correlation IDs context registration
    app.add_middleware(RequestIDMiddleware)
    
    # 3. Inject Security Headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 4. Token Bucket Rate Limiter
    app.add_middleware(
        RateLimiterMiddleware,
        requests_limit=settings.RATE_LIMIT_REQUESTS,
        window_secs=settings.RATE_LIMIT_WINDOW
    )
    
    # 5. GZip Performance compression (compress response when size exceeds 1KB)
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)
    
    # 6. Restrict incoming HTTP Host headers (Runs near outer layer)
    # Parse allowed hosts (split list if ALLOWED_HOSTS is list/str)
    allowed = settings.ALLOWED_HOSTS
    if isinstance(allowed, str):
        allowed = [allowed]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed)

    # 7. Add CORS last (So it executes outer-most to handle preflights)
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS],
            allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://pvai-.*\.vercel\.app",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
