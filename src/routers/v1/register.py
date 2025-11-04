"""
Роутер для регистрации новых пользователей.

Модуль предоставляет HTTP API для работы с регистрацией:
- Регистрация нового пользователя (register)
- Подтверждение email адреса (verify-email)

Обработка исключений: автоматическая обработка через глобальный exception handler.
Поддерживает опциональное хранение токенов в cookies.
"""

from fastapi import Query, Response

from src.routers.base import BaseRouter
from src.core.dependencies import RegisterServiceDep
from src.schemas.v1.register import (
    RegistrationRequestSchema,
    RegistrationResponseSchema,
)


class RegisterRouter(BaseRouter):
    """
    Роутер для регистрации пользователей.

    Предоставляет HTTP API для работы с регистрацией:

    Public Endpoints:
        POST /register - Регистрация нового пользователя

    Архитектурные особенности:
        - Отправка email для подтверждения регистрации
        - JWT токены с автоматической ротацией
        - Опциональное хранение токенов в cookies
        - Валидация email и других полей через Pydantic
    """

    def __init__(self):
        """Инициализирует RegisterRouter с префиксом и тегами."""
        super().__init__(prefix="register", tags=["Registration"])

    def configure(self):
        """Настройка эндпоинтов регистрации."""

        @self.router.post(
            path="",
            response_model=RegistrationResponseSchema,
            status_code=201,
        )
        async def register_user(
            response: Response,
            new_user: RegistrationRequestSchema,
            register_service: RegisterServiceDep = None,
            use_cookies: bool = Query(
                False, description="Использовать куки для хранения токенов"
            ),
        ) -> RegistrationResponseSchema:
            """
            Регистрация нового пользователя.

            Создает нового пользователя в системе с ролью user.
            Возвращает JWT токены (в теле или cookies).

            Args:
                response: HTTP response объект для установки cookies
                new_user: Данные нового пользователя
                register_service: Сервис регистрации (внедрение зависимости)
                use_cookies: Использовать cookies для хранения токенов

            Returns:
                RegistrationResponseSchema: Информация о созданном пользователе + токены

            Raises:
                UserAlreadyExistsError: Пользователь с таким email/username уже существует
                UserCreationError: Ошибка при создании пользователя
                RoleAssignmentError: Ошибка при присвоении роли user
            """
            from src.schemas.v1.register import RegistrationDataSchema

            # Вызываем service.register_user (возвращает user + tokens)
            user, tokens = await register_service.register_user(
                user_data={
                    "email": new_user.email,
                    "password": new_user.password,
                }
            )

            # Если use_cookies=True, сохраняем токены в cookies
            if use_cookies:
                response.set_cookie(
                    key="access_token",
                    value=tokens["access_token"],
                    httponly=True,
                    secure=True,
                    samesite="lax",
                )
                response.set_cookie(
                    key="refresh_token",
                    value=tokens["refresh_token"],
                    httponly=True,
                    secure=True,
                    samesite="lax",
                )

            # Конвертируем UserModel → RegistrationDataSchema
            user_data = RegistrationDataSchema(
                id=user.id,
                username=user.username,
                email=user.email,
                phone=user.phone,
                role="user",  # Всегда user при регистрации
                is_active=user.is_active,
                created_at=user.created_at,
                access_token=None if use_cookies else tokens["access_token"],
                refresh_token=None if use_cookies else tokens["refresh_token"],
                token_type="Bearer",
            )

            return RegistrationResponseSchema(
                success=True,
                message="Пользователь успешно зарегистрирован",
                data=user_data,
            )
