"""
Сервис RAG-поиска с использованием pgvector и OpenRouter embeddings.

Этот модуль реализует семантический поиск по документам Knowledge Base
с использованием векторных представлений (embeddings) и cosine similarity.
"""

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.settings import settings
from src.core.exceptions import KnowledgeBaseNotFoundError
from src.repository.v1.document_chunks import DocumentChunkRepository
from src.repository.v1.knowledge_bases import KnowledgeBaseRepository


class RAGSearchResult:
    """
    Результат RAG-поиска по одному чанку документа.

    Attributes:
        document_id: UUID документа
        filename: Имя файла документа
        content: Текстовое содержимое чанка
        chunk_index: Индекс чанка в документе
        similarity_score: Cosine similarity (0-1, чем выше - тем релевантнее)
    """

    def __init__(
        self,
        document_id: UUID,
        filename: str,
        content: str,
        chunk_index: int,
        similarity_score: float,
    ):
        self.document_id = document_id
        self.filename = filename
        self.content = content
        self.chunk_index = chunk_index
        self.similarity_score = similarity_score

    def to_dict(self) -> dict:
        """Преобразование результата в словарь."""
        return {
            "document_id": str(self.document_id),
            "filename": self.filename,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "similarity_score": round(self.similarity_score, 4),
        }


class RAGSearchService:
    """
    Сервис для семантического поиска по документам через pgvector.

    Использует OpenRouter API для генерации embeddings запросов
    и PostgreSQL pgvector extension для векторного поиска.
    """

    def __init__(
        self,
        session: AsyncSession,
        openrouter_client,  # TODO: типизация после создания OpenRouter client
    ):
        """
        Инициализация RAG Search Service.

        Args:
            session: Async SQLAlchemy сессия
            openrouter_client: Клиент для OpenRouter API (embeddings)
        """
        self.session = session
        self.openrouter = openrouter_client
        self.kb_repository = KnowledgeBaseRepository(session)
        self.chunk_repository = DocumentChunkRepository(session)

    async def search(
        self,
        query: str,
        kb_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> List[RAGSearchResult]:
        """
        Семантический поиск по запросу в Knowledge Base.

        Процесс:
        1. Генерация embedding для query через OpenRouter
        2. Vector similarity search в pgvector
        3. Rerank результатов по similarity score

        Args:
            query: Поисковый запрос на естественном языке
            kb_id: UUID Knowledge Base для поиска
            limit: Максимальное количество результатов (default: 5)
            min_similarity: Минимальный порог similarity (0-1, default: 0.7)

        Returns:
            List[RAGSearchResult]: Отсортированные результаты (от более релевантных)

        Raises:
            KnowledgeBaseNotFoundError: Если KB не найдена
        """
        # Проверка существования KB
        kb = await self.kb_repository.get_item_by_id(kb_id)
        if not kb:
            raise KnowledgeBaseNotFoundError(kb_id=kb_id)

        # Генерация embedding для запроса
        query_embedding = await self._generate_query_embedding(query)

        # Векторный поиск
        results = await self.similarity_search(
            embedding=query_embedding,
            kb_id=kb_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        return results

    async def similarity_search(
        self,
        embedding: List[float],
        kb_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> List[RAGSearchResult]:
        """
        Векторный поиск по готовому embedding.

        Делегирует поиск в DocumentChunkRepository (DB access в repository layer).

        Args:
            embedding: Векторное представление запроса (1536 dimensions)
            kb_id: UUID Knowledge Base
            limit: Макс. количество результатов
            min_similarity: Минимальный порог similarity (0-1)

        Returns:
            List[RAGSearchResult]: Результаты поиска
        """
        # Делегируем поиск в репозиторий (DB access только через repository)
        rows = await self.chunk_repository.vector_search(
            embedding=embedding,
            kb_id=kb_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        # Преобразуем в domain objects
        search_results = [
            RAGSearchResult(
                document_id=row[0],
                filename=row[1],
                chunk_index=row[2],
                similarity_score=row[3],
                content=row[4],
            )
            for row in rows
        ]

        return search_results

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """
        Генерация embedding для текстового запроса через OpenRouter.

        Использует настройки из settings: OPENROUTER_EMBEDDING_MODEL

        Args:
            query: Текстовый запрос

        Returns:
            List[float]: Вектор embedding (обычно 1536 чисел)
        """
        # TODO: Реализовать после создания OpenRouter client
        # Временная заглушка для проверки архитектуры
        response = await self.openrouter.embeddings.create(
            model=settings.OPENROUTER_EMBEDDING_MODEL,
            input=query,
        )

        embedding = response.data[0].embedding
        return embedding

    async def rerank_results(
        self,
        results: List[RAGSearchResult],
        query: str,
        top_k: int = 3,
    ) -> List[RAGSearchResult]:
        """
        Reranking результатов поиска (опционально).

        Использует дополнительную модель для переранжирования топ-N результатов.
        Полезно когда нужно улучшить качество топовых результатов.

        Args:
            results: Список результатов из similarity_search
            query: Исходный поисковый запрос
            top_k: Сколько топовых результатов вернуть

        Returns:
            List[RAGSearchResult]: Переранжированные результаты

        Note:
            Требует интеграции с reranking моделью (напр. Cohere Rerank).
            В текущей реализации просто обрезает до top_k.
        """
        # TODO: Интегрировать reranking модель если необходимо
        # Пока просто возвращаем топ-K без изменений
        return results[:top_k]
