"""
SRIBEESonline FastAPI Backend - Database Configuration

Async PostgreSQL connection using SQLAlchemy 2.0 with asyncpg.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.utils.logger import logger

# Create async engine
engine = create_async_engine(
    settings.async_database_url,
    echo=settings.database_echo,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,  # Enable connection health checks
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for declarative models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: Database session for the request

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions outside of request context.

    Usage:
        async with get_db_context() as db:
            result = await db.execute(query)
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection, create all tables,
    and seed a default super admin user if not already present.
    """
    try:
        # Import all models to ensure they are registered with SQLAlchemy Base metadata
        import app.models  # noqa

        async with engine.begin() as conn:
            # Test connection using text() for raw SQL
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))

            # Create all tables if they do not exist
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ PostgreSQL connected and tables initialized successfully")

        # Seed default super admin user if not present
        async with get_db_context() as db:
            from uuid import uuid4

            from sqlalchemy import select

            from app.core.security import hash_password
            from app.models.admin import Admin, AdminRole

            # Check if superadmin already exists
            email = "superadmin@freshcart.lk"
            result = await db.execute(select(Admin).where(Admin.email == email))
            existing_admin = result.scalar_one_or_none()

            if not existing_admin:
                logger.info("Seeding default super admin user...")
                super_admin = Admin(
                    admin_id=uuid4(),
                    email=email,
                    password_hash=hash_password("Admin@123"),
                    full_name="Super Admin",
                    role=AdminRole.SUPER_ADMIN,
                    is_active=True
                )
                db.add(super_admin)
                await db.commit()
                logger.info("✅ Default super admin seeded successfully!")

    except Exception as e:
        logger.error(f"❌ PostgreSQL connection/initialization failed: {e}")
        raise


async def close_db() -> None:
    """
    Close database connections.

    Called during application shutdown.
    """
    await engine.dispose()
    logger.info("PostgreSQL connections closed")


# For testing - use NullPool to avoid connection issues
def get_test_engine():
    """Create a test engine with NullPool for testing."""
    return create_async_engine(
        settings.async_database_url,
        echo=True,
        poolclass=NullPool,
    )
