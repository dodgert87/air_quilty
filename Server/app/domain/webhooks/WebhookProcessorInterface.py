from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models.schemas.webhook.webhook_schema import WebhookConfig

# Define a generic type for the event payloads
T = TypeVar("T", bound=BaseModel)


class WebhookProcessorInterface(ABC, Generic[T]):
    """
    Abstract interface for webhook processors tied to a specific event type.

    Each implementation manages in-memory configuration of webhooks,
    executes delivery when triggered, and supports hot-reloading from the DB.

    This interface allows centralized coordination and polymorphic usage of processors.
    """

    @abstractmethod
    async def handle(self, payload: T, session: AsyncSession) -> None:
        """
        Trigger this webhook processor for a specific event payload.

        This method is called when an event of this type occurs.

        Args:
            payload (T): The event payload (must match the processor's expected input model).
            session (AsyncSession): DB session, optionally used for logging failures, etc.
        """
        ...

    @abstractmethod
    async def load(self, session: AsyncSession) -> None:
        """
        Load all webhook configurations of this type from the database.

        Typically called at startup or during refresh.
        Populates the in-memory list of `WebhookConfig` entries.
        """
        ...

    @abstractmethod
    def get_all(self) -> list[WebhookConfig]:
        """
        Return the list of all webhook configurations currently loaded in memory.

        Returns:
            list[WebhookConfig]: The current in-memory set of webhooks listening to this event.
        """
        ...

    @abstractmethod
    def add(self, config: WebhookConfig) -> None:
        """
        Add a new webhook configuration to memory.

        Args:
            config (WebhookConfig): Webhook configuration to add.
        """
        ...

    @abstractmethod
    def remove(self, webhook_id: UUID) -> None:
        """
        Remove a webhook configuration from memory by its ID.

        Args:
            webhook_id (UUID): ID of the webhook to remove.
        """
        ...

    @abstractmethod
    def replace(self, config: WebhookConfig) -> None:
        """
        Replace an existing webhook configuration by ID.

        Args:
            config (WebhookConfig): New configuration to replace an old one with the same ID.
        """
        ...
