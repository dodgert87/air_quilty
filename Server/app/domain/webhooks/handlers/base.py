from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

# T is the payload type (must be a Pydantic model)
T = TypeVar("T", bound=BaseModel)

class WebhookEventHandler(ABC, Generic[T]):
    @abstractmethod
    async def handle(self, payload: T, session: AsyncSession) -> None:
        ...