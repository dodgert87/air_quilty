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
    page_size = page_size or settings.DEFAULT_PAGE_SIZE

    # figure out how many columns the SELECT will produce
    # SQLAlchemy keeps the raw ColumnElements in _raw_columns
    col_count = len(base_query._raw_columns)

    async with run_in_transaction() as session:
        # 1) Total count
        count_q = select(func.count()).select_from(base_query.subquery())
        total = await session.scalar(count_q) or 0

        # 2) Paged
        paged = base_query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(paged)

        if col_count == 1:
            # single-column (could be ORM entity or a simple scalar)
            records = result.scalars().all()
            items = [schema.model_validate(r) for r in records]
        else:
            # multi-column → get a list of dicts
            maps = result.mappings().all()
            items = [schema.model_validate(m) for m in maps]

        return PaginatedResponse[T](
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
