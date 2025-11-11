"""
Модуль issue_comments.py содержит модели для работы с комментариями к проблемам.

Этот модуль предоставляет:
   IssueCommentModel - модель комментария к проблеме (упрощённая версия без вложенности).
"""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .issues import IssueModel
    from .users import UserModel


class IssueCommentModel(BaseModel):
    """
    Модель комментария к проблеме (упрощённая версия без вложенности).

    Attributes:
        issue_id (UUID): ID проблемы, к которой относится комментарий.
        author_id (UUID): ID автора комментария.
        content (str): Текстовое содержимое комментария.
        is_solution (bool): Флаг, отмечающий комментарий как решение.
        created_at (datetime): Дата и время создания.
        updated_at (datetime): Дата и время последнего обновления.

    Relationships:
        issue (IssueModel): Проблема, к которой относится комментарий.
        author (UserModel): Автор комментария.

    Example:
        >>> comment = IssueCommentModel(
        ...     issue_id=issue.id,
        ...     author_id=user.id,
        ...     content="Попробуйте перезагрузить сервер",
        ...     is_solution=False
        ... )
        >>> session.add(comment)
        >>> await session.commit()

    Note:
        Упрощённая версия без поддержки вложенных комментариев (parent_id).
        Для MVP достаточно плоской структуры комментариев.
    """

    __tablename__ = "issue_comments"

    # Связь с проблемой
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID проблемы",
    )

    # Связь с автором
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID автора комментария",
    )

    # Содержимое комментария
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текстовое содержимое комментария",
    )

    # Флаг решения
    is_solution: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Флаг, отмечающий комментарий как решение проблемы",
    )

    # Relationships
    issue: Mapped["IssueModel"] = relationship(
        "IssueModel",
        back_populates="comments",
        lazy="selectin",
    )

    author: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="issue_comments",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """
        Строковое представление комментария.

        Returns:
            str: Строка с информацией о комментарии.

        Example:
            >>> comment = IssueCommentModel(issue_id=uuid, author_id=uuid)
            >>> repr(comment)
            '<IssueComment(id=..., issue_id=..., author_id=..., is_solution=False)>'
        """
        return (
            f"<IssueComment("
            f"id={self.id}, "
            f"issue_id={self.issue_id}, "
            f"author_id={self.author_id}, "
            f"is_solution={self.is_solution}"
            f")>"
        )
