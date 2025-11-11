"""
Базовые схемы для работы с поиском (Search) в API v1.

Этот модуль содержит основные Pydantic схемы для валидации данных поиска.
Схемы используются как базовые классы для request и response схем.

Схемы:
    - SearchSourceEnum: Enum для источников поиска (DB/RAG/MCP)
    - SearchResultBaseSchema: Базовая схема для результата поиска
    - SearchMetadataSchema: Схема для метаданных поиска

Использование:
    >>> # Базовый результат поиска
    >>> result = SearchResultBaseSchema(
    ...     id=uuid4(),
    ...     title="Ошибка E401",
    ...     content="Проблема с оборудованием",
    ...     source="db",
    ...     score=0.95
    ... )

Note:
    Все схемы наследуются от CommonBaseSchema и используют Field() для
    детального описания полей и валидации.

See Also:
    - src.schemas.v1.search.requests: Схемы для входящих запросов
    - src.schemas.v1.search.responses: Схемы для HTTP ответов
    - src.services.v1.search: SearchService для бизнес-логики
"""

import uuid
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import Field

from src.schemas.base import CommonBaseSchema


class SearchSourceEnum(str, Enum):
    """
    Enum для источников результатов поиска.

    Values:
        DB: Результат из базы данных (Issues).
        RAG: Результат из RAG поиска (Knowledge Base).
        MCP: Результат из n8n MCP smart search.

    Example:
        >>> source = SearchSourceEnum.DB
        >>> source.value
        'db'
    """

    DB = "db"
    RAG = "rag"
    MCP = "mcp"


class SearchPatternEnum(str, Enum):
    """
    Enum для паттерна поиска.

    Values:
        MATCH: Простой матч (по умолчанию).
        PHRASE: Поиск точной фразы.
        FUZZY: Нечёткий поиск.
    """

    MATCH = "match"
    PHRASE = "phrase"
    FUZZY = "fuzzy"


class SearchResultSchema(CommonBaseSchema):
    """
    Базовая схема для результата поиска.

    Используется для представления единичного результата из любого источника.

    Attributes:
        id: UUID результата (Issue ID или Document ID).
        title: Заголовок результата.
        content: Содержимое результата (описание Issue или фрагмент документа).
        source: Источник результата (db/rag/mcp).
        score: Оценка релевантности (0.0-1.0).
        metadata: Дополнительные метаданные (категория, дата, приоритет и т.д.).

    Example:
        >>> result = SearchResultSchema(
        ...     id=uuid4(),
        ...     title="Ошибка E401",
        ...     content="При запуске станка возникает ошибка",
        ...     source="db",
        ...     score=0.95,
        ...     metadata={"category": "equipment", "priority": "high"}
        ... )
    """

    id: uuid.UUID = Field(
        description="UUID результата (Issue ID или Document ID)",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    title: str = Field(
        description="Заголовок результата",
        examples=["Ошибка E401 на станке №3"],
    )
    content: str = Field(
        description="Содержимое результата",
        examples=["При запуске станка возникает ошибка E401"],
    )
    source: SearchSourceEnum = Field(
        description="Источник результата (db/rag/mcp)",
        examples=["db", "rag", "mcp"],
    )
    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Оценка релевантности (0.0-1.0)",
        examples=[0.95, 0.87, 0.76],
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Дополнительные метаданные результата (категория, дата и т.д.)",
        examples=[{"category": "equipment", "date": "2024-11-10", "priority": "high"}],
    )


class SearchStatsSchema(CommonBaseSchema):
    """
    Схема для статистики поиска.

    Содержит информацию о выполненном поиске и статистику.

    Attributes:
        total_results: Общее количество результатов.
        db_results: Количество результатов из DB.
        rag_results: Количество результатов из RAG.
        mcp_results: Количество результатов из MCP.
        search_time_ms: Время выполнения поиска (миллисекунды).
        cached: Флаг кеширования (результаты из Redis).
    """

    total_results: int = Field(
        ge=0,
        description="Общее количество результатов",
        examples=[15],
    )
    db_results: int = Field(
        ge=0,
        description="Количество результатов из DB",
        examples=[5],
    )
    rag_results: int = Field(
        ge=0,
        description="Количество результатов из RAG",
        examples=[7],
    )
    mcp_results: int = Field(
        ge=0,
        description="Количество результатов из MCP",
        examples=[3],
    )
    search_time_ms: float = Field(
        ge=0.0,
        description="Время выполнения поиска (миллисекунды)",
        examples=[234.5],
    )
    cached: bool = Field(
        default=False,
        description="Флаг кеширования (результаты из Redis)",
        examples=[False, True],
    )
