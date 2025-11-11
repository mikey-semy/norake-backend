"""
Роутеры для гибридного поиска (Hybrid Search).

Модуль предоставляет HTTP API для умного поиска по базе знаний:
- SearchPublicRouter (BaseRouter) - публичный поиск по публичным Issues
- SearchProtectedRouter (ProtectedRouter) - полный поиск с приватными данными

Архитектура поиска:
    1. Поиск в БД (IssueRepository) - priority 1.0
    2. RAG поиск (pgvector) - priority 0.8
    3. MCP поиск (n8n webhook) - priority 0.6
    4. Взвешенное ранжирование результатов
    5. Redis кэширование (300s TTL)

Обработка исключений: автоматическая обработка через глобальный exception handler.
Роутеры преобразуют результаты SearchService в SearchResponseSchema.
"""

from fastapi import status, Body

from src.core.dependencies.search import SearchServiceDep
from src.core.security import CurrentUserDep
from src.routers.base import BaseRouter, ProtectedRouter
from src.schemas.v1.search import (
    SearchRequestSchema,
    SearchResponseSchema,
)


class SearchPublicRouter(BaseRouter):
    """
    Публичный роутер для поиска решений проблем.

    Предоставляет HTTP API для быстрого доступа к решениям:

    Public Endpoints (без аутентификации):
        POST /search/public - Поиск по публичным Issues

    Архитектурные особенности:
        - Поиск ТОЛЬКО по публичным Issues (visibility=public)
        - Без RAG (Knowledge Base может содержать приватные документы)
        - Ограниченные фильтры (статус, категория)
        - Быстрый доступ к коллективной памяти решений
        - Redis кэширование результатов
    """

    def __init__(self):
        """Инициализирует SearchPublicRouter с префиксом и тегами."""
        super().__init__(prefix="search", tags=["Search"])

    def configure(self):
        """Настройка публичных endpoint'ов роутера."""

        # ==================== PUBLIC SEARCH ====================

        @self.router.post(
            path="/public",
            response_model=SearchResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔍 Публичный поиск решений проблем

            Быстрый поиск по коллективной памяти решений БЕЗ регистрации.
            Ищет только среди публичных Issues (visibility=public).

            ### 🌐 Публичный доступ (без токена)

            ### Request Body (SearchRequestSchema):
            * **query** *(required)*: Поисковый запрос (1-500 символов)
            * **pattern**: Паттерн поиска (match/phrase/fuzzy)
            * **limit**: Макс. результатов (1-100, по умолчанию 20)
            * **min_score**: Минимальный score (0.0-1.0)
            * **filters**: Фильтры:
              - **categories**: Список категорий (hardware/software/process и т.д.)
              - **statuses**: Список статусов (red/green)

            ⚠️ **Ограничения**:
            - Только публичные Issues (приватные воркспейсов недоступны)
            - Без RAG/AI поиска (использует только БД)
            - workspace_id, kb_id, author_id, date_range игнорируются

            ### Response (SearchResponseSchema):
            * **success**: Успешность запроса
            * **data**: Объект с результатами:
              - **results**: Список SearchResultDetailSchema
              - **stats**: Статистика (total, источники, query_time)

            ### Примеры использования:

            **1. Поиск решения:**
            ```json
            {
              "query": "проблема с подключением к базе данных",
              "limit": 10
            }
            ```

            **2. Поиск с фильтрами:**
            ```json
            {
              "query": "ошибка деплоя",
              "filters": {
                "categories": ["software"],
                "statuses": ["green"]
              },
              "limit": 20,
              "min_score": 0.7
            }
            ```

            **3. Точный поиск фразы:**
            ```json
            {
              "query": "connection timeout",
              "pattern": "phrase",
              "limit": 15
            }
            ```

            ### Returns:
            * **SearchResponseSchema**: Результаты поиска с метаданными

            ### Errors:
            * **400**: Невалидный запрос (query < 1 char)
            * **408**: Timeout поиска
            * **500**: Внутренняя ошибка сервера
            """,
        )
        async def search_public(
            search_service: SearchServiceDep = None,
            request: SearchRequestSchema = Body(..., description="Параметры поиска"),
        ) -> SearchResponseSchema:
            """
            Выполняет публичный поиск по Issues.

            Args:
                search_service: Сервис гибридного поиска (DI)
                request: Параметры поиска (query, filters)

            Returns:
                SearchResponseSchema: Результаты поиска (только публичные Issues)

            Raises:
                ValueError: Невалидный запрос (автоматически → 400)
                SearchTimeoutError: Timeout поиска (автоматически → 408)
                SearchError: Ошибка поиска (автоматически → 500)
            """
            # Публичный поиск: только БД, без AI/RAG, без workspace_id
            result = await search_service.search_with_ai(
                query=request.query,
                workspace_id=None,  # Публичный поиск - без привязки к воркспейсу
                use_ai=False,  # Без RAG/MCP (может содержать приватные данные)
                kb_id=None,
                pattern=request.pattern,
                limit=request.limit,
                min_score=request.min_score,
                filters=request.filters,
            )

            return result


class SearchProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для полного поиска.

    Предоставляет HTTP API для расширенного поиска с AI:

    Protected Endpoints (требуется токен):
        POST /search - Полный поиск (DB + RAG + MCP)

    Архитектурные особенности:
        - Требует аутентификацию (CurrentUserDep)
        - Доступ ко ВСЕМ Issues (публичные + приватные воркспейса)
        - Полный AI-поиск (RAG через pgvector + MCP через n8n)
        - Все фильтры доступны (workspace_id, author, даты)
        - Redis кэширование результатов
    """

    def __init__(self):
        """Инициализирует SearchProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="search", tags=["Search"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== FULL SEARCH ====================

        @self.router.post(
            path="",
            response_model=SearchResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔍 Полный поиск с AI-интеграцией

            Расширенный поиск с доступом к приватным данным и AI.
            Комбинирует три источника:
            1. **DB Search** - все Issues (публичные + приватные) - priority 1.0
            2. **RAG Search** - семантический поиск через pgvector - priority 0.8
            3. **MCP Search** - поиск через n8n smart-search webhook - priority 0.6

            ### 🔒 Требуется аутентификация

            ### Request Body (SearchRequestSchema):
            * **query** *(required)*: Поисковый запрос (1-500 символов)
            * **workspace_id**: UUID воркспейса (доступ к приватным Issues)
            * **use_ai**: Использовать AI (RAG + MCP), по умолчанию true
            * **kb_id**: UUID Knowledge Base для RAG поиска
            * **pattern**: Паттерн поиска (match/phrase/fuzzy)
            * **limit**: Макс. результатов (1-100, по умолчанию 20)
            * **min_score**: Минимальный score (0.0-1.0)
            * **filters**: Полные фильтры:
              - **categories**: Список категорий
              - **statuses**: Список статусов
              - **author_id**: UUID автора
              - **date_from/date_to**: Временной диапазон

            ### Response (SearchResponseSchema):
            * **success**: Успешность запроса
            * **data**: Объект с результатами:
              - **results**: Список SearchResultDetailSchema
              - **stats**: Статистика (total, источники, query_time)

            ### SearchResultDetailSchema:
            * **id**: UUID результата
            * **title**: Заголовок
            * **content**: Контент (excerpt)
            * **source**: Источник (database/rag/mcp_n8n)
            * **score**: Релевантность (0.0-1.0)
            * **metadata**: Дополнительные данные (category, author, timestamps)

            ### Примеры использования:

            **1. Полный поиск с AI:**
            ```json
            {
              "query": "проблема с подключением к базе данных",
              "use_ai": true,
              "limit": 10
            }
            ```

            **2. Поиск в воркспейсе:**
            ```json
            {
              "query": "ошибка авторизации",
              "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
              "filters": {
                "categories": ["software", "security"],
                "statuses": ["red"]
              },
              "limit": 20
            }
            ```

            **3. RAG-поиск по Knowledge Base:**
            ```json
            {
              "query": "как настроить OAuth2",
              "use_ai": true,
              "kb_id": "550e8400-e29b-41d4-a716-446655440000",
              "limit": 5
            }
            ```

            ### Returns:
            * **SearchResponseSchema**: Взвешенные результаты с метаданными

            ### Errors:
            * **400**: Невалидный запрос
            * **401**: Не авторизован
            * **408**: Timeout поиска
            * **500**: Внутренняя ошибка сервера
            """,
        )
        async def search_full(
            current_user: CurrentUserDep = None,
            search_service: SearchServiceDep = None,
            request: SearchRequestSchema = Body(..., description="Параметры поиска"),
        ) -> SearchResponseSchema:
            """
            Выполняет полный поиск с AI-интеграцией.

            Args:
                current_user: Текущий пользователь из JWT токена
                search_service: Сервис гибридного поиска (DI)
                request: Параметры поиска (query, filters, AI settings)

            Returns:
                SearchResponseSchema: Результаты поиска с взвешенным ранжированием

            Raises:
                ValueError: Невалидный запрос (автоматически → 400)
                SearchTimeoutError: Timeout поиска (автоматически → 408)
                SearchError: Ошибка поиска (автоматически → 500)
            """
            # Выполняем полный гибридный поиск (DB + RAG + MCP)
            result = await search_service.search_with_ai(
                query=request.query,
                workspace_id=request.workspace_id,
                use_ai=request.use_ai,
                kb_id=request.kb_id,
                pattern=request.pattern,
                limit=request.limit,
                min_score=request.min_score,
                filters=request.filters,
            )

            return result
