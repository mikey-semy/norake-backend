"""
Защищенный роутер для тестирования аутентификации.

Этот роутер демонстрирует использование get_current_user
для защиты эндпоинтов, требующих аутентификации.
"""

from src.routers.base import BaseRouter
from src.core.security import CurrentUserDep
from src.schemas.base import BaseResponseSchema


class ProtectedRouter(BaseRouter):
    """
    Роутер для защищенных эндпоинтов.

    Все эндпоинты требуют валидный JWT токен.
    """

    def __init__(self):
        """Инициализирует ProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="protected", tags=["Protected"])

    def configure(self):
        """Настройка эндпоинтов защищенного роутера."""

        @self.router.get(
            path="/test",
            response_model=BaseResponseSchema,
            description="""
            ## 🔒 Тестовый защищенный эндпоинт

            Требует аутентификацию. Возвращает информацию о текущем пользователе.

            ### Требуется:
            * Валидный access токен в заголовке Authorization или в cookies

            ### Returns:
            * Информация о текущем пользователе
            """,
            responses={
                200: {"description": "Успешный доступ"},
                401: {"description": "Не авторизован"},
                403: {"description": "Доступ запрещен"},
            },
        )
        async def test_protected(
            current_user: CurrentUserDep,
        ) -> BaseResponseSchema:
            """
            Тестовый защищенный эндпоинт.

            Args:
                current_user: Текущий пользователь (внедряется автоматически)

            Returns:
                BaseResponseSchema: Информация о пользователе
            """
            return BaseResponseSchema(
                success=True,
                message=f"Привет, {current_user.username}! Ты аутентифицирован.",
                data={
                    "user_id": str(current_user.id),
                    "username": current_user.username,
                    "email": current_user.email,
                    "role": current_user.role,
                }
            )

        @self.router.get(
            path="/admin-only",
            response_model=BaseResponseSchema,
            description="""
            ## 🔒 Эндпоинт только для администраторов

            Требует аутентификацию с ролью admin.

            ### Требуется:
            * Валидный access токен
            * Роль: admin

            ### Returns:
            * Данные доступные только администраторам
            """,
            responses={
                200: {"description": "Успешный доступ"},
                401: {"description": "Не авторизован"},
                403: {"description": "Недостаточно прав"},
            },
        )
        async def admin_only(
            current_user: CurrentUserDep,
        ) -> BaseResponseSchema:
            """
            Эндпоинт только для администраторов.

            Args:
                current_user: Текущий пользователь (внедряется автоматически)

            Returns:
                BaseResponseSchema: Данные для администраторов

            Raises:
                HTTPException: Если пользователь не администратор
            """
            from fastapi import HTTPException, status

            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Доступ разрешен только администраторам"
                )

            return BaseResponseSchema(
                success=True,
                message="Добро пожаловать в админ-панель!",
                data={
                    "admin_data": "Секретная информация для администраторов",
                    "user": current_user.username
                }
            )
