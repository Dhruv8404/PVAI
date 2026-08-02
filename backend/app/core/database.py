from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

import time
import logging
from sqlalchemy import event
from app.core.metrics import DB_QUERIES_TOTAL, DB_QUERY_DURATION_SECONDS

db_logger = logging.getLogger("app.request")

# Async database engine setup with statement command timeout (30 seconds)
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"command_timeout": 30.0}
)

# Slow Query Monitoring and Prometheus Metrics collection via SQLAlchemy events
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    if hasattr(context, "_query_start_time"):
        total_time = time.time() - context._query_start_time
        # Track query count and latency
        DB_QUERIES_TOTAL.inc()
        DB_QUERY_DURATION_SECONDS.observe(total_time)
        
        # Log queries exceeding 500ms threshold
        if total_time > 0.5:
            db_logger.warning(
                f"[SLOW QUERY] Latency: {total_time:.2f}s | Statement: {statement} | Params: {parameters}"
            )


# Async session maker
SessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)


# Modern SQLAlchemy 2.0 Declarative base
class Base(DeclarativeBase):
    pass


# Async session yield dependency helper
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
