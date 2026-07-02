from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Async database engine setup
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800
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
