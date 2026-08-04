import os
import time
import shutil
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.future import select
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.core.exceptions import setup_exception_handlers
from app.core.middleware import setup_middlewares
from app.core.security import get_password_hash
from app.core.logging_config import setup_production_logging
from app.core.config_validator import validate_config

START_TIME = time.time()


# Import routers
from app.modules.auth.routes import router as auth_router
from app.modules.users.routes import router as users_router
from app.modules.templates.routes import router as templates_router
from app.modules.templates.html_routes import admin_router as html_admin_router, public_router as html_public_router, spec_router as html_spec_router
from app.modules.templates.report_routes import report_router
from app.modules.documents.routes import router as documents_router
from app.modules.downloads.routes import router as downloads_router
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.ops.routes import router as ops_router



# Import models for seeding
from app.modules.users.model import User, Role, Permission
from app.modules.templates.model import DocumentTemplate, HtmlTemplate, AIConfiguration


async def async_startup_tasks():
    """Performs database migrations, user seeding, and AI service initialization asynchronously in the background."""
    logger_startup = logging.getLogger("app.startup")
    logger_startup.info("Starting background DB schema migration & seeding tasks...")

    # 1. Create tables & migrate columns
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
            for col_name, col_type in [
                ("template_version", "VARCHAR(50) DEFAULT '1.0.0'"),
                ("report_type", "VARCHAR(50) DEFAULT 'PSUR'"),
                ("generated_file_size", "INTEGER DEFAULT 0"),
                ("download_count", "INTEGER DEFAULT 0"),
                ("last_downloaded_at", "TIMESTAMP WITH TIME ZONE"),
                ("browser", "VARCHAR(255)"),
                ("ip_address", "VARCHAR(50)"),
                ("failed_reason", "VARCHAR(500)"),
                ("html_template_id", "UUID"),
                ("template_name", "VARCHAR(255)"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE generated_documents ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                except Exception:
                    pass
                    
            for col_name, col_type in [
                ("preview_image", "VARCHAR(255)"),
                ("status", "VARCHAR(20) DEFAULT 'Draft'"),
                ("required_files", "JSON"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE html_templates ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                except Exception:
                    pass

            for col_name, col_type in [
                ("llm_provider", "VARCHAR(50) DEFAULT 'openai'"),
            ]:
                try:
                    await conn.execute(text(f"ALTER TABLE ai_configurations ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                except Exception:
                    pass
    except Exception as e:
        logger_startup.warning(f"Background DB migration check error: {e}")

    # 2. Seed default roles, templates, user accounts, and AI configs
    try:
        async with SessionLocal() as db:
            # Sync Roles
            stmt_roles = select(Role)
            res_roles = await db.execute(stmt_roles)
            roles_dict = {r.name: r for r in res_roles.scalars().all()}
            
            if "Admin" not in roles_dict:
                roles_dict["Admin"] = Role(name="Admin", description="Administrator permissions")
                db.add(roles_dict["Admin"])
            if "User" not in roles_dict:
                roles_dict["User"] = Role(name="User", description="Standard user permissions")
                db.add(roles_dict["User"])
            await db.flush()

            # Sync Document Templates
            stmt_tpl = select(DocumentTemplate)
            res_tpl = await db.execute(stmt_tpl)
            tpls = res_tpl.scalars().all()
            if not tpls:
                psur_tpl = DocumentTemplate(
                    name="PSUR Event Summary",
                    description="Periodic safety update report event summaries compiler",
                    version="1.0.0",
                    required_files=["Event ID", "Severity", "Date"],
                    status="Active"
                )
                quant_tpl = DocumentTemplate(
                    name="Quantitative Method",
                    description="Z-Score safety methods indicators compiler",
                    version="2.1.0",
                    required_files=["Method ID", "Value", "Z-Score"],
                    status="Active"
                )
                pv_tpl = DocumentTemplate(
                    name="PV Auto Tool",
                    description="Automated signal detections PRR compiler",
                    version="1.0.0",
                    required_files=["ID", "AutoCode", "Priority"],
                    status="Active"
                )
                db.add_all([psur_tpl, quant_tpl, pv_tpl])
                await db.flush()
                tpls = [psur_tpl, quant_tpl, pv_tpl]

            # Sync Accounts (Password123!)
            pwd_hash = get_password_hash("Password123!")

            # Admin account
            stmt_admin = select(User).where(User.email == "admin@company.com")
            res_admin = await db.execute(stmt_admin)
            admin_user = res_admin.scalars().first()
            if not admin_user:
                admin_user = User(
                    name="Sarah Connor",
                    email="admin@company.com",
                    hashed_password=pwd_hash,
                    status="Active"
                )
                admin_user.roles.append(roles_dict["Admin"])
                if tpls:
                    admin_user.allowed_templates.extend(tpls)
                db.add(admin_user)
            else:
                admin_user.hashed_password = pwd_hash
                admin_user.status = "Active"

            # Standard User account
            stmt_user = select(User).where(User.email == "user@company.com")
            res_user = await db.execute(stmt_user)
            standard_user = res_user.scalars().first()
            if not standard_user:
                standard_user = User(
                    name="Alex Mercer",
                    email="user@company.com",
                    hashed_password=pwd_hash,
                    status="Active"
                )
                standard_user.roles.append(roles_dict["User"])
                if tpls:
                    standard_user.allowed_templates.extend(tpls[:2])
                db.add(standard_user)
            else:
                standard_user.hashed_password = pwd_hash
                standard_user.status = "Active"

            # Seed default HTML template if empty
            stmt_html = select(HtmlTemplate)
            res_html = await db.execute(stmt_html)
            html_tpls = res_html.scalars().all()
            if not html_tpls:
                os.makedirs(settings.TEMPLATES_DIR, exist_ok=True)
                app_dir = os.path.dirname(os.path.abspath(__file__))
                default_src = os.path.join(app_dir, "templates", "drafting_studio.html")
                default_dest = os.path.join(settings.TEMPLATES_DIR, "default_drafting_studio.html")
                if os.path.exists(default_src):
                    shutil.copy2(default_src, default_dest)
                    default_tpl = HtmlTemplate(
                        name="Default Drafting Studio",
                        version="1.0.0",
                        description="Standard bundled PV drafting studio template",
                        html_file=default_dest,
                        is_active=True,
                        is_deleted=False,
                        uploaded_by="system@company.com"
                    )
                    db.add(default_tpl)

            # Sync AI Configuration
            stmt_ai = select(AIConfiguration)
            res_ai = await db.execute(stmt_ai)
            ai_config = res_ai.scalars().first()
            if not ai_config:
                default_config = AIConfiguration(
                    embedding_model=settings.EMBEDDING_MODEL,
                    llm_provider=settings.LLM_PROVIDER,
                    similarity_threshold=settings.SIMILARITY_THRESHOLD,
                    llm_threshold=settings.LLM_THRESHOLD,
                    llm_model="gpt-4o" if settings.LLM_PROVIDER == "openai" else "gemini-1.5-flash" if settings.LLM_PROVIDER == "gemini" else "llama3" if settings.LLM_PROVIDER == "ollama" else "gpt-4"
                )
                db.add(default_config)
            else:
                ai_config.embedding_model = settings.EMBEDDING_MODEL
                ai_config.llm_provider = settings.LLM_PROVIDER
                ai_config.similarity_threshold = settings.SIMILARITY_THRESHOLD
                ai_config.llm_threshold = settings.LLM_THRESHOLD

            await db.commit()
            logger_startup.info("[SEEDER] Accounts, templates & AI config synchronized successfully.")
    except Exception as e:
        logger_startup.warning(f"[SEEDER] Background DB seeding warning: {e}")

    # 3. Redis service
    from app.core.redis_service import redis_service
    try:
        redis_service.initialize()
    except Exception as e:
        logger_startup.warning(f"Redis client initialization failed: {e}")

    # 4. ChromaDB service
    from app.modules.ai.vector_db.chroma_service import chroma_service
    try:
        chroma_service.initialize()
    except Exception as e:
        logger_startup.warning(f"ChromaDB initialization failed: {e}")

    # 5. Preload embedding model (if enabled)
    if getattr(settings, "PRELOAD_EMBEDDING_MODEL", False):
        from app.modules.ai.embeddings.embedding_service import embedding_service
        try:
            embedding_service.load_model()
        except Exception as e:
            logger_startup.warning(f"Embedding model preloading exception: {e}")

    # 6. LLM provider check
    from app.modules.ai.providers.llm_factory import llm_factory
    try:
        provider = llm_factory.get_provider()
        await provider.validate()
    except Exception as e:
        logger_startup.warning(f"LLM provider validation exception: {e}")

    # 7. Backup check
    from app.core.backup_validator import validate_backups
    try:
        validate_backups()
    except Exception as e:
        logger_startup.warning(f"Backup validation exception: {e}")

    # 8. Start worker threads
    from app.core.task_queue import start_worker
    try:
        start_worker()
    except Exception as e:
        logger_startup.warning(f"Task worker startup exception: {e}")


# Fast Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize logging
    setup_production_logging()
    logger_startup = logging.getLogger("app.startup")
    logger_startup.info("Starting PVAI Backend application lifecycle...")

    # 2. Fast config validation & storage check
    try:
        validate_config()
    except Exception as e:
        logger_startup.critical(f"Configuration validation failed: {e}")
        raise e

    required_folders = [
        "storage", "storage/uploads", "storage/templates", "storage/reports",
        "storage/logs", "storage/generated", "storage/generated/html", "storage/generated/pdf"
    ]
    if settings.CHROMA_DB_PATH:
        required_folders.append(settings.CHROMA_DB_PATH)
    for folder in required_folders:
        os.makedirs(folder, exist_ok=True)
    logger_startup.info("Storage directory structure verified.")

    # 3. Schedule heavy migrations & seeding as non-blocking background task
    asyncio.create_task(async_startup_tasks())

    logger_startup.info("FastAPI web server ready. Bound socket port now available.")
    yield

    # Shutdown logic
    from app.core.task_queue import stop_worker
    try:
        stop_worker()
    except Exception:
        pass
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan
)

# Setup core modules
setup_middlewares(app)
setup_exception_handlers(app)

# Register routes under v1 Prefix
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(templates_router, prefix=settings.API_V1_STR)
app.include_router(html_admin_router, prefix=settings.API_V1_STR)
app.include_router(html_public_router, prefix=settings.API_V1_STR)
app.include_router(html_spec_router, prefix="/api")
app.include_router(report_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(downloads_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(ops_router, prefix=settings.API_V1_STR)




@app.get("/health/live")
async def health_live():
    return {"status": "healthy"}


@app.get("/health/ready")
async def health_ready():
    # Check PostgreSQL connection
    db_status = "disconnected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass
        
    # Check Storage structure
    storage_status = "ready"
    required_folders = ["storage", "storage/uploads", "storage/templates", "storage/reports", "storage/logs"]
    for folder in required_folders:
        if not os.path.exists(folder):
            storage_status = "missing_folders"
            break
            
    is_ready = db_status == "connected" and storage_status == "ready"
    data = {
        "status": "healthy" if is_ready else "unhealthy",
        "database": {"status": db_status},
        "storage": {"status": storage_status}
    }
    
    if not is_ready:
        return JSONResponse(status_code=503, content=data)
    return data


@app.get("/health/full")
async def health_full():
    # 1. Check PostgreSQL Database connection
    db_status = "disconnected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass
        
    # 2. Check ChromaDB client status
    from app.modules.ai.vector_db.chroma_service import chroma_service
    chroma_status = "disconnected"
    collections_count = 0
    if chroma_service.is_connected():
        chroma_status = "ready"
        try:
            if chroma_service._client:
                collections_count = len(chroma_service._client.list_collections())
        except Exception:
            pass
            
    # 3. Check Embedding Model status
    from app.modules.ai.embeddings.embedding_service import embedding_service
    embedding_status = "not_loaded"
    if embedding_service.is_loaded():
        embedding_status = "loaded"
        
    # 4. Check LLM status
    from app.modules.ai.providers.llm_factory import llm_factory
    llm_status = "unavailable"
    provider = llm_factory.get_provider()
    try:
        if await provider.validate():
            llm_status = "available"
    except Exception:
        pass
        
    # 5. Validate storage folders
    storage_status = "ready"
    required_folders = [
        "storage",
        "storage/uploads",
        "storage/templates",
        "storage/reports",
        "storage/logs"
    ]
    for folder in required_folders:
        if not os.path.exists(folder):
            storage_status = "missing_folders"
            break
            
    # 6. Check background task worker status
    from app.core.task_queue import get_worker_status
    worker_info = get_worker_status()
    
    # Critical dependencies determine overall status
    is_healthy = (
        db_status == "connected" and
        storage_status == "ready"
    )
    
    health_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": {
            "status": db_status
        },
        "chromadb": {
            "status": chroma_status,
            "collections": collections_count
        },
        "embedding": {
            "status": embedding_status,
            "model": settings.EMBEDDING_MODEL
        },
        "llm": {
            "provider": settings.LLM_PROVIDER,
            "status": llm_status
        },
        "storage": {
            "status": storage_status
        },
        "worker": worker_info,
        "version": "1.0.0",
        "environment": settings.ENV,
        "uptime": round(time.time() - START_TIME, 2)
    }
    
    if not is_healthy:
        return JSONResponse(status_code=503, content=health_data)
    return health_data


@app.get("/health")
async def health_check():
    return await health_full()


@app.get("/metrics")
async def metrics_endpoint():
    from app.core.metrics import HAS_PROMETHEUS, get_system_metrics
    # Update current resource measurements
    await get_system_metrics()
    
    from fastapi import Response
    if HAS_PROMETHEUS:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    else:
        # Graceful fallback reporting mock metrics format
        mock_metrics = (
            "# HELP http_active_requests Current number of active requests being processed\n"
            "# TYPE http_active_requests gauge\n"
            "http_active_requests 0\n"
            "# HELP system_cpu_usage System CPU usage percentage\n"
            "# TYPE system_cpu_usage gauge\n"
            "system_cpu_usage 0.0\n"
        )
        return Response(content=mock_metrics, media_type="text/plain; version=0.0.4")
