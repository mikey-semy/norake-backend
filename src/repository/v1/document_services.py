"""
Репозиторий для работы с сервисами документов (Document Services).

Предоставляет методы доступа к данным сервисов документов с поддержкой
фильтрации по тегам, типам файлов, авторам, workspace и полнотекстового поиска.

Classes:
    DocumentServiceRepository: Репозиторий с CRUD методами для DocumentServiceModel.

Example:
    >>> repository = DocumentServiceRepository(session=session)
    >>> public_services = await repository.get_public_services()
    >>> user_services = await repository.get_by_author(user_id)
    >>> pdf_services = await repository.get_by_file_type(DocumentFileType.PDF)
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.document_services import (
    DocumentFileType,
    DocumentServiceModel,
)
from src.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class DocumentServiceRepository(BaseRepository[DocumentServiceModel]):
    """
    Репозиторий для работы с сервисами документов.

    Наследует BaseRepository[DocumentServiceModel] и добавляет специфичные методы
    для работы с сервисами документов: поиск по тегам, фильтрация по типам файлов,
    полнотекстовый поиск, управление счётчиком просмотров.

    Attributes:
        session: Асинхронная сессия базы данных.
        model: DocumentServiceModel класс.

    Example:
        >>> repository = DocumentServiceRepository(session=session)
        >>> # Получить публичные сервисы
        >>> services = await repository.get_public_services()
        >>> # Поиск по тегам
        >>> tagged = await repository.get_by_tags(["технический", "оборудование"])
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий сервисов документов.

        Args:
            session: Асинхронная сессия базы данных.
        """
        super().__init__(session=session, model=DocumentServiceModel)
        self.logger = logging.getLogger(__name__)

    async def get_public_services(
        self,
        file_type: Optional[DocumentFileType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentServiceModel]:
        """
        Получает публичные сервисы документов.

        Возвращает только сервисы с is_public=True, отсортированные по дате создания.
        Можно фильтровать по типу файла.

        Args:
            file_type: Фильтр по типу файла (опционально).
            limit: Количество результатов (по умолчанию 50).
            offset: Смещение для пагинации (по умолчанию 0).

        Returns:
            Список публичных DocumentServiceModel.

        Example:
            >>> # Все публичные сервисы
            >>> services = await repository.get_public_services()
            >>> # Только публичные PDF
            >>> pdfs = await repository.get_public_services(
            ...     file_type=DocumentFileType.PDF
            ... )
        """
        filters = {"is_public": True, "limit": limit, "offset": offset}
        if file_type:
            filters["file_type"] = file_type

        services = await self.filter_by_ordered(
            "created_at", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d публичных сервисов (file_type=%s)",
            len(services),
            file_type.value if file_type else "any",
        )
        return services

    async def get_by_author(
        self,
        author_id: UUID,
        include_public: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentServiceModel]:
        """
        Получает все сервисы документов конкретного автора.

        Args:
            author_id: UUID автора сервисов.
            include_public: Включать ли публичные сервисы (по умолчанию True).
            limit: Количество результатов.
            offset: Смещение для пагинации.

        Returns:
            Список DocumentServiceModel автора.

        Example:
            >>> # Все сервисы пользователя
            >>> services = await repository.get_by_author(user_id)
            >>> # Только приватные сервисы
            >>> private = await repository.get_by_author(
            ...     user_id, include_public=False
            ... )
        """
        filters = {"author_id": author_id, "limit": limit, "offset": offset}
        if not include_public:
            filters["is_public"] = False

        services = await self.filter_by_ordered(
            "created_at", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d сервисов автора %s (include_public=%s)",
            len(services),
            author_id,
            include_public,
        )
        return services

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentServiceModel]:
        """
        Получает все сервисы документов в workspace.

        Args:
            workspace_id: UUID workspace.
            limit: Количество результатов.
            offset: Смещение для пагинации.

        Returns:
            Список DocumentServiceModel в workspace.

        Example:
            >>> services = await repository.get_by_workspace(workspace_id)
        """
        services = await self.filter_by_ordered(
            "created_at",
            ascending=False,
            workspace_id=workspace_id,
            limit=limit,
            offset=offset,
        )

        self.logger.info(
            "Получено %d сервисов в workspace %s",
            len(services),
            workspace_id,
        )
        return services

    async def get_by_file_type(
        self,
        file_type: DocumentFileType,
        is_public: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentServiceModel]:
        """
        Получает сервисы по типу файла.

        Args:
            file_type: Тип файла (PDF, SPREADSHEET, TEXT, IMAGE).
            is_public: Фильтр по публичности (опционально).
            limit: Количество результатов.
            offset: Смещение для пагинации.

        Returns:
            Список DocumentServiceModel с указанным типом файла.

        Example:
            >>> # Все PDF сервисы
            >>> pdfs = await repository.get_by_file_type(DocumentFileType.PDF)
            >>> # Только публичные PDF
            >>> public_pdfs = await repository.get_by_file_type(
            ...     DocumentFileType.PDF, is_public=True
            ... )
        """
        filters = {"file_type": file_type, "limit": limit, "offset": offset}
        if is_public is not None:
            filters["is_public"] = is_public

        services = await self.filter_by_ordered(
            "created_at", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d сервисов с типом файла %s (is_public=%s)",
            len(services),
            file_type.value,
            is_public,
        )
        return services

    async def get_by_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentServiceModel]:
        """
        Получает сервисы по тегам с поддержкой PostgreSQL ARRAY операторов.

        Args:
            tags: Список тегов для поиска.
            match_all: True для AND (все теги должны присутствовать),
                      False для OR (хотя бы один тег). По умолчанию False.
            limit: Количество результатов.
            offset: Смещение для пагинации.

        Returns:
            Список DocumentServiceModel с указанными тегами.

        Example:
            >>> # Сервисы с любым из тегов (OR)
            >>> services = await repository.get_by_tags(
            ...     ["технический", "оборудование"]
            ... )
            >>> # Сервисы со всеми тегами (AND)
            >>> services = await repository.get_by_tags(
            ...     ["технический", "оборудование"],
            ...     match_all=True
            ... )

        Note:
            Использует PostgreSQL ARRAY операторы:
            - overlap (&&) для OR логики (хотя бы один тег совпадает)
            - contains (@>) для AND логики (все теги присутствуют)
        """
        try:
            stmt = select(self.model)

            # PostgreSQL ARRAY operators для поиска по тегам
            if match_all:
                # @> оператор: массив содержит все указанные элементы (AND)
                stmt = stmt.where(self.model.tags.contains(tags))
            else:
                # && оператор: массивы имеют общие элементы (OR)
                stmt = stmt.where(self.model.tags.overlap(tags))

            stmt = stmt.order_by(self.model.created_at.desc())

            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)

            services = await self.execute_and_return_scalars(stmt)

            self.logger.info(
                "Получено %d сервисов по тегам %s (match_all=%s)",
                len(services),
                tags,
                match_all,
            )
            return services

        except SQLAlchemyError as e:
            self.logger.error("Ошибка при поиске по тегам %s: %s", tags, e)
            return []

    async def search_by_text(
        self,
        search_text: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DocumentServiceModel]:
        """
        Полнотекстовый поиск по названию и описанию.

        Использует PostgreSQL ILIKE для поиска без учёта регистра.

        Args:
            search_text: Текст для поиска.
            limit: Количество результатов.
            offset: Смещение для пагинации.

        Returns:
            Список DocumentServiceModel с совпадениями.

        Example:
            >>> # Поиск по тексту
            >>> services = await repository.search_by_text("техническая документация")
        """
        try:
            pattern = f"%{search_text}%"

            stmt = (
                select(self.model)
                .where(
                    or_(
                        self.model.title.ilike(pattern),
                        self.model.description.ilike(pattern),
                    )
                )
                .order_by(self.model.view_count.desc(), self.model.created_at.desc())
            )

            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)

            services = await self.execute_and_return_scalars(stmt)

            self.logger.info(
                "Найдено %d сервисов по запросу '%s'",
                len(services),
                search_text,
            )
            return services

        except SQLAlchemyError as e:
            self.logger.error("Ошибка при полнотекстовом поиске '%s': %s", search_text, e)
            return []

    async def get_most_viewed(
        self,
        file_type: Optional[DocumentFileType] = None,
        limit: int = 10,
    ) -> List[DocumentServiceModel]:
        """
        Получает самые просматриваемые сервисы.

        Args:
            file_type: Фильтр по типу файла (опционально).
            limit: Количество результатов (по умолчанию 10).

        Returns:
            Список DocumentServiceModel, отсортированных по view_count.

        Example:
            >>> # Топ-10 самых просматриваемых
            >>> top = await repository.get_most_viewed()
            >>> # Топ-5 PDF по просмотрам
            >>> top_pdfs = await repository.get_most_viewed(
            ...     file_type=DocumentFileType.PDF, limit=5
            ... )
        """
        filters = {"limit": limit}
        if file_type:
            filters["file_type"] = file_type

        services = await self.filter_by_ordered(
            "view_count", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d самых просматриваемых сервисов (file_type=%s)",
            len(services),
            file_type.value if file_type else "any",
        )
        return services

    async def increment_view_count(self, service_id: UUID) -> Optional[DocumentServiceModel]:
        """
        Увеличивает счётчик просмотров сервиса.

        Вызывается при каждом просмотре документа.
        Инкрементирует view_count на 1.

        Args:
            service_id: UUID сервиса документа.

        Returns:
            Обновлённая DocumentServiceModel или None, если не найден.

        Example:
            >>> service = await repository.increment_view_count(service_id)
            >>> print(f"Просмотров: {service.view_count}")
        """
        service = await self.get_item_by_id(service_id)
        if not service:
            self.logger.warning("Сервис %s не найден для инкремента view_count", service_id)
            return None

        service.view_count += 1
        await self.session.commit()
        await self.session.refresh(service)

        self.logger.info(
            "Увеличен view_count для сервиса %s (новое значение: %d)",
            service_id,
            service.view_count,
        )
        return service

    async def get_recent_services(
        self,
        author_id: Optional[UUID] = None,
        workspace_id: Optional[UUID] = None,
        limit: int = 10,
    ) -> List[DocumentServiceModel]:
        """
        Получает недавно созданные сервисы.

        Args:
            author_id: Фильтр по автору (опционально).
            workspace_id: Фильтр по workspace (опционально).
            limit: Количество результатов (по умолчанию 10).

        Returns:
            Список недавно созданных DocumentServiceModel.

        Example:
            >>> # Последние 10 сервисов
            >>> recent = await repository.get_recent_services()
            >>> # Последние 5 сервисов пользователя
            >>> recent_user = await repository.get_recent_services(
            ...     author_id=user_id, limit=5
            ... )
        """
        filters = {"limit": limit}
        if author_id:
            filters["author_id"] = author_id
        if workspace_id:
            filters["workspace_id"] = workspace_id

        services = await self.filter_by_ordered(
            "created_at", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d недавних сервисов (author_id=%s, workspace_id=%s)",
            len(services),
            author_id,
            workspace_id,
        )
        return services
