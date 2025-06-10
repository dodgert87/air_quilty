from typing import TypeVar, Generic, List, Type
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.config import settings

T = TypeVar("T", bound=BaseModel)

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int

    model_config = {
        "from_attributes": True
    }

async def paginate_query(
    base_query: Select,
    schema: Type[T],
    page: int = 1,
    page_size: int | None = None
) -> PaginatedResponse[T]:
    """
    Execute a paginated query inside a transaction.
    Returns a standardized Pydantic PaginatedResponse with serialized items.
    """
    page_size = page_size or settings.DEFAULT_PAGE_SIZE

    async with run_in_transaction() as session:
        # Total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total = await session.scalar(count_query)

        # Paged query
        result = await session.execute(
            base_query.offset((page - 1) * page_size).limit(page_size)
        )
        records = result.scalars().all()
        items = [schema.model_validate(r) for r in records]

        return PaginatedResponse[T](
            items=items,
            total=total or 0,
            page=page,
            page_size=page_size
        )
