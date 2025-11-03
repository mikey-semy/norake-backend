"""
Сервис для проверки состояния приложения и его зависимостей.
"""

from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.repository.v1.health import HealthRepository
from src.services.base import BaseService


class HealthService(BaseService):
    """
    Сервис для проверки состояния приложения и его зависимостей.

    Attributes:
        repository (HealthRepository): Репозиторий для проверки состояния БД

    Methods:
        check: Проверяет состояние приложения и его зависимостей (БД)
        check_liveness: Быстрая проверка жизнеспособности без зависимостей
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует сервис проверки состояния.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        super().__init__(session)
        self.repository = HealthRepository(session)

    async def check(self) -> Dict[str, str]:
        """
        Проверяет состояние приложения и его зависимостей.

        Returns:
            Dict[str, str]: Словарь со статусами сервисов (app, db)

        Raises:
            ValueError: Если критичные сервисы недоступны
        """
        self.logger.info("Checking application health")

        db_ok = await self.repository.check_database_connection()

        self._validate_critical_services(db_ok)

        status = {
            "app": "ok",
            "db": "ok" if db_ok else "fail",
        }

        self.logger.info("Health check completed: %s", status)

        return status

    async def check_liveness(self) -> Dict[str, str]:
        """
        Быстрая проверка жизнеспособности без проверки зависимостей.

        Используется для liveness probe в Kubernetes/Docker.

        Returns:
            Dict[str, str]: Минимальный словарь со статусом (app, остальные=unknown)
        """
        self.logger.debug("Liveness check")

        return {
            "app": "ok",
            "db": "unknown",
        }

    def _validate_critical_services(self, db_ok: bool) -> None:
        """
        Проверяет доступность критичных сервисов.

        Args:
            db_ok (bool): Статус базы данных

        Raises:
            ValueError: Если критичные сервисы недоступны
        """
        if not db_ok:
            self.logger.error(
                "Критичная проверка сервиса не пройдена: база данных недоступна"
            )
            raise ValueError("База данных недоступна")
