from typing import Optional
from uuid import UUID


class AppException(Exception):
    def __init__(
        self,
        *,
        message: str,
        status_code: int = 400,
        domain: str = "other",
        public_message: Optional[str] = None,
    ):
        self.message = message                    # full internal message (for logs)
        self.status_code = status_code            # HTTP code
        self.public_message = public_message or   "An unexpected error occurred"
        self.domain = domain                      # Used for LogDomain if mapped
        super().__init__(message)


# Example domain exceptions
class AuthError(AppException):
    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(
            message=message,
            status_code=401,
            public_message="Invalid email or password.",
            domain="auth"
        )


class SensorDataError(AppException):
    def __init__(self, message: str = "Sensor data fetch failed"):
        super().__init__(
            message=message,
            status_code=422,
            public_message="Data could not be retrieved.",
            domain="sensor"
        )


class SensorNotFoundError(AppException):
    def __init__(self, sensor_id: str | UUID):
        super().__init__(
            message=f"Sensor with ID {sensor_id} not found.",
            status_code=404,
            public_message="Sensor not found.",
            domain="sensor"
        )



class UserNotFoundError(AppException):
    def __init__(self, context: str = "User"):
        super().__init__(
            message=f"{context} not found.",
            status_code=404,
            public_message="User not found.",
            domain="auth"
        )

class AuthValidationError(AppException):
    def __init__(self, public_message: str = "Invalid credentials", context: str = ""):
        super().__init__(
            message=f"Auth validation error: {context}",
            status_code=401,
            public_message=public_message,
            domain="auth"
        )

class AuthConflictError(AppException):
    def __init__(self, public_message: str = "Resource conflict", context: str = ""):
        super().__init__(
            message=f"Auth conflict: {context}",
            status_code=409,
            public_message=public_message,
            domain="auth"
        )