from typing import List
from uuid import UUID
from fastapi import APIRouter, Request, status
from app.models.schemas.webhook.webhook_schema import WebhookCreate, WebhookDeletePayload, WebhookRead, WebhookUpdatePayload
from app.domain.webhook_logic import (
    get_user_webhooks,
    get_allowed_events_for_role,
    create_webhook,
    delete_webhook,
    update_webhook
)

router = APIRouter(
    prefix="/auth/webhooks",
    tags=["Webhooks"]
)

@router.get("/", response_model=List[WebhookRead])
async def get_user_webhooks_route(request: Request):
    return await get_user_webhooks(request.state.user_id)

@router.get("/allowed-events", response_model=List[str])
async def get_allowed_webhook_events_route(request: Request):
    return await get_allowed_events_for_role(request.state.user.role)

@router.post("/", response_model=WebhookRead, status_code=status.HTTP_201_CREATED)
async def create_webhook_route(payload: WebhookCreate, request: Request):
    return await create_webhook(
        user_id=request.state.user.id,
        user_role=request.state.user.role,
        data=payload
    )

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_route(request: Request, payload: WebhookDeletePayload):
    user_id = request.state.user_id
    await delete_webhook(user_id=user_id, webhook_id=payload.webhook_id)


@router.put("/", response_model=WebhookRead)
async def update_webhook_route(request: Request, payload: WebhookUpdatePayload):
    user = request.state.user
    return await update_webhook(user_id=user.id, payload=payload)