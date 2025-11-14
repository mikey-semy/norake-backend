"""
Схемы ответов для работы с сервисами документов (Document Services) в API v1.

Этот модуль содержит Pydantic схемы для форматирования HTTP ответов
при работе с сервисами документов.

Схемы:
    - DocumentServiceAuthorBriefSchema: Краткая информация об авторе
    - DocumentServiceWorkspaceBriefSchema: Краткая информация о workspace
    - DocumentServiceDetailSchema: Детальная информация о сервисе
    - DocumentServiceListItemSchema: Краткая информация для списков
    - DocumentServiceResponseSchema: Обёртка для одиночного ответа
    - DocumentServiceListResponseSchema: Обёртка для списка сервисов

Использование:
    >>> # Детальный ответ
    >>> service = DocumentServiceDetailSchema.model_validate(service_model)
    >>> response = DocumentServiceResponseSchema(
    ...     success=True,
    ...     message="Сервис документа получен",
    ...     data=service
    ... )

    >>> # Список сервисов
    >>> services = [DocumentServiceListItemSchema.model_validate(s) for s in models]
    >>> response = DocumentServiceListResponseSchema(
    ...     success=True,
    ...     data=services
    ... )

Note:
    Все response-схемы наследуются от BaseResponseSchema и содержат
    поля success, message, data.

See Also:
    - src.schemas.v1.document_services.base: Базовые схемы
    - src.schemas.v1.document_services.requests: Схемы запросов
"""

import uuid
from typing import Any, List, Optional

from pydantic import ConfigDict, Field, field_validator

from src.models.v1.document_services import (
    CoverType,
    DocumentFileType,
)
from src.schemas.base import BaseResponseSchema, BaseSchema, CommonBaseSchema
from src.schemas.v1.document_services.base import ServiceFunctionSchema


class DocumentServiceAuthorBriefSchema(CommonBaseSchema):
    """
    Краткая схема информации об авторе сервиса документа.

    Attributes:
        username: Имя пользователя.
        email: Email автора.

    Note:
        БЕЗ id/created_at/updated_at (brief схема).

    Example:
        {
            "username": "john_doe",
            "email": "john@example.com"
        }
    """

    username: str = Field(description="Имя пользователя")
    email: str = Field(description="Email автора")


class DocumentServiceWorkspaceBriefSchema(CommonBaseSchema):
    """
    Краткая схема информации о workspace сервиса документа.

    Attributes:
        name: Название workspace.
        slug: URL-friendly идентификатор.

    Note:
        БЕЗ id/created_at/updated_at (brief схема).

    Example:
        {
            "name": "Marketing Team",
            "slug": "marketing-team"
        }
    """

    name: str = Field(description="Название workspace")
    slug: str = Field(description="URL-friendly идентификатор")


class DocumentServiceDetailSchema(BaseSchema):
    """
    Детальная схема сервиса документа для ответов API.

    Содержит полную информацию о сервисе, включая автора, workspace и JSONB поля.

    Attributes:
        id: UUID сервиса (наследуется из BaseSchema).
        title: Название сервиса документа.
        description: Описание содержимого.
        tags: Теги для поиска.
        file_url: URL файла в S3.
        file_size: Размер файла в байтах.
        file_type: Тип файла (PDF/SPREADSHEET/TEXT/IMAGE).
        cover_type: Тип обложки (GENERATED/ICON/IMAGE).
        cover_url: URL обложки в S3 (если есть).
        cover_icon: Имя иконки (если cover_type=ICON).
        available_functions: Список доступных функций (JSONB).
        author: Краткая информация об авторе.
        author_id: UUID автора.
        workspace: Краткая информация о workspace (если есть).
        workspace_id: UUID workspace (опционально).
        is_public: Публичный ли сервис.
        view_count: Количество просмотров.
        created_at: Дата создания (наследуется из BaseSchema).
        updated_at: Дата последнего обновления (наследуется из BaseSchema).

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Техническая документация",
            "description": "Руководство по эксплуатации оборудования XYZ",
            "tags": ["технический", "оборудование"],
            "file_url": "https://s3.amazonaws.com/bucket/documents/xyz.pdf",
            "file_size": 2048576,
            "file_type": "PDF",
            "cover_type": "GENERATED",
            "cover_url": "https://s3.amazonaws.com/bucket/covers/xyz_cover.jpg",
            "cover_icon": null,
            "available_functions": [
                {
                    "name": "view_pdf",
                    "enabled": true,
                    "label": "Открыть PDF",
                    "icon": "📄",
                    "config": {}
                }
            ],
            "author": {
                "username": "john_doe",
                "email": "john@example.com"
            },
            "author_id": "...",
            "workspace": {
                "name": "Marketing Team",
                "slug": "marketing-team"
            },
            "workspace_id": "...",
            "is_public": false,
            "view_count": 42,
            "created_at": "2025-11-10T08:00:00Z",
            "updated_at": "2025-11-10T10:30:00Z"
        }
    """

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(description="Название сервиса документа")
    description: Optional[str] = Field(description="Описание содержимого")
    tags: List[str] = Field(description="Теги для поиска")
    file_url: str = Field(description="URL файла в S3")
    file_size: int = Field(description="Размер файла в байтах")
    file_type: DocumentFileType = Field(description="Тип файла")
    cover_type: CoverType = Field(description="Тип обложки")
    cover_url: Optional[str] = Field(description="URL обложки в S3")
    cover_icon: Optional[str] = Field(description="Имя иконки")
    available_functions: List[ServiceFunctionSchema] = Field(
        description="Список доступных функций (JSONB)"
    )
    author: DocumentServiceAuthorBriefSchema = Field(description="Информация об авторе")
    author_id: uuid.UUID = Field(description="UUID автора")
    workspace: Optional[DocumentServiceWorkspaceBriefSchema] = Field(
        default=None,
        description="Информация о workspace"
    )
    workspace_id: Optional[uuid.UUID] = Field(description="UUID workspace")
    is_public: bool = Field(description="Публичный ли сервис")
    view_count: int = Field(description="Количество просмотров")

    @field_validator("available_functions", mode="before")
    @classmethod
    def extract_functions_from_jsonb(cls, value: Any) -> List[dict]:
        """
        Извлекает список функций из JSONB структуры.

        В модели DocumentServiceModel поле available_functions хранится как list dict.

        Args:
            value: JSONB list или dict.

        Returns:
            Список функций.

        Raises:
            ValueError: Если формат JSONB некорректен.
        """
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, dict) and "functions" in value:
            return value["functions"]

        return []


class DocumentServiceListItemSchema(BaseSchema):
    """
    Краткая схема сервиса документа для списков.

    Содержит основную информацию без вложенных связей для оптимизации.

    Attributes:
        id: UUID сервиса.
        title: Название сервиса.
        description: Краткое описание (первые 200 символов).
        tags: Теги для поиска.
        file_type: Тип файла.
        cover_url: URL обложки.
        cover_icon: Имя иконки.
        author_id: UUID автора.
        workspace_id: UUID workspace.
        is_public: Публичный ли сервис.
        view_count: Количество просмотров.
        created_at: Дата создания.

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Техническая документация",
            "description": "Руководство по эксплуатации оборудования XYZ",
            "tags": ["технический", "оборудование"],
            "file_type": "PDF",
            "cover_url": "https://s3.amazonaws.com/bucket/covers/xyz_cover.jpg",
            "cover_icon": null,
            "author_id": "...",
            "workspace_id": "...",
            "is_public": false,
            "view_count": 42,
            "created_at": "2025-11-10T08:00:00Z"
        }
    """

    model_config = ConfigDict(from_attributes=True)

    title: str = Field(description="Название сервиса")
    description: Optional[str] = Field(description="Краткое описание")
    tags: List[str] = Field(description="Теги для поиска")
    file_type: DocumentFileType = Field(description="Тип файла")
    cover_url: Optional[str] = Field(description="URL обложки")
    cover_icon: Optional[str] = Field(description="Имя иконки")
    author_id: uuid.UUID = Field(description="UUID автора")
    workspace_id: Optional[uuid.UUID] = Field(description="UUID workspace")
    is_public: bool = Field(description="Публичный ли сервис")
    view_count: int = Field(description="Количество просмотров")


class DocumentServiceResponseSchema(BaseResponseSchema):
    """
    Схема ответа для одиночного сервиса документа.

    Attributes:
        success: Флаг успешности операции.
        message: Сообщение о результате операции.
        data: Детальная информация о сервисе документа.

    Example:
        {
            "success": true,
            "message": "Сервис документа получен",
            "data": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Техническая документация",
                ...
            }
        }
    """

    data: Optional[DocumentServiceDetailSchema] = Field(
        default=None,
        description="Детальная информация о сервисе документа"
    )


class DocumentServiceListResponseSchema(BaseResponseSchema):
    """
    Схема ответа для списка сервисов документов.

    Attributes:
        success: Флаг успешности операции.
        message: Сообщение о результате операции.
        data: Список сервисов документов.
        total: Общее количество результатов (для пагинации).

    Example:
        {
            "success": true,
            "message": "Список сервисов документов",
            "data": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Техническая документация",
                    ...
                }
            ],
            "total": 15
        }
    """

    data: List[DocumentServiceListItemSchema] = Field(
        default_factory=list,
        description="Список сервисов документов"
    )
    total: Optional[int] = Field(
        default=None,
        description="Общее количество результатов (для пагинации)"
    )
