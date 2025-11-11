"""
Репозиторий для работы с Knowledge Bases.

Предоставляет CRUD и специфичные запросы для KnowledgeBaseModel.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.knowledge_bases import KnowledgeBaseModel
from src.repository.base import BaseRepository


class KnowledgeBaseRepository(BaseRepository[KnowledgeBaseModel]):
    """Репозиторий для KnowledgeBaseModel.

    Предоставляет стандартные CRUD через BaseRepository и дополнительные методы.
    """

    def __init__(self, session: AsyncSession):
        """Инициализирует репозиторий для knowledge bases.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(session=session, model=KnowledgeBaseModel)
