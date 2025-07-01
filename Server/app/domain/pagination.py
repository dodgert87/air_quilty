from typing import TypeVar, Generic, List, Type
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.sql import Select
from app.infrastructure.database.transaction import run_in_transaction
from app.utils.config import settings
from loguru import logger


T = TypeVar("T", bound=BaseModel)

class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model.

    Attributes:
        items (List[T]): List of returned items of type T.
        total (int): Total number of records (unpaginated).
        page (int): Current page number.
        page_size (int): Number of items per page.
    """
    items: List[T]
    total: int
    page: int
    page_size: int

    model_config = {
        "from_attributes": True  # Supports ORM or dict inputs
    }


async def paginate_query(
    base_query: Select,
    schema: Type[T],
    page: int = 1,
    page_size: int | None = None
) -> PaginatedResponse[T]:
    """
    Execute and paginate any SQLAlchemy query.

    Args:
        base_query (Select): A SQLAlchemy select query.
        schema (Type[T]): Pydantic model to validate and serialize each row.
        page (int): Page number (1-based).
        page_size (int | None): Number of items per page. Defaults to settings.DEFAULT_PAGE_SIZE.

    Returns:
        PaginatedResponse[T]: Paginated result set.
    """
    page_size = page_size or settings.DEFAULT_PAGE_SIZE
    col_count = len(base_query._raw_columns)

    try:
        async with run_in_transaction() as session:
            # ── Get total count ──
            count_q = select(func.count()).select_from(base_query.subquery())
            total = await session.scalar(count_q) or 0

            # ── Apply pagination ──
            paged = base_query.offset((page - 1) * page_size).limit(page_size)
            result = await session.execute(paged)

            # ── Deserialize results ──
            if col_count == 1:
                records = result.scalars().all()
                items = [schema.model_validate(r) for r in records]
            else:
                maps = result.mappings().all()
                items = [schema.model_validate(m) for m in maps]

            logger.info(
                "[PAGINATION] Queried page=%d page_size=%d total=%d returned=%d",
                page, page_size, total, len(items)
            )

            return PaginatedResponse[T](
                items=items,
                total=total,
                page=page,
                page_size=page_size
            )

    except Exception as e:
        logger.exception("[PAGINATION] Query failed | page=%d page_size=%d", page, page_size)
        raise
