"""
Схемы ответов для работы с шаблонами (Templates) в API v1.

Этот модуль содержит Pydantic схемы для форматирования HTTP ответов
при работе с шаблонами проблем.

Схемы:
    - TemplateAuthorSchema: Информация об авторе шаблона
    - TemplateDetailSchema: Детальная информация о шаблоне
    - TemplateListItemSchema: Краткая информация для списков
    - TemplateResponseSchema: Обёртка для одиночного ответа
    - TemplateListResponseSchema: Обёртка для списка шаблонов

Использование:
    >>> # Детальный ответ
    >>> template = TemplateDetailSchema.model_validate(template_model)
    >>> response = TemplateResponseSchema(
    ...     success=True,
    ...     message="Шаблон получен",
    ...     data=template
    ... )

    >>> # Список шаблонов
    >>> templates = [TemplateListItemSchema.model_validate(t) for t in models]
    >>> response = TemplateListResponseSchema(
    ...     success=True,
    ...     data=templates
    ... )

Note:
    Все response-схемы наследуются от BaseResponseSchema и содержат
    поля success, message, data.

See Also:
    - src.schemas.v1.templates.base: Базовые схемы
    - src.schemas.v1.templates.requests: Схемы запросов
"""

import uuid
from typing import List

from pydantic import Field

from src.models.v1.templates import TemplateVisibility
from src.schemas.base import BaseResponseSchema, BaseSchema
from src.schemas.v1.templates.base import TemplateFieldSchema


class TemplateAuthorSchema(BaseSchema):
    """
    Схема информации об авторе шаблона.

    Attributes:
        id: UUID автора.
        username: Имя пользователя.
        email: Email автора.

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "username": "john_doe",
            "email": "john@example.com"
        }
    """

    id: uuid.UUID = Field(description="UUID автора")
    username: str = Field(description="Имя пользователя")
    email: str = Field(description="Email автора")


class TemplateDetailSchema(BaseSchema):
    """
    Детальная схема шаблона для ответов API.

    Содержит полную информацию о шаблоне, включая автора и JSONB поля.

    Attributes:
        id: UUID шаблона (наследуется из BaseSchema).
        title: Название шаблона.
        description: Описание назначения.
        category: Категория (hardware/software/process).
        fields: Список динамических полей (JSONB).
        visibility: Уровень видимости (PUBLIC/PRIVATE/TEAM).
        usage_count: Количество использований.
        is_active: Активен ли шаблон.
        author: Информация об авторе.
        author_id: UUID автора.
        created_at: Дата создания (наследуется из BaseSchema).
        updated_at: Дата последнего обновления (наследуется из BaseSchema).

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Аппаратная неисправность",
            "description": "Шаблон для проблем с оборудованием",
            "category": "hardware",
            "fields": [
                {
                    "name": "equipment_id",
                    "label": "ID оборудования",
                    "type": "text",
                    "required": true,
                    "placeholder": "Введите номер оборудования"
                }
            ],
            "visibility": "PUBLIC",
            "usage_count": 42,
            "is_active": true,
            "author": {
                "id": "...",
                "username": "john_doe",
                "email": "john@example.com"
            },
            "author_id": "...",
            "created_at": "2025-11-10T08:00:00Z",
            "updated_at": "2025-11-10T10:30:00Z"
        }
    """

    title: str = Field(description="Название шаблона")
    description: str | None = Field(description="Описание назначения")
    category: str = Field(description="Категория шаблона")
    fields: List[TemplateFieldSchema] = Field(
        description="Динамические поля (JSONB)"
    )
    visibility: TemplateVisibility = Field(description="Уровень видимости")
    usage_count: int = Field(description="Количество использований")
    is_active: bool = Field(description="Активен ли шаблон")
    author: TemplateAuthorSchema = Field(description="Информация об авторе")
    author_id: uuid.UUID = Field(description="UUID автора")


class TemplateListItemSchema(BaseSchema):
    """
    Краткая схема шаблона для списков.

    Содержит основную информацию без детальных полей (fields, author).
    Используется в списках для оптимизации размера ответа.

    Attributes:
        id: UUID шаблона (наследуется из BaseSchema).
        title: Название шаблона.
        description: Описание (краткое).
        category: Категория.
        visibility: Уровень видимости.
        usage_count: Количество использований.
        is_active: Активен ли шаблон.
        author_id: UUID автора.
        created_at: Дата создания (наследуется из BaseSchema).

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Аппаратная неисправность",
            "description": "Шаблон для проблем с оборудованием",
            "category": "hardware",
            "visibility": "PUBLIC",
            "usage_count": 42,
            "is_active": true,
            "author_id": "...",
            "created_at": "2025-11-10T08:00:00Z"
        }
    """

    title: str = Field(description="Название шаблона")
    description: str | None = Field(description="Описание")
    category: str = Field(description="Категория")
    visibility: TemplateVisibility = Field(description="Видимость")
    usage_count: int = Field(description="Количество использований")
    is_active: bool = Field(description="Активен ли")
    author_id: uuid.UUID = Field(description="UUID автора")


class TemplateResponseSchema(BaseResponseSchema):
    """
    Схема ответа API для одного шаблона.

    Обёртка для TemplateDetailSchema. Наследует success и message из BaseResponseSchema.

    Attributes:
        success: Успешность операции (наследуется из BaseResponseSchema).
        message: Сообщение о результате (наследуется из BaseResponseSchema).
        data: Детальная информация о шаблоне.

    Example:
        {
            "success": true,
            "message": "Шаблон успешно создан",
            "data": {
                "id": "...",
                "title": "Аппаратная неисправность",
                ...
            }
        }
    """

    data: TemplateDetailSchema = Field(description="Данные шаблона")


class TemplateListResponseSchema(BaseResponseSchema):
    """
    Схема ответа API для списка шаблонов.

    Обёртка для List[TemplateListItemSchema]. Наследует success и message из BaseResponseSchema.

    Attributes:
        success: Успешность операции (наследуется из BaseResponseSchema).
        message: Сообщение о результате (наследуется из BaseResponseSchema).
        data: Список шаблонов.

    Example:
        {
            "success": true,
            "message": "Получено 5 шаблонов",
            "data": [
                {
                    "id": "...",
                    "title": "Аппаратная неисправность",
                    ...
                },
                ...
            ]
        }
    """

    data: List[TemplateListItemSchema] = Field(description="Список шаблонов")
