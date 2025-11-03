"""
Схемы ответов для регистрации пользователей.

Содержит Pydantic схемы для исходящих данных endpoints регистрации.
Все схемы следуют единому формату: {success, message, data}.
"""

from src.schemas.base import BaseResponseSchema
from .base import RegistrationDataSchema


class RegistrationResponseSchema(BaseResponseSchema):
    """
    Схема полного ответа API при успешной регистрации пользователя.

    Содержит стандартные поля ответа (success, message) плюс данные
    зарегистрированного пользователя с JWT токенами.

    Attributes:
        success: Статус успешности операции (всегда True)
        message: Информационное сообщение о результате регистрации
        data: Данные зарегистрированного пользователя с токенами

    Example:
        ```json
        {
            "success": true,
            "message": "Регистрация завершена успешно. Добро пожаловать!",
            "data": {
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
        }
        ```

    Note:
        При регистрации username генерируется автоматически из email.
        Поля phone заполняются позже в профиле пользователя.
    """

    data: RegistrationDataSchema
