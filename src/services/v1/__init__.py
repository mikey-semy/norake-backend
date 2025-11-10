"""
Модуль с сервисами для API версии 1.

Exports:
    IssueService: Сервис для работы с проблемами.
"""

from .issues import IssueService

__all__ = [
    "IssueService",
]
