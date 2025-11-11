"""
Репозиторий для работы с DocumentChunkModel.

Предоставляет методы для поиска по векторным эмбеддингам (pgvector).
Все базовые CRUD операции наследуются от BaseRepository.

Документация pgvector-python SQLAlchemy integration:
https://context7.com/pgvector/pgvector-python/llms.txt
https://github.com/pgvector/pgvector-python

Key concepts:
- cosine_distance() для семантического поиска (меньше = похожее)
- l2_distance() для Euclidean distance
- max_inner_product() для dot product similarity
- Используем SQLAlchemy ORM методы вместо raw SQL для type safety
"""

from typing import List, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.knowledge_bases import DocumentChunkModel, DocumentModel
from src.repository.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunkModel]):
    """Репозиторий для DocumentChunkModel с поддержкой pgvector поиска.

    Использует pgvector extension для векторного similarity search.
    Все методы используют SQLAlchemy ORM для type safety и переиспользования кода.

    Attributes:
        session: AsyncSession из BaseRepository (через SessionMixin)
        model: DocumentChunkModel class (через BaseRepository)

    Methods:
        vector_search: Cosine similarity search по embedding
    """

    def __init__(self, session: AsyncSession):
        """Инициализирует репозиторий для чанков документов.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session=session, model=DocumentChunkModel)

    async def vector_search(
        self,
        embedding: List[float],
        kb_id: UUID,
        limit: int = 5,
        min_similarity: float = 0.7,
    ) -> List[Tuple[UUID, str, int, float, str]]:
        """Выполняет семантический поиск по векторным эмбеддингам.

        Использует pgvector cosine_distance() для поиска похожих чанков.
        Cosine distance: 0 = идентичные векторы, 2 = противоположные.
        Similarity = 1 - cosine_distance (чем выше similarity, тем релевантнее).

        Процесс:
        1. JOIN с DocumentModel для получения filename и фильтрации по kb_id
        2. Вычисление similarity = 1 - cosine_distance(embedding, query)
        3. Фильтрация по min_similarity порогу
        4. Сортировка по distance (ascending = более похожие первыми)
        5. LIMIT для топ-N результатов

        Args:
            embedding: Векторное представление запроса (list of floats)
            kb_id: UUID Knowledge Base для фильтрации документов
            limit: Максимальное количество результатов (default: 5)
            min_similarity: Минимальный порог similarity 0-1 (default: 0.7)

        Returns:
            List[Tuple]: Каждый элемент содержит:
                - document_id (UUID): ID документа
                - filename (str): Имя файла документа
                - chunk_index (int): Индекс чанка в документе
                - similarity (float): Similarity score (0-1, выше = релевантнее)
                - content (str): Текстовое содержимое чанка

        Example:
            >>> repo = DocumentChunkRepository(session)
            >>> query_vec = [0.1, 0.2, ..., 0.5]  # 1536 dimensions
            >>> results = await repo.vector_search(
            ...     embedding=query_vec,
            ...     kb_id=UUID('...'),
            ...     limit=5,
            ...     min_similarity=0.7
            ... )
            >>> for doc_id, filename, idx, sim, content in results:
            ...     print(f"{filename} chunk {idx}: {sim:.4f}")

        References:
            - pgvector cosine_distance: https://github.com/pgvector/pgvector-python
            - SQLAlchemy ORM methods: https://context7.com/pgvector/pgvector-python
        """
        # Вычисляем distance и similarity используя pgvector методы
        # cosine_distance() - метод из pgvector.sqlalchemy
        distance = DocumentChunkModel.embedding.cosine_distance(embedding)
        similarity = (1 - distance).label("similarity")

        # Строим запрос с JOIN и фильтрацией
        # Используем execute_and_return_scalars не подходит (нужны multiple columns)
        # Поэтому используем session.execute напрямую с select()
        stmt = (
            select(
                DocumentChunkModel.document_id,
                DocumentModel.filename,
                DocumentChunkModel.chunk_index,
                similarity,
                DocumentChunkModel.content,
            )
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(DocumentModel.kb_id == kb_id)
            .where(DocumentChunkModel.embedding.is_not(None))
            .where(similarity >= min_similarity)
            .order_by(distance)  # ORDER BY distance ASC (меньше = похожее)
            .limit(limit)
        )

        # Выполняем запрос через self.session (наследуется от SessionMixin)
        result = await self.session.execute(stmt)
        rows = result.fetchall()

        # Преобразуем Row objects в типизированные tuples
        # Row object: (document_id, filename, chunk_index, similarity, content)
        return [
            (
                UUID(row[0]) if isinstance(row[0], str) else row[0],  # document_id
                row[1],        # filename (str)
                row[2],        # chunk_index (int)
                float(row[3]), # similarity (float)
                row[4],        # content (str)
            )
            for row in rows
        ]
