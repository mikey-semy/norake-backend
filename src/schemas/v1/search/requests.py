"""
Схемы запросов для работы с поиском (Search) в API v1.

Этот модуль содержит Pydantic схемы для валидации входящих запросов
при работе с поиском.

Схемы:
    - SearchRequestSchema: Выполнение гибридного поиска

Использование:
    >>> # Поиск с AI
    >>> search_data = SearchRequestSchema(
    ...     query="ошибка E401 на станке",
    ...     workspace_id=uuid4(),
    ...     use_ai=True,
    ...     limit=10
    ... )
    
    >>> # Простой поиск по DB
    >>> search_data = SearchRequestSchema(
    ...     query="ошибка станка",
    ...     workspace_id=uuid4(),
    ...     use_ai=False
    ... )

Note:
    Все схемы наследуются от BaseRequestSchema и не содержат
    системных полей (id, created_at, updated_at).

See Also:
    - src.schemas.v1.search.base: Базовые схемы
    - src.schemas.v1.search.responses: Схемы ответов
    - src.services.v1.search: SearchService
"""

from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseRequestSchema
from .base import SearchPatternEnum


class SearchRequestSchema(BaseRequestSchema):
    """
    Схема для выполнения гибридного поиска.

    Attributes:
        query: Поисковый запрос (обязательно, 1-500 символов).
        workspace_id: UUID рабочего пространства для поиска.
        use_ai: Флаг использования AI (RAG + n8n MCP). По умолчанию True.
        kb_id: UUID Knowledge Base для RAG поиска (опционально).
        limit: Максимальное количество результатов (1-100, по умолчанию 10).
        min_score: Минимальный порог релевантности (0.0-1.0, по умолчанию 0.5).

    Note:
        Процесс поиска:
        1. DB search (ВСЕГДА) - поиск Issues в workspace
        2. Если use_ai=True:
           - RAG search (поиск в KB с embeddings)
           - n8n MCP smart search (webhook)
        3. Объединение результатов с ранжированием:
           - DB results: priority 1.0
           - RAG results: priority 0.8
           - MCP results: priority 0.6
        4. Redis кеширование (TTL 5 минут)

    Example:
        POST /api/v1/search
        {
            "query": "ошибка E401 на станке №3",
            "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
            "use_ai": true,
            "kb_id": "456e7890-e89b-12d3-a456-426614174111",
            "limit": 10,
            "min_score": 0.5
        }
    """

    query: str = Field(
        min_length=1,
        max_length=500,
        description="Поисковый запрос",
        examples=["ошибка E401 на станке №3", "проблема с датчиком"],
    )
    workspace_id: UUID = Field(
        description="UUID рабочего пространства для поиска",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    use_ai: bool = Field(
        default=True,
        description="Флаг использования AI (RAG + n8n MCP smart search)",
        examples=[True, False],
    )
    kb_id: Optional[UUID] = Field(
        None,
        description="UUID Knowledge Base для RAG поиска (если use_ai=True)",
        examples=["456e7890-e89b-12d3-a456-426614174111"],
    )
    pattern: SearchPatternEnum = Field(
        default=SearchPatternEnum.MATCH,
        description="Паттерн поиска: match|phrase|fuzzy",
        examples=["match", "phrase", "fuzzy"],
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Максимальное количество результатов",
        examples=[10, 20, 50],
    )
    min_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Минимальный порог релевантности (0.0-1.0)",
        examples=[0.5, 0.7, 0.8],
    )
