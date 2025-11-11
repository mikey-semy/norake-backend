"""
Модуль v1 содержит все модели данных версии 1 API.

Экспортируемые модели:
    - UserModel, UserRoleModel, RoleCode (пользователи и роли)
    - IssueModel, IssueStatus (проблемы)
    - TemplateModel, TemplateVisibility (шаблоны)
    - AIModuleModel, WorkspaceModuleModel, AIModuleType (AI модули)
    - WorkspaceModel, WorkspaceMemberModel, WorkspaceVisibility, WorkspaceMemberRole (workspace)
    - KnowledgeBaseModel, DocumentModel, DocumentChunkModel, KnowledgeBaseType, DocumentStatus (KB)
"""

from .ai_modules import AIModuleModel, AIModuleType, WorkspaceModuleModel
from .issues import IssueModel, IssueStatus
from .knowledge_bases import (
    DocumentChunkModel,
    DocumentModel,
    DocumentStatus,
    KnowledgeBaseModel,
    KnowledgeBaseType,
)
from .roles import RoleCode, UserRoleModel
from .templates import TemplateModel, TemplateVisibility
from .users import UserModel
from .workspaces import (
    WorkspaceMemberModel,
    WorkspaceMemberRole,
    WorkspaceModel,
    WorkspaceVisibility,
)

__all__ = [
    # Users & Roles
    "UserModel",
    "UserRoleModel",
    "RoleCode",
    # Issues
    "IssueModel",
    "IssueStatus",
    # Templates
    "TemplateModel",
    "TemplateVisibility",
    # AI Modules
    "AIModuleModel",
    "WorkspaceModuleModel",
    "AIModuleType",
    # Workspaces
    "WorkspaceModel",
    "WorkspaceMemberModel",
    "WorkspaceVisibility",
    "WorkspaceMemberRole",
    # Knowledge Base
    "KnowledgeBaseModel",
    "DocumentModel",
    "DocumentChunkModel",
    "KnowledgeBaseType",
    "DocumentStatus",
]
