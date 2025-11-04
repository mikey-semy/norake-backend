from typing import Optional, Sequence, List

from fastapi import APIRouter, Depends


class BaseRouter:
    """
    Базовый класс для всех роутеров.

    Предоставляет общий функционал для создания обычных и защищенных маршрутов.

    Attributes:
        router (APIRouter): Базовый FastAPI роутер
        _dependencies (List[Depends]): Список глобальных зависимостей для роутера
    """

    def __init__(
        self,
        prefix: str = "",
        tags: Optional[Sequence[str]] = None,
        dependencies: Optional[List[Depends]] = None,
    ):
        """
        Инициализирует базовый роутер.

        Args:
            prefix: Префикс URL для всех маршрутов
            tags: Список тегов для документации Swagger
            dependencies: Список глобальных зависимостей (например, для защиты всех эндпоинтов)
        """
        self._dependencies = dependencies or []
        self.router = APIRouter(
            prefix=f"/{prefix}" if prefix else "",
            tags=tags or [],
            dependencies=self._dependencies,
        )
        self.configure()

    def configure(self):
        """Переопределяется в дочерних классах для настройки роутов"""

    def get_router(self) -> APIRouter:
        """
        Возвращает настроенный FastAPI роутер.

        Returns:
            APIRouter: Настроенный FastAPI роутер
        """
        return self.router


class ProtectedRouter(BaseRouter):
    """
    Защищенный роутер с автоматической аутентификацией.

    Все эндпоинты в этом роутере автоматически защищены через CurrentUserDep.
    Пользователь доступен в каждом эндпоинте через параметр `current_user`.

    Пример использования:
        ```python
        class UsersRouter(ProtectedRouter):
            def __init__(self):
                super().__init__(prefix="users", tags=["Users"])

            def configure(self):
                @self.router.get("/profile")
                async def get_profile(current_user: CurrentUserDep = None):
                    # current_user уже валидирован!
                    return {"user_id": current_user.id}
        ```

    Attributes:
        router (APIRouter): FastAPI роутер с глобальной защитой через CurrentUserDep
    """

    def __init__(
        self,
        prefix: str = "",
        tags: Optional[Sequence[str]] = None,
        additional_dependencies: Optional[List[Depends]] = None,
    ):
        """
        Инициализирует защищенный роутер.

        Args:
            prefix: Префикс URL для всех маршрутов
            tags: Список тегов для документации Swagger
            additional_dependencies: Дополнительные зависимости (кроме аутентификации)
        """
        # Импортируем внутри метода чтобы избежать циклических импортов
        from src.core.security import get_current_user

        # Создаем список зависимостей: аутентификация + дополнительные
        dependencies = [Depends(get_current_user)]
        if additional_dependencies:
            dependencies.extend(additional_dependencies)

        # Инициализируем базовый роутер с зависимостями
        super().__init__(prefix=prefix, tags=tags, dependencies=dependencies)
