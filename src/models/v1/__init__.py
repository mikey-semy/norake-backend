"""
Модуль v1 содержит все модели данных версии 1 API.

Экспортируемые модели:
    - UserModel, UserRoleModel, RoleCode (пользователи и роли)
    - IssueModel, IssueStatus (проблемы)
    - IssueCommentModel (комментарии к проблемам)
    - TemplateModel, TemplateVisibility (шаблоны)
    - AIModuleModel, WorkspaceModuleModel, AIModuleType (AI модули)
    - WorkspaceModel, WorkspaceMemberModel, WorkspaceVisibility, WorkspaceMemberRole (workspace)
    - KnowledgeBaseModel, DocumentModel, DocumentChunkModel, KnowledgeBaseType, DocumentStatus (KB)
    - N8nWorkflowModel, N8nWorkflowType (n8n workflows)
    - DocumentServiceModel, ServiceFunctionType, DocumentFileType, CoverType (document services)
"""

from .ai_modules import AIModuleModel, AIModuleType, WorkspaceModuleModel
from .document_processing import (
    DocumentProcessingModel,
    ExtractionMethod,
    ProcessingStatus,
)
from .document_services import (
    CoverType,
    DocumentFileType,
    DocumentServiceModel,
    ServiceFunctionType,
)
from .issue_comments import IssueCommentModel
from .issues import IssueModel, IssueStatus
from .knowledge_bases import (
    DocumentChunkModel,
    DocumentModel,
    DocumentStatus,
    KnowledgeBaseModel,
    KnowledgeBaseType,
)
from .n8n_workflows import N8nWorkflowModel, N8nWorkflowType
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
    # Issue Comments
    "IssueCommentModel",
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
    # n8n Workflows
    "N8nWorkflowModel",
    "N8nWorkflowType",
    # Document Services
    "DocumentServiceModel",
    "ServiceFunctionType",
    "DocumentFileType",
    "CoverType",
    # Document Processing
    "DocumentProcessingModel",
    "ProcessingStatus",
    "ExtractionMethod",
]
