"""
Схемы для работы с сервисами документов (Document Services) в API v1.

Экспортируемые схемы:
    Base:
        - ServiceFunctionSchema: Конфигурация функции сервиса
        - DocumentServiceBaseSchema: Базовая схема сервиса документа
    
    Requests:
        - DocumentServiceCreateRequestSchema: Создание сервиса
        - DocumentServiceUpdateRequestSchema: Обновление сервиса
        - DocumentServiceQueryRequestSchema: Фильтрация и поиск
        - DocumentFunctionAddRequestSchema: Добавление функции
    
    Responses:
        - DocumentServiceAuthorBriefSchema: Краткая информация об авторе
        - DocumentServiceWorkspaceBriefSchema: Краткая информация о workspace
        - DocumentServiceDetailSchema: Детальная информация о сервисе
        - DocumentServiceListItemSchema: Краткая информация для списков
        - DocumentServiceResponseSchema: Обёртка одиночного ответа
        - DocumentServiceListResponseSchema: Обёртка списка

Использование:
    >>> from src.schemas.v1.document_services import (
    ...     DocumentServiceCreateRequestSchema,
    ...     DocumentServiceResponseSchema,
    ...     DocumentServiceDetailSchema
    ... )
"""

from .base import (
    DocumentServiceBaseSchema,
    ServiceFunctionSchema,
)
from .requests import (
    DocumentFunctionAddRequestSchema,
    DocumentServiceCreateRequestSchema,
    DocumentServiceQueryRequestSchema,
    DocumentServiceUpdateRequestSchema,
)
from .responses import (
    DocumentServiceAuthorBriefSchema,
    DocumentServiceDetailSchema,
    DocumentServiceListItemSchema,
    DocumentServiceListResponseSchema,
    DocumentServiceResponseSchema,
    DocumentServiceWorkspaceBriefSchema,
)

__all__ = [
    # Base
    "ServiceFunctionSchema",
    "DocumentServiceBaseSchema",
    # Requests
    "DocumentServiceCreateRequestSchema",
    "DocumentServiceUpdateRequestSchema",
    "DocumentServiceQueryRequestSchema",
    "DocumentFunctionAddRequestSchema",
    # Responses
    "DocumentServiceAuthorBriefSchema",
    "DocumentServiceWorkspaceBriefSchema",
    "DocumentServiceDetailSchema",
    "DocumentServiceListItemSchema",
    "DocumentServiceResponseSchema",
    "DocumentServiceListResponseSchema",
]
