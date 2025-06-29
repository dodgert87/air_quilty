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
        self.message = message                          # internal log message
        self.internal_message = message                 # alias for clarity in logs
        self.status_code = status_code
        self.public_message = public_message or "An unexpected error occurred"
        self.domain = domain
        super().__init__(message)

    @staticmethod
    def from_internal_error(msg: str, domain: str = "other") -> "AppException":
        return AppException(
            message=msg,
            public_message="Internal server error",
            domain=domain,
            status_code=500,
        )

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
    """Raised for authentication / validation problems (HTTP-400)."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=400,
            public_message=message,
            domain="auth",
        )

    def __str__(self) -> str:      # noqa: DunderStr
        return f"Auth validation error: {self.message}" if self.message else "Auth validation error"


class AuthConflictError(AppException):
    """Raised for auth conflicts (e.g. duplicate labels, key limit reached)."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=409,
            public_message=message,
            domain="auth",
        )

    def __str__(self) -> str:
        return self.message or "Auth conflict"