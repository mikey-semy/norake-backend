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
# Auth Service dependency
from .auth import AuthServiceDep
# Register Service dependency
from .register import RegisterServiceDep
__all__ = [
    # Database dependencies
    "AsyncSessionDep",
    # Cache dependencies
    "RedisDep",
    # Health Service dependency
    "HealthServiceDep",
    # Auth Service dependency
    "AuthServiceDep",
    # Register Service dependency
    "RegisterServiceDep",
]
