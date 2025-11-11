"""
Базовые Pydantic-схемы для Workspace.

Содержит общие поля и конфигурацию для схем workspace.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.v1.workspaces import WorkspaceVisibility


class WorkspaceBaseSchema(BaseModel):
    """
    Базовая схема для Workspace с общими полями.

    Содержит поля, общие для всех операций с workspace.

    Attributes:
        name: Название workspace
        description: Описание workspace
        visibility: Видимость (PUBLIC/PRIVATE)
        settings: Настройки workspace в JSON-формате

    Example:
        >>> data = {
        ...     "name": "Marketing Team",
        ...     "description": "Team for marketing activities",
        ...     "visibility": "public",
        ...     "settings": {"auto_categorize": True}
        ... }
    """

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Название workspace",
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Описание workspace",
    )
    visibility: WorkspaceVisibility = Field(
        default=WorkspaceVisibility.PRIVATE,
        description="Видимость workspace (public/private)",
    )
    settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Настройки workspace (JSONB)",
    )

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=False,
    )


class WorkspaceMemberBaseSchema(BaseModel):
    """
    Базовая схема для WorkspaceMember.

    Attributes:
        user_id: UUID пользователя
        role: Роль в workspace

    Example:
        >>> data = {
        ...     "user_id": "uuid-here",
        ...     "role": "admin"
        ... }
    """

    user_id: UUID = Field(
        ...,
        description="UUID пользователя",
    )
    role: str = Field(
        ...,
        description="Роль в workspace (owner/admin/member)",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """
        Валидация роли.

        Args:
            v: Значение роли

        Returns:
            str: Валидированная роль

        Raises:
            ValueError: Если роль невалидна
        """
        allowed_roles = {"owner", "admin", "member"}
        if v.lower() not in allowed_roles:
            raise ValueError(f"Роль должна быть одной из: {allowed_roles}")
        return v.lower()

    model_config = ConfigDict(
        from_attributes=True,
    )
