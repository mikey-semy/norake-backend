"""
Схемы запросов для работы с шаблонами (Templates) в API v1.

Этот модуль содержит Pydantic схемы для валидации входящих запросов
при работе с шаблонами проблем.

Схемы:
    - TemplateCreateRequestSchema: Создание нового шаблона
    - TemplateUpdateRequestSchema: Обновление существующего шаблона
    - TemplateQueryRequestSchema: Фильтрация и поиск шаблонов

Использование:
    >>> # Создание шаблона
    >>> create_data = TemplateCreateRequestSchema(
    ...     title="Аппаратная неисправность",
    ...     description="Шаблон для проблем с оборудованием",
    ...     category="hardware",
    ...     fields=[
    ...         {
    ...             "name": "equipment_id",
    ...             "label": "ID оборудования",
    ...             "type": "text",
    ...             "required": True
    ...         }
    ...     ],
    ...     visibility="PUBLIC"
    ... )

Note:
    Все схемы наследуются от BaseRequestSchema и не содержат
    системных полей (id, created_at, updated_at, author_id).

See Also:
    - src.schemas.v1.templates.base: Базовые схемы
    - src.schemas.v1.templates.responses: Схемы ответов
"""

from typing import List, Optional

from pydantic import Field

from src.models.v1.templates import TemplateVisibility
from src.schemas.base import BaseRequestSchema
from src.schemas.v1.templates.base import TemplateFieldSchema


class TemplateCreateRequestSchema(BaseRequestSchema):
    """
    Схема для создания нового шаблона проблемы.

    Attributes:
        title: Название шаблона (3-200 символов).
        description: Описание назначения шаблона.
        category: Категория (hardware/software/process).
        fields: Список динамических полей (JSONB).
        visibility: Уровень видимости (PUBLIC/PRIVATE/TEAM).

    Note:
        Поля author_id, usage_count, is_active устанавливаются автоматически:
        - author_id = текущий пользователь
        - usage_count = 0
        - is_active = True

    Example:
        POST /api/v1/templates
        {
            "title": "Аппаратная неисправность",
            "description": "Шаблон для описания проблем с оборудованием",
            "category": "hardware",
            "fields": [
                {
                    "name": "equipment_id",
                    "label": "ID оборудования",
                    "type": "text",
                    "required": true,
                    "placeholder": "Введите номер оборудования"
                },
                {
                    "name": "error_code",
                    "label": "Код ошибки",
                    "type": "text",
                    "required": false
                }
            ],
            "visibility": "PUBLIC"
        }
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Название шаблона",
        examples=["Аппаратная неисправность", "Ошибка ПО"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Описание назначения шаблона",
        examples=["Шаблон для описания проблем с оборудованием"],
    )

    category: str = Field(
        ...,
        max_length=50,
        description="Категория шаблона (hardware, software, process)",
        examples=["hardware", "software", "process"],
    )

    fields: List[TemplateFieldSchema] = Field(
        default_factory=list,
        description="Динамические поля шаблона (JSONB)",
    )

    visibility: TemplateVisibility = Field(
        default=TemplateVisibility.PRIVATE,
        description="Уровень видимости шаблона",
    )


class TemplateUpdateRequestSchema(BaseRequestSchema):
    """
    Схема для обновления существующего шаблона.

    Все поля опциональны - обновляются только переданные.

    Attributes:
        title: Новое название шаблона.
        description: Новое описание.
        category: Новая категория.
        fields: Новый список полей (полностью заменяет существующий).
        visibility: Новый уровень видимости.

    Note:
        Поля is_active, usage_count, author_id не обновляются этой схемой.
        Для деактивации используется отдельный endpoint.

    Example:
        PATCH /api/v1/templates/{template_id}
        {
            "title": "Обновлённое название",
            "visibility": "PUBLIC"
        }
    """

    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Новое название шаблона",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Новое описание",
    )

    category: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Новая категория",
    )

    fields: Optional[List[TemplateFieldSchema]] = Field(
        default=None,
        description="Новый список полей (заменяет существующий)",
    )

    visibility: Optional[TemplateVisibility] = Field(
        default=None,
        description="Новый уровень видимости",
    )


class TemplateQueryRequestSchema(BaseRequestSchema):
    """
    Схема для фильтрации и поиска шаблонов.

    Все параметры опциональны. Используется для GET запросов с query params.

    Attributes:
        category: Фильтр по категории.
        visibility: Фильтр по видимости.
        author_id: Фильтр по автору (UUID).
        is_active: Фильтр по активности.
        search: Текстовый поиск по title и description.
        limit: Максимальное количество результатов.
        offset: Смещение для пагинации.

    Example:
        GET /api/v1/templates?category=hardware&visibility=PUBLIC&limit=10
    """

    category: Optional[str] = Field(
        default=None,
        description="Фильтр по категории",
    )

    visibility: Optional[TemplateVisibility] = Field(
        default=None,
        description="Фильтр по видимости",
    )

    author_id: Optional[str] = Field(
        default=None,
        description="Фильтр по автору (UUID)",
    )

    is_active: Optional[bool] = Field(
        default=None,
        description="Фильтр по активности",
    )

    search: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Текстовый поиск по title и description",
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Максимальное количество результатов",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Смещение для пагинации",
    )
