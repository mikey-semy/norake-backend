"""
Репозиторий для работы с проблемами (Issues).

Этот модуль содержит IssueRepository с методами для работы с проблемами в БД.
Наследуется от BaseRepository и добавляет специализированные методы.

Classes:
    IssueRepository: Репозиторий для CRUD операций с Issues.

Example:
    >>> repo = IssueRepository(session=session)
    >>> issues = await repo.get_by_status(IssueStatus.RED)
    >>> resolved = await repo.resolve_issue(issue_id, "Решение найдено")
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError

from src.models.v1.issues import IssueModel, IssueStatus
from src.repository.base import BaseRepository


class IssueRepository(BaseRepository[IssueModel]):
    """
    Репозиторий для работы с проблемами (Issues).

    Наследуется от BaseRepository[IssueModel] и добавляет специализированные
    методы для фильтрации, поиска и решения проблем.

    Methods:
        get_by_status: Получить проблемы по статусу (RED/GREEN).
        get_by_category: Получить проблемы по категории.
        get_by_author: Получить проблемы конкретного пользователя.
        search_by_text: Полнотекстовый поиск по title и description.
        get_recent: Получить недавние проблемы (по created_at).
        resolve_issue: Решить проблему (установить status=GREEN, solution, resolved_at).

    Example:
        >>> repo = IssueRepository(session=session)
        >>> # Получить все нерешённые проблемы
        >>> red_issues = await repo.get_by_status(IssueStatus.RED)
        >>> # Поиск по тексту
        >>> found = await repo.search_by_text("ошибка E401")
        >>> # Решить проблему
        >>> resolved = await repo.resolve_issue(
        ...     issue_id=uuid,
        ...     solution="Заменён датчик"
        ... )
    """

    def __init__(self, session):
        """
        Инициализирует IssueRepository.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        super().__init__(session=session, model=IssueModel)
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_by_status(
        self,
        status: IssueStatus,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[IssueModel]:
        """
        Получить проблемы по статусу.

        Args:
            status: Статус проблем (IssueStatus.RED или IssueStatus.GREEN).
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список проблем с указанным статусом.

        Example:
            >>> red_issues = await repo.get_by_status(IssueStatus.RED, limit=10)
            >>> len(red_issues)
            10
        """
        try:
            query = select(IssueModel).where(IssueModel.status == status)

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            issues = result.scalars().all()

            self.logger.info(
                "Получено %d проблем со статусом %s", len(issues), status.value
            )
            return list(issues)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении проблем по статусу: %s", e)
            raise

    async def get_by_category(
        self,
        category: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[IssueModel]:
        """
        Получить проблемы по категории.

        Args:
            category: Категория проблем (hardware, software, process).
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список проблем указанной категории.

        Example:
            >>> hardware_issues = await repo.get_by_category("hardware")
        """
        try:
            query = select(IssueModel).where(IssueModel.category == category)

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            issues = result.scalars().all()

            self.logger.info(
                "Получено %d проблем категории '%s'", len(issues), category
            )
            return list(issues)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении проблем по категории: %s", e)
            raise

    async def get_by_author(
        self,
        author_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[IssueModel]:
        """
        Получить проблемы конкретного пользователя.

        Args:
            author_id: UUID автора проблем.
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список проблем пользователя.

        Example:
            >>> user_issues = await repo.get_by_author(user_id, limit=20)
        """
        try:
            query = select(IssueModel).where(IssueModel.author_id == author_id)

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            issues = result.scalars().all()

            self.logger.info(
                "Получено %d проблем пользователя %s", len(issues), author_id
            )
            return list(issues)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении проблем пользователя: %s", e)
            raise

    async def search_by_text(
        self,
        query_text: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[IssueModel]:
        """
        Полнотекстовый поиск по заголовку и описанию проблем.

        Ищет вхождения query_text в title или description (case-insensitive).

        Args:
            query_text: Текст для поиска.
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список найденных проблем.

        Example:
            >>> found = await repo.search_by_text("ошибка E401")
            >>> found[0].title
            "Ошибка E401 на станке №3"
        """
        try:
            search_pattern = f"%{query_text}%"
            query = select(IssueModel).where(
                or_(
                    IssueModel.title.ilike(search_pattern),
                    IssueModel.description.ilike(search_pattern),
                )
            )

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            issues = result.scalars().all()

            self.logger.info(
                "Найдено %d проблем по запросу '%s'", len(issues), query_text
            )
            return list(issues)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при поиске проблем: %s", e)
            raise

    async def get_recent(
        self,
        limit: int = 50,
        offset: Optional[int] = None,
    ) -> List[IssueModel]:
        """
        Получить недавние проблемы (сортировка по created_at DESC).

        Args:
            limit: Максимальное количество результатов (по умолчанию 50).
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список последних проблем.

        Example:
            >>> recent = await repo.get_recent(limit=10)
        """
        try:
            query = (
                select(IssueModel)
                .order_by(IssueModel.created_at.desc())
                .limit(limit)
            )

            if offset:
                query = query.offset(offset)

            result = await self.session.execute(query)
            issues = result.scalars().all()

            self.logger.info("Получено %d последних проблем", len(issues))
            return list(issues)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при получении последних проблем: %s", e)
            raise

    async def resolve_issue(
        self,
        issue_id: UUID,
        solution: str,
    ) -> Optional[IssueModel]:
        """
        Решить проблему (закрыть с решением).

        Устанавливает:
        - status = IssueStatus.GREEN
        - solution = переданный текст
        - resolved_at = текущая datetime

        Args:
            issue_id: UUID проблемы для решения.
            solution: Текст решения проблемы.

        Returns:
            Optional[IssueModel]: Обновлённая проблема или None если не найдена.

        Raises:
            SQLAlchemyError: При ошибке обновления.

        Example:
            >>> resolved = await repo.resolve_issue(
            ...     issue_id=uuid,
            ...     solution="Заменён датчик положения"
            ... )
            >>> resolved.status
            <IssueStatus.GREEN: 'green'>
            >>> resolved.resolved_at
            datetime(2025, 11, 10, 16, 30, 0)
        """
        try:
            issue = await self.get_item_by_id(issue_id)
            if not issue:
                self.logger.warning("Проблема %s не найдена для решения", issue_id)
                return None

            # Обновляем поля решения
            issue.status = IssueStatus.GREEN
            issue.solution = solution
            issue.resolved_at = datetime.now(timezone.utc)

            await self.session.commit()
            await self.session.refresh(issue)

            self.logger.info(
                "Проблема %s решена: %s", issue_id, solution[:50] + "..."
            )
            return issue
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при решении проблемы %s: %s", issue_id, e)
            raise

    async def get_filtered(
        self,
        status: Optional[IssueStatus] = None,
        category: Optional[str] = None,
        author_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IssueModel]:
        """
        Получить проблемы с множественными фильтрами.

        Комбинирует фильтры через AND. Все параметры опциональны.

        Args:
            status: Фильтр по статусу.
            category: Фильтр по категории.
            author_id: Фильтр по автору.
            search: Поиск по title/description.
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список отфильтрованных проблем.

        Example:
            >>> # Нерешённые проблемы hardware конкретного пользователя
            >>> issues = await repo.get_filtered(
            ...     status=IssueStatus.RED,
            ...     category="hardware",
            ...     author_id=user_id
            ... )
        """
        try:
            query = select(IssueModel)
            conditions = []

            if status:
                conditions.append(IssueModel.status == status)
            if category:
                conditions.append(IssueModel.category == category)
            if author_id:
                conditions.append(IssueModel.author_id == author_id)
            if search:
                search_pattern = f"%{search}%"
                conditions.append(
                    or_(
                        IssueModel.title.ilike(search_pattern),
                        IssueModel.description.ilike(search_pattern),
                    )
                )

            if conditions:
                query = query.where(and_(*conditions))

            query = query.order_by(IssueModel.created_at.desc()).limit(limit).offset(offset)

            result = await self.session.execute(query)
            issues = result.scalars().all()

            self.logger.info("Получено %d отфильтрованных проблем", len(issues))
            return list(issues)
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при фильтрации проблем: %s", e)
            raise
