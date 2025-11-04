"""
Роутер для аутентификации и авторизации пользователей.

Модуль предоставляет HTTP API для работы с аутентификацией:
- Вход в систему (login) для всех ролей (admin/user)
- Обновление токенов (refresh)
- Выход из системы (logout)
- Получение информации о текущем пользователе (me)

Обработка исключений: автоматическая обработка через глобальный exception handler.
Поддерживает как заголовки Authorization, так и cookies для токенов.
"""

from typing import Optional

from fastapi import Cookie, Depends, Header, Query, Response, status
from fastapi.security import OAuth2PasswordRequestForm

from src.routers.base import BaseRouter
from src.core.dependencies import AuthServiceDep
from src.schemas.v1.auth import (
    TokenResponseSchema,
    LogoutResponseSchema,
    CurrentUserResponseSchema,
)


class AuthRouter(BaseRouter):
    """
    Роутер для аутентификации пользователей.

    Предоставляет HTTP API для работы с аутентификацией:

    Public Endpoints:
        POST /auth/login - Вход в систему (admin/user)
        POST /auth/refresh - Обновление токенов
        POST /auth/logout - Выход из системы
        GET /auth/me - Получение текущего пользователя

    Архитектурные особенности:
        - Поддержка ролей: admin (полный доступ) и user (пользователь)
        - JWT токены с автоматической ротацией refresh токенов
        - Опциональное хранение токенов в cookies
        - Интеграция с Redis для blacklist токенов
    """

    def __init__(self):
        """Инициализирует AuthRouter с префиксом и тегами."""
        super().__init__(prefix="auth", tags=["Authentication"])

    def configure(self):
        """Настройка endpoint'ов роутера."""

        # ==================== АУТЕНТИФИКАЦИЯ ====================

        @self.router.post(
            path="/login",
            response_model=TokenResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔐 Вход в систему для всех пользователей

            Аутентифицирует пользователя (admin или user) по email и паролю,
            возвращает JWT токены для доступа к API.

            ### Поддерживаемые роли:
            * **admin** - Администратор системы (полный доступ)
            * **user** - Пользователь (Ограниченный доступ)

            ### Параметры:
            * **username**: Email адрес пользователя
            * **password**: Пароль пользователя
            * **use_cookies**: Сохранить токены в cookies (по умолчанию False)

            ### Returns:
            * **access_token**: JWT токен доступа (срок действия: 15 минут)
            * **refresh_token**: Refresh токен для обновления (срок действия: 7 дней)
            * **token_type**: Тип токена (Bearer)
            * **expires_in**: Время жизни access токена в секундах

            ### Безопасность:
            * Проверка активности аккаунта (is_active)
            * Хеширование паролей через bcrypt
            * Rate limiting для защиты от брутфорса
            * Логирование всех попыток входа
            """,
            responses={
                200: {"description": "Успешная аутентификация"},
                401: {"description": "Неверные учетные данные"},
                403: {"description": "Аккаунт деактивирован"},
                429: {"description": "Превышен лимит запросов"},
            },
        )
        async def login(
            response: Response,
            form_data: OAuth2PasswordRequestForm = Depends(),
            use_cookies: bool = Query(
                False,
                description="Использовать cookies для хранения токенов"
            ),
            auth_service: AuthServiceDep = None,
        ) -> TokenResponseSchema:
            """
            Аутентификация пользователя с получением JWT токенов.

            Args:
                response: Ответ FastAPI для установки cookies.
                form_data: Данные формы аутентификации (email, password).
                use_cookies: Использовать ли cookies для хранения токенов.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                TokenResponseSchema: Токены доступа и обновления.

            Raises:
                InvalidCredentialsError: Неверные учетные данные (обрабатывается глобально).
                UserInactiveError: Аккаунт деактивирован (обрабатывается глобально).
                RateLimitExceededError: Превышен лимит запросов (обрабатывается глобально).
            """
            return await auth_service.authenticate(
                form_data=form_data,
                response=response,
                use_cookies=use_cookies
            )

        # ==================== ОБНОВЛЕНИЕ ТОКЕНОВ ====================

        @self.router.post(
            path="/refresh",
            response_model=TokenResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔄 Обновление токена доступа

            Получение нового access токена с помощью refresh токена.
            Используется когда access токен истек, но refresh токен еще действителен.

            ### Источники refresh токена:
            * **refresh-token** (заголовок): Приоритетный источник
            * **refresh_token** (cookie): Используется если заголовок отсутствует

            ### Returns:
            * **access_token**: Новый JWT токен доступа
            * **refresh_token**: Новый refresh токен (ротация токенов)
            * **token_type**: Тип токена (Bearer)
            * **expires_in**: Время жизни нового access токена в секундах

            ### Безопасность:
            * Refresh токены имеют ограниченный срок действия (7 дней)
            * При каждом обновлении выдается новый refresh токен
            * Старый refresh токен становится недействительным (rotation)
            * Проверка принадлежности токена пользователю
            """,
            responses={
                200: {"description": "Токен успешно обновлен"},
                401: {"description": "Токен отсутствует"},
                419: {"description": "Токен просрочен"},
                422: {"description": "Невалидный токен"},
                429: {"description": "Превышен лимит запросов"},
            },
        )
        async def refresh_token(
            response: Response,
            use_cookies: bool = Query(
                False,
                description="Использовать cookies для токенов"
            ),
            refresh_token_header: Optional[str] = Header(
                None,
                alias="refresh-token",
                description="Refresh токен из заголовка"
            ),
            refresh_token_cookie: Optional[str] = Cookie(
                None,
                alias="refresh_token",
                description="Refresh токен из cookie"
            ),
            auth_service: AuthServiceDep = None,
        ) -> TokenResponseSchema:
            """
            Обновление токена доступа с использованием refresh токена.

            Args:
                response: Ответ FastAPI для установки cookies.
                use_cookies: Использовать ли cookies для хранения токенов.
                refresh_token_header: Refresh токен из заголовка запроса.
                refresh_token_cookie: Refresh токен из cookie.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                TokenResponseSchema: Обновленные токены.

            Raises:
                TokenMissingError: Если refresh токен отсутствует (обрабатывается глобально).
                TokenExpiredError: Токен истек (обрабатывается глобально).
                TokenInvalidError: Токен недействителен (обрабатывается глобально).
                RateLimitExceededError: Превышен лимит запросов (обрабатывается глобально).
            """
            # Приоритет: заголовок -> cookie
            refresh_token = refresh_token_header or refresh_token_cookie

            return await auth_service.refresh_token(
                refresh_token=refresh_token,
                response=response,
                use_cookies=use_cookies
            )

        # ==================== ВЫХОД ====================

        @self.router.post(
            path="/logout",
            response_model=LogoutResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🚪 Выход из системы

            Завершает сессию пользователя и добавляет токены в черный список.
            После выхода все токены пользователя становятся недействительными.

            ### Источники токена:
            * **Authorization** (заголовок): Bearer токен для идентификации сессии
            * **access_token** (cookie): Токен из cookie если заголовок отсутствует

            ### Query Parameters:
            * **clear_cookies**: Очистить ли cookies при выходе (по умолчанию False)

            ### Returns:
            * **success**: Булево значение успешности выхода
            * **message**: Сообщение о успешном выходе
            * **data**: Объект с полем logged_out_at (ISO 8601)

            ### Безопасность:
            * Токены добавляются в черный список (blacklist)
            * Все активные сессии пользователя завершаются
            * Требуется повторная аутентификация для доступа
            * Логирование операции выхода
            """,
            responses={
                200: {"description": "Успешный выход из системы"},
                401: {"description": "Токен отсутствует"},
                419: {"description": "Токен просрочен"},
                422: {"description": "Невалидный токен"},
                429: {"description": "Превышен лимит запросов"},
            },
        )
        async def logout(
            response: Response,
            clear_cookies: bool = Query(
                False,
                description="Очистить cookies при выходе"
            ),
            authorization: Optional[str] = Header(
                None,
                description="Bearer токен доступа"
            ),
            access_token_cookie: Optional[str] = Cookie(
                None,
                alias="access_token",
                description="Access токен из cookie"
            ),
            auth_service: AuthServiceDep = None,
        ) -> LogoutResponseSchema:
            """
            Выход из системы с удалением токенов и очисткой cookies.

            Args:
                response: Ответ FastAPI для очистки cookies.
                clear_cookies: Очистить ли cookies при выходе.
                authorization: Bearer токен из заголовка запроса.
                access_token_cookie: Access токен из cookie.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                LogoutResponseSchema: Результат выхода с временной меткой.

            Raises:
                TokenMissingError: Если токен доступа отсутствует (обрабатывается глобально).
                TokenExpiredError: Токен истек (обрабатывается глобально).
                TokenInvalidError: Токен недействителен (обрабатывается глобально).
                RateLimitExceededError: Превышен лимит запросов (обрабатывается глобально).
            """
            # Приоритет: заголовок -> cookie
            if not authorization and access_token_cookie:
                authorization = f"Bearer {access_token_cookie}"

            return await auth_service.logout(
                authorization=authorization,
                response=response,
                clear_cookies=clear_cookies
            )

        # ==================== ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ ====================

        @self.router.get(
            path="/me",
            response_model=CurrentUserResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 👤 Получение информации о текущем пользователе

            Возвращает информацию об аутентифицированном пользователе
            на основе токена доступа.

            ### Требуется:
            * Валидный access токен в заголовке Authorization или в cookies

            ### Returns:
            * **id**: UUID пользователя
            * **email**: Email адрес
            * **full_name**: ФИО пользователя
            * **role**: Роль пользователя (admin/user)
            * **company**: Данные компании (для user)
            * **is_active**: Статус активности аккаунта

            ### Использование:
            * Отображение профиля пользователя
            * Проверка прав доступа на клиенте
            * Валидация токена перед запросами
            """,
            responses={
                200: {"description": "Данные текущего пользователя"},
                401: {"description": "Токен отсутствует или недействителен"},
                419: {"description": "Токен просрочен"},
            },
        )
        async def get_current_user(
            authorization: Optional[str] = Header(
                None,
                description="Bearer токен доступа"
            ),
            access_token_cookie: Optional[str] = Cookie(
                None,
                alias="access_token",
                description="Access токен из cookie"
            ),
            auth_service: AuthServiceDep = None,
        ) -> CurrentUserResponseSchema:
            """
            Получает информацию о текущем аутентифицированном пользователе.

            Args:
                authorization: Bearer токен из заголовка запроса.
                access_token_cookie: Access токен из cookie.
                auth_service: Сервис аутентификации (dependency injection).

            Returns:
                CurrentUserResponseSchema: Данные текущего пользователя.

            Raises:
                TokenMissingError: Если токен доступа отсутствует (обрабатывается глобально).
                TokenExpiredError: Токен истек (обрабатывается глобально).
                TokenInvalidError: Токен недействителен (обрабатывается глобально).
            """
            # Приоритет: заголовок -> cookie
            if not authorization and access_token_cookie:
                authorization = f"Bearer {access_token_cookie}"

            return await auth_service.get_current_user(authorization=authorization)
