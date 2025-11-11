"""
Схемы ответов для работы с поиском (Search) в API v1.

Этот модуль содержит Pydantic схемы для форматирования HTTP ответов
при работе с поиском.

Схемы:
    - SearchResultSchema: Детальная информация о результате поиска
    - SearchResponseSchema: Обёртка для ответа с результатами поиска

Использование:
    >>> # Формирование ответа с результатами
    >>> results = [SearchResultSchema.model_validate(r) for r in search_results]
    >>> metadata = SearchMetadataSchema(
    ...     total_results=len(results),
    ...     db_results=5,
    ...     rag_results=3,
    ...     mcp_results=2,
    ...     search_time_ms=234.5
    ... )
    >>> response = SearchResponseSchema(
    ...     success=True,
    ...     message="Найдено 10 результатов",
    ...     data=results,
    ...     metadata=metadata
    ... )

Note:
    Все response-схемы наследуются от BaseResponseSchema и содержат
    поля success, message, data.

See Also:
    - src.schemas.v1.search.base: Базовые схемы
    - src.schemas.v1.search.requests: Схемы запросов
    - src.services.v1.search: SearchService
"""

from typing import List, Optional

from pydantic import Field

from src.schemas.base import BaseResponseSchema
from .base import SearchStatsSchema, SearchResultBaseSchema


class SearchResultSchema(SearchResultBaseSchema):
    """
    Детальная схема результата поиска для ответов API.

    Наследует все поля из SearchResultBaseSchema.

    Attributes:
        id: UUID результата (наследуется).
        title: Заголовок результата (наследуется).
        content: Содержимое результата (наследуется).
        source: Источник результата (наследуется).
        score: Оценка релевантности (наследуется).
        metadata: Дополнительные метаданные результата (наследуется).

    Example:
        {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Ошибка E401 на станке №3",
            "content": "При запуске станка возникает ошибка E401",
            "source": "db",
            "score": 0.95,
            "metadata": {
                "category": "hardware",
                "status": "red",
                "author": "john_doe"
            }
        }
    """

    model_config = SearchResultBaseSchema.model_config


class SearchResponseSchema(BaseResponseSchema):
    """
    Схема ответа для результатов поиска.

    Содержит список результатов и метаданные поиска.

    Attributes:
        success: Флаг успешности операции (наследуется).
        message: Сообщение о результате (наследуется).
        data: Список результатов поиска.
        stats: Статистика поиска (общее число, время, разбивка по источникам).

    Example:
        {
            "success": true,
            "message": "Найдено 10 результатов",
            "data": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "title": "Ошибка E401",
                    "content": "Проблема с оборудованием",
                    "source": "db",
                    "score": 0.95,
                    "metadata": {"category": "hardware"}
                },
                ...
            ],
            "metadata": {
                "total_results": 10,
                "db_results": 5,
                "rag_results": 3,
                "mcp_results": 2,
                "search_time_ms": 234.5,
                "cached": false
            }
        }
    """

    data: List[SearchResultSchema] = Field(
        default=[],
        description="Список результатов поиска",
    )
    stats: Optional[SearchStatsSchema] = Field(
        None,
        description="Статистика поиска (количество результатов, время выполнения, кеш)",
    )
