"""
Схемы ответов для работы с проблемами (Issues) в API v1.

Этот модуль содержит Pydantic схемы для форматирования HTTP ответов
при работе с проблемами.

Схемы:
    - IssueDetailSchema: Детальная информация о проблеме
    - IssueListItemSchema: Краткая информация для списков
    - IssueResponseSchema: Обёртка для одиночного ответа
    - IssueListResponseSchema: Обёртка для списка проблем

Использование:
    >>> # Детальный ответ
    >>> issue = IssueDetailSchema.model_validate(issue_model)
    >>> response = IssueResponseSchema(
    ...     success=True,
    ...     message="Проблема получена",
    ...     data=issue
    ... )
    
    >>> # Список проблем
    >>> issues = [IssueListItemSchema.model_validate(i) for i in issue_models]
    >>> response = IssueListResponseSchema(
    ...     success=True,
    ...     data=issues
    ... )

Note:
    Все response-схемы наследуются от BaseResponseSchema и содержат
    поля success, message, data.

See Also:
    - src.schemas.v1.issues.base: Базовые схемы
    - src.schemas.v1.issues.requests: Схемы запросов
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import Field

from src.schemas.base import BaseResponseSchema, BaseSchema
from .base import IssueAuthorSchema


class IssueDetailSchema(BaseSchema):
    """
    Детальная схема проблемы для ответов API.

    Содержит полную информацию о проблеме, включая автора и решение.

    Attributes:
        id: UUID проблемы (наследуется из BaseSchema).
        title: Заголовок проблемы.
        description: Подробное описание.
        category: Категория (hardware/software/process).
        status: Статус (red/green).
        solution: Текст решения (если проблема решена).
        author: Информация об авторе.
        author_id: UUID автора.
        resolved_at: Дата и время решения.
        created_at: Дата создания (наследуется из BaseSchema).
        updated_at: Дата последнего обновления (наследуется из BaseSchema).

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Ошибка E401",
            "description": "Проблема с оборудованием",
            "category": "hardware",
            "status": "green",
            "solution": "Заменён датчик",
            "author": {
                "id": "...",
                "username": "john_doe",
                "email": "john@example.com"
            },
            "author_id": "...",
            "resolved_at": "2025-11-10T10:30:00Z",
            "created_at": "2025-11-10T08:00:00Z",
            "updated_at": "2025-11-10T10:30:00Z"
        }
    """

    title: str = Field(description="Заголовок проблемы")
    description: str = Field(description="Подробное описание")
    category: str = Field(description="Категория проблемы")
    status: str = Field(description="Статус проблемы (red/green)")
    solution: Optional[str] = Field(None, description="Текст решения")
    author: IssueAuthorSchema = Field(description="Информация об авторе")
    author_id: uuid.UUID = Field(description="UUID автора")
    resolved_at: Optional[datetime] = Field(None, description="Дата решения")


class IssueListItemSchema(BaseSchema):
    """
    Краткая схема проблемы для списков.

    Используется в списках проблем, не содержит полное описание и решение.

    Attributes:
        id: UUID проблемы (наследуется из BaseSchema).
        title: Заголовок проблемы.
        category: Категория.
        status: Статус (red/green).
        author_id: UUID автора.
        created_at: Дата создания (наследуется из BaseSchema).
        resolved_at: Дата решения (если решена).

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Ошибка E401",
            "category": "hardware",
            "status": "red",
            "author_id": "...",
            "created_at": "2025-11-10T08:00:00Z",
            "resolved_at": null
        }
    """

    title: str = Field(description="Заголовок проблемы")
    category: str = Field(description="Категория проблемы")
    status: str = Field(description="Статус проблемы (red/green)")
    author_id: uuid.UUID = Field(description="UUID автора")
    resolved_at: Optional[datetime] = Field(None, description="Дата решения")


class IssueResponseSchema(BaseResponseSchema):
    """
    Схема ответа с одной проблемой.

    Обёртка для детальной информации о проблеме.

    Attributes:
        success: Флаг успешности операции.
        message: Сообщение для пользователя.
        data: Детальная информация о проблеме.

    Example:
        {
            "success": true,
            "message": "Проблема получена успешно",
            "data": {
                "id": "...",
                "title": "Ошибка E401",
                ...
            }
        }
    """

    data: IssueDetailSchema = Field(description="Данные проблемы")


class IssueListResponseSchema(BaseResponseSchema):
    """
    Схема ответа со списком проблем.

    Обёртка для списка проблем с краткой информацией.

    Attributes:
        success: Флаг успешности операции.
        message: Сообщение для пользователя.
        data: Список проблем.

    Example:
        {
            "success": true,
            "message": "Найдено 15 проблем",
            "data": [
                {
                    "id": "...",
                    "title": "Ошибка E401",
                    "status": "red",
                    ...
                },
                ...
            ]
        }
    """

    data: List[IssueListItemSchema] = Field(
        default_factory=list, description="Список проблем"
    )
