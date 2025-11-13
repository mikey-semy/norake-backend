"""
Response-схемы для Workspace API.

Содержит схемы для исходящих ответов (detail, list, members).
"""

from typing import List, Optional
from uuid import UUID

from pydantic import Field

from src.models.v1.workspaces import WorkspaceVisibility
from src.schemas.base import BaseResponseSchema, BaseSchema, CommonBaseSchema


class UserBriefSchema(CommonBaseSchema):
    """
    Краткая информация о пользователе.

    Используется в составе других схем.
    Не содержит id, created_at, updated_at - только бизнес-данные.

    Attributes:
        username: Имя пользователя
        email: Email пользователя
    """

    username: str = Field(..., description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")


class WorkspaceMemberDetailSchema(BaseSchema):
    """
    Детальная информация об участнике Workspace.

    Включает информацию о пользователе.
    Наследует id, created_at, updated_at из BaseSchema.

    Attributes:
        workspace_id: UUID workspace
        user_id: UUID пользователя
        role: Роль в workspace
        user: Информация о пользователе

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

    workspace_id: UUID = Field(..., description="UUID workspace")
    user_id: UUID = Field(..., description="UUID пользователя")
    role: str = Field(..., description="Роль в workspace")
    user: UserBriefSchema = Field(..., description="Информация о пользователе")


class WorkspaceDetailSchema(BaseSchema):
    """
    Детальная информация о Workspace.

    Включает информацию о владельце и участниках.
    Наследует id, created_at, updated_at из BaseSchema.

    Attributes:
        name: Название workspace
        description: Описание workspace
        slug: URL-friendly идентификатор
        visibility: Видимость (PUBLIC/PRIVATE)
        owner_id: UUID владельца
        owner: Информация о владельце
        members: Список участников
        settings: Настройки workspace
        ai_modules_enabled: Включены ли AI-модули

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

    name: str = Field(..., description="Название workspace")
    description: Optional[str] = Field(None, description="Описание workspace")
    slug: str = Field(..., description="URL-friendly идентификатор")
    visibility: WorkspaceVisibility = Field(..., description="Видимость")
    owner_id: UUID = Field(..., description="UUID владельца")
    owner: UserBriefSchema = Field(..., description="Информация о владельце")
    members: List[WorkspaceMemberDetailSchema] = Field(
        default_factory=list,
        description="Список участников workspace",
    )
    settings: Optional[dict] = Field(None, description="Настройки workspace")
    ai_modules_enabled: bool = Field(
        default=True,
        description="Включены ли AI-модули",
    )


class WorkspaceListItemSchema(BaseSchema):
    """
    Упрощённая информация о Workspace для списков.

    Используется в /workspaces/me для списка workspace.
    Наследует id, created_at, updated_at из BaseSchema.

    Attributes:
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


class WorkspaceResponseSchema(BaseResponseSchema):
    """
    Стандартная обёртка для ответов API.

    Наследует success, message из BaseResponseSchema.

    Attributes:
        data: Данные workspace

    Example:
        >>> {
        ...     "success": True,
        ...     "data": {...},
        ...     "message": "Workspace создан успешно"
        ... }
    """

    data: WorkspaceDetailSchema = Field(..., description="Данные workspace")


class WorkspaceListResponseSchema(BaseResponseSchema):
    """
    Обёртка для списка workspace.

    Наследует success, message из BaseResponseSchema.

    Attributes:
        data: Список workspace
        total: Общее количество

    Example:
        >>> {
        ...     "success": True,
        ...     "data": [...],
        ...     "total": 10,
        ...     "message": null
        ... }
    """

    data: List[WorkspaceListItemSchema] = Field(
        ...,
        description="Список workspace",
    )
    total: int = Field(..., description="Общее количество workspace")


class MemberResponseSchema(BaseResponseSchema):
    """
    Обёртка для ответа при операциях с участниками.

    Наследует success, message из BaseResponseSchema.

    Attributes:
        data: Данные участника

    Example:
        >>> {
        ...     "success": True,
        ...     "data": {...},
        ...     "message": "Участник добавлен"
        ... }
    """

    data: WorkspaceMemberDetailSchema = Field(..., description="Данные участника")


class MemberListResponseSchema(BaseResponseSchema):
    """
    Обёртка для списка участников workspace.

    Наследует success, message из BaseResponseSchema.

    Attributes:
        data: Список участников
        total: Общее количество участников

    Example:
        >>> {
        ...     "success": True,
        ...     "data": [...],
        ...     "total": 5,
        ...     "message": null
        ... }
    """

    data: List[WorkspaceMemberDetailSchema] = Field(
        ...,
        description="Список участников workspace",
    )
    total: int = Field(..., description="Общее количество участников")
