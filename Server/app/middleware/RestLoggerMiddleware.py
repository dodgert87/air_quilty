from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.constants.domain_const import  DOMAIN_ROUTE_MAP, LogDomain, infer_domain
from app.utils.logger_utils import log_rest
from app.infrastructure.database.transaction import run_in_transaction
from time import time


class RestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.start_time = time()

        # --- capture body & query params early ---
        body_bytes = await request.body()
        request.state.raw_body = body_bytes              # bytes, cached

        response: Response | None = None
        error_msg: str | None = None

        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error_msg = getattr(request.state, "_log_error_msg", error_msg)
            raise
        finally:
            try:
                async with run_in_transaction() as session:
                    await log_rest(
                        request=request,
                        response=response or Response(status_code=500),
                        db_session=session,
                        domain=infer_domain(request.url.path),
                        user_id=getattr(request.state, "user_id", None),
                        start_time=request.state.start_time,
                        error_message=getattr(request.state, "_log_error_msg", error_msg),
                    )
            except Exception:
                pass
