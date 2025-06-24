from typing import List
from fastapi import APIRouter, Request, status
from loguru import logger
from app.utils.exceptions_base import AppException
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
    try:
        webhooks = await get_user_webhooks(request.state.user_id)
        logger.info("[WEBHOOK] Retrieved user webhooks | user=%s | count=%d", request.state.user_id, len(webhooks))
        return webhooks
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to fetch user webhooks | user=%s", request.state.user_id)
        raise AppException.from_internal_error("Failed to fetch webhooks", domain="auth")



@router.get("/allowed-events", response_model=List[str])
@limiter.limit(settings.WEBHOOK_QUERY_RATE_LIMIT)
async def get_allowed_webhook_events_route(request: Request):
    try:
        events = await get_allowed_events_for_role(request.state.user.role)
        logger.info("[WEBHOOK] Allowed events fetched | role=%s | count=%d", request.state.user.role, len(events))
        return events
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to get allowed events | role=%s", request.state.user.role)
        raise AppException.from_internal_error("Failed to fetch allowed webhook events", domain="auth")



# ──────────────── Mutation Endpoints ───────────── #

@router.post("/", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.WEBHOOK_WRITE_RATE_LIMIT)
async def create_webhook_route(payload: WebhookCreate, request: Request):
    try:
        result = await create_webhook(
            user_id=request.state.user.id,
            user_role=request.state.user.role,
            data=payload
        )
        logger.info("[WEBHOOK] Created webhook | user=%s | event=%s", request.state.user.id, payload.event_type)
        return result
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to create webhook | user=%s | payload=%s", request.state.user.id, payload)
        raise AppException.from_internal_error("Failed to create webhook", domain="auth")



@router.put("/", response_model=WebhookRead)
@limiter.limit(settings.WEBHOOK_WRITE_RATE_LIMIT)
async def update_webhook_route(request: Request, payload: WebhookUpdatePayload):
    try:
        result = await update_webhook(user_id=request.state.user.id, payload=payload)
        logger.info("[WEBHOOK] Updated webhook | user=%s | webhook_id=%s", request.state.user.id, payload.webhook_id)
        return result
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to update webhook | user=%s | payload=%s", request.state.user.id, payload)
        raise AppException.from_internal_error("Failed to update webhook", domain="auth")



@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.WEBHOOK_WRITE_RATE_LIMIT)
async def delete_webhook_route(request: Request, payload: WebhookDeletePayload):
    try:
        await delete_webhook(user_id=request.state.user_id, webhook_id=payload.webhook_id)
        logger.info("[WEBHOOK] Deleted webhook | user=%s | webhook_id=%s", request.state.user_id, payload.webhook_id)
    except Exception as e:
        logger.exception("[WEBHOOK] Failed to delete webhook | user=%s | webhook_id=%s", request.state.user_id, payload.webhook_id)
        raise AppException.from_internal_error("Failed to delete webhook", domain="auth")
