"""
Модуль аутентификации и авторизации пользователей.

Этот модуль предоставляет компоненты для проверки подлинности
и авторизации пользователей в приложении FastAPI с использованием
JWT токенов.

Основные компоненты:
- OAuth2PasswordBearer: схема безопасности для документации OpenAPI
- get_current_user: функция-зависимость для получения текущего пользователя

Примеры использования:

1. В маршрутах FastAPI с использованием стандартных зависимостей:
    ```
    @router.get("/protected")
    async def protected_route(user: CurrentUserSchema = Depends(get_current_user)):
        return {"message": f"Hello, {user.username}!"}
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from src.core.exceptions import (
    InvalidCredentialsError,
    TokenError,
    TokenInvalidError,
    TokenMissingError,
)
from src.core.security.token_manager import TokenManager
from src.schemas.v1.auth.base import UserCurrentSchema

logger = logging.getLogger(__name__)

# Создаем экземпляр OAuth2PasswordBearer для использования с Depends
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    scheme_name="OAuth2PasswordBearer",
    description="Bearer token",
    auto_error=False,
)


class AuthenticationManager:
    """
    Менеджер аутентификации пользователей.

    Этот класс предоставляет методы для работы с аутентификацией,
    включая проверку токенов и получение данных текущего пользователя.

    Методы:
        get_current_user: Получает данные текущего пользователя по токену
        extract_token_from_request: Извлекает токен из запроса (заголовок или cookies)
    """

    @staticmethod
    def extract_token_from_request(request: Request, header_token: str = None) -> str:
        """
        Извлекает токен из запроса - сначала из заголовка Authorization, затем из cookies.

        Args:
            request: Запрос FastAPI, содержащий заголовки HTTP и cookies
            header_token: Токен из заголовка Authorization (если есть)

        Returns:
            str: Найденный токен

        Raises:
            TokenMissingError: Если токен не найден ни в заголовке, ни в cookies
        """
        # Сначала пробуем получить токен из заголовка Authorization
        if header_token:
            logger.debug("Токен найден в заголовке Authorization")
            return header_token

        # Если токена нет в заголовке, проверяем cookies
        access_token_cookie = request.cookies.get("access_token")

        if access_token_cookie:
            logger.debug("Токен найден в cookies")
            return access_token_cookie

        # Если токен не найден ни в заголовке, ни в cookies
        logger.debug("Токен не найден ни в заголовке Authorization, ни в cookies")
        raise TokenMissingError()

    @staticmethod
    async def get_current_user(
        request: Request,
        token: str = Depends(oauth2_scheme),
    ) -> UserCurrentSchema:
        """
        Получает данные текущего аутентифицированного пользователя.

        Эта функция проверяет JWT токен, переданный в заголовке Authorization или cookies,
        декодирует его, и получает пользователя из системы по идентификатору
        в токене (sub).

        Args:
            request: Запрос FastAPI, содержащий заголовки HTTP и cookies
            token: Токен доступа, извлекаемый из заголовка Authorization (может быть None)

        Returns:
            UserCurrentSchema: Схема данных текущего пользователя

        Raises:
            TokenInvalidError: Если токен отсутствует, недействителен или истек
        """
        # Импортируем внутри функции чтобы избежать циклического импорта
        from src.repository.v1.users import UserRepository
        from src.core.integrations.cache.authenticate import AuthRedisManager

        logger.debug(
            "Обработка запроса аутентификации с заголовками: %s", request.headers
        )
        logger.debug("Начало получения данных пользователя")
        logger.debug("Получен токен из заголовка: %s", token[:50] + "..." if token else "None")

        try:
            # Извлекаем токен из запроса (заголовок или cookies)
            actual_token = AuthenticationManager.extract_token_from_request(request, token)
            logger.debug("Используемый токен: %s", actual_token[:50] + "..." if actual_token else "None")

            # Проверяем и декодируем токен
            payload = TokenManager.decode_token(actual_token)

            # Валидируем payload и получаем email
            user_email = payload.get("email")
            if not user_email:
                logger.warning("Email не найден в payload токена")
                raise TokenInvalidError()

            # Получаем подключения через utility functions
            from src.core.connections.database import get_db_session
            from src.core.connections.cache import get_redis_client

            # Используем async generator для получения сессии БД
            async for session in get_db_session():
                redis = await get_redis_client()
                redis_manager = AuthRedisManager(redis)

                # Проверяем, что токен существует в Redis (не в blacklist)
                cached_user = await redis_manager.get_user_by_token(actual_token)
                if not cached_user:
                    logger.warning("Токен не найден в Redis (blacklist или истек)")
                    raise TokenInvalidError()

                # Получаем пользователя из БД с eager loading ролей
                repository = UserRepository(session)
                user_model = await repository.get_user_by_identifier(user_email)

                if not user_model:
                    logger.warning("Пользователь с email %s не найден", user_email)
                    raise InvalidCredentialsError()

                # Проверяем активность пользователя
                if not user_model.is_active:
                    logger.warning("Попытка доступа с неактивным аккаунтом: %s", user_email)
                    raise InvalidCredentialsError()

                # Создаем схему текущего пользователя
                current_user = UserCurrentSchema(
                    id=user_model.id,
                    username=user_model.username,
                    email=user_model.email,
                    role=user_model.role,
                )

                logger.debug("Пользователь успешно аутентифицирован: %s", current_user.username)
                return current_user

        except TokenError:
            # Перехватываем все ошибки токенов и пробрасываем дальше
            raise
        except Exception as e:
            logger.error("Ошибка при аутентификации: %s", str(e), exc_info=True)
            raise TokenInvalidError() from e


# Для удобства использования создаем алиас функции
get_current_user = AuthenticationManager.get_current_user


async def get_current_user_optional(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> UserCurrentSchema | None:
    """
    Получает данные текущего пользователя БЕЗ обязательной аутентификации.

    Используется для публичных endpoints с опциональной авторизацией:
    - Если токен валиден → возвращает UserCurrentSchema
    - Если токена нет или невалиден → возвращает None (НЕ выбрасывает исключение)

    Args:
        request: Запрос FastAPI
        token: Токен доступа из заголовка Authorization или cookies (опционально)

    Returns:
        UserCurrentSchema | None: Данные пользователя или None

    Example:
        >>> @router.get("/documents")
        >>> async def list_documents(current_user: OptionalUserDep = None):
        >>>     # Публичные документы доступны всем
        >>>     # Приватные - только авторизованным
        >>>     user_id = current_user.id if current_user else None
        >>>     return await service.list_documents(user_id)
    """
    try:
        # Пробуем получить пользователя обычным способом
        return await AuthenticationManager.get_current_user(request, token)
    except (TokenMissingError, TokenInvalidError):
        # Если токена нет или он невалиден - возвращаем None
        logger.debug("Опциональная аутентификация: токен отсутствует или невалиден")
        return None
    except Exception as e:
        # Любые другие ошибки (например, пользователь не найден) - тоже None
        logger.debug("Опциональная аутентификация: ошибка %s", str(e))
        return None


# Type annotation для dependency injection
CurrentUserDep = Annotated[UserCurrentSchema, Depends(get_current_user)]
OptionalUserDep = Annotated[UserCurrentSchema | None, Depends(get_current_user_optional)]
