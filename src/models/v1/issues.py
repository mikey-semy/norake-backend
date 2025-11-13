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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .issue_comments import IssueCommentModel
    from .templates import TemplateModel
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


class IssueVisibility(str, enum.Enum):
    """
    Enum для видимости проблем.

    Attributes:
        PUBLIC: Проблема доступна всем без аутентификации (коллективная память).
        WORKSPACE: Проблема видна только участникам воркспейса и администраторам.
        PRIVATE: Проблема видна только автору и администраторам.

    Note:
        - PUBLIC: быстрый доступ к решениям без логина, видна в публичном поиске.
        - WORKSPACE: для внутренних проблем компании/подразделения.
        - PRIVATE: для конфиденциальных данных (future: ACL per-user/team).

    Example:
        >>> issue = IssueModel(visibility=IssueVisibility.PUBLIC)
        >>> issue.visibility
        <IssueVisibility.PUBLIC: 'public'>
        >>> issue.visibility = IssueVisibility.WORKSPACE
    """

    PUBLIC = "public"
    WORKSPACE = "workspace"
    PRIVATE = "private"


class IssueModel(BaseModel):
    """
    Модель проблемы (Issue).

    Attributes:
        title (str): Заголовок проблемы (до 255 символов).
        description (str): Подробное описание проблемы.
        category (str): Категория проблемы (hardware/software/process/documentation/
            safety/quality/maintenance/training/other).
        status (IssueStatus): Текущий статус проблемы (RED/GREEN).
        visibility (IssueVisibility): Видимость проблемы (PUBLIC/WORKSPACE/PRIVATE).
        solution (Optional[str]): Текст решения проблемы (заполняется при закрытии).
        author_id (UUID): Foreign Key на users.id (автор проблемы).
        workspace_id (UUID): Foreign Key на workspaces.id (рабочее пространство).
        template_id (Optional[UUID]): Foreign Key на templates.id (шаблон для динамических полей).
        custom_fields (dict): JSONB со значениями динамических полей из шаблона.
        resolved_at (Optional[datetime]): Дата и время решения проблемы.

        author (UserModel): Relationship к пользователю-автору.
        workspace (WorkspaceModel): Relationship к рабочему пространству.
        template (Optional[TemplateModel]): Relationship к шаблону (если используется).

    Properties:
        is_resolved (bool): Проверяет, решена ли проблема (status == GREEN).

    Note:
        При создании проблемы статус по умолчанию RED.
        При решении проблемы нужно:
        - Установить status = IssueStatus.GREEN
        - Заполнить solution текстом решения
        - Установить resolved_at = datetime.now(timezone.utc)

        template_id и custom_fields опциональны - используются, если issue создана по шаблону.
        custom_fields хранит значения динамических полей (например, {"equipment_model": "CNC-1000"}).

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
    visibility: Mapped[IssueVisibility] = mapped_column(
        Enum(
            IssueVisibility,
            name="issue_visibility",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=IssueVisibility.PUBLIC,
        server_default="public",
        index=True,
    )
    solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    custom_fields: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
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

    template: Mapped[Optional["TemplateModel"]] = relationship(
        "TemplateModel",
        back_populates="issues",
        lazy="selectin",
    )

    comments: Mapped[list["IssueCommentModel"]] = relationship(
        "IssueCommentModel",
        back_populates="issue",
        lazy="selectin",
        cascade="all, delete-orphan",
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
