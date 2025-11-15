"""
Зависимости для гибридного сервиса поиска (Hybrid Search).

Этот модуль содержит провайдеры для создания экземпляров сервисов поиска
с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_rag_search_service: Провайдер для RAGSearchService
    - get_search_service: Провайдер для SearchService (гибридный поиск)

Typed Dependencies:
    - RAGSearchServiceDep: Типизированная зависимость для RAGSearchService
    - SearchServiceDep: Типизированная зависимость для SearchService

Usage:
    ```python
    from src.core.dependencies import SearchServiceDep

    @router.post("/search")
    async def search(
        search_service: SearchServiceDep = None,
        request: SearchRequestSchema = ...,
    ) -> SearchResponseSchema:
        results, stats = await search_service.search_with_ai(request)
        return SearchResponseSchema(
            success=True,
            data=results,
            stats=stats
        )
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.cache import RedisDep
from src.core.dependencies.database import AsyncSessionDep
from src.core.integrations.ai.embeddings.openrouter import OpenRouterEmbeddings
from src.core.exceptions.base import BaseAPIException
from src.services.v1.rag_search import RAGSearchService
from src.services.v1.search import SearchService

logger = logging.getLogger(__name__)


async def get_rag_search_service(
    session: AsyncSessionDep,
) -> RAGSearchService:
    """
    Провайдер для RAGSearchService.

    Создаёт экземпляр RAGSearchService с внедрёнными зависимостями:
    - Сессия базы данных (для работы с Knowledge Base и Documents)

    Args:
        session: Асинхронная сессия базы данных.

    Returns:
        RAGSearchService: Настроенный экземпляр сервиса RAG поиска.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        @router.post("/rag/search")
        async def rag_search(
            rag_service: RAGSearchServiceDep = None,
            query: str = ...,
            kb_id: UUID = ...,
        ):
            results = await rag_service.search(query, kb_id)
            return results
        ```
    """
    try:
        logger.debug("Создание экземпляра RAGSearchService")
        # Создаём OpenRouter embeddings клиент
        openrouter_client = OpenRouterEmbeddings()
        return RAGSearchService(session=session, openrouter_client=openrouter_client)
    except BaseAPIException:
        # Пробрасываем бизнес-исключения (например, OpenRouterConfigError)
        raise
    except Exception as e:
        logger.error(
            "Ошибка при создании RAGSearchService: %s", str(e), exc_info=True
        )
        raise


async def get_search_service(
    session: AsyncSessionDep,
    redis: RedisDep,
    rag_service: Annotated[RAGSearchService, Depends(get_rag_search_service)],
) -> SearchService:
    """
    Провайдер для SearchService (гибридный поиск).

    Создаёт экземпляр SearchService с внедрёнными зависимостями:
    - Сессия базы данных (для DB search через IssueRepository)
    - Redis клиент (для кеширования результатов)
    - RAGSearchService (для семантического поиска по Knowledge Base)

    Гибридный поиск объединяет результаты из трёх источников:
    - DB search: Поиск по Issues в PostgreSQL (всегда выполняется)
    - RAG search: Семантический поиск через pgvector (если use_ai=True)
    - MCP search: Умный поиск через n8n webhook (если use_ai=True)

    Args:
        session: Асинхронная сессия базы данных.
        redis: Redis клиент для кеширования.
        rag_service: Сервис RAG поиска.

    Returns:
        SearchService: Настроенный экземпляр гибридного поиска.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        @router.post("/api/v1/search")
        async def hybrid_search(
            search_service: SearchServiceDep = None,
            request: SearchRequestSchema = ...,
        ):
            results, stats = await search_service.search_with_ai(request)
            return SearchResponseSchema(
                success=True,
                data=results,
                stats=stats
            )
        ```
    """
    try:
        logger.debug("Создание экземпляра SearchService")
        return SearchService(
            session=session,
            redis=redis,
            rag_service=rag_service,
        )
    except BaseAPIException:
        # Пробрасываем бизнес-исключения (например, OpenRouterConfigError)
        raise
    except Exception as e:
        logger.error(
            "Ошибка при создании SearchService: %s", str(e), exc_info=True
        )
        raise


# Типизированные зависимости для удобства использования
RAGSearchServiceDep = Annotated[RAGSearchService, Depends(get_rag_search_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
