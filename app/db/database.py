"""
Database connection and session management.
Uses Supabase PostgreSQL when DATABASE_URL is configured, otherwise SQLite.
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


def _async_database_url(url: str) -> str:
    """Convert a standard PostgreSQL URL into SQLAlchemy's asyncpg URL."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


if settings.database_url:
    DATABASE_URL = _async_database_url(settings.database_url)
else:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{settings.database_path}"

engine_options = {
    "echo": settings.debug,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL,
    **engine_options,
)

# Session factory for creating database sessions
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


async def get_db() -> AsyncSession:
    """
    Dependency that provides a database session.
    Automatically closes the session after the request.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """
    Initialize database: create tables.
    Call this on application startup.
    """
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections.
    Call this on application shutdown.
    """
    await engine.dispose()
