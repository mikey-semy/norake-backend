"""
Схемы для работы с Workspace API.

Экспорт всех схем для удобного импорта.
"""

from src.schemas.v1.workspaces.base import (
    WorkspaceBaseSchema,
    WorkspaceMemberBaseSchema,
)
from src.schemas.v1.workspaces.requests import (
    MemberAddSchema,
    MemberUpdateSchema,
    WorkspaceCreateSchema,
    WorkspaceUpdateSchema,
)
from src.schemas.v1.workspaces.responses import (
    MemberListResponseSchema,
    MemberResponseSchema,
    UserBriefSchema,
    WorkspaceDetailSchema,
    WorkspaceListItemSchema,
    WorkspaceListResponseSchema,
    WorkspaceMemberDetailSchema,
    WorkspaceResponseSchema,
)

__all__ = [
    # Base
    "WorkspaceBaseSchema",
    "WorkspaceMemberBaseSchema",
    # Requests
    "WorkspaceCreateSchema",
    "WorkspaceUpdateSchema",
    "MemberAddSchema",
    "MemberUpdateSchema",
    # Responses
    "UserBriefSchema",
    "WorkspaceMemberDetailSchema",
    "WorkspaceDetailSchema",
    "WorkspaceListItemSchema",
    "WorkspaceResponseSchema",
    "WorkspaceListResponseSchema",
    "MemberResponseSchema",
    "MemberListResponseSchema",
]
