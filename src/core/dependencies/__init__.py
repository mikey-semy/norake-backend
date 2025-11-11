"""
Модуль зависимостей FastAPI.

Содержит все зависимости для внедрения в роуты и сервисы приложения.
Организован по категориям соответствующим src.core.connections.
"""

# Database dependencies
from .database import AsyncSessionDep
# Cache dependencies
from .cache import RedisDep
# Health Service dependency
from .health import HealthServiceDep
# Token Service dependency
from .token import TokenServiceDep
# Auth Service dependency
from .auth import AuthServiceDep
# Register Service dependency
from .register import RegisterServiceDep
# Issue Service dependency
from .issues import IssueServiceDep
# Template Service dependency
from .templates import TemplateServiceDep
# Workspace Service dependency
from .workspaces import WorkspaceServiceDep
# Search Service dependencies
from .search import RAGSearchServiceDep, SearchServiceDep

__all__ = [
    # Database dependencies
    "AsyncSessionDep",
    # Cache dependencies
    "RedisDep",
    # Health Service dependency
    "HealthServiceDep",
    # Token Service dependency
    "TokenServiceDep",
    # Auth Service dependency
    "AuthServiceDep",
    # Register Service dependency
    "RegisterServiceDep",
    # Issue Service dependency
    "IssueServiceDep",
    # Template Service dependency
    "TemplateServiceDep",
    # Workspace Service dependency
    "WorkspaceServiceDep",
    # Search Service dependencies
    "RAGSearchServiceDep",
    "SearchServiceDep",
]
