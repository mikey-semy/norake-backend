"""
Исключения для работы с комментариями к проблемам.

Содержит:
    CommentNotFoundError - комментарий не найден.
    CommentAccessDeniedError - нет доступа к комментарию.
"""

from typing import Optional
from uuid import UUID

from .base import BaseAPIException


class CommentNotFoundError(BaseAPIException):
    """
    Исключение, возникающее при попытке получить несуществующий комментарий.

    Attributes:
        comment_id (UUID): ID комментария, который не был найден.

    Example:
        >>> raise CommentNotFoundError(comment_id=uuid)
    """

    def __init__(
        self,
        comment_id: UUID,
        extra: Optional[dict] = None,
    ):
        """
        Инициализирует исключение CommentNotFoundError.

        Args:
            comment_id (UUID): ID комментария.
            extra (Optional[dict]): Дополнительные данные для логирования.
        """
        self.comment_id = comment_id
        super().__init__(
            status_code=404,
            detail=f"💬 Комментарий с ID {comment_id} не найден",
            error_type="comment_not_found",
            extra={"comment_id": str(comment_id), **(extra or {})},
        )


class CommentAccessDeniedError(BaseAPIException):
    """
    Исключение при попытке удалить чужой комментарий.

    Attributes:
        comment_id (UUID): ID комментария.
        user_id (UUID): ID пользователя, пытающегося удалить комментарий.

    Example:
        >>> raise CommentAccessDeniedError(comment_id=uuid, user_id=uuid)
    """

    def __init__(
        self,
        comment_id: UUID,
        user_id: UUID,
        extra: Optional[dict] = None,
    ):
        """
        Инициализирует исключение CommentAccessDeniedError.

        Args:
            comment_id (UUID): ID комментария.
            user_id (UUID): ID пользователя.
            extra (Optional[dict]): Дополнительные данные.
        """
        self.comment_id = comment_id
        self.user_id = user_id
        super().__init__(
            status_code=403,
            detail="🔐 Вы не можете удалить чужой комментарий",
            error_type="comment_access_denied",
            extra={
                "comment_id": str(comment_id),
                "user_id": str(user_id),
                **(extra or {}),
            },
        )
