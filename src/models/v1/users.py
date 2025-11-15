from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .ai_chats import AIChatModel
    from .issue_comments import IssueCommentModel
    from .issues import IssueModel
    from .roles import UserRoleModel
    from .templates import TemplateModel
    from .workspaces import WorkspaceMemberModel, WorkspaceModel
    from .document_services import DocumentServiceModel

class UserModel(BaseModel):
    """
    Модель пользователя.

    Attributes:
        username (str): Уникальное имя пользователя для входа в систему.
        email (str): Email адрес для входа в систему (уникальный).
        phone (Optional[str]): Контактный телефон пользователя (заполняется в профиле).
        password_hash (Optional[str]): Bcrypt хеш пароля для аутентификации.
        is_active (bool): Флаг активности аккаунта (деактивированные не могут входить).

        user_roles (List[UserRoleModel]): Список ролей пользователя (admin/user).
        issues (List[IssueModel]): Список проблем, созданных пользователем.
        owned_workspaces (List[WorkspaceModel]): Список workspace, где user - владелец.
        workspace_memberships (List[WorkspaceMemberModel]): Участие в workspace.

    Relationships:
        user_roles: One-to-Many связь с UserRoleModel (роли пользователя).
        issues: One-to-Many связь с IssueModel (проблемы автора).
        owned_workspaces: One-to-Many связь с WorkspaceModel (владение workspace).
        workspace_memberships: One-to-Many связь с WorkspaceMemberModel (участие).

    Properties:
        role: Основная роль пользователя для API ("admin" или "user").

    Note:
        При регистрации создается пользователь с минимальными данными (username, email, password).
        Поле phone заполняется позже в профиле.

    Example:
        >>> # Регистрация с минимальными данными
        >>> user = UserModel(
        ...     username="john_doe",
        ...     email="john@example.com",
        ...     password_hash=hashed_password,
        ...     is_active=True
        ... )
        >>> user.role
        "user"
        >>>
        >>> # Заполнение профиля позже
        >>> user.phone = "+79991234567"
        >>> user.has_role("admin")
        False
        >>> user.has_role("user")
        True
    """

    __tablename__ = "users"

    # Основная информация
    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Уникальное имя пользователя для входа",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Email адрес пользователя",
    )

    phone: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="Контактный телефон (опционально)",
    )

    # Аутентификация
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Хеш пароля"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Активен ли пользователь"
    )

    user_roles: Mapped[List["UserRoleModel"]] = relationship(
        "UserRoleModel",
        foreign_keys="[UserRoleModel.user_id]",
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    issues: Mapped[List["IssueModel"]] = relationship(
        "IssueModel",
        foreign_keys="[IssueModel.author_id]",
        back_populates="author",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    templates: Mapped[List["TemplateModel"]] = relationship(
        "TemplateModel",
        foreign_keys="[TemplateModel.author_id]",
        back_populates="author",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    owned_workspaces: Mapped[List["WorkspaceModel"]] = relationship(
        "WorkspaceModel",
        foreign_keys="[WorkspaceModel.owner_id]",
        back_populates="owner",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    workspace_memberships: Mapped[List["WorkspaceMemberModel"]] = relationship(
        "WorkspaceMemberModel",
        foreign_keys="[WorkspaceMemberModel.user_id]",
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    comments: Mapped[List["IssueCommentModel"]] = relationship(
        "IssueCommentModel",
        foreign_keys="[IssueCommentModel.author_id]",
        back_populates="author",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    document_services: Mapped[List["DocumentServiceModel"]] = relationship(
        "DocumentServiceModel",
        foreign_keys="[DocumentServiceModel.author_id]",
        back_populates="author",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    ai_chats: Mapped[List["AIChatModel"]] = relationship(
        "AIChatModel",
        foreign_keys="[AIChatModel.user_id]",
        back_populates="user",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    def has_role(self, role_code: str) -> bool:
        """
        Проверяет наличие роли у пользователя.

        Args:
            role_code: Код роли для проверки ("admin" или "user").

        Returns:
            True если роль назначена, False в противном случае.

        Example:
            >>> user.has_role("admin")
            False
            >>> user.has_role("user")
            True
        """
        return any(ur.role_code.value == role_code for ur in self.user_roles)

    @property
    def role(self) -> str:
        """
        Возвращает основную роль пользователя для API.

        Используется для сериализации в API responses. Если у пользователя
        несколько ролей, возвращается первая из списка. По умолчанию "user".

        Returns:
            Код роли: "admin" или "user".

        Note:
            В текущей реализации у пользователя может быть только одна роль,
            но модель поддерживает множественные роли для будущего расширения.
        """
        if self.user_roles:
            return self.user_roles[0].role_code.value
        return "user"

    def __repr__(self) -> str:
        """Строковое представление модели для отладки."""
        return f"<UserModel(username={self.username}, email={self.email}, role={self.role})>"
