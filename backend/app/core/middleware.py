import time
import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings

# Setup standard logger
logger = logging.getLogger("app_request_log")
logging.basicConfig(level=logging.INFO)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        client_ip = request.client.host if request.client else "unknown"
        
        # Log details
        logger.info(
            f"Client: {client_ip} | Method: {request.method} | Path: {request.url.path} | "
            f"Status: {response.status_code} | Duration: {process_time:.2f}ms"
        )
        
        # Add response time header
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response


def setup_middlewares(app: FastAPI) -> None:
    # Add Logging Middleware first (so it gets wrapped by CORS and runs inner-most)
    app.add_middleware(RequestLoggingMiddleware)

    # Add CORS last (so it wraps all other middlewares and runs outer-most)
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS],
            allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://pvai-.*\.vercel\.app",
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
