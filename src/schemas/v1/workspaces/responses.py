"""
Response-схемы для Workspace API.

Содержит схемы для исходящих ответов (detail, list, members).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.v1.workspaces import WorkspaceMemberRole, WorkspaceVisibility
from src.schemas.v1.workspaces.base import (
    WorkspaceBaseSchema,
    WorkspaceMemberBaseSchema,
)


class UserBriefSchema(BaseModel):
    """
    Краткая информация о пользователе.

    Используется в составе других схем.

    Attributes:
        id: UUID пользователя
        username: Имя пользователя
        email: Email пользователя
    """

    id: UUID = Field(..., description="UUID пользователя")
    username: str = Field(..., description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceMemberDetailSchema(WorkspaceMemberBaseSchema):
    """
    Детальная информация об участнике Workspace.

    Включает информацию о пользователе.

    Attributes:
        id: UUID записи участника
        workspace_id: UUID workspace
        user: Информация о пользователе
        created_at: Дата добавления в workspace

    Example:
        >>> {
        ...     "id": "uuid-here",
        ...     "workspace_id": "uuid-here",
        ...     "user_id": "uuid-here",
        ...     "role": "admin",
        ...     "user": {
        ...         "id": "uuid-here",
        ...         "username": "john",
        ...         "email": "john@example.com"
        ...     },
        ...     "created_at": "2024-11-10T12:00:00"
        ... }
    """

    id: UUID = Field(..., description="UUID записи участника")
    workspace_id: UUID = Field(..., description="UUID workspace")
    user: UserBriefSchema = Field(..., description="Информация о пользователе")
    created_at: datetime = Field(..., description="Дата добавления в workspace")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceDetailSchema(WorkspaceBaseSchema):
    """
    Детальная информация о Workspace.

    Включает информацию о владельце и участниках.

    Attributes:
        id: UUID workspace
        slug: URL-friendly идентификатор
        owner_id: UUID владельца
        owner: Информация о владельце
        members: Список участников
        ai_modules_enabled: Включены ли AI-модули
        created_at: Дата создания
        updated_at: Дата последнего обновления

    Example:
        >>> {
        ...     "id": "uuid-here",
        ...     "slug": "marketing-team",
        ...     "name": "Marketing Team",
        ...     "description": "Team workspace",
        ...     "visibility": "private",
        ...     "owner_id": "uuid-here",
        ...     "owner": {...},
        ...     "members": [...],
        ...     "settings": {},
        ...     "ai_modules_enabled": True,
        ...     "created_at": "2024-11-10T12:00:00",
        ...     "updated_at": "2024-11-10T12:00:00"
        ... }
    """

    id: UUID = Field(..., description="UUID workspace")
    slug: str = Field(..., description="URL-friendly идентификатор")
    owner_id: UUID = Field(..., description="UUID владельца")
    owner: UserBriefSchema = Field(..., description="Информация о владельце")
    members: List[WorkspaceMemberDetailSchema] = Field(
        default_factory=list,
        description="Список участников workspace",
    )
    ai_modules_enabled: bool = Field(
        default=True,
        description="Включены ли AI-модули",
    )
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата последнего обновления")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceListItemSchema(BaseModel):
    """
    Упрощённая информация о Workspace для списков.

    Используется в /workspaces/me для списка workspace.

    Attributes:
        id: UUID workspace
        slug: URL-friendly идентификатор
        name: Название workspace
        description: Описание workspace
        visibility: Видимость
        owner_id: UUID владельца
        member_count: Количество участников
        ai_modules_enabled: Включены ли AI-модули

    Example:
        >>> {
        ...     "id": "uuid-here",
        ...     "slug": "marketing-team",
        ...     "name": "Marketing Team",
        ...     "description": "Team workspace",
        ...     "visibility": "private",
        ...     "owner_id": "uuid-here",
        ...     "member_count": 5,
        ...     "ai_modules_enabled": True
        ... }
    """

    id: UUID = Field(..., description="UUID workspace")
    slug: str = Field(..., description="URL-friendly идентификатор")
    name: str = Field(..., description="Название workspace")
    description: Optional[str] = Field(None, description="Описание workspace")
    visibility: WorkspaceVisibility = Field(..., description="Видимость")
    owner_id: UUID = Field(..., description="UUID владельца")
    member_count: int = Field(default=0, description="Количество участников")
    ai_modules_enabled: bool = Field(
        default=True,
        description="Включены ли AI-модули",
    )

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResponseSchema(BaseModel):
    """
    Стандартная обёртка для ответов API.

    Attributes:
        success: Успешность операции
        data: Данные workspace
        message: Дополнительное сообщение

    Example:
        >>> {
        ...     "success": True,
        ...     "data": {...},
        ...     "message": "Workspace создан успешно"
        ... }
    """

    success: bool = Field(default=True, description="Успешность операции")
    data: WorkspaceDetailSchema = Field(..., description="Данные workspace")
    message: Optional[str] = Field(None, description="Дополнительное сообщение")

    model_config = ConfigDict(from_attributes=True)


class WorkspaceListResponseSchema(BaseModel):
    """
    Обёртка для списка workspace.

    Attributes:
        success: Успешность операции
        data: Список workspace
        total: Общее количество
        message: Дополнительное сообщение

    Example:
        >>> {
        ...     "success": True,
        ...     "data": [...],
        ...     "total": 10,
        ...     "message": null
        ... }
    """

    success: bool = Field(default=True, description="Успешность операции")
    data: List[WorkspaceListItemSchema] = Field(
        ...,
        description="Список workspace",
    )
    total: int = Field(..., description="Общее количество workspace")
    message: Optional[str] = Field(None, description="Дополнительное сообщение")

    model_config = ConfigDict(from_attributes=True)


class MemberResponseSchema(BaseModel):
    """
    Обёртка для ответа при операциях с участниками.

    Attributes:
        success: Успешность операции
        data: Данные участника
        message: Дополнительное сообщение

    Example:
        >>> {
        ...     "success": True,
        ...     "data": {...},
        ...     "message": "Участник добавлен"
        ... }
    """

    success: bool = Field(default=True, description="Успешность операции")
    data: WorkspaceMemberDetailSchema = Field(..., description="Данные участника")
    message: Optional[str] = Field(None, description="Дополнительное сообщение")

    model_config = ConfigDict(from_attributes=True)
