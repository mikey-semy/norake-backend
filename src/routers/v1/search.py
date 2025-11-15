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
Роутеры передают параметры в SearchService с visibility context.
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
        POST /search/public - Поиск по публичным Issues (visibility=public)

    Архитектурные особенности:
        - Поиск ТОЛЬКО по публичным Issues (visibility=public)
        - Без AI/RAG по умолчанию (use_ai=false для безопасности)
        - Ограниченные фильтры (статус, категория)
        - Быстрый доступ к коллективной памяти решений
        - Redis кэширование с изоляцией публичных результатов
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
            deprecated=True,
            description="""
            ## ⚠️ DEPRECATED: Используйте /document-services с RAG

            ## 🔍 Публичный поиск по решениям проблем

            **⚠️ УСТАРЕЛО**: Этот эндпоинт будет удалён.
            Используйте `/api/v1/document-services` с RAG для семантического поиска.

            Быстрый поиск по коллективной памяти решений **без аутентификации**.
            Возвращает только публичные Issues (visibility=public).

            ### 🌐 Публичный доступ (без токена)

            ### Request Body (SearchRequestSchema):
            * **query** *(required)*: Поисковый запрос (1-500 символов)
            * **use_ai**: Использовать AI (по умолчанию false для публичных запросов)
            * **pattern**: Паттерн поиска (match/phrase/fuzzy, по умолчанию match)
            * **limit**: Макс. результатов (1-100, по умолчанию 20)
            * **min_score**: Минимальный score (0.0-1.0, по умолчанию 0.0)
            * **filters**: Фильтры (categories, statuses)

            **Note**: workspace_id, kb_id, filters.author_id игнорируются в публичном API.

            ### Response (SearchResponseSchema):
            * **success**: Успешность запроса
            * **data**: Объект с результатами:
              - **results**: Список SearchResultDetailSchema (только PUBLIC)
              - **stats**: Статистика (total, источники, query_time)

            ### Redis кэширование:
            * **TTL**: 300 секунд (5 минут)
            * **Key**: MD5 хэш от query + filters + public_only=true
            * **Изоляция**: Публичные и приватные результаты кэшируются отдельно

            ### Примеры использования:

            **1. Простой поиск проблемы:**
            ```json
            {
              "query": "ошибка подключения к базе данных",
              "limit": 10
            }
            ```

            **2. Поиск с фильтрами:**
            ```json
            {
              "query": "ошибка авторизации",
              "filters": {
                "categories": ["software", "security"],
                "statuses": ["green"]
              },
              "limit": 20
            }
            ```

            **3. Поиск по категории:**
            ```json
            {
              "query": "станок не запускается",
              "filters": {
                "categories": ["hardware", "maintenance"]
              },
              "pattern": "phrase"
            }
            ```

            ### Returns:
            * **SearchResponseSchema**: Публичные результаты с метриками

            ### Errors:
            * **400**: Невалидный запрос (query < 1 char)
            * **408**: Timeout поиска
            * **500**: Внутренняя ошибка сервера
            """,
        )
        async def search_public(
            search_service: SearchServiceDep = None,
            request: SearchRequestSchema = Body(..., description="Параметры публичного поиска"),
        ) -> SearchResponseSchema:
            """
            Публичный поиск по Issues (только visibility=public).

            Args:
                search_service: Сервис гибридного поиска (DI)
                request: Параметры поиска (query, filters, pattern)

            Returns:
                SearchResponseSchema: Результаты поиска (только публичные)

            Raises:
                ValueError: Невалидный запрос (автоматически → 400)
                SearchTimeoutError: Timeout поиска (автоматически → 408)
                SearchError: Ошибка поиска (автоматически → 500)
            """
            # Публичный поиск: use_ai=false, public_only=true, no user context
            return await search_service.search_with_ai(
                query=request.query,
                workspace_id=None,  # Игнорируем workspace_id в публичном API
                use_ai=False,  # Без AI для безопасности (RAG может содержать приватные данные)
                kb_id=None,
                pattern=request.pattern,
                limit=request.limit,
                min_score=request.min_score,
                filters=request.filters,
                current_user_id=None,
                is_admin=False,
                public_only=True,  # КРИТИЧНО: только публичные Issues
            )


class SearchProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для гибридного поиска.

    Предоставляет HTTP API для полного поиска с AI-интеграцией:

    Protected Endpoints (требуется токен):
        POST /search - Гибридный поиск (DB + RAG + MCP) с visibility правилами

    Архитектурные особенности:
        - Требует аутентификацию (CurrentUserDep)
        - Применяет visibility rules (PUBLIC + WORKSPACE + PRIVATE)
        - Полный AI-поиск (RAG + MCP) если use_ai=true
        - Admin override (админ видит всё)
        - Кэш изолирован по user_id/workspace_id
    """

    def __init__(self):
        """Инициализирует SearchProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="search", tags=["Search"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== PROTECTED SEARCH ====================

        @self.router.post(
            path="",
            response_model=SearchResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔍 Гибридный поиск с AI-интеграцией

            Полный поиск с visibility правилами и AI (RAG + MCP).

            ### 🔒 Требуется аутентификация

            ### Visibility правила:
            * **PUBLIC**: Видны всем (включая anonymous)
            * **WORKSPACE**: Видны только участникам воркспейса + админам
            * **PRIVATE**: Видны только автору + админам
            * **Admin override**: Админ видит все Issues

            ### Request Body (SearchRequestSchema):
            * **query** *(required)*: Поисковый запрос (1-500 символов)
            * **workspace_id**: UUID воркспейса (для WORKSPACE visibility)
            * **use_ai**: Использовать AI (RAG + MCP), по умолчанию true
            * **kb_id**: UUID Knowledge Base для RAG поиска
            * **pattern**: Паттерн поиска (match/phrase/fuzzy)
            * **limit**: Макс. результатов (1-100, по умолчанию 20)
            * **min_score**: Минимальный score (0.0-1.0)
            * **filters**: Фильтры (categories, statuses, author_id, date_range)

            ### Response (SearchResponseSchema):
            * **success**: Успешность запроса
            * **data**: Объект с результатами:
              - **results**: Список SearchResultDetailSchema (с учётом visibility)
              - **stats**: Статистика (total, источники, query_time)

            ### Примеры использования:

            **1. Полный поиск с AI:**
            ```json
            {
              "query": "проблема с подключением к базе данных",
              "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
              "use_ai": true,
              "limit": 10
            }
            ```

            **2. RAG-поиск по Knowledge Base:**
            ```json
            {
              "query": "как настроить OAuth2",
              "use_ai": true,
              "kb_id": "550e8400-e29b-41d4-a716-446655440000",
              "limit": 5
            }
            ```

            **3. Поиск с фильтрами:**
            ```json
            {
              "query": "ошибка авторизации",
              "workspace_id": "123e4567-e89b-12d3-a456-426614174000",
              "filters": {
                "categories": ["software"],
                "statuses": ["red"],
                "date_from": "2024-01-01T00:00:00Z"
              }
            }
            ```

            ### Returns:
            * **SearchResponseSchema**: Результаты с visibility фильтрацией

            ### Errors:
            * **400**: Невалидный запрос
            * **401**: Не авторизован
            * **408**: Timeout поиска
            * **500**: Внутренняя ошибка сервера
            """,
        )
        async def search_protected(
            current_user: CurrentUserDep = None,
            search_service: SearchServiceDep = None,
            request: SearchRequestSchema = Body(..., description="Параметры поиска"),
        ) -> SearchResponseSchema:
            """
            Гибридный поиск с visibility правилами и AI.

            Args:
                current_user: Текущий пользователь из JWT токена
                search_service: Сервис гибридного поиска (DI)
                request: Параметры поиска (query, workspace_id, use_ai, filters)

            Returns:
                SearchResponseSchema: Результаты поиска с visibility фильтрацией

            Raises:
                ValueError: Невалидный запрос (автоматически → 400)
                SearchTimeoutError: Timeout поиска (автоматически → 408)
                SearchError: Ошибка поиска (автоматически → 500)
            """
            # TODO: Проверить роль админа через current_user.role == 'admin'
            # Blocked: требуется UserModel с полем role
            is_admin = False  # Placeholder до реализации role system

            # Полный поиск с visibility правилами
            return await search_service.search_with_ai(
                query=request.query,
                workspace_id=request.workspace_id,
                use_ai=request.use_ai,
                kb_id=request.kb_id,
                pattern=request.pattern,
                limit=request.limit,
                min_score=request.min_score,
                filters=request.filters,
                current_user_id=current_user.id,
                is_admin=is_admin,
                public_only=False,
            )
