from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models.schemas.webhook.webhook_schema import WebhookConfig

T = TypeVar("T", bound=BaseModel)

class WebhookProcessorInterface(ABC, Generic[T]):
    @abstractmethod
    async def handle(self, payload: T, session: AsyncSession) -> None:
        """Handle the incoming payload for this webhook event."""
        ...

    @abstractmethod
    async def load(self, session: AsyncSession) -> None:
        """Load all relevant webhook configs from the DB into memory."""
        ...

    @abstractmethod
    def get_all(self) -> list[WebhookConfig]:
        """Return all loaded webhook configurations for this event."""
        ...

    @abstractmethod
    def add(self, config: WebhookConfig) -> None:
        """Add a new webhook config to memory."""
        ...

    @abstractmethod
    def remove(self, webhook_id: UUID) -> None:
        """Remove a webhook config from memory."""
        ...

    @abstractmethod
    def replace(self, config: WebhookConfig) -> None:
        """Replace an existing webhook config (by ID) with a new one."""
        ...
