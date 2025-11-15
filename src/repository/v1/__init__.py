"""
Модуль v1 репозиториев для работы с базой данных.

Экспортируемые репозитории:
    - IssueRepository: Работа с проблемами (Issues)
    - IssueCommentRepository: Работа с комментариями к проблемам
    - TemplateRepository: Работа с шаблонами (Templates)
    - WorkspaceRepository: Работа с workspace
    - WorkspaceMemberRepository: Работа с участниками workspace
    - DocumentServiceRepository: Работа с сервисами документов
    - DocumentRepository: Работа с документами Knowledge Base
    - DocumentChunkRepository: Работа с чанками документов (pgvector)
    - KnowledgeBaseRepository: Работа с Knowledge Base
    - AIChatRepository: Работа с AI чатами
"""

from .ai_chats import AIChatRepository
from .document_chunks import DocumentChunkRepository
from .document_processing import DocumentProcessingRepository
from .document_services import DocumentServiceRepository
from .documents import DocumentRepository
from .issue_comments import IssueCommentRepository
from .issues import IssueRepository
from .knowledge_bases import KnowledgeBaseRepository
from .templates import TemplateRepository
from .workspaces import WorkspaceMemberRepository, WorkspaceRepository

__all__ = [
    "IssueRepository",
    "IssueCommentRepository",
    "TemplateRepository",
    "WorkspaceRepository",
    "WorkspaceMemberRepository",
    "DocumentServiceRepository",
    "DocumentProcessingRepository",
    "DocumentRepository",
    "DocumentChunkRepository",
    "KnowledgeBaseRepository",
    "AIChatRepository",
]
