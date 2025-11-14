from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .ai_modules import WorkspaceModuleModel
    from .document_services import DocumentServiceModel
    from .knowledge_bases import KnowledgeBaseModel
    from .n8n_workflows import N8nWorkflowModel
    from .users import UserModel


class WorkspaceVisibility(str, Enum):
    """
    Enum видимости workspace.

    Attributes:
        PUBLIC: Публичное workspace - видно всем пользователям системы.
        PRIVATE: Приватное workspace - доступно только участникам.

    Note:
        PUBLIC workspace используются для демо, открытых проектов, общедоступных баз знаний.
        PRIVATE workspace для команд, конфиденциальных проектов, личного использования.

    Example:
        >>> workspace = WorkspaceModel(
        ...     name="Public Demo",
        ...     visibility=WorkspaceVisibility.PUBLIC
        ... )
        >>> workspace.visibility == WorkspaceVisibility.PUBLIC
        True
    """

    PUBLIC = "public"
    PRIVATE = "private"


class WorkspaceMemberRole(str, Enum):
    """
    Enum роли участника workspace.

    Attributes:
        OWNER: Владелец workspace - полный доступ + удаление workspace.
        ADMIN: Администратор - управление участниками, настройки, модерация.
        MEMBER: Участник - создание/редактирование Issues, доступ к KB.

    Hierarchy:
        OWNER > ADMIN > MEMBER

    Permissions:
        OWNER: все права + удаление workspace
        ADMIN: управление участниками, AI modules, настройки
        MEMBER: CRUD Issues, поиск в KB, использование n8n workflows

    Note:
        При создании workspace автор становится OWNER.
        Может быть только один OWNER на workspace.
        OWNER может передать владение другому участнику.

    Example:
        >>> member = WorkspaceMemberModel(
        ...     workspace_id=workspace_id,
        ...     user_id=user_id,
        ...     role=WorkspaceMemberRole.ADMIN
        ... )
        >>> member.role == WorkspaceMemberRole.ADMIN
        True
        >>> member.role.value
        'admin'
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class WorkspaceModel(BaseModel):
    """
    Модель workspace - группы проблем для изоляции по командам.

    Workspace изолирует Issues, KB, AI modules по командам/проектам.
    Каждый workspace имеет владельца, участников, настройки AI модулей.

    Attributes:
        name (str): Название workspace (например, "Marketing Team").
        slug (str): Уникальный URL-friendly идентификатор (например, "marketing-team").
        description (Optional[str]): Описание назначения workspace.
        visibility (WorkspaceVisibility): Видимость (PUBLIC/PRIVATE).
        owner_id (UUID): UUID владельца workspace (FK users.id).
        settings (dict): JSONB настройки workspace (JSON Schema валидация).
        ai_modules_enabled (bool): Флаг активации AI модулей (RAG, n8n, search).

        owner (UserModel): Владелец workspace.
        members (List[WorkspaceMemberModel]): Список участников с ролями.
        ai_modules (List[WorkspaceModuleModel]): Подключенные AI модули.

    Relationships:
        owner: Many-to-One связь с UserModel (владелец).
        members: One-to-Many связь с WorkspaceMemberModel (участники).
        ai_modules: One-to-Many связь с WorkspaceModuleModel (AI модули).

    Settings JSONB Schema:
        {
            "default_issue_visibility": "public" | "private",
            "auto_categorize": bool,
            "smart_search_enabled": bool,
            "n8n_workflows": {
                "auto_categorize_webhook": str,
                "smart_search_webhook": str
            },
            "rag_config": {
                "embedding_model": str,
                "chunk_size": int,
                "overlap": int
            }
        }

    Note:
        slug генерируется автоматически из name при создании.
        При создании workspace автор автоматически добавляется как OWNER.
        ai_modules_enabled должен быть True для использования RAG/n8n/search.
        settings валидируется JSON Schema в service layer.

    Example:
        >>> # Создание workspace
        >>> workspace = WorkspaceModel(
        ...     name="Marketing Team",
        ...     slug="marketing-team",
        ...     description="Issues and KB for marketing department",
        ...     visibility=WorkspaceVisibility.PRIVATE,
        ...     owner_id=user_id,
        ...     settings={
        ...         "default_issue_visibility": "private",
        ...         "auto_categorize": True,
        ...         "smart_search_enabled": True
        ...     },
        ...     ai_modules_enabled=True
        ... )
        >>> workspace.visibility == WorkspaceVisibility.PRIVATE
        True
        >>> workspace.ai_modules_enabled
        True
        >>>
        >>> # Проверка настроек
        >>> workspace.settings.get("auto_categorize")
        True
    """

    __tablename__ = "workspaces"

    # Основная информация
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Название workspace",
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Уникальный URL-friendly идентификатор",
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Описание назначения workspace",
    )

    visibility: Mapped[WorkspaceVisibility] = mapped_column(
        SQLEnum(
            WorkspaceVisibility,
            name="workspace_visibility",
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
        default=WorkspaceVisibility.PRIVATE,
        comment="Видимость workspace (PUBLIC/PRIVATE)",
    )

    # Владение
    owner_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID владельца workspace",
    )

    # Настройки
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="JSONB настройки workspace (валидируется JSON Schema)",
    )

    ai_modules_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Флаг активации AI модулей (RAG, n8n, search)",
    )

    # Relationships
    owner: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="owned_workspaces",
        lazy="joined",
    )

    members: Mapped[List["WorkspaceMemberModel"]] = relationship(
        "WorkspaceMemberModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    ai_modules: Mapped[List["WorkspaceModuleModel"]] = relationship(
        "WorkspaceModuleModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    knowledge_bases: Mapped[List["KnowledgeBaseModel"]] = relationship(
        "KnowledgeBaseModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    n8n_workflows: Mapped[List["N8nWorkflowModel"]] = relationship(
        "N8nWorkflowModel",
        back_populates="workspace",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    document_services: Mapped[List["DocumentServiceModel"]] = relationship(
        "DocumentServiceModel",
        foreign_keys="[DocumentServiceModel.workspace_id]",
        back_populates="workspace",
        passive_deletes=True,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Представление модели для отладки."""
        return (
            f"<WorkspaceModel(id={self.id}, name='{self.name}', "
            f"slug='{self.slug}', visibility={self.visibility.value}, "
            f"ai_enabled={self.ai_modules_enabled})>"
        )


class WorkspaceMemberModel(BaseModel):
    """
    Модель участника workspace.

    Связывает пользователей с workspace и определяет их роли.
    Один пользователь может быть участником нескольких workspace.

    Attributes:
        workspace_id (UUID): UUID workspace (FK workspaces.id).
        user_id (UUID): UUID пользователя (FK users.id).
        role (WorkspaceMemberRole): Роль в workspace (OWNER/ADMIN/MEMBER).

        workspace (WorkspaceModel): Workspace, в котором участник состоит.
        user (UserModel): Пользователь-участник.

    Relationships:
        workspace: Many-to-One связь с WorkspaceModel.
        user: Many-to-One связь с UserModel.

    Constraints:
        Unique constraint на (workspace_id, user_id) - один user = одна роль в workspace.
        Один workspace может иметь только одного OWNER.

    Note:
        При создании workspace автор автоматически добавляется с ролью OWNER.
        OWNER может быть только один - при передаче владения меняется роль.
        При удалении workspace все members удаляются (CASCADE).
        При удалении user удаляются все его membership (CASCADE).

    Example:
        >>> # Добавление участника
        >>> member = WorkspaceMemberModel(
        ...     workspace_id=workspace_id,
        ...     user_id=user_id,
        ...     role=WorkspaceMemberRole.MEMBER
        ... )
        >>> member.role == WorkspaceMemberRole.MEMBER
        True
        >>>
        >>> # Повышение до админа
        >>> member.role = WorkspaceMemberRole.ADMIN
        >>> member.role.value
        'admin'
    """

    __tablename__ = "workspace_members"

    # Связи
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID workspace",
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID пользователя",
    )

    # Роль
    role: Mapped[WorkspaceMemberRole] = mapped_column(
        SQLEnum(
            WorkspaceMemberRole,
            name="workspace_member_role",
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        index=True,
        comment="Роль в workspace (OWNER/ADMIN/MEMBER)",
    )

    # Relationships
    workspace: Mapped["WorkspaceModel"] = relationship(
        "WorkspaceModel",
        back_populates="members",
        lazy="joined",
    )

    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="workspace_memberships",
        lazy="joined",
    )

    def __repr__(self) -> str:
        """Представление модели для отладки."""
        return (
            f"<WorkspaceMemberModel(id={self.id}, workspace_id={self.workspace_id}, "
            f"user_id={self.user_id}, role={self.role.value})>"
        )
