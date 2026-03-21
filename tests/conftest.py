from __future__ import annotations

import pytest_asyncio

from backend.database.db import reset_database


@pytest_asyncio.fixture(autouse=True)
async def _reset_postgres_state() -> None:
    await reset_database()
    yield
