"""
Модуль APIv1 - роутер версии 1 API.

Агрегирует все роутеры версии 1 и предоставляет единую точку входа.
"""

from fastapi import APIRouter

from .health import HealthRouter
from .auth import AuthRouter
from .register import RegisterRouter


class APIv1:
    """
    Главный роутер для API версии 1.
    
    Агрегирует все роутеры v1 и предоставляет методы для их настройки.
    """

    def __init__(self):
        self.router = APIRouter()
        self._routers = [
            HealthRouter(),
            AuthRouter(),
            RegisterRouter(),
        ]

    def configure_routes(self):
        """Настраивает все роутеры версии 1."""
        for router in self._routers:
            router.configure()
            self.router.include_router(router.get_router())

    def get_router(self) -> APIRouter:
        """Возвращает настроенный роутер."""
        return self.router
