from typing import TypeVar, Generic, List
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.config import settings


T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int


async def paginate_query(
    base_query: Select,
    page: int = 1,
    page_size: int | None = None
) -> PaginatedResponse:
    """
    Execute a paginated query inside a transaction.
    Returns a standardized Pydantic PaginatedResponse.
    """
    async with run_in_transaction() as session:

        page_size = settings.DEFAULT_PAGE_SIZE

        # Total count query
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await session.scalar(count_query)

        # Paged data query
        result = await session.execute(
            base_query.offset((page - 1) * page_size).limit(page_size)
        )
        items = list(result.scalars().all())

        return PaginatedResponse(
            items=items,
            total=total or 0,
            page=page,
            page_size=page_size
        )
