"""
Репозиторий для работы с комментариями к проблемам.

Содержит:
    IssueCommentRepository - класс для CRUD операций с комментариями.
"""

import logging
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.issue_comments import IssueCommentModel
from src.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class IssueCommentRepository(BaseRepository[IssueCommentModel]):
    """
    Репозиторий для работы с комментариями к проблемам.

    Наследует BaseRepository с типом IssueCommentModel.
    Предоставляет специфичные методы для работы с комментариями.

    Example:
        >>> repo = IssueCommentRepository(session)
        >>> comments = await repo.get_by_issue(issue_id)
        >>> for comment in comments:
        ...     print(comment.content)
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий комментариев.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
        """
        super().__init__(session=session, model=IssueCommentModel)
        logger.debug("🔍 Инициализирован IssueCommentRepository")

    async def get_by_issue(
        self,
        issue_id: UUID,
        order_by_created: bool = True,
    ) -> List[IssueCommentModel]:
        """
        Получает все комментарии для конкретной проблемы.

        Args:
            issue_id (UUID): ID проблемы.
            order_by_created (bool): Сортировать по дате создания (по умолчанию True).

        Returns:
            List[IssueCommentModel]: Список комментариев проблемы.

        Example:
            >>> comments = await repo.get_by_issue(issue_id)
            >>> len(comments)
            5
            >>> comments[0].content
            'Первый комментарий'

        Note:
            Использует filter_by_ordered из BaseRepository для оптимизации.
        """
        logger.debug(f"🔍 Получение комментариев для проблемы: {issue_id}")

        if order_by_created:
            comments = await self.filter_by_ordered(
                "created_at",
                ascending=True,
                issue_id=issue_id,
            )
        else:
            comments = await self.filter_by(issue_id=issue_id)

        logger.info(f"✨ Получено {len(comments)} комментариев для проблемы {issue_id}")
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
        logger.debug(f"🔍 Получение решений для проблемы: {issue_id}")

        solutions = await self.filter_by(
            issue_id=issue_id,
            is_solution=True,
        )

        logger.info(
            f"✨ Получено {len(solutions)} решений для проблемы {issue_id}"
        )
        return solutions

    async def count_by_issue(self, issue_id: UUID) -> int:
        """
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
        """
        logger.debug(f"🔍 Подсчёт комментариев для проблемы: {issue_id}")

        count = await self.count_items(issue_id=issue_id)

        logger.info(f"✨ У проблемы {issue_id} найдено {count} комментариев")
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
            f"🔍 Обновление флага is_solution для комментария: {comment_id}"
        )

        updated_comment = await self.update_item(
            comment_id,
            {"is_solution": is_solution},
        )

        if updated_comment:
            status = "решением" if is_solution else "обычным комментарием"
            logger.info(f"✨ Комментарий {comment_id} отмечен как {status}")
        else:
            logger.warning(f"⚠️ Комментарий {comment_id} не найден")

        return updated_comment
