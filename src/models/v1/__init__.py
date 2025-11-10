"""
Модуль v1 содержит все модели данных версии 1 API.

Экспортируемые модели:
    - UserModel, UserRoleModel, RoleCode (пользователи и роли)
    - IssueModel, IssueStatus (проблемы)
    - TemplateModel, TemplateVisibility (шаблоны)
"""

from .issues import IssueModel, IssueStatus
from .roles import RoleCode, UserRoleModel
from .templates import TemplateModel, TemplateVisibility
from .users import UserModel

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
]
