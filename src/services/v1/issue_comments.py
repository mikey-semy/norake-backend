"""
Сервис для работы с комментариями к проблемам.

Содержит:
    IssueCommentService - бизнес-логика для управления комментариями.
"""

import logging
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    CommentAccessDeniedError,
    CommentNotFoundError,
    IssueNotFoundError,
)
from src.models.v1.issue_comments import IssueCommentModel
from src.repository.v1.issue_comments import IssueCommentRepository
from src.repository.v1.issues import IssueRepository

logger = logging.getLogger(__name__)


class IssueCommentService:
    """
    Сервис для управления комментариями к проблемам.

    Attributes:
        comment_repository (IssueCommentRepository): Репозиторий комментариев.
        issue_repository (IssueRepository): Репозиторий проблем для валидации.

    Example:
        >>> service = IssueCommentService(session)
        >>> comment = await service.create_comment(
        ...     issue_id=issue_id,
        ...     author_id=user_id,
        ...     content="Попробуйте перезагрузить"
        ... )
    """

    def __init__(
        self,
        session: AsyncSession,
    ):
        """
        Инициализирует сервис комментариев.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
        """
        self.comment_repository = IssueCommentRepository(session)
        self.issue_repository = IssueRepository(session)
        logger.debug("🔍 Инициализирован IssueCommentService")

    async def create_comment(
        self,
        issue_id: UUID,
        author_id: UUID,
        content: str,
        is_solution: bool = False,
    ) -> IssueCommentModel:
        """
        Создаёт новый комментарий к проблеме.

        Args:
            issue_id (UUID): ID проблемы.
            author_id (UUID): ID автора комментария.
            content (str): Текстовое содержимое комментария.
            is_solution (bool): Флаг, отмечающий комментарий как решение.

        Returns:
            IssueCommentModel: Созданный комментарий.

        Raises:
            IssueNotFoundError: Если проблема с указанным ID не существует.

        Example:
            >>> comment = await service.create_comment(
            ...     issue_id=uuid,
            ...     author_id=uuid,
            ...     content="Решение найдено"
            ... )
            >>> comment.content
            'Решение найдено'
        """
        logger.info(
            "✨ Создание комментария для проблемы %s от пользователя %s",
            issue_id,
            author_id,
        )

        # Проверка существования проблемы
        issue = await self.issue_repository.get_item_by_id(issue_id)
        if not issue:
            logger.warning("⚠️ Проблема %s не найдена", issue_id)
            raise IssueNotFoundError(issue_id=issue_id)

        # Создание комментария
        comment_data = {
            "issue_id": issue_id,
            "author_id": author_id,
            "content": content,
            "is_solution": is_solution,
        }

        comment = await self.comment_repository.create_item(comment_data)

        logger.info(
            "✅ Комментарий %s успешно создан для проблемы %s",
            comment.id,
            issue_id,
        )
        return comment

    async def get_comments(
        self,
        issue_id: UUID,
    ) -> List[IssueCommentModel]:
        """
        Получает все комментарии для проблемы.

        Args:
            issue_id (UUID): ID проблемы.

        Returns:
            List[IssueCommentModel]: Список комментариев (отсортирован по created_at).

        Raises:
            IssueNotFoundError: Если проблема не существует.

        Example:
            >>> comments = await service.get_comments(issue_id)
            >>> len(comments)
            5
        """
        logger.info("✨ Получение комментариев для проблемы %s", issue_id)

        # Проверка существования проблемы
        issue = await self.issue_repository.get_item_by_id(issue_id)
        if not issue:
            logger.warning("⚠️ Проблема %s не найдена", issue_id)
            raise IssueNotFoundError(issue_id=issue_id)

        # Получение комментариев
        comments = await self.comment_repository.get_by_issue(
            issue_id=issue_id,
            order_by_created=True,
        )

        logger.info(
            "✅ Получено %s комментариев для проблемы %s",
            len(comments),
            issue_id,
        )
        return comments

    async def delete_comment(
        self,
        comment_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        """
        Удаляет комментарий.

        Args:
            comment_id (UUID): ID комментария для удаления.
            user_id (UUID): ID пользователя, пытающегося удалить комментарий.
            is_admin (bool): Является ли пользователь администратором.

        Raises:
            CommentNotFoundError: Если комментарий не найден.
            CommentAccessDeniedError: Если пользователь не автор и не админ.

        Example:
            >>> await service.delete_comment(
            ...     comment_id=uuid,
            ...     user_id=uuid,
            ...     is_admin=False
            ... )

        Note:
            Только автор комментария или администратор могут удалить комментарий.
        """
        logger.info(
            "✨ Удаление комментария %s пользователем %s",
            comment_id,
            user_id,
        )

        # Получение комментария
        comment = await self.comment_repository.get_item_by_id(comment_id)
        if not comment:
            logger.warning("⚠️ Комментарий %s не найден", comment_id)
            raise CommentNotFoundError(comment_id=comment_id)

        # Проверка прав доступа
        if not is_admin and comment.author_id != user_id:
            logger.warning(
                "⚠️ Пользователь %s не имеет прав удалить "
                "комментарий %s (автор: %s)",
                user_id,
                comment_id,
                comment.author_id,
            )
            raise CommentAccessDeniedError(
                comment_id=comment_id,
                user_id=user_id,
            )

        # Удаление комментария
        await self.comment_repository.delete_item(comment_id)

        logger.info("✅ Комментарий %s успешно удалён", comment_id)

    async def mark_as_solution(
        self,
        comment_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> IssueCommentModel:
        """
        Отмечает комментарий как решение проблемы.

        Args:
            comment_id (UUID): ID комментария.
            user_id (UUID): ID пользователя.
            is_admin (bool): Является ли пользователь администратором.

        Returns:
            IssueCommentModel: Обновлённый комментарий.

        Raises:
            CommentNotFoundError: Если комментарий не найден.
            CommentAccessDeniedError: Если пользователь не автор проблемы и не админ.

        Example:
            >>> comment = await service.mark_as_solution(
            ...     comment_id=uuid,
            ...     user_id=uuid
            ... )
            >>> comment.is_solution
            True

        Note:
            Только автор проблемы или администратор могут отмечать решения.
        """
        logger.info(
            "✨ Отметка комментария %s как решения пользователем %s",
            comment_id,
            user_id,
        )

        # Получение комментария
        comment = await self.comment_repository.get_item_by_id(comment_id)
        if not comment:
            logger.warning("⚠️ Комментарий %s не найден", comment_id)
            raise CommentNotFoundError(comment_id=comment_id)

        # Получение проблемы для проверки прав
        issue = await self.issue_repository.get_item_by_id(comment.issue_id)
        if not issue:
            logger.warning("⚠️ Проблема %s не найдена", comment.issue_id)
            raise IssueNotFoundError(issue_id=comment.issue_id)

        # Проверка прав: только автор проблемы или админ
        if not is_admin and issue.author_id != user_id:
            logger.warning(
                "⚠️ Пользователь %s не является автором проблемы %s (автор: %s)",
                user_id,
                issue.id,
                issue.author_id,
            )
            raise CommentAccessDeniedError(
                comment_id=comment_id,
                user_id=user_id,
            )

        # Отметка как решение
        updated_comment = await self.comment_repository.mark_as_solution(
            comment_id=comment_id,
            is_solution=True,
        )

        logger.info("✅ Комментарий %s отмечен как решение", comment_id)
        return updated_comment  # type: ignore
