import os
import re
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, UTC
from app.core.config import settings
from app.core.request_context import request_id_var, user_id_var

logger = logging.getLogger("app.startup")

# Pre-compiled regex patterns to redact sensitive credentials
REDACT_PATTERNS = [
    (re.compile(r"(bearer\s+)[a-zA-Z0-9_\-\.\+/=]+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(api[-_]key\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-\.\+/=]+(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"(password\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-\.\+/=]+(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"(secret\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-\.\+/=]+(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\2"),
    (re.compile(r"(token\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-\.\+/=]+(['\"]?)", re.IGNORECASE), r"\1[REDACTED]\2")
]


class JSONFormatter(logging.Formatter):
    def __init__(self, secrets=None):
        super().__init__()
        # Filter out empty strings or short dummy values
        self.secrets = [s for s in (secrets or []) if s and len(s) > 4]

    def scrub_text(self, text: str) -> str:
        if not isinstance(text, str):
            return text
            
        # 1. Apply regex pattern-based redactions
        for pattern, replacement in REDACT_PATTERNS:
            text = pattern.sub(replacement, text)
            
        # 2. Apply literal settings secrets scrubbing
        for secret in self.secrets:
            text = text.replace(secret, "[REDACTED]")
            
        return text

    def format(self, record):
        req_id = request_id_var.get()
        user_id = user_id_var.get()
        
        # Scrub message string
        message = record.getMessage()
        message = self.scrub_text(message)
        
        # Compile base JSON structure
        log_data = {
            "timestamp": datetime.now(UTC).isoformat() + "Z",
            "level": record.levelname,
            "request_id": req_id,
            "user_id": user_id,
            "logger": record.name,
            "message": message,
            "service": "pvai-backend",
            "environment": settings.ENV
        }
        
        # If record contains request details from RequestLoggingMiddleware
        if hasattr(record, "request_details"):
            details = record.request_details
            log_data.update({
                "endpoint": details.get("endpoint", "-"),
                "status_code": details.get("status_code", 0),
                "duration_ms": details.get("duration_ms", 0.0),
                "method": details.get("method", "-")
            })
        else:
            log_data.update({
                "endpoint": "-",
                "status_code": 0,
                "duration_ms": 0.0
            })
            
        return json.dumps(log_data)


def setup_production_logging():
    """Configures structured JSON logging writing to separated Rotating File Handlers."""
    log_dir = "storage/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # File paths
    app_log_path = os.path.join(log_dir, "application.log")
    ai_log_path = os.path.join(log_dir, "ai.log")
    error_log_path = os.path.join(log_dir, "error.log")
    startup_log_path = os.path.join(log_dir, "startup.log")
    request_log_path = os.path.join(log_dir, "request.log")
    
    # 5MB per file, max 5 backup files
    max_bytes = 5 * 1024 * 1024
    backup_count = 5
    
    # Secrets to scrub
    secrets = [
        getattr(settings, "SECRET_KEY", ""),
        getattr(settings, "JWT_SECRET", ""),
        getattr(settings, "OMNIROUTE_API_KEY", ""),
        getattr(settings, "OPENAI_API_KEY", ""),
        getattr(settings, "GEMINI_API_KEY", ""),
        getattr(settings, "DEEPSEEK_API_KEY", ""),
        getattr(settings, "CLOUDINARY_API_SECRET", ""),
        getattr(settings, "POSTGRES_PASSWORD", "")
    ]
    
    # Instantiate the JSON Formatter
    json_formatter = JSONFormatter(secrets=secrets)
    
    # 1. Error Handler (Global ERROR level)
    error_handler = RotatingFileHandler(error_log_path, maxBytes=max_bytes, backupCount=backup_count)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    
    # 2. Application Handler (Root logger)
    app_handler = RotatingFileHandler(app_log_path, maxBytes=max_bytes, backupCount=backup_count)
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(json_formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Remove existing handlers to avoid duplicates during test runs
    root_logger.handlers = []
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
    
    # 3. AI Log Handler
    ai_handler = RotatingFileHandler(ai_log_path, maxBytes=max_bytes, backupCount=backup_count)
    ai_handler.setLevel(logging.INFO)
    ai_handler.setFormatter(json_formatter)
    
    ai_logger = logging.getLogger("app.ai")
    ai_logger.setLevel(logging.INFO)
    ai_logger.propagate = False
    ai_logger.handlers = []
    ai_logger.addHandler(ai_handler)
    ai_logger.addHandler(error_handler)
    
    # 4. Startup Log Handler
    startup_handler = RotatingFileHandler(startup_log_path, maxBytes=max_bytes, backupCount=backup_count)
    startup_handler.setLevel(logging.INFO)
    startup_handler.setFormatter(json_formatter)
    
    startup_logger = logging.getLogger("app.startup")
    startup_logger.setLevel(logging.INFO)
    startup_logger.propagate = False
    startup_logger.handlers = []
    startup_logger.addHandler(startup_handler)
    startup_logger.addHandler(error_handler)
    
    # 5. Request Log Handler
    request_handler = RotatingFileHandler(request_log_path, maxBytes=max_bytes, backupCount=backup_count)
    request_handler.setLevel(logging.INFO)
    request_handler.setFormatter(json_formatter)
    
    request_logger = logging.getLogger("app_request_log")
    request_logger.setLevel(logging.INFO)
    request_logger.propagate = False
    request_logger.handlers = []
    request_logger.addHandler(request_handler)
    request_logger.addHandler(error_handler)
    
    # Console Stream Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(json_formatter)
    
    root_logger.addHandler(console_handler)
    ai_logger.addHandler(console_handler)
    startup_logger.addHandler(console_handler)
    request_logger.addHandler(console_handler)
    
    startup_logger.info("Logging infrastructure configured to use structured JSON formatter.")
