from fastapi import APIRouter, Depends, Request, Response
from strawberry.fastapi import GraphQLRouter
from app.api.graphql.main_schema import schema # type: ignore
from app.middleware.rate_limit_middleware import limiter

from app.utils.config import settings

graphql_router = GraphQLRouter(schema)
router = APIRouter()

# --- real dependency -------------------------------------------------
async def _graphql_rate_limit(request: Request) -> None:  # param name MUST be "request"
    return None

graphql_rate_limit_dep = Depends(
    limiter
    .shared_limit(settings.GRAPHQL_DATA_QUERY_LIMIT, scope="graphql")
    (_graphql_rate_limit)
)
# --------------------------------------------------------------------

router.include_router(
    graphql_router,
    prefix="/sensor/data/graphql",
    dependencies=[graphql_rate_limit_dep],   # apply limit to every GraphQL call
)