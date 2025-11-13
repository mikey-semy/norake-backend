"""
Сервис для работы с комментариями к проблемам.

Содержит бизнес-логику для управления комментариями с поддержкой вложенности:
    - Создание комментариев и ответов (parent_id)
    - Получение дерева комментариев с eager loading
    - Обновление и удаление с проверкой прав
    - Отметка комментария как решения

Возвращает domain objects (IssueCommentModel), НЕ схемы!

Classes:
    IssueCommentService: Сервис с методами для работы с комментариями.

Example:
    >>> service = IssueCommentService(session=session)
    >>> # Создание корневого комментария
    >>> comment = await service.create_comment(
    ...     issue_id=issue_id,
    ...     author_id=user_id,
    ...     content="Попробуйте перезагрузить"
    ... )
    >>> # Ответ на комментарий
    >>> reply = await service.create_comment(
    ...     issue_id=issue_id,
    ...     author_id=user_id,
    ...     content="Спасибо, помогло!",
    ...     parent_id=comment.id
    ... )
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

    Содержит бизнес-логику: валидацию, проверку прав доступа,
    оркестрацию действий. Возвращает domain objects (IssueCommentModel).

    Attributes:
        comment_repository: Репозиторий для работы с IssueCommentModel.
        issue_repository: Репозиторий для валидации проблем.

    Methods:
        create_comment: Создать комментарий или ответ (с parent_id).
        get_comments: Получить корневые комментарии с опциональной вложенностью.
        get_comment_with_replies: Получить конкретный комментарий с деревом ответов.
        update_comment: Обновить содержимое комментария (только автор или admin).
        delete_comment: Удалить комментарий (только автор или admin).
        mark_as_solution: Отметить комментарий как решение (только автор проблемы или admin).

    Business Rules:
        - Ответы (parent_id) должны принадлежать той же проблеме
        - Только автор комментария или admin могут удалить/редактировать
        - Комментарии-решения (is_solution=True) нельзя редактировать
        - Только автор проблемы или admin могут отметить решение

    Example:
        >>> service = IssueCommentService(session)
        >>> # Создание комментария
        >>> comment = await service.create_comment(
        ...     issue_id=issue_id,
        ...     author_id=user_id,
        ...     content="Попробуйте перезагрузить"
        ... )
        >>> # Получение дерева комментариев
        >>> comments = await service.get_comments(issue_id, with_replies=True)
        >>> # Обновление комментария
        >>> updated = await service.update_comment(
        ...     comment_id=comment.id,
        ...     user_id=user_id,
        ...     content="Обновлённый текст"
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
        parent_id: UUID | None = None,
    ) -> IssueCommentModel:
        """
        Создаёт новый комментарий к проблеме.

        Args:
            issue_id (UUID): ID проблемы.
            author_id (UUID): ID автора комментария.
            content (str): Текстовое содержимое комментария.
            is_solution (bool): Флаг, отмечающий комментарий как решение.
            parent_id (UUID | None): ID родительского комментария для ответа.

        Returns:
            IssueCommentModel: Созданный комментарий.

        Raises:
            IssueNotFoundError: Если проблема с указанным ID не существует.
            CommentNotFoundError: Если parent_id указан, но родительский комментарий не найден.
            CommentAccessDeniedError: Если parent_id принадлежит другой проблеме.

        Example:
            >>> comment = await service.create_comment(
            ...     issue_id=uuid,
            ...     author_id=uuid,
            ...     content="Решение найдено"
            ... )
            >>> comment.content
            'Решение найдено'
            >>> # Ответ на комментарий
            >>> reply = await service.create_comment(
            ...     issue_id=uuid,
            ...     author_id=uuid,
            ...     content="Спасибо!",
            ...     parent_id=comment.id
            ... )
        """
        logger.info(
            "✨ Создание комментария для проблемы %s от пользователя %s (parent_id=%s)",
            issue_id,
            author_id,
            parent_id,
        )

        # Проверка существования проблемы
        issue = await self.issue_repository.get_item_by_id(issue_id)
        if not issue:
            logger.warning("⚠️ Проблема %s не найдена", issue_id)
            raise IssueNotFoundError(issue_id=issue_id)

        # Валидация parent_id (если указан)
        if parent_id:
            parent_comment = await self.comment_repository.get_item_by_id(parent_id)
            if not parent_comment:
                logger.warning("⚠️ Родительский комментарий %s не найден", parent_id)
                raise CommentNotFoundError(comment_id=parent_id)

            # Проверка что parent принадлежит той же проблеме
            if parent_comment.issue_id != issue_id:
                logger.warning(
                    "⚠️ Родительский комментарий %s принадлежит проблеме %s, а не %s",
                    parent_id,
                    parent_comment.issue_id,
                    issue_id,
                )
                raise CommentAccessDeniedError(
                    comment_id=parent_id,
                    user_id=author_id,
                )

        # Создание комментария
        comment_data = {
            "issue_id": issue_id,
            "author_id": author_id,
            "content": content,
            "is_solution": is_solution,
            "parent_id": parent_id,
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
        with_replies: bool = True,
    ) -> List[IssueCommentModel]:
        """
        Получает комментарии для проблемы (только корневые или с ответами).

        Args:
            issue_id (UUID): ID проблемы.
            with_replies (bool): Загружать ли вложенные ответы (eager loading).

        Returns:
            List[IssueCommentModel]: Список корневых комментариев (с replies если with_replies=True).

        Raises:
            IssueNotFoundError: Если проблема не существует.

        Example:
            >>> comments = await service.get_comments(issue_id)
            >>> len(comments)
            5
            >>> comments[0].replies  # Вложенные ответы загружены
            [<IssueCommentModel>, <IssueCommentModel>]
            >>> # Только корневые комментарии без ответов
            >>> root_comments = await service.get_comments(issue_id, with_replies=False)
        """
        logger.info(
            "✨ Получение комментариев для проблемы %s (with_replies=%s)",
            issue_id,
            with_replies,
        )

        # Проверка существования проблемы
        issue = await self.issue_repository.get_item_by_id(issue_id)
        if not issue:
            logger.warning("⚠️ Проблема %s не найдена", issue_id)
            raise IssueNotFoundError(issue_id=issue_id)

        # Получение комментариев через новый метод
        comments = await self.comment_repository.get_issue_comments(
            issue_id=issue_id,
            with_replies=with_replies,
        )

        logger.info(
            "✅ Получено %s корневых комментариев для проблемы %s",
            len(comments),
            issue_id,
        )
        return comments

    async def get_comment_with_replies(
        self,
        comment_id: UUID,
    ) -> IssueCommentModel:
        """
        Получает конкретный комментарий с полным деревом ответов.

        Args:
            comment_id (UUID): ID комментария.

        Returns:
            IssueCommentModel: Комментарий с загруженными вложенными ответами.

        Raises:
            CommentNotFoundError: Если комментарий не найден.

        Example:
            >>> comment = await service.get_comment_with_replies(comment_id)
            >>> comment.replies  # Дерево ответов загружено
            [<IssueCommentModel(replies=[...])>, ...]
        """
        logger.info("✨ Получение комментария %s с деревом ответов", comment_id)

        # Получение дерева комментариев
        comments = await self.comment_repository.get_comment_tree(parent_id=comment_id)

        # Проверка что корневой комментарий существует
        if not comments:
            logger.warning("⚠️ Комментарий %s не найден", comment_id)
            raise CommentNotFoundError(comment_id=comment_id)

        # Первый элемент - корневой комментарий
        root_comment = comments[0]

        logger.info(
            "✅ Комментарий %s получен с %s ответами",
            comment_id,
            len(root_comment.replies) if root_comment.replies else 0,
        )
        return root_comment

    async def update_comment(
        self,
        comment_id: UUID,
        user_id: UUID,
        content: str,
        is_admin: bool = False,
    ) -> IssueCommentModel:
        """
        Обновляет содержимое комментария.

        Args:
            comment_id (UUID): ID комментария.
            user_id (UUID): ID пользователя, пытающегося обновить комментарий.
            content (str): Новое содержимое комментария.
            is_admin (bool): Является ли пользователь администратором.

        Returns:
            IssueCommentModel: Обновлённый комментарий.

        Raises:
            CommentNotFoundError: Если комментарий не найден.
            CommentAccessDeniedError: Если пользователь не автор и не админ.
            IssueValidationError: Если комментарий является решением (нельзя редактировать).

        Example:
            >>> updated = await service.update_comment(
            ...     comment_id=uuid,
            ...     user_id=uuid,
            ...     content="Обновлённый текст"
            ... )

        Note:
            Только автор комментария или администратор могут редактировать комментарий.
            Комментарии, отмеченные как решения (is_solution=True), нельзя редактировать.
        """
        logger.info(
            "✨ Обновление комментария %s пользователем %s",
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
                "⚠️ Пользователь %s не имеет прав редактировать "
                "комментарий %s (автор: %s)",
                user_id,
                comment_id,
                comment.author_id,
            )
            raise CommentAccessDeniedError(
                comment_id=comment_id,
                user_id=user_id,
            )

        # Проверка что комментарий не является решением
        if comment.is_solution:
            logger.warning(
                "⚠️ Комментарий %s является решением и не может быть отредактирован",
                comment_id,
            )
            from src.core.exceptions import IssueValidationError

            raise IssueValidationError(
                field="is_solution",
                message="Комментарии-решения нельзя редактировать",
            )

        # Обновление комментария
        updated_comment = await self.comment_repository.update_item(
            item_id=comment_id,
            data={"content": content},
        )

        logger.info("✅ Комментарий %s успешно обновлён", comment_id)
        return updated_comment

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
