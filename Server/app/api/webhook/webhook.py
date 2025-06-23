from typing import List
from fastapi import APIRouter, Request, status
from app.models.schemas.webhook.webhook_schema import (
    WebhookCreate, WebhookDeletePayload, WebhookRead, WebhookUpdatePayload
)
from app.domain.webhooks.webhook_logic import (
    get_user_webhooks, get_allowed_events_for_role,
    create_webhook, delete_webhook, update_webhook
)
from app.middleware.rate_limit_middleware import limiter
from app.utils.config import settings

router = APIRouter(
    prefix="/auth/webhooks",
    tags=["Webhooks"]
)

# ──────────────── Query Endpoints ───────────── #

@router.get("/", response_model=List[WebhookRead])
@limiter.limit(settings.WEBHOOK_QUERY_RATE_LIMIT)
async def get_user_webhooks_route(request: Request):
    """
    List all active webhooks registered by the authenticated user.
    """
    return await get_user_webhooks(request.state.user_id)


@router.get("/allowed-events", response_model=List[str])
@limiter.limit(settings.WEBHOOK_QUERY_RATE_LIMIT)
async def get_allowed_webhook_events_route(request: Request):
    """
    Return a list of webhook event types the current user's role is allowed to subscribe to.
    """
    return await get_allowed_events_for_role(request.state.user.role)


# ──────────────── Mutation Endpoints ───────────── #

@router.post("/", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.WEBHOOK_WRITE_RATE_LIMIT)
async def create_webhook_route(payload: WebhookCreate, request: Request):
    """
    Register a new webhook with event type, target URL, and custom headers.
    """
    return await create_webhook(
        user_id=request.state.user.id,
        user_role=request.state.user.role,
        data=payload
    )


@router.put("/", response_model=WebhookRead)
@limiter.limit(settings.WEBHOOK_WRITE_RATE_LIMIT)
async def update_webhook_route(request: Request, payload: WebhookUpdatePayload):
    """
    Update webhook settings like event type or URL.
    """
    user = request.state.user
    return await update_webhook(user_id=user.id, payload=payload)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.WEBHOOK_WRITE_RATE_LIMIT)
async def delete_webhook_route(request: Request, payload: WebhookDeletePayload):
    """
    Delete a registered webhook by ID.
    """
    user_id = request.state.user_id
    await delete_webhook(user_id=user_id, webhook_id=payload.webhook_id)
