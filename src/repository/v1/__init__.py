"""
Модуль v1 репозиториев для работы с базой данных.

Экспортируемые репозитории:
    - IssueRepository: Работа с проблемами (Issues)
    - TemplateRepository: Работа с шаблонами (Templates)
"""

from .issues import IssueRepository
from .templates import TemplateRepository

__all__ = [
    "IssueRepository",
    "TemplateRepository",
]
