"""
Request-схемы для Workspace API.

Содержит схемы для входящих запросов (создание, обновление).
"""

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseRequestSchema


class WorkspaceCreateRequestSchema(BaseRequestSchema):
    """
    Схема для создания Workspace.

    Slug генерируется автоматически из name.
    Creator автоматически становится OWNER.

    Example:
        >>> data = WorkspaceCreateRequestSchema(
        ...     name="Marketing Team",
        ...     description="Our marketing workspace",
        ...     visibility="private",
        ...     settings={"auto_categorize": True}
        ... )
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Название workspace",
        examples=["Marketing Team"],
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Описание workspace",
    )
    visibility: str = Field(
        default="private",
        description="Видимость workspace (private/public/team)",
        examples=["private"],
    )
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Настройки workspace (JSONB)",
    )


class WorkspaceUpdateRequestSchema(BaseRequestSchema):
    """
    Схема для обновления Workspace.

    Все поля опциональны.
    Slug не может быть изменён.

    Example:
        >>> data = WorkspaceUpdateRequestSchema(
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


class MemberAddRequestSchema(BaseRequestSchema):
    """
    Схема для добавления участника в Workspace.

    Может использоваться только OWNER или ADMIN.
    Нельзя добавить второго OWNER.

    Example:
        >>> data = MemberAddRequestSchema(
        ...     user_id="uuid-here",
        ...     role="admin"
        ... )
    """

    user_id: UUID = Field(
        ...,
        description="UUID пользователя для добавления",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )
    role: str = Field(
        default="member",
        description="Роль участника (owner/admin/member)",
        examples=["member"],
    )


class MemberUpdateRequestSchema(BaseRequestSchema):
    """
    Схема для изменения роли участника.

    Может использоваться только OWNER или ADMIN.
    Нельзя изменить роль единственного OWNER.

    Example:
        >>> data = MemberUpdateRequestSchema(
        ...     role="member"
        ... )
    """

    role: str = Field(
        ...,
        description="Новая роль участника (owner/admin/member)",
        examples=["admin"],
    )
