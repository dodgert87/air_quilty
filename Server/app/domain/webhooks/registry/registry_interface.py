from abc import ABC, abstractmethod
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas.webhook.webhook_schema import WebhookConfig



class WebhookRegistryInterface(ABC):
    @classmethod
    @abstractmethod
    async def load(cls, session: AsyncSession) -> None:
        """Load all relevant webhooks from the database into memory."""
        ...

    @classmethod
    @abstractmethod
    def get_all(cls) -> List[WebhookConfig]:
        """Return the list of currently loaded webhook configurations."""
        ...

    @classmethod
    @abstractmethod
    def add(cls, config: WebhookConfig) -> None:
        """Add a new webhook configuration to the in-memory list."""
        ...

    @classmethod
    @abstractmethod
    def remove(cls, webhook_id: UUID) -> None:
        """Remove a webhook from memory by its ID."""
        ...

    @classmethod
    @abstractmethod
    def replace(cls, config: WebhookConfig) -> None:
        """Replace an existing webhook (by ID) with a new configuration."""
        ...
