"""
Репозиторий для работы с DocumentModel (KB documents).

Предоставляет методы для работы с документами в Knowledge Base.
Все базовые CRUD операции наследуются от BaseRepository.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.knowledge_bases import DocumentModel, DocumentStatus
from src.repository.base import BaseRepository


class DocumentRepository(BaseRepository[DocumentModel]):
    """
    Репозиторий для DocumentModel.

    Управляет документами в Knowledge Base с поддержкой
    фильтрации по статусам и метаданным.

    Attributes:
        session: AsyncSession из BaseRepository
        model: DocumentModel class

    Example:
        >>> repo = DocumentRepository(session)
        >>> doc = await repo.create_item({
        ...     "kb_id": kb_id,
        ...     "filename": "contract.pdf",
        ...     "status": DocumentStatus.INDEXING
        ... })
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий документов KB.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session=session, model=DocumentModel)

    async def get_by_kb_and_filename(
        self,
        kb_id: UUID,
        filename: str,
    ) -> DocumentModel | None:
        """
        Получает документ по KB ID и имени файла.

        Args:
            kb_id: UUID Knowledge Base
            filename: Имя файла

        Returns:
            DocumentModel | None: Найденный документ или None

        Example:
            >>> doc = await repo.get_by_kb_and_filename(kb_id, "contract.pdf")
        """
        docs = await self.filter_by(kb_id=kb_id, filename=filename)
        return docs[0] if docs else None

    async def get_kb_documents(
        self,
        kb_id: UUID,
        status: DocumentStatus | None = None,
    ) -> list[DocumentModel]:
        """
        Получает все документы Knowledge Base.

        Args:
            kb_id: UUID Knowledge Base
            status: Опциональный фильтр по статусу

        Returns:
            list[DocumentModel]: Список документов

        Example:
            >>> # Все документы
            >>> docs = await repo.get_kb_documents(kb_id)
            >>> # Только проиндексированные
            >>> docs = await repo.get_kb_documents(kb_id, DocumentStatus.INDEXED)
        """
        if status:
            return await self.filter_by(kb_id=kb_id, status=status)
        return await self.filter_by(kb_id=kb_id)
