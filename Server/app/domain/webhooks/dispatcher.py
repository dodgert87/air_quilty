from typing import Dict, Type
from app.utils.exceptions_base import AppException
from app.constants.webhooks import WebhookEvent
from app.domain.webhooks.handlers.base import WebhookEventHandler
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.transaction import run_in_transaction
from pydantic import BaseModel, ValidationError


class WebhookDispatcher:
    def __init__(self):
        self._handlers: Dict[WebhookEvent, WebhookEventHandler] = {}

    def register(self, event: WebhookEvent, handler: WebhookEventHandler):
        self._handlers[event] = handler

    def can_handle(self, event: WebhookEvent) -> bool:
        return event in self._handlers

    async def dispatch(self, event: WebhookEvent, payload: BaseModel | dict) -> None:
        handler = self._handlers.get(event)
        if not handler:
            # Silently skip if no handler
            return

        # Validate payload type
        try:
            if isinstance(payload, dict):
                raw_model = getattr(handler, "payload_model", None)
                if not isinstance(raw_model, type) or not issubclass(raw_model, BaseModel):
                    return  # skip if model is invalid

                payload_model: Type[BaseModel] = raw_model
                payload = payload_model.model_validate(payload)

            elif not isinstance(payload, BaseModel):
                return  # unknown payload type, skip

        except ValidationError as ve:
            # Payload invalid — skip dispatch, don't raise
            # Optional: log this as a warning
            return

        try:
            async with run_in_transaction() as session:
                await handler.handle(payload, session=session)

        except AppException:
            raise

        except Exception as e:
            raise AppException(
                message=f"Unhandled error in webhook dispatcher for event '{event}': {e}",
                status_code=500,
                public_message="Webhook dispatch failed.",
                domain="webhook"
            )
