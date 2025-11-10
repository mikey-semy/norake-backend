"""
Request-схемы для Workspace API.

Содержит схемы для входящих запросов (создание, обновление).
"""

from typing import Any, Dict, Optional

from pydantic import Field

from src.schemas.v1.workspaces.base import (
    WorkspaceBaseSchema,
    WorkspaceMemberBaseSchema,
)


class WorkspaceCreateSchema(WorkspaceBaseSchema):
    """
    Схема для создания Workspace.

    Slug генерируется автоматически из name.
    Creator автоматически становится OWNER.

    Example:
        >>> data = WorkspaceCreateSchema(
        ...     name="Marketing Team",
        ...     description="Our marketing workspace",
        ...     visibility="private",
        ...     settings={"auto_categorize": True}
        ... )
    """

    pass


class WorkspaceUpdateSchema(WorkspaceBaseSchema):
    """
    Схема для обновления Workspace.

    Все поля опциональны.
    Slug не может быть изменён.

    Example:
        >>> data = WorkspaceUpdateSchema(
        ...     name="New Marketing Team",
        ...     description="Updated description"
        ... )
    """

    name: Optional[str] = Field(
        None,
        min_length=3,
        max_length=100,
        description="Новое название workspace",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Новое описание workspace",
    )
    visibility: Optional[str] = Field(
        None,
        description="Новая видимость workspace",
    )
    settings: Optional[Dict[str, Any]] = Field(
        None,
        description="Обновлённые настройки workspace",
    )


class MemberAddSchema(WorkspaceMemberBaseSchema):
    """
    Схема для добавления участника в Workspace.

    Может использоваться только OWNER или ADMIN.
    Нельзя добавить второго OWNER.

    Example:
        >>> data = MemberAddSchema(
        ...     user_id="uuid-here",
        ...     role="admin"
        ... )
    """

    pass


class MemberUpdateSchema(WorkspaceMemberBaseSchema):
    """
    Схема для изменения роли участника.

    Может использоваться только OWNER или ADMIN.
    Нельзя изменить роль единственного OWNER.

    Example:
        >>> data = MemberUpdateSchema(
        ...     role="member"
        ... )
    """

    user_id: Optional[str] = Field(
        None,
        description="UUID пользователя (не изменяется)",
    )
