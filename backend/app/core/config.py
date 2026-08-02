import os
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, BeforeValidator, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


def parse_cors_origins(v: Union[str, List[str]]) -> List[str]:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Document Generation Platform"
    
    # Security keys (In production, load these from environment variables)
    SECRET_KEY: str = "7aef83b519c2f6d90d8a4362b2e8a1c97f6c3d9e8b7a6e5d4c3b2a10f9e8d7c6"
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    FRONTEND_URL: str = "http://localhost:5173"
    ENV: str = "development"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.JWT_SECRET if self.JWT_SECRET else self.SECRET_KEY

    
    CORS_ORIGINS: str = ""
    ALLOWED_HOSTS: Union[str, List[str]] = "*"
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and v:
            if v == "*":
                return ["*"]
            return [i.strip() for i in v.split(",") if i.strip()]
        return v


    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and v:
            return [i.strip() for i in v.split(",") if i.strip()]
        import os
        cors_env = os.getenv("CORS_ORIGINS", "")
        if cors_env:
            return [i.strip() for i in cors_env.split(",") if i.strip()]
        return v

    BACKEND_CORS_ORIGINS: Annotated[
        List[str], BeforeValidator(parse_cors_origins)
    ] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "https://pvai-olive.vercel.app"
    ]
    
    # PostgreSQL Configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "newpassword"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "docgen_db"
    
    DATABASE_URL: str = ""
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            import urllib.parse
            passwd = urllib.parse.quote_plus(self.REDIS_PASSWORD)
            return f"redis://:{passwd}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Cache Settings
    CACHE_TYPE: str = "memory" # memory or redis
    CACHE_DEFAULT_TTL: int = 300 # seconds

    # File Storage configurations
    STORAGE_TYPE: str = "cloudinary" # local or cloudinary
    CLOUDINARY_CLOUD_NAME: str = "mapopioz"
    CLOUDINARY_API_KEY: str = "576796838931328"
    CLOUDINARY_API_SECRET: str = "OnYrRfUEMmuQWrv0YCUQvBnkD7Y"
    UPLOAD_DIR: str = "storage/uploads"
    TEMPLATES_DIR: str = "storage/templates"
    GENERATED_HTML_DIR: str = "storage/generated/html"
    GENERATED_PDF_DIR: str = "storage/generated/pdf"
    
    # S3 configuration (future-ready)
    S3_BUCKET_NAME: str = "document-vault"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT_URL: str = ""

    # AI and Vector Database Settings
    CHROMA_DB_PATH: str = "storage/chromadb"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    LLM_PROVIDER: str = "omniroute"
    OMNIROUTE_API_KEY: str = ""
    OMNIROUTE_BASE_URL: str = ""
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    SIMILARITY_THRESHOLD: float = 0.90
    LLM_THRESHOLD: float = 0.70


settings = Settings()
