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

from .base import SearchStatsSchema, SearchResultSchema, SearchSourceEnum, SearchPatternEnum
from .requests import SearchRequestSchema, SearchFiltersRequestSchema
from .responses import SearchResponseSchema, SearchResultDetailSchema

__all__ = [
    # Base
    "SearchSourceEnum",
    "SearchPatternEnum",
    "SearchResultSchema",
    "SearchStatsSchema",
    # Requests
    "SearchRequestSchema",
    "SearchFiltersRequestSchema",
    # Responses
    "SearchResultDetailSchema",
    "SearchResponseSchema",
]
