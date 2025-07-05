from fastapi import APIRouter, Depends, Request
from strawberry.fastapi import GraphQLRouter

from app.middleware.rate_limit_middleware import limiter
from app.utils.config import settings
from app.api.graphql.main_schema import (
    sensor_data_schema,
    sensor_meta_schema
)

router = APIRouter()

# ---------------------------------------------------------------------------
# helper → turns a SlowAPI limit-string into a FastAPI dependency
# ---------------------------------------------------------------------------
def build_limit_dep(limit_str: str, scope: str):
    """Return a dependency that enforces *only* `limit_str` for this route."""
    async def _gate(request: Request):
        return None

    _gate.__name__ = f"rl_{scope}"
    # override_defaults=True ensures *only* this limit applies
    return Depends(
        limiter.limit(limit_str, override_defaults=True)(_gate)
    )

# ========== sensor-data endpoint ===============================
data_router = GraphQLRouter(sensor_data_schema)
router.include_router(
    data_router,
    prefix="/sensor/data/graphql",
    dependencies=[build_limit_dep(settings.GRAPHQL_DATA_QUERY_LIMIT, scope="graphql-data")],

)

# ========== sensor-meta endpoint ==============================
meta_router = GraphQLRouter(sensor_meta_schema)
router.include_router(
    meta_router,
    prefix="/sensor/meta/graphql",
    dependencies=[build_limit_dep(settings.GRAPHQL_META_QUERY_LIMIT, scope="graphql-meta")],
)
