"""
Shared test fixtures.

Strategy:
- Each test function gets a fresh SQLite file (tmp_path) to ensure isolation.
- The global engine/SessionLocal in app.database are monkey-patched to point at
  the test DB before the FastAPI lifespan runs (lifespan calls init_db which
  creates FTS5 tables and seeds settings).
- APScheduler start/stop are mocked so no background jobs fire during tests.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from unittest.mock import AsyncMock, patch

import app.database as db_module


@pytest_asyncio.fixture
async def client(tmp_path):
    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    test_engine = create_async_engine(db_url, echo=False)
    test_session = async_sessionmaker(test_engine, expire_on_commit=False)

    # Patch global engine + session BEFORE init_db runs
    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = test_session

    # Explicitly initialise the test DB — httpx's ASGITransport does not
    # trigger ASGI lifespan events, so we cannot rely on the FastAPI lifespan
    # to call init_db() for us.
    await db_module.init_db()

    with (
        patch("app.services.scheduler.start_scheduler", new_callable=AsyncMock),
        patch("app.services.scheduler.stop_scheduler", new_callable=AsyncMock),
    ):
        from app.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    # Restore originals
    db_module.engine = original_engine
    db_module.SessionLocal = original_session
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db(tmp_path):
    """Direct DB session for setting up test data without going through the API."""
    db_url = f"sqlite+aiosqlite:///{tmp_path}/direct.db"
    test_engine = create_async_engine(db_url, echo=False)
    test_session = async_sessionmaker(test_engine, expire_on_commit=False)

    original_engine = db_module.engine
    original_session = db_module.SessionLocal
    db_module.engine = test_engine
    db_module.SessionLocal = test_session

    await db_module.init_db()

    async with test_session() as session:
        yield session

    db_module.engine = original_engine
    db_module.SessionLocal = original_session
    await test_engine.dispose()
