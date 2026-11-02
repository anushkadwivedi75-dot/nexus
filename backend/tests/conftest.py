import asyncio
import os
import sys
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure backend root is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis_pool
from app.main import app

test_engine = create_async_engine(settings.async_database_url, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture(autouse=True)
async def reset_redis_pool():
    """Disconnects pooled Redis connections between tests to avoid closed-loop socket reuse."""
    try:
        await redis_pool.disconnect()
    except Exception:
        pass
    yield
    try:
        await redis_pool.disconnect()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    """Provides an isolated database session for direct service-level tests."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncClient:
    """Provides an AsyncClient for testing FastAPI endpoints with fresh per-request sessions."""
    async def override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
