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
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.repository.v1.issues import IssueRepository
from src.schemas.v1.search.base import SearchPatternEnum, SearchResultSchema, SearchSourceEnum
from src.schemas.v1.search.requests import SearchFiltersRequestSchema, SearchRequestSchema
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
        >>> results = await service.search_with_ai(
        ...     request=SearchRequestSchema(
        ...         query="ошибка E401",
        ...         use_ai=True,
        ...         kb_id=kb_uuid
        ...     )
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
        request: SearchRequestSchema,
    ) -> tuple[List[SearchResultSchema], Dict[str, Any]]:
        """
        Гибридный поиск с объединением результатов из всех источников.

        Процесс:
        1. Проверка кеша Redis (ключ от query + filters)
        2. DB search (всегда выполняется)
        3. Если use_ai=True:
           - RAG search (если указан kb_id)
           - MCP search (через n8n webhook)
        4. Объединение результатов с ранжированием
        5. Сохранение в кеш

        Args:
            request: SearchRequestSchema с параметрами поиска

        Returns:
            tuple: (results, stats)
                - results: List[SearchResultSchema] - отсортированные результаты
                - stats: Dict с метриками (total_results, db_results, rag_results, mcp_results, search_time_ms, cached)

        Raises:
            SearchError: При критических ошибках поиска
        """
        start_time = time.time()

        # 1. Проверка кеша
        cache_key = self._generate_cache_key(request)
        cached_data = await self._get_cached_results(cache_key)
        if cached_data:
            logger.info("Возвращены результаты из кеша: %s", cache_key)
            return cached_data["results"], cached_data["stats"]

        # 2. DB search (всегда выполняется)
        logger.info("Выполняется DB search: query='%s'", request.query)
        db_results = await self._search_db(
            query=request.query,
            pattern=request.pattern,
            filters=request.filters,
        )
        logger.info("DB search завершён: найдено %d результатов", len(db_results))

        rag_results: List[SearchResultSchema] = []
        mcp_results: List[SearchResultSchema] = []

        # 3. AI search (если включено)
        if request.use_ai:
            # RAG search (если указан KB)
            if request.kb_id:
                logger.info("Выполняется RAG search: kb_id=%s", request.kb_id)
                rag_results = await self._search_rag(
                    query=request.query,
                    kb_id=request.kb_id,
                )
                logger.info("RAG search завершён: найдено %d результатов", len(rag_results))

            # MCP search (через n8n webhook)
            logger.info("Выполняется MCP search через n8n")
            mcp_results = await self._search_mcp(query=request.query)
            logger.info("MCP search завершён: найдено %d результатов", len(mcp_results))

        # 4. Объединение и ранжирование
        merged_results = self._merge_and_rank(
            db_results=db_results,
            rag_results=rag_results,
            mcp_results=mcp_results,
        )

        # 5. Подсчёт статистики
        search_time = (time.time() - start_time) * 1000  # в миллисекундах
        stats = {
            "total_results": len(merged_results),
            "db_results": len(db_results),
            "rag_results": len(rag_results),
            "mcp_results": len(mcp_results),
            "search_time_ms": round(search_time, 2),
            "cached": False,
        }

        # 6. Сохранение в кеш
        await self._cache_results(cache_key, merged_results, stats)

        logger.info(
            "Поиск завершён: %d результатов за %.2fms",
            stats["total_results"],
            stats["search_time_ms"],
        )
        return merged_results, stats

    async def _search_db(
        self,
        query: str,
        pattern: SearchPatternEnum,
        filters: Optional[SearchFiltersRequestSchema],
    ) -> List[SearchResultSchema]:
        """
        Поиск по Issues в базе данных.

        Использует IssueRepository для поиска по title/description.
        Поддерживает фильтры по категории, статусу, автору.

        Args:
            query: Поисковый запрос
            pattern: Паттерн поиска (MATCH/PHRASE/FUZZY)
            filters: Фильтры (category, status, author_id, date_from, date_to)

        Returns:
            List[SearchResultSchema]: Результаты из БД с source='db'
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

            # Используем метод get_filtered из IssueRepository
            issues = await self.issue_repository.get_filtered(
                status=status_filter,
                category=filters.categories[0] if filters and filters.categories else None,
                author_id=filters.author_id if filters else None,
                search=query,  # search_by_text внутри get_filtered
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
        except (ValueError, TypeError, KeyError) as e:
            logger.error("RAG search ошибка: %s", e)
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

    def _generate_cache_key(self, request: SearchRequestSchema) -> str:
        """
        Генерирует ключ кеша на основе параметров запроса.

        Args:
            request: Параметры поиска

        Returns:
            str: MD5 хеш от query + filters
        """
        cache_data = {
            "query": request.query,
            "pattern": request.pattern.value,
            "use_ai": request.use_ai,
            "kb_id": str(request.kb_id) if request.kb_id else None,
            "filters": request.filters.model_dump() if request.filters else None,
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        hash_obj = hashlib.md5(cache_str.encode())
        return f"search:{hash_obj.hexdigest()}"

    async def _cache_results(
        self,
        cache_key: str,
        results: List[SearchResultSchema],
        stats: Dict[str, Any],
    ) -> None:
        """
        Сохраняет результаты поиска в Redis.

        Args:
            cache_key: Ключ кеша
            results: Результаты поиска
            stats: Статистика поиска
        """
        try:
            cache_data = {
                "results": [r.model_dump() for r in results],
                "stats": {**stats, "cached": True},
            }
            await self.redis.set(
                cache_key,
                json.dumps(cache_data),
                ex=settings.SEARCH_CACHE_TTL,
            )
            logger.debug("Результаты сохранены в кеш: %s", cache_key)
        except (ValueError, TypeError) as e:
            logger.error("Ошибка сохранения в кеш: %s", e)

    async def _get_cached_results(
        self,
        cache_key: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Получает результаты поиска из Redis.

        Args:
            cache_key: Ключ кеша

        Returns:
            Optional[Dict]: {"results": [...], "stats": {...}} или None
        """
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                # Восстанавливаем Pydantic объекты
                data["results"] = [
                    SearchResultSchema.model_validate(r) for r in data["results"]
                ]
                return data
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            logger.error("Ошибка чтения из кеша: %s", e)
        return None
