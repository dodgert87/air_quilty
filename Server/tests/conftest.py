
import asyncio
import sys
import pytest
from app.infrastructure.database.init_db import init_db


@pytest.fixture(scope="session", autouse=True)
def initialize_test_db():
    """Ensure tables are created before tests run."""
    asyncio.run(init_db()) # type: ignore

@pytest.fixture(scope="session", autouse=True)
def _set_selector_event_loop_policy():
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())