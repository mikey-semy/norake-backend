"""
Схемы запросов для работы с сервисами документов (Document Services) в API v1.

Этот модуль содержит Pydantic схемы для валидации входящих запросов
при работе с сервисами документов.

Схемы:
    - DocumentServiceCreateRequestSchema: Создание нового сервиса документа
    - DocumentServiceUpdateRequestSchema: Обновление существующего сервиса
    - DocumentServiceQueryRequestSchema: Фильтрация и поиск сервисов
    - DocumentFunctionAddRequestSchema: Добавление функции к сервису

Использование:
    >>> # Создание сервиса документа
    >>> create_data = DocumentServiceCreateRequestSchema(
    ...     title="Техническая документация",
    ...     description="Руководство по эксплуатации",
    ...     tags=["технический", "оборудование"],
    ...     file_type=DocumentFileType.PDF,
    ...     workspace_id=workspace_uuid
    ... )

Note:
    Все схемы наследуются от BaseRequestSchema и не содержат
    системных полей (id, created_at, updated_at, author_id).

See Also:
    - src.schemas.v1.document_services.base: Базовые схемы
    - src.schemas.v1.document_services.responses: Схемы ответов
"""

import uuid
from typing import List, Optional

from pydantic import Field, field_validator

from src.models.v1.document_services import (
    CoverType,
    DocumentFileType,
    ServiceFunctionType,
)
from src.schemas.base import BaseRequestSchema
from src.schemas.v1.document_services.base import ServiceFunctionSchema


class DocumentServiceCreateRequestSchema(BaseRequestSchema):
    """
    Схема для создания нового сервиса документа.

    Attributes:
        title: Название сервиса (3-255 символов).
        description: Описание содержимого.
        tags: Теги для поиска.
        file_type: Тип файла (PDF/SPREADSHEET/TEXT/IMAGE).
        cover_type: Тип обложки (GENERATED/ICON/IMAGE).
        cover_icon: Имя иконки (если cover_type=ICON).
        available_functions: Список функций сервиса.
        workspace_id: UUID workspace (опционально, NULL для публичных).
        is_public: Публичный ли сервис.

    Note:
        Поля author_id, file_url, file_size, cover_url устанавливаются автоматически:
        - author_id = текущий пользователь
        - file_url, file_size = из загруженного файла
        - cover_url = генерируется автоматически для PDF

    Example:
        POST /api/v1/document-services
        Content-Type: multipart/form-data

        {
            "title": "Техническая документация",
            "description": "Руководство по эксплуатации оборудования XYZ",
            "tags": ["технический", "оборудование"],
            "file_type": "PDF",
            "cover_type": "GENERATED",
            "available_functions": [
                {
                    "name": "view_pdf",
                    "enabled": true,
                    "label": "Открыть PDF",
                    "icon": "📄"
                },
                {
                    "name": "download",
                    "enabled": true,
                    "label": "Скачать",
                    "icon": "📥"
                }
            ],
            "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
            "is_public": false
        }

        file: <binary PDF data>
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Название сервиса документа",
        examples=["Техническая документация", "Прайс-лист 2025"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Описание содержимого документа",
        examples=["Руководство по эксплуатации оборудования XYZ"],
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Теги для поиска и категоризации",
        examples=[["технический", "оборудование"], ["прайс", "цены"]],
    )

    file_type: str = Field(
        default="pdf",
        description="Тип файла документа (pdf/spreadsheet/text/image)",
    )

    cover_type: str = Field(
        default="generated",
        description="Тип обложки (generated/icon/image)",
    )

    cover_icon: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Имя иконки для обложки (если cover_type=ICON)",
        examples=["📄", "📊", "📋"],
    )

    available_functions: List[ServiceFunctionSchema] = Field(
        default_factory=lambda: [
            ServiceFunctionSchema(
                name=ServiceFunctionType.VIEW_PDF.value,
                enabled=True,
                label="Открыть PDF",
                icon="📄",
            ),
            ServiceFunctionSchema(
                name=ServiceFunctionType.DOWNLOAD.value,
                enabled=True,
                label="Скачать",
                icon="📥",
            ),
        ],
        description="Список доступных функций сервиса",
    )

    @field_validator("file_type", "cover_type", mode="before")
    @classmethod
    def validate_enum_case(cls, value):
        """
        Валидатор для enum полей - конвертирует UPPERCASE в lowercase.

        Swagger UI и FastAPI Form() отправляют enum NAMES (TEXT, PDF) вместо VALUES (text, pdf).
        Этот валидатор приводит к lowercase для совместимости с БД enum значениями.

        Args:
            value: Значение из Form() (строка "TEXT", "PDF", "GENERATED" и т.д.) или enum.

        Returns:
            str: Lowercase строка для записи в БД.

        Example:
            >>> # FastAPI Form() передаёт: {"file_type": "TEXT"}
            >>> # Валидатор конвертирует: "TEXT" -> "text"
            >>> # Результат: "text" записывается в БД
        """
        if isinstance(value, str):
            return value.lower()
        # Если уже enum (из кода), извлекаем value
        if hasattr(value, "value"):
            return value.value
        return value

    workspace_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID workspace (NULL для публичных документов)",
    )

    is_public: bool = Field(
        default=False,
        description="Публичный ли сервис (доступен всем без авторизации)",
    )


class DocumentServiceUpdateRequestSchema(BaseRequestSchema):
    """
    Схема для обновления существующего сервиса документа.

    Все поля опциональны - обновляются только переданные.

    Attributes:
        title: Новое название сервиса.
        description: Новое описание.
        tags: Новый список тегов (полностью заменяет существующий).
        cover_type: Новый тип обложки.
        cover_icon: Новая иконка обложки.
        available_functions: Новый список функций (полностью заменяет).
        workspace_id: Новый workspace (можно переместить между workspace).
        is_public: Новое значение публичности.

    Note:
        Поля file_url, file_size, file_type, author_id не обновляются.
        Для замены файла используется отдельный endpoint.

    Example:
        PATCH /api/v1/document-services/{service_id}
        {
            "title": "Обновлённое название",
            "tags": ["новый_тег"],
            "is_public": true
        }
    """

    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=255,
        description="Новое название сервиса",
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Новое описание",
    )

    tags: Optional[List[str]] = Field(
        default=None,
        description="Новый список тегов (заменяет существующий)",
    )

    cover_type: Optional[CoverType] = Field(
        default=None,
        description="Новый тип обложки",
    )

    cover_icon: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Новая иконка обложки",
    )

    available_functions: Optional[List[ServiceFunctionSchema]] = Field(
        default=None,
        description="Новый список функций (заменяет существующий)",
    )

    workspace_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Новый workspace (NULL для публичных)",
    )

    is_public: Optional[bool] = Field(
        default=None,
        description="Новое значение публичности",
    )


class DocumentServiceQueryRequestSchema(BaseRequestSchema):
    """
    Схема для фильтрации и поиска сервисов документов.

    Attributes:
        search: Поиск по названию и описанию.
        tags: Фильтр по тегам (AND логика).
        file_type: Фильтр по типу файла.
        author_id: Фильтр по автору.
        workspace_id: Фильтр по workspace.
        is_public: Фильтр по публичности.
        limit: Количество результатов (по умолчанию 50).
        offset: Смещение для пагинации (по умолчанию 0).
        order_by: Поле сортировки (created_at/view_count/title).
        ascending: Направление сортировки (False = DESC).

    Example:
        GET /api/v1/document-services?search=техническая&tags=оборудование&limit=20
    """

    search: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Поиск по названию и описанию",
    )

    tags: Optional[List[str]] = Field(
        default=None,
        description="Фильтр по тегам (AND логика)",
    )

    file_type: Optional[DocumentFileType] = Field(
        default=None,
        description="Фильтр по типу файла",
    )

    author_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Фильтр по автору",
    )

    workspace_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Фильтр по workspace",
    )

    is_public: Optional[bool] = Field(
        default=None,
        description="Фильтр по публичности",
    )

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Количество результатов (1-100)",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Смещение для пагинации",
    )

    order_by: str = Field(
        default="created_at",
        description="Поле сортировки (created_at/view_count/title)",
        examples=["created_at", "view_count", "title"],
    )

    ascending: bool = Field(
        default=False,
        description="Направление сортировки (False = DESC)",
    )


class DocumentFunctionAddRequestSchema(BaseRequestSchema):
    """
    Схема для добавления функции к существующему сервису.

    Attributes:
        function: Конфигурация функции для добавления.

    Example:
        POST /api/v1/document-services/{service_id}/functions
        {
            "function": {
                "name": "ai_chat",
                "enabled": true,
                "label": "AI Ассистент",
                "icon": "🤖",
                "config": {
                    "model": "gpt-4",
                    "context_size": 8192
                }
            }
        }
    """

    function: ServiceFunctionSchema = Field(
        ...,
        description="Конфигурация функции для добавления",
    )
