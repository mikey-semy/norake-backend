"""Схемы запросов для аутентификации и авторизации."""

from pydantic import EmailStr, Field

from src.schemas.base import BaseRequestSchema


class AuthSchema(BaseRequestSchema):
    """
    Схема для внутренней валидации аутентификации.

    ⚠️ ТОЛЬКО для internal использования в сервисах!

    Attributes:
        username: Email или username для входа.
        password: Пароль пользователя.
    """

    username: str = Field(description="Email или username пользователя")
    password: str = Field(description="Пароль пользователя")


class LoginRequestSchema(BaseRequestSchema):
    """
    Схема для входа в систему.

    Attributes:
        email: Email пользователя для входа.
        password: Пароль пользователя.
    """

    email: EmailStr = Field(description="Email пользователя")
    password: str = Field(min_length=8, description="Пароль (минимум 8 символов)")


class ForgotPasswordRequestSchema(BaseRequestSchema):
    """
    Схема для запроса сброса пароля.

    Attributes:
        email: Email адрес для восстановления пароля.
    """

    email: EmailStr = Field(description="Email адрес для восстановления пароля")


class PasswordResetConfirmRequestSchema(BaseRequestSchema):
    """
    Схема для подтверждения сброса пароля.

    Attributes:
        token: Токен восстановления из письма.
        password: Новый пароль (минимум 8 символов).
    """

    token: str = Field(description="Токен восстановления из письма")
    password: str = Field(min_length=8, max_length=128, description="Новый пароль (минимум 8 символов)")


class RefreshTokenRequestSchema(BaseRequestSchema):
    """
    Схема для обновления токена доступа.

    Attributes:
        refresh_token: Токен обновления из предыдущего ответа login/register.
    """

    refresh_token: str = Field(description="Refresh токен для получения новой пары токенов")
