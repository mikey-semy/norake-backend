"""
Схемы API версии 1.

Экспортирует все схемы для версии API v1.
"""

# Common (из base.py)
from .base import (BaseRequestSchema, BaseResponseSchema, BaseSchema,
                   CommonBaseSchema, ErrorResponseSchema, ErrorSchema)
from .v1.health import HealthCheckDataSchema, HealthCheckResponseSchema

# Auth
from .v1.auth import (
    TokenDataSchema,
    LogoutDataSchema,
    PasswordResetDataSchema,
    PasswordResetConfirmDataSchema,
    UserCredentialsSchema,
    UserCurrentSchema,
    LoginRequestSchema,
    ForgotPasswordRequestSchema,
    PasswordResetConfirmRequestSchema,
    RefreshTokenRequestSchema,
    TokenResponseSchema,
    LogoutResponseSchema,
    CurrentUserResponseSchema,
    PasswordResetResponseSchema,
    PasswordResetConfirmResponseSchema,
)

# Register
from .v1.register import (
    RegistrationRequestSchema,
    RegistrationDataSchema,
    RegistrationResponseSchema,
)
__all__ = [
    # Common
    "CommonBaseSchema",
    "BaseSchema",
    "BaseRequestSchema",
    "BaseResponseSchema",
    "ErrorSchema",
    "ErrorResponseSchema",

    # V1 Health
    "HealthCheckResponseSchema",
    "HealthCheckDataSchema",

    # V1 Auth
    "TokenDataSchema",
    "LogoutDataSchema",
    "PasswordResetDataSchema",
    "PasswordResetConfirmDataSchema",
    "UserCredentialsSchema",
    "UserCurrentSchema",
    "LoginRequestSchema",
    "ForgotPasswordRequestSchema",
    "PasswordResetConfirmRequestSchema",
    "RefreshTokenRequestSchema",
    "TokenResponseSchema",
    "LogoutResponseSchema",
    "CurrentUserResponseSchema",
    "PasswordResetResponseSchema",
    "PasswordResetConfirmResponseSchema",

    # V1 Register
    "RegistrationRequestSchema",
    "RegistrationDataSchema",
    "RegistrationResponseSchema",
]
