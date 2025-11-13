"""
Модуль issue_comments.py содержит модели для работы с комментариями к проблемам.

Этот модуль предоставляет:
   IssueCommentModel - модель комментария к проблеме с поддержкой вложенности (threaded comments).
"""

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .issues import IssueModel
    from .users import UserModel


class IssueCommentModel(BaseModel):
    """
    Модель комментария к проблеме с поддержкой вложенности (threaded comments).

    Комментарии могут быть корневыми (parent_id=None) или вложенными (parent_id указывает
    на родительский комментарий). Это позволяет создавать древовидные обсуждения к проблемам.

    Attributes:
        issue_id (UUID): ID проблемы, к которой относится комментарий.
        author_id (UUID): ID автора комментария.
        content (str): Текстовое содержимое комментария.
        parent_id (Optional[UUID]): ID родительского комментария для вложенности.
        is_solution (bool): Флаг, отмечающий комментарий как решение.
        created_at (datetime): Дата и время создания.
        updated_at (datetime): Дата и время последнего обновления.

    Relationships:
        issue (IssueModel): Проблема, к которой относится комментарий.
        author (UserModel): Автор комментария.
        parent (IssueCommentModel): Родительский комментарий (для вложенных комментариев).
        replies (List[IssueCommentModel]): Дочерние комментарии (ответы на этот комментарий).

    Example:
        >>> # Корневой комментарий
        >>> root_comment = IssueCommentModel(
        ...     issue_id=issue.id,
        ...     author_id=user.id,
        ...     content="Проблема воспроизводится на всех станках серии X200",
        ...     parent_id=None
        ... )
        >>> session.add(root_comment)
        >>> await session.commit()
        >>>
        >>> # Ответ на комментарий
        >>> reply = IssueCommentModel(
        ...     issue_id=issue.id,
        ...     author_id=another_user.id,
        ...     content="Подтверждаю, на X200-5 тоже наблюдается",
        ...     parent_id=root_comment.id
        ... )
        >>> session.add(reply)
        >>> await session.commit()

    Note:
        При удалении родительского комментария все дочерние комментарии также удаляются
        (cascade="all, delete-orphan"). При создании корневого комментария parent_id = None.
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

    # Поддержка вложенности (parent_id для threaded comments)
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("issue_comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="ID родительского комментария для вложенности",
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
        lazy="joined",
    )

    author: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="comments",
        lazy="joined",
    )

    # Self-referencing relationship для вложенности
    parent: Mapped[Optional["IssueCommentModel"]] = relationship(
        "IssueCommentModel",
        remote_side="IssueCommentModel.id",
        back_populates="replies",
        lazy="selectin",
    )

    replies: Mapped[list["IssueCommentModel"]] = relationship(
        "IssueCommentModel",
        back_populates="parent",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """
        Строковое представление комментария.

        Returns:
            str: Строка с информацией о комментарии.

        Example:
            >>> comment = IssueCommentModel(issue_id=uuid, author_id=uuid)
            >>> repr(comment)
            "IssueCommentModel(id=..., issue_id=..., parent_id=None)"
        """
        content_preview = (
            self.content[:50] + "..." if len(self.content) > 50 else self.content
        )
        return (
            f"IssueCommentModel(id={self.id}, issue_id={self.issue_id}, "
            f"author_id={self.author_id}, parent_id={self.parent_id}, "
            f"content='{content_preview}')"
        )
