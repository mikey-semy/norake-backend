"""
Гибридный сервис поиска (Hybrid Search Service).

Объединяет результаты из трёх источников:
- DB search: Поиск по Issues в PostgreSQL (всегда выполняется)
- RAG search: Семантический поиск по Knowledge Base через pgvector
- MCP search: Умный поиск через n8n webhook

Ранжирование результатов:
- DB results: priority 1.0 (высший приоритет)
- RAG results: priority 0.8
- MCP results: priority 0.6

Redis кеширование с TTL 5 минут для оптимизации повторных запросов.
"""

import hashlib
import json
import logging
import time
from typing import List, Optional
from uuid import UUID

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.repository.v1.issues import IssueRepository
from src.schemas.v1.search.base import (
    SearchPatternEnum,
    SearchResultSchema,
    SearchSourceEnum,
    SearchStatsSchema,
)
from src.schemas.v1.search.requests import SearchFiltersRequestSchema
from src.schemas.v1.search.responses import SearchResultDetailSchema, SearchResponseSchema
from src.services.base import BaseService
from src.services.v1.rag_search import RAGSearchService

logger = logging.getLogger(__name__)


class SearchService(BaseService):
    """
    Гибридный сервис поиска с объединением DB + RAG + MCP результатов.

    Attributes:
        session: AsyncSession для работы с БД
        redis: Redis клиент для кеширования
        rag_service: RAGSearchService для семантического поиска
        issue_repository: Repository для работы с Issues

    Methods:
        search_with_ai: Основной метод поиска с поддержкой AI
        _search_db: Поиск по Issues в БД
        _search_rag: Семантический поиск по Knowledge Base
        _search_mcp: Умный поиск через n8n webhook
        _merge_and_rank: Объединение и ранжирование результатов
        _cache_results: Сохранение результатов в Redis
        _get_cached_results: Получение результатов из Redis

    Example:
        >>> service = SearchService(session=session, redis=redis, rag_service=rag)
        >>> response = await service.search_with_ai(
        ...     query="ошибка E401",
        ...     workspace_id=workspace_uuid,
        ...     use_ai=True,
        ...     kb_id=kb_uuid,
        ...     current_user_id=user_uuid,
        ...     is_admin=False,
        ...     public_only=False,
        ... )
    """

    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        rag_service: RAGSearchService,
    ):
        """
        Инициализация Hybrid Search Service.

        Args:
            session: Async SQLAlchemy сессия
            redis: Redis клиент для кеширования
            rag_service: RAGSearchService для семантического поиска
        """
        super().__init__(session)
        self.redis = redis
        self.rag_service = rag_service
        self.issue_repository = IssueRepository(session)

    async def search_with_ai(
        self,
        query: str,
        workspace_id: Optional[UUID] = None,
        use_ai: bool = True,
        kb_id: Optional[UUID] = None,
        pattern: SearchPatternEnum = SearchPatternEnum.MATCH,
        limit: int = 20,
        min_score: float = 0.0,
        filters: Optional[SearchFiltersRequestSchema] = None,
        current_user_id: Optional[UUID] = None,
        is_admin: bool = False,
        public_only: bool = False,
    ) -> SearchResponseSchema:
        """
        Гибридный поиск с объединением результатов из всех источников.

        Процесс:
        1. Проверка кеша Redis (ключ от query + filters + visibility context)
        2. DB search (всегда выполняется) с visibility фильтрацией
        3. Если use_ai=True:
           - RAG search (если указан kb_id)
           - MCP search (через n8n webhook)
        4. Объединение результатов с ранжированием
        5. Сохранение в кеш

        Visibility правила (применяются в DB search):
            - public_only=True: только PUBLIC issues (для публичного API)
            - is_admin=True: доступ ко всем issues
            - current_user_id + workspace_id: PUBLIC + WORKSPACE + PRIVATE (автор)
            - current_user_id only: PUBLIC + PRIVATE (автор)
            - None: только PUBLIC

        Args:
            query: Поисковый запрос (1-500 символов)
            workspace_id: UUID воркспейса (для WORKSPACE visibility)
            use_ai: Использовать AI поиск (RAG + MCP)
            kb_id: UUID Knowledge Base для RAG
            pattern: Паттерн поиска (MATCH/PHRASE/FUZZY)
            limit: Макс. результатов (1-100)
            min_score: Минимальный score (0.0-1.0)
            filters: Фильтры (categories, statuses, author_id, date_range)
            current_user_id: UUID текущего пользователя (для visibility)
            is_admin: Флаг админа (bypasses visibility)
            public_only: Только PUBLIC issues (для публичного поиска)

        Returns:
            SearchResponseSchema: Результаты с stats

        Raises:
            SearchError: При критических ошибках поиска
        """
        start_time = time.time()

        # 1. Проверка кеша
        cache_key = self._generate_cache_key(
            query=query,
            workspace_id=workspace_id,
            pattern=pattern,
            filters=filters,
            current_user_id=current_user_id if not public_only else None,
            public_only=public_only,
        )
        cached_data = await self._get_cached_results(cache_key)
        if cached_data:
            logger.info("Возвращены результаты из кеша: %s", cache_key)
            # Cached data уже SearchResponseSchema
            return cached_data

        # 2. DB search (всегда выполняется) с visibility фильтрацией
        logger.info("Выполняется DB search: query='%s', public_only=%s", query, public_only)
        db_results = await self._search_db(
            query=query,
            pattern=pattern,
            filters=filters,
            workspace_id=workspace_id,
            current_user_id=current_user_id,
            is_admin=is_admin,
            public_only=public_only,
        )
        logger.info("DB search завершён: найдено %d результатов", len(db_results))

        rag_results: List[SearchResultSchema] = []
        mcp_results: List[SearchResultSchema] = []

        # 3. AI search (если включено)
        if use_ai:
            # RAG search (если указан KB)
            if kb_id:
                logger.info("Выполняется RAG search: kb_id=%s", kb_id)
                rag_results = await self._search_rag(
                    query=query,
                    kb_id=kb_id,
                )
                logger.info("RAG search завершён: найдено %d результатов", len(rag_results))

            # MCP search (через n8n webhook)
            logger.info("Выполняется MCP search через n8n")
            mcp_results = await self._search_mcp(query=query)
            logger.info("MCP search завершён: найдено %d результатов", len(mcp_results))

        # 4. Объединение и ранжирование
        merged_results = self._merge_and_rank(
            db_results=db_results,
            rag_results=rag_results,
            mcp_results=mcp_results,
        )

        # 5. Применение limit и min_score фильтров
        filtered_results = [r for r in merged_results if r.score >= min_score]
        limited_results = filtered_results[:limit]

        # 6. Подсчёт статистики
        search_time = (time.time() - start_time) * 1000  # в миллисекундах
        stats = SearchStatsSchema(
            total=len(limited_results),
            sources={
                "database": len(db_results),
                "rag": len(rag_results),
                "mcp_n8n": len(mcp_results),
            },
            query_time=round(search_time, 2),
        )

        # 7. Формирование response
        response = SearchResponseSchema(
            success=True,
            data={
                "results": [SearchResultDetailSchema.model_validate(r) for r in limited_results],
                "stats": stats,
            }
        )

        # 8. Сохранение в кеш
        await self._cache_results(cache_key, response)

        logger.info(
            "Поиск завершён: %d результатов за %.2fms",
            stats.total,
            stats.query_time,
        )
        return response

    async def _search_db(
        self,
        query: str,
        pattern: SearchPatternEnum,
        filters: Optional[SearchFiltersRequestSchema],
        workspace_id: Optional[UUID] = None,
        current_user_id: Optional[UUID] = None,
        is_admin: bool = False,
        public_only: bool = False,
    ) -> List[SearchResultSchema]:
        """
        Поиск по Issues в базе данных с visibility фильтрацией.

        Использует IssueRepository.get_filtered с visibility rules:
        - public_only=True: только PUBLIC issues
        - is_admin=True: все issues (admin override)
        - current_user_id + workspace_id: PUBLIC + WORKSPACE + PRIVATE (автор)
        - current_user_id only: PUBLIC + PRIVATE (автор)
        - None: только PUBLIC

        Args:
            query: Поисковый запрос
            pattern: Паттерн поиска (MATCH/PHRASE/FUZZY)
            filters: Фильтры (category, status, author_id, date_from, date_to)
            workspace_id: UUID воркспейса (для WORKSPACE visibility)
            current_user_id: UUID текущего пользователя (для PRIVATE visibility)
            is_admin: Флаг админа (bypasses visibility)
            public_only: Только PUBLIC issues (для публичного API)

        Returns:
            List[SearchResultSchema]: Результаты из БД с source='database'
        """
        try:
            # Преобразуем statuses из строк в IssueStatus enum
            status_filter = None
            if filters and filters.statuses:
                # Берём первый статус из списка (get_filtered принимает Optional[IssueStatus])
                status_str = filters.statuses[0]
                try:
                    from src.models.v1.issues import IssueStatus
                    status_filter = IssueStatus(status_str)  # "red" → IssueStatus.RED
                except ValueError:
                    logger.warning("Неизвестный статус: %s, игнорируем фильтр", status_str)

            # Используем метод get_filtered с visibility параметрами
            issues = await self.issue_repository.get_filtered(
                status=status_filter,
                category=filters.categories[0] if filters and filters.categories else None,
                author_id=filters.author_id if filters else None,
                search=query,
                workspace_id=workspace_id,
                current_user_id=current_user_id,
                is_admin=is_admin,
                public_only=public_only,
                limit=settings.DB_SEARCH_LIMIT,
                offset=0,
            )

            # Преобразуем IssueModel в SearchResultSchema
            results = []
            for issue in issues:
                # Вычисляем score на основе релевантности (эвристика из settings)
                if query.lower() in issue.title.lower():
                    score = settings.DB_SEARCH_SCORE_TITLE
                elif query.lower() in (issue.description or "").lower():
                    score = settings.DB_SEARCH_SCORE_DESCRIPTION
                else:
                    score = settings.DB_SEARCH_SCORE_OTHER

                results.append(
                    SearchResultSchema(
                        id=issue.id,
                        title=issue.title,
                        content=issue.description or "",
                        source=SearchSourceEnum.DB,
                        score=score,
                        metadata={
                            "category": issue.category,
                            "status": issue.status.value,
                            "author_id": str(issue.author_id),
                            "created_at": issue.created_at.isoformat(),
                            "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
                        },
                    )
                )

            logger.debug("DB search: найдено %d Issues по запросу '%s'", len(results), query)
            return results

        except Exception as e:
            logger.error("DB search ошибка: %s", e)
            return []

    async def _search_rag(
        self,
        query: str,
        kb_id: UUID,
    ) -> List[SearchResultSchema]:
        """
        Семантический поиск по Knowledge Base через RAG.

        Делегирует поиск в RAGSearchService.

        Args:
            query: Поисковый запрос
            kb_id: UUID Knowledge Base

        Returns:
            List[SearchResultSchema]: Результаты RAG поиска с source='rag'
        """
        try:
            rag_results = await self.rag_service.search(
                query=query,
                kb_id=kb_id,
                # limit и min_similarity берутся из settings в RAGSearchService
            )

            # Преобразуем RAGSearchResult в SearchResultSchema
            return [
                SearchResultSchema(
                    id=result.document_id,
                    title=result.filename,
                    content=result.content,
                    source=SearchSourceEnum.RAG,
                    score=result.similarity_score,
                    metadata={
                        "chunk_index": result.chunk_index,
                        "kb_id": str(kb_id),
                    },
                )
                for result in rag_results
            ]
        except ValueError as e:
            logger.error("RAG search validation error: %s", e)
            return []
        except TypeError as e:
            logger.error("RAG search type error (возможно некорректный формат данных): %s", e)
            return []
        except KeyError as e:
            logger.error("RAG search missing key error: %s", e)
            return []
        except Exception as e:
            logger.exception("RAG search unexpected error: %s", e)
            return []

    async def _search_mcp(self, query: str) -> List[SearchResultSchema]:
        """
        Умный поиск через n8n MCP webhook.

        Вызывает n8n workflow "Smart Search Helper" для AI-поиска.

        Args:
            query: Поисковый запрос

        Returns:
            List[SearchResultSchema]: Результаты MCP поиска с source='mcp'
        """
        try:
            # Получаем webhook URL из централизованных настроек
            webhook_url = settings.N8N_SMART_SEARCH_WEBHOOK
            if not webhook_url:
                logger.warning("N8N_SMART_SEARCH_WEBHOOK не настроен в settings")
                return []

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook_url,
                    json={"query": query},
                )
                response.raise_for_status()
                data = response.json()

            # Преобразуем ответ n8n в SearchResultSchema
            # TODO: Адаптировать под реальный формат ответа n8n workflow
            results = []
            for item in data.get("results", []):
                results.append(
                    SearchResultSchema(
                        id=UUID(item["id"]),
                        title=item["title"],
                        content=item["content"],
                        source=SearchSourceEnum.MCP,
                        score=item.get("score", 0.6),
                        metadata=item.get("metadata"),
                    )
                )
            return results

        except httpx.RequestError as e:
            logger.error("MCP search сетевая ошибка: %s", e)
            return []
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error("MCP search ошибка парсинга: %s", e)
            return []

    def _merge_and_rank(
        self,
        db_results: List[SearchResultSchema],
        rag_results: List[SearchResultSchema],
        mcp_results: List[SearchResultSchema],
    ) -> List[SearchResultSchema]:
        """
        Объединение и ранжирование результатов из всех источников.

        Применяет весовые коэффициенты к score:
        - DB: score * 1.0
        - RAG: score * 0.8
        - MCP: score * 0.6

        Args:
            db_results: Результаты из БД
            rag_results: Результаты из RAG
            mcp_results: Результаты из MCP

        Returns:
            List[SearchResultSchema]: Отсортированные результаты (по убыванию weighted_score)
        """
        all_results: List[SearchResultSchema] = []

        # Применяем весовые коэффициенты
        for result in db_results:
            result.score = result.score * settings.SEARCH_PRIORITY_DB
            all_results.append(result)

        for result in rag_results:
            result.score = result.score * settings.SEARCH_PRIORITY_RAG
            all_results.append(result)

        for result in mcp_results:
            result.score = result.score * settings.SEARCH_PRIORITY_MCP
            all_results.append(result)

        # Сортируем по score (от большего к меньшему)
        all_results.sort(key=lambda x: x.score, reverse=True)

        return all_results

    def _generate_cache_key(
        self,
        query: str,
        workspace_id: Optional[UUID],
        pattern: SearchPatternEnum,
        filters: Optional[SearchFiltersRequestSchema],
        current_user_id: Optional[UUID],
        public_only: bool,
    ) -> str:
        """
        Генерирует ключ кеша с учётом visibility context.

        Важно: Кеши изолируются по visibility для безопасности:
        - Публичные запросы (public_only=True) кэшируются отдельно.
        - Приватные запросы включают current_user_id или workspace_id в ключ.

        Args:
            query: Поисковый запрос
            workspace_id: UUID воркспейса
            pattern: Паттерн поиска
            filters: Фильтры
            current_user_id: UUID текущего пользователя
            public_only: Флаг публичного поиска

        Returns:
            str: MD5 хеш от параметров + visibility context
        """
        cache_data = {
            "query": query,
            "pattern": pattern.value,
            "filters": filters.model_dump() if filters else None,
            # Visibility context для изоляции кеша
            "public_only": public_only,
            "workspace_id": str(workspace_id) if workspace_id and not public_only else None,
            "user_id": str(current_user_id) if current_user_id and not public_only else None,
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        hash_obj = hashlib.md5(cache_str.encode())
        return f"search:{hash_obj.hexdigest()}"

    async def _cache_results(
        self,
        cache_key: str,
        response: SearchResponseSchema,
    ) -> None:
        """
        Сохраняет SearchResponseSchema в Redis.

        Args:
            cache_key: Ключ кеша (изолированный по visibility)
            response: Полный response schema для кэширования
        """
        try:
            await self.redis.set(
                cache_key,
                response.model_dump_json(),
                ex=settings.SEARCH_CACHE_TTL,
            )
            logger.debug("Результаты сохранены в кеш: %s", cache_key)
        except (ValueError, TypeError) as e:
            logger.error("Ошибка сохранения в кеш: %s", e)

    async def _get_cached_results(
        self,
        cache_key: str,
    ) -> Optional[SearchResponseSchema]:
        """
        Получает результаты поиска из Redis.

        Args:
            cache_key: Ключ кеша

        Returns:
            Optional[SearchResponseSchema]: Кешированный response или None
        """
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return SearchResponseSchema.model_validate_json(cached)
            return None
        except (ValueError, TypeError, KeyError, Exception) as e:
            logger.error("Ошибка чтения из кеша: %s", e)
            return None
