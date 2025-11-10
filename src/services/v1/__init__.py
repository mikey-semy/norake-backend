"""
Модуль с сервисами для API версии 1.

Exports:
    IssueService: Сервис для работы с проблемами.
    TemplateService: Сервис для работы с шаблонами.
"""

from .issues import IssueService
from .templates import TemplateService

__all__ = [
    "IssueService",
    "TemplateService",
]
