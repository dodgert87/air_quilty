
import asyncio
import sys
import pytest
import pytest_asyncio
from app.infrastructure.database.init_db import init_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_db():
    await init_db()

@pytest.fixture(scope="session", autouse=True)
def _set_selector_event_loop_policy():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())