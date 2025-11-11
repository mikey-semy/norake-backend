"""
Модуль APIv1 - роутер версии 1 API.

Агрегирует все роутеры версии 1 и предоставляет единую точку входа.
"""

from src.routers.base import BaseRouter
from .health import HealthRouter
from .auth import AuthRouter
from .register import RegisterRouter
from .protected import ProtectedRouter as ProtectedDemoRouter
from .users import UsersRouter
from .issues import IssuePublicRouter, IssueProtectedRouter
from .templates import TemplateProtectedRouter
from .workspaces import WorkspaceProtectedRouter
from .n8n_workflows import N8nWorkflowProtectedRouter


class APIv1(BaseRouter):
    """
    Главный роутер для API версии 1.

    Агрегирует все роутеры v1 и предоставляет методы для их настройки.
    """

    def configure(self):
        """Настраивает все роутеры версии 1."""
        self.router.include_router(HealthRouter().get_router())
        self.router.include_router(AuthRouter().get_router())
        self.router.include_router(RegisterRouter().get_router())
        self.router.include_router(ProtectedDemoRouter().get_router())
        self.router.include_router(UsersRouter().get_router())
        self.router.include_router(IssuePublicRouter().get_router())
        self.router.include_router(IssueProtectedRouter().get_router())
        self.router.include_router(TemplateProtectedRouter().get_router())
        self.router.include_router(WorkspaceProtectedRouter().get_router())
        self.router.include_router(N8nWorkflowProtectedRouter().get_router())
