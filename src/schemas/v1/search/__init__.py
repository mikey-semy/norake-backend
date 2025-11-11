"""
Пакет схем для работы с поиском (Search) в API v1.

Экспортируемые схемы:
    Базовые:
        - SearchSourceEnum: Enum источников поиска
        - SearchResultBaseSchema: Базовая схема результата
        - SearchMetadataSchema: Схема метаданных
    
    Запросы:
        - SearchRequestSchema: Схема запроса на поиск
    
    Ответы:
        - SearchResultSchema: Схема результата в ответе
        - SearchResponseSchema: Схема полного ответа

Использование:
    >>> from src.schemas.v1.search import (
    ...     SearchRequestSchema,
    ...     SearchResponseSchema,
    ...     SearchSourceEnum
    ... )
"""

from .base import SearchMetadataSchema, SearchResultBaseSchema, SearchSourceEnum
from .requests import SearchRequestSchema
from .responses import SearchResponseSchema, SearchResultSchema

__all__ = [
    # Base
    "SearchSourceEnum",
    "SearchResultBaseSchema",
    "SearchMetadataSchema",
    # Requests
    "SearchRequestSchema",
    # Responses
    "SearchResultSchema",
    "SearchResponseSchema",
]
