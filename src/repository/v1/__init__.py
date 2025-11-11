"""
Модуль v1 репозиториев для работы с базой данных.

Экспортируемые репозитории:
    - IssueRepository: Работа с проблемами (Issues)
    - TemplateRepository: Работа с шаблонами (Templates)
    - WorkspaceRepository: Работа с workspace
    - WorkspaceMemberRepository: Работа с участниками workspace
"""

from .issues import IssueRepository
from .templates import TemplateRepository
from .workspaces import WorkspaceMemberRepository, WorkspaceRepository

__all__ = [
    "IssueRepository",
    "TemplateRepository",
    "WorkspaceRepository",
    "WorkspaceMemberRepository",
]
