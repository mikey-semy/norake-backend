"""
Модуль v1 репозиториев для работы с базой данных.

Экспортируемые репозитории:
    - IssueRepository: Работа с проблемами (Issues)
"""

from .issues import IssueRepository

__all__ = [
    "IssueRepository",
]
