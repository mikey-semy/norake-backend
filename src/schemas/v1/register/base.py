"""
Базовые схемы данных для регистрации пользователей.

Содержит классы данных, которые помещаются в поле `data` ответов API.
Эти схемы описывают структуру полезной нагрузки ответов регистрации.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from src.schemas.base import CommonBaseSchema


class RegistrationDataSchema(CommonBaseSchema):
    """
    Схема данных пользователя при успешной регистрации.

    Содержит основную информацию о зарегистрированном пользователе,
    которая безопасна для передачи клиенту. Исключает конфиденциальные
    данные такие как хешированный пароль.

    Attributes:
        id: Уникальный UUID идентификатор пользователя в системе
        username: Имя пользователя для входа в систему
        email: Email адрес пользователя
        phone: Контактный телефон (опционально, заполняется в профиле)
        role: Роль пользователя в системе (по умолчанию "user")
        is_active: Статус активности аккаунта
        created_at: Дата и время создания аккаунта
        access_token: JWT токен доступа (None если use_cookies=True)
        refresh_token: JWT токен для обновления (None если use_cookies=True)
        token_type: Тип токена (всегда "Bearer")

    Example:
        ```python
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "username": "john_doe",
            "email": "john@example.com",
            "phone": null,
            "role": "user",
            "is_active": true,
            "created_at": "2025-10-29T10:30:00Z",
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "Bearer"
        }
        ```

    Note:
        При регистрации username генерируется автоматически из email.
        Поля phone, full_name, company данные заполняются позже в профиле.
    """

    id: UUID = Field(
        description="Уникальный UUID идентификатор пользователя",
        examples=[
            "550e8400-e29b-41d4-a716-446655440000",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b811-9dad-11d1-80b4-00c04fd430c8",
        ],
    )

    username: Optional[str] = Field(
        description="Имя пользователя для входа в систему",
        examples=["john_doe", "user123", "ivan_petrov"],
    )

    email: EmailStr = Field(
        description="Email адрес пользователя",
        examples=["user@example.com", "john.doe@company.org"],
    )

    phone: Optional[str] = Field(
        None,
        description="Контактный телефон (заполняется в профиле)",
        examples=["+79991234567", "+7 999 123-45-67"],
    )

    full_name: Optional[str] = Field(
        None,
        description="ФИО пользователя (заполняется в профиле)",
        examples=["Иванов Иван Иванович", "Петров П.П."],
    )

    role: str = Field(
        default="user",
        description="Роль пользователя в системе (user при регистрации)",
        examples=["user", "admin"],
    )

    is_active: bool = Field(
        default=True,
        description="Статус активности аккаунта пользователя"
    )

    created_at: datetime = Field(
        description="Дата и время создания аккаунта",
        examples=["2025-10-29T10:30:00Z"]
    )

    access_token: Optional[str] = Field(
        default=None,
        description="JWT токен доступа для авторизации запросов. "
        "Будет None если используются cookies (use_cookies=true)",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", None],
    )

    refresh_token: Optional[str] = Field(
        default=None,
        description="JWT токен для обновления access токена. "
        "Будет None если используются cookies (use_cookies=true)",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...", None],
    )

    token_type: str = Field(
        default="Bearer",
        description="Тип токена для использования в заголовке Authorization"
    )
