"""
Схемы для работы с шаблонами (Templates) в API v1.

Этот пакет содержит все Pydantic схемы для валидации запросов
и форматирования ответов при работе с шаблонами проблем.

Модули:
    base: Базовые схемы (TemplateFieldSchema, TemplateBaseSchema)
    requests: Схемы для входящих запросов (Create, Update, Query)
    responses: Схемы для HTTP ответов (Detail, List, Response)

Использование:
    >>> from src.schemas.v1.templates import (
    ...     TemplateCreateRequestSchema,
    ...     TemplateResponseSchema,
    ...     TemplateFieldSchema
    ... )
"""

from .base import (
    TemplateBaseSchema,
    TemplateFieldSchema,
    TemplateVisibilitySchema,
)
from .requests import (
    TemplateCreateRequestSchema,
    TemplateQueryRequestSchema,
    TemplateUpdateRequestSchema,
)
from .responses import (
    TemplateAuthorSchema,
    TemplateDetailSchema,
    TemplateListItemSchema,
    TemplateListResponseSchema,
    TemplateResponseSchema,
)

__all__ = [
    # Base schemas
    "TemplateBaseSchema",
    "TemplateFieldSchema",
    "TemplateVisibilitySchema",
    # Request schemas
    "TemplateCreateRequestSchema",
    "TemplateUpdateRequestSchema",
    "TemplateQueryRequestSchema",
    # Response schemas
    "TemplateAuthorSchema",
    "TemplateDetailSchema",
    "TemplateListItemSchema",
    "TemplateResponseSchema",
    "TemplateListResponseSchema",
]
