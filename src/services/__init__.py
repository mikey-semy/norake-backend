"""
Инициализация модуля сервисов v1.

Exports:
    - BaseService: Базовый класс для всех сервисов
    - SessionMixin: Миксин для работы с сессией БД
    - HealthService: Сервис проверки состояния приложения
    - AuthService: Сервис аутентификации пользователей
    - RegisterService: Сервис регистрации новых пользователей
"""

from .base import BaseService, SessionMixin
from .v1.health import HealthService
from .v1.auth import AuthService
from .v1.register import RegisterService

__all__ = [
    "BaseService",
    "SessionMixin",
    "HealthService",
    "AuthService",
    "RegisterService",

]
