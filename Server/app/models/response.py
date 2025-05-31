from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel
from pydantic.generics import GenericModel
from enum import Enum
from starlette.status import (
    HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
)

# ─────────────────────────────────────────────
# Standard Constants
# ─────────────────────────────────────────────

class AppCode(int, Enum):
    OK = 1000
    CREATED = 1001
    VALIDATION_ERROR = 1401
    NOT_FOUND = 1404
    UNAUTHORIZED = 1403
    DB_ERROR = 1500
    UNKNOWN_ERROR = 1501

class AppMessage(str, Enum):
    OK = "Request completed successfully."
    CREATED = "Resource created successfully."
    VALIDATION_ERROR = "Request validation failed."
    NOT_FOUND = "Resource not found."
    UNAUTHORIZED = "Unauthorized access."
    DB_ERROR = "A database error occurred."
    UNKNOWN_ERROR = "An unexpected server error occurred."

class AppHttpStatus(int, Enum):
    OK = HTTP_200_OK
    CREATED = HTTP_201_CREATED
    BAD_REQUEST = HTTP_400_BAD_REQUEST
    UNAUTHORIZED = HTTP_401_UNAUTHORIZED
    FORBIDDEN = HTTP_403_FORBIDDEN
    NOT_FOUND = HTTP_404_NOT_FOUND
    VALIDATION_ERROR = HTTP_422_UNPROCESSABLE_ENTITY
    SERVER_ERROR = HTTP_500_INTERNAL_SERVER_ERROR

# ─────────────────────────────────────────────
# Response Schemas
# ─────────────────────────────────────────────

T = TypeVar("T")

class SuccessResponse(GenericModel, Generic[T]):
    status: str = "success"
    message: str
    http_code: int
    app_code: AppCode
    data: Optional[T] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    http_code: int
    app_code: AppCode
    errors: Optional[Any] = None

# ─────────────────────────────────────────────
# Unified Access Point
# ─────────────────────────────────────────────

class Response:
    code = AppCode
    message = AppMessage
    http = AppHttpStatus
    success = SuccessResponse
    error = ErrorResponse
