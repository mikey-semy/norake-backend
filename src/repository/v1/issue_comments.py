"""
Репозиторий для работы с комментариями к проблемам (IssueComments).

Этот модуль содержит IssueCommentRepository с методами для работы с комментариями
и их древовидной структурой. Наследуется от BaseRepository и добавляет методы
для работы с вложенными комментариями.

Classes:
    IssueCommentRepository: Репозиторий для CRUD операций с комментариями.

Example:
    >>> repo = IssueCommentRepository(session=session)
    >>> comments = await repo.get_issue_comments(issue_id, with_replies=True)
    >>> tree = await repo.get_comment_tree(parent_comment_id)
"""

import logging
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.sql import func

from src.models.v1.issue_comments import IssueCommentModel
from src.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class IssueCommentRepository(BaseRepository[IssueCommentModel]):
    """
    Репозиторий для работы с комментариями к проблемам.

    Наследуется от BaseRepository[IssueCommentModel] и добавляет специализированные
    методы для работы с древовидной структурой комментариев.

    Methods:
        get_issue_comments: Получить все комментарии проблемы с опциональной загрузкой ответов.
        get_comment_tree: Получить дерево комментариев начиная с родительского.
        get_comment_count: Подсчитать количество комментариев у проблемы.
        mark_as_solution: Отметить комментарий как решение.

    Example:
        >>> repo = IssueCommentRepository(session=session)
        >>> # Получить все комментарии с ответами
        >>> comments = await repo.get_issue_comments(issue_id, with_replies=True)
        >>> # Получить дерево ответов на комментарий
        >>> replies_tree = await repo.get_comment_tree(comment_id)
        >>> # Подсчитать комментарии
        >>> count = await repo.get_comment_count(issue_id)
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует IssueCommentRepository.

        Args:
            session (AsyncSession): Асинхронная сессия SQLAlchemy.
        """
        super().__init__(session=session, model=IssueCommentModel)
        self.logger = logging.getLogger(self.__class__.__name__)
        logger.debug("🔍 Инициализирован IssueCommentRepository")

    async def get_issue_comments(
        self,
        issue_id: UUID,
        with_replies: bool = True,
    ) -> List[IssueCommentModel]:
        """
        Получить все комментарии проблемы.

        Возвращает только корневые комментарии (parent_id IS NULL).
        Если with_replies=True, загружает вложенные ответы через selectinload.

        Args:
            issue_id (UUID): UUID проблемы.
            with_replies (bool): Загружать ли вложенные ответы (по умолчанию True).

        Returns:
            List[IssueCommentModel]: Список корневых комментариев с авторами и ответами.

        Example:
            >>> comments = await repo.get_issue_comments(issue_id)
            >>> comments[0].replies  # Вложенные ответы загружены
            [<IssueCommentModel>, ...]
            >>> comments[0].author  # Автор загружен
            <UserModel>

        Note:
            Использует joinedload для author и selectinload для replies.
            Возвращает только корневые комментарии (parent_id IS NULL).
        """
        logger.debug(
            "🔍 Получение комментариев для проблемы: %s (with_replies=%s)",
            issue_id,
            with_replies,
        )

        query = (
            select(IssueCommentModel)
            .where(
                IssueCommentModel.issue_id == issue_id,
                IssueCommentModel.parent_id.is_(None),  # Только корневые комментарии
            )
            .options(joinedload(IssueCommentModel.author))  # Eager load автора
            .order_by(IssueCommentModel.created_at)  # Сортировка по времени
        )

        if with_replies:
            # Рекурсивная загрузка всех ответов
            query = query.options(
                selectinload(IssueCommentModel.replies).options(
                    joinedload(IssueCommentModel.author),
                    selectinload(IssueCommentModel.replies),  # Вложенные ответы
                )
            )

        comments = await self.execute_and_return_scalars(query)

        logger.info(
            "✨ Получено %d корневых комментариев для проблемы %s (with_replies=%s)",
            len(comments),
            issue_id,
            with_replies,
        )
        return comments

    async def get_comment_tree(
        self,
        parent_id: UUID,
    ) -> List[IssueCommentModel]:
        """
        Получить дерево ответов на конкретный комментарий.

        Возвращает все прямые ответы (parent_id = указанный ID) с загрузкой
        авторов и вложенных ответов.

        Args:
            parent_id (UUID): UUID родительского комментария.

        Returns:
            List[IssueCommentModel]: Список ответов с авторами и вложенными ответами.

        Example:
            >>> replies = await repo.get_comment_tree(comment_id)
            >>> replies[0].author  # Автор загружен
            <UserModel>
            >>> replies[0].replies  # Вложенные ответы загружены
            [<IssueCommentModel>, ...]

        Note:
            Использует joinedload для author и selectinload для рекурсивной загрузки replies.
        """
        logger.debug(
            "🔍 Получение дерева ответов на комментарий: %s", parent_id
        )

        query = (
            select(IssueCommentModel)
            .where(IssueCommentModel.parent_id == parent_id)
            .options(
                joinedload(IssueCommentModel.author),  # Eager load автора
                selectinload(IssueCommentModel.replies).options(
                    joinedload(IssueCommentModel.author),
                    selectinload(IssueCommentModel.replies),  # Рекурсивная загрузка
                ),
            )
            .order_by(IssueCommentModel.created_at)
        )

        replies = await self.execute_and_return_scalars(query)

        logger.info(
            "✨ Получено %d ответов на комментарий %s", len(replies), parent_id
        )
        return replies

    async def get_comment_count(
        self,
        issue_id: UUID,
    ) -> int:
        """
        Подсчитать общее количество комментариев у проблемы.

        Считает ВСЕ комментарии (корневые + ответы).

        Args:
            issue_id (UUID): UUID проблемы.

        Returns:
            int: Количество комментариев.

        Example:
            >>> count = await repo.get_comment_count(issue_id)
            >>> count
            42

        Note:
            Использует func.count() для подсчёта всех комментариев проблемы.
        """
        logger.debug("🔍 Подсчёт комментариев для проблемы: %s", issue_id)

        query = select(func.count(IssueCommentModel.id)).where(
            IssueCommentModel.issue_id == issue_id
        )

        result = await self.session.execute(query)
        count = result.scalar_one()

        logger.info("✨ Проблема %s имеет %d комментариев", issue_id, count)
        return count

    # Оставляем существующие методы для обратной совместимости

    async def get_by_issue(
        self,
        issue_id: UUID,
        order_by_created: bool = True,
    ) -> List[IssueCommentModel]:
        """
        DEPRECATED: Использовать get_issue_comments(issue_id, with_replies=False).

        Получает все комментарии для конкретной проблемы (включая ответы).

        Args:
            issue_id (UUID): ID проблемы.
            order_by_created (bool): Сортировать по дате создания (по умолчанию True).

        Returns:
            List[IssueCommentModel]: Список всех комментариев проблемы.

        Example:
            >>> comments = await repo.get_by_issue(issue_id)
            >>> len(comments)
            5

        Note:
            Использует filter_by_ordered из BaseRepository.
            Для новой логики с деревом используйте get_issue_comments.
        """
        logger.debug("🔍 Получение комментариев для проблемы: %s", issue_id)

        if order_by_created:
            comments = await self.filter_by_ordered(
                "created_at",
                ascending=True,
                issue_id=issue_id,
            )
        else:
            comments = await self.filter_by(issue_id=issue_id)

        logger.info(
            "✨ Получено %d комментариев для проблемы %s", len(comments), issue_id
        )
        return comments

    async def get_solutions_by_issue(
        self,
        issue_id: UUID,
    ) -> List[IssueCommentModel]:
        """
        Получает только комментарии, отмеченные как решения.

        Args:
            issue_id (UUID): ID проблемы.

        Returns:
            List[IssueCommentModel]: Список комментариев-решений.

        Example:
            >>> solutions = await repo.get_solutions_by_issue(issue_id)
            >>> all(comment.is_solution for comment in solutions)
            True

        Note:
            Полезно для отображения только проверенных решений проблемы.
        """
        logger.debug("🔍 Получение решений для проблемы: %s", issue_id)

        solutions = await self.filter_by(
            issue_id=issue_id,
            is_solution=True,
        )

        logger.info(
            "✨ Получено %d решений для проблемы %s", len(solutions), issue_id
        )
        return solutions

    async def count_by_issue(self, issue_id: UUID) -> int:
        """
        DEPRECATED: Использовать get_comment_count(issue_id).

        Подсчитывает количество комментариев у проблемы.

        Args:
            issue_id (UUID): ID проблемы.

        Returns:
            int: Количество комментариев.

        Example:
            >>> count = await repo.count_by_issue(issue_id)
            >>> count
            12

        Note:
            Использует count_items из BaseRepository.
            Для новой логики используйте get_comment_count.
        """
        logger.debug("🔍 Подсчёт комментариев для проблемы: %s", issue_id)

        count = await self.count_items(issue_id=issue_id)

        logger.info("✨ У проблемы %s найдено %d комментариев", issue_id, count)
        return count

    async def mark_as_solution(
        self,
        comment_id: UUID,
        is_solution: bool = True,
    ) -> IssueCommentModel | None:
        """
        Отмечает комментарий как решение (или снимает отметку).

        Args:
            comment_id (UUID): ID комментария.
            is_solution (bool): True - отметить как решение, False - снять отметку.

        Returns:
            IssueCommentModel | None: Обновлённый комментарий или None.

        Example:
            >>> comment = await repo.mark_as_solution(comment_id, True)
            >>> comment.is_solution
            True

        Note:
            Использует update_item из BaseRepository.
        """
        logger.debug(
            "🔍 Обновление флага is_solution для комментария: %s", comment_id
        )

        updated_comment = await self.update_item(
            comment_id,
            {"is_solution": is_solution},
        )

        if updated_comment:
            status = "решением" if is_solution else "обычным комментарием"
            logger.info("✨ Комментарий %s отмечен как %s", comment_id, status)
        else:
            logger.warning("⚠️ Комментарий %s не найден", comment_id)

        return updated_comment
