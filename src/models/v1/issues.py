"""
Модуль issues.py содержит модели для работы с проблемами (Issues).

Этот модуль предоставляет:
   IssueStatus - enum для статусов проблем (RED/GREEN).
   IssueModel - модель проблемы с полями и связями.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .users import UserModel


class IssueStatus(str, enum.Enum):
    """
    Enum для статусов проблем.

    Attributes:
        RED: Проблема не решена (активная).
        GREEN: Проблема решена (закрыта).

    Example:
        >>> issue = IssueModel(status=IssueStatus.RED)
        >>> issue.status
        <IssueStatus.RED: 'red'>
        >>> issue.status = IssueStatus.GREEN
        >>> issue.is_resolved
        True
    """

    RED = "red"
    GREEN = "green"


class IssueModel(BaseModel):
    """
    Модель проблемы (Issue).

    Attributes:
        title (str): Заголовок проблемы (до 255 символов).
        description (str): Подробное описание проблемы.
        category (str): Категория проблемы (hardware/software/process/documentation/
            safety/quality/maintenance/training/other).
        status (IssueStatus): Текущий статус проблемы (RED/GREEN).
        solution (Optional[str]): Текст решения проблемы (заполняется при закрытии).
        author_id (UUID): Foreign Key на users.id (автор проблемы).
        workspace_id (UUID): Foreign Key на workspaces.id (рабочее пространство).
        resolved_at (Optional[datetime]): Дата и время решения проблемы.

        author (UserModel): Relationship к пользователю-автору.
        workspace (WorkspaceModel): Relationship к рабочему пространству.

    Properties:
        is_resolved (bool): Проверяет, решена ли проблема (status == GREEN).

    Note:
        При создании проблемы статус по умолчанию RED.
        При решении проблемы нужно:
        - Установить status = IssueStatus.GREEN
        - Заполнить solution текстом решения
        - Установить resolved_at = datetime.now(timezone.utc)

    Example:
        >>> # Создание новой проблемы
        >>> issue = IssueModel(
        ...     title="Ошибка E401 на станке",
        ...     description="При запуске станка возникает ошибка E401",
        ...     category="hardware",
        ...     status=IssueStatus.RED,
        ...     author_id=user_id,
        ...     workspace_id=workspace_id
        ... )
        >>> issue.is_resolved
        False
        >>>
        >>> # Решение проблемы
        >>> issue.status = IssueStatus.GREEN
        >>> issue.solution = "Заменён датчик положения, проблема устранена"
        >>> issue.resolved_at = datetime.now(timezone.utc)
        >>> issue.is_resolved
        True
    """

    __tablename__ = "issues"

    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, name="issue_status"),
        nullable=False,
        default=IssueStatus.RED,
        index=True,
    )
    solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="issues",
        lazy="joined",
    )

    @property
    def is_resolved(self) -> bool:
        """
        Проверяет, решена ли проблема.

        Returns:
            bool: True если status == GREEN, иначе False.

        Example:
            >>> issue = IssueModel(status=IssueStatus.RED)
            >>> issue.is_resolved
            False
            >>> issue.status = IssueStatus.GREEN
            >>> issue.is_resolved
            True
        """
        return self.status == IssueStatus.GREEN

    def __repr__(self) -> str:
        """
        Строковое представление модели Issue.

        Returns:
            str: Строка в формате "IssueModel(id=..., title=..., status=...)".
        """
        return (
            f"IssueModel(id={self.id}, title='{self.title}', "
            f"status={self.status.value}, category='{self.category}')"
        )
