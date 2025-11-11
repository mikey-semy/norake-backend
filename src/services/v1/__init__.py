"""
Модуль с сервисами для API версии 1.

Exports:
    IssueService: Сервис для работы с проблемами.
    TemplateService: Сервис для работы с шаблонами.
    WorkspaceService: Сервис для работы с workspace.
"""

from .issues import IssueService
from .templates import TemplateService
from .workspaces import WorkspaceService

__all__ = [
    "IssueService",
    "TemplateService",
    "WorkspaceService",
]
