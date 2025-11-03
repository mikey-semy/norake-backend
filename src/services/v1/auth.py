"""
Сервис для аутентификации пользователей.

Предоставляет методы для:
- Аутентификации пользователей (admin/user)
- Обновления токенов (refresh)
- Выхода из системы (logout)
- Получения текущего пользователя (me)
- Работы с токенами через Redis
"""

from datetime import datetime, timezone
from typing import Optional, Tuple
from uuid import UUID

from fastapi import Response
from fastapi.security import OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.base import BaseService
from src.repository.v1.users import UserRepository
from src.models.v1.users import UserModel
from src.schemas.v1.auth.base import UserCredentialsSchema, UserCurrentSchema
from src.schemas.v1.auth.requests import AuthSchema
from src.schemas.v1.auth.responses import (
    TokenResponseSchema,
    LogoutResponseSchema,
    CurrentUserResponseSchema,
)
from src.schemas.v1.auth.base import LogoutDataSchema
from src.core.integrations.cache.authenticate import AuthRedisManager
from src.core.exceptions import (
    InvalidCredentialsError,
    UserNotFoundError,
    UserInactiveError,
    TokenExpiredError,
    TokenInvalidError,
    TokenMissingError,
)

from src.core.security import PasswordManager, TokenManager, CookieManager


class AuthService(BaseService):
    """
    Сервис для аутентификации пользователей.

    Обрабатывает аутентификацию для всех ролей (admin/user) через JWT токены.
    Поддерживает хранение токенов в заголовках и cookies.

    Attributes:
        repository: Репозиторий для работы с UserModel.
        redis_manager: Менеджер для работы с токенами в Redis.
    """

    def __init__(self, session: AsyncSession, redis: Redis):
        """
        Инициализация сервиса аутентификации.

        Args:
            session: Асинхронная сессия базы данных.
            redis: Клиент Redis для работы с токенами.
        """
        super().__init__(session)
        self.redis = redis
        self.repository = UserRepository(session=session, model=UserModel)
        self.redis_manager = AuthRedisManager(redis)

    # ==================== АУТЕНТИФИКАЦИЯ ====================

    async def authenticate(
        self,
        form_data: OAuth2PasswordRequestForm,
        response: Optional[Response] = None,
        use_cookies: bool = False,
    ) -> TokenResponseSchema:
        """
        Аутентифицирует пользователя по email и паролю.

        Поддерживает все роли (admin/user). Проверяет активность аккаунта,
        генерирует JWT токены, устанавливает online статус в Redis.

        Args:
            form_data: Данные для аутентификации (email, password).
            response: HTTP ответ для установки куков (опционально).
            use_cookies: Использовать ли куки для хранения токенов.

        Returns:
            TokenResponseSchema: Токены доступа и обновления.

        Raises:
            InvalidCredentialsError: Если email или пароль неверные.
            UserInactiveError: Если аккаунт деактивирован.
        """
        self.logger.info(
            "Попытка аутентификации пользователя: %s", form_data.username
        )

        # 1. Валидация и получение пользователя
        user_model, credentials = await self._validate_and_get_user(form_data)

        # 2. Проверка пароля
        await self._check_user_password(user_model, credentials)

        # 3. Проверка активности аккаунта
        if not user_model.is_active:
            self.logger.warning(
                "Попытка входа с деактивированным аккаунтом",
                extra={"user_id": user_model.id, "email": user_model.email}
            )
            raise UserInactiveError()

        # 4. Преобразование модели в схему с хешированным паролем
        user_schema = UserCredentialsSchema(
            id=user_model.id,
            username=user_model.username,
            email=user_model.email,
            password_hash=user_model.password_hash,
            is_active=user_model.is_active,
            role=user_model.role  # @property вызывается явно
        )

        # 5. Обработка успешной аутентификации
        return await self._handle_successful_auth(user_schema, response, use_cookies)

    async def _validate_and_get_user(
        self, form_data: OAuth2PasswordRequestForm
    ) -> Tuple[UserModel, AuthSchema]:
        """
        Валидирует входные данные и ищет пользователя по email.

        Args:
            form_data: Данные формы аутентификации.

        Returns:
            Tuple[UserModel, AuthSchema]: Модель пользователя и credentials.

        Raises:
            InvalidCredentialsError: Если пользователь не найден.
        """
        credentials = AuthSchema(
            username=form_data.username,
            password=form_data.password
        )

        identifier = credentials.username  # email, phone, or username

        self.logger.info(
            "Поиск пользователя по идентификатору: %s", identifier
        )

        # Поиск по email/phone/username через get_user_by_identifier()
        user_model = await self.repository.get_user_by_identifier(identifier)

        if not user_model:
            self.logger.warning(
                "Пользователь не найден", extra={"identifier": identifier}
            )
            raise InvalidCredentialsError()

        return user_model, credentials

    async def _check_user_password(
        self, user_model: UserModel, credentials: AuthSchema
    ) -> None:
        """
        Проверяет корректность пароля пользователя.

        Args:
            user_model: Модель пользователя.
            credentials: Учетные данные пользователя.

        Raises:
            InvalidCredentialsError: Если пароль неверный.
        """
        if not PasswordManager.verify(user_model.password_hash, credentials.password):
            self.logger.warning(
                "Неверный пароль пользователя",
                extra={"identifier": credentials.username, "user_id": user_model.id}
            )
            raise InvalidCredentialsError()

    async def _handle_successful_auth(
        self,
        user_schema: UserCredentialsSchema,
        response: Optional[Response],
        use_cookies: bool,
    ) -> TokenResponseSchema:
        """
        Обрабатывает успешную аутентификацию пользователя.

        Args:
            user_schema: Схема пользователя.
            response: HTTP-ответ FastAPI.
            use_cookies: Использовать ли куки для токенов.

        Returns:
            TokenResponseSchema: Схема ответа с токенами.
        """
        # 1. Логируем успешную аутентификацию
        self.logger.info(
            "Аутентификация успешна",
            extra={
                "user_id": user_schema.id,
                "email": user_schema.email,
            }
        )

        # 2. Устанавливаем статус "онлайн"
        await self.redis_manager.set_online_status(user_schema.id, True)

        # 3. Генерируем токены
        access_token, refresh_token = await self._generate_tokens(user_schema)

        # 4. Обновляем последнюю активность
        await self.redis_manager.update_last_activity(access_token)

        # 5. Устанавливаем куки, если требуется
        if response and use_cookies:
            CookieManager.set_auth_cookies(response, access_token, refresh_token)

            return TokenResponseSchema(
                message="Аутентификация успешна",
                access_token=None,  # Токены в cookies
                refresh_token=None,
                expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
            )

        # Возвращаем токены в схеме ответа
        return TokenResponseSchema(
            message="Аутентификация успешна",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
        )

    async def _generate_tokens(
        self, user_schema: UserCredentialsSchema
    ) -> Tuple[str, str]:
        """
        Генерирует access и refresh токены.

        Args:
            user_schema: Схема пользователя.

        Returns:
            Tuple[str, str]: Access токен, refresh токен.
        """
        access_token = await self.create_token(user_schema)
        refresh_token = await self.create_refresh_token(user_schema.id)
        return access_token, refresh_token

    async def create_token(self, user_schema: UserCredentialsSchema) -> str:
        """
        Создание JWT access токена.

        Args:
            user_schema: Схема пользователя.

        Returns:
            str: Access токен.
        """
        payload = TokenManager.create_payload(user_schema)
        access_token = TokenManager.generate_token(payload)

        await self.redis_manager.save_token(user_schema, access_token)

        self.logger.info(
            "Access токен создан",
            extra={"user_id": user_schema.id}
        )

        return access_token

    async def create_refresh_token(self, user_id: UUID) -> str:
        """
        Создание JWT refresh токена.

        Args:
            user_id: ID пользователя.

        Returns:
            str: Refresh токен.
        """
        payload = TokenManager.create_refresh_payload(user_id)
        refresh_token = TokenManager.generate_token(payload)

        await self.redis_manager.save_refresh_token(user_id, refresh_token)

        self.logger.info(
            "Refresh токен создан",
            extra={"user_id": user_id}
        )

        return refresh_token

    # ==================== ОБНОВЛЕНИЕ ТОКЕНОВ ====================

    async def refresh_token(
        self,
        refresh_token: str,
        response: Optional[Response] = None,
        use_cookies: bool = False,
    ) -> TokenResponseSchema:
        """
        Обновляет access токен с помощью refresh токена.

        Args:
            refresh_token: Refresh токен.
            response: HTTP ответ для установки куков.
            use_cookies: Использовать ли куки для токенов.

        Returns:
            TokenResponseSchema: Новые токены доступа.

        Raises:
            TokenMissingError: Если refresh токен отсутствует.
            TokenInvalidError: Если refresh токен недействителен.
            TokenExpiredError: Если refresh токен истек.
        """
        if not refresh_token:
            self.logger.warning("Попытка обновления токена без refresh token")
            raise TokenMissingError()

        try:
            # 1. Валидация refresh токена и получение пользователя
            user_model, user_id = await self._validate_and_get_user_by_refresh_token(
                refresh_token
            )

            # 2. Преобразование модели в схему
            user_schema = UserCredentialsSchema(
                id=user_model.id,
                username=user_model.username,
                email=user_model.email,
                password_hash=user_model.password_hash,
                is_active=user_model.is_active,
                role=user_model.role  # @property вызывается явно
            )

            # 3. Генерация и сохранение новых токенов
            access_token, new_refresh_token = await self._generate_and_save_new_tokens(
                user_schema, user_id, refresh_token
            )

            self.logger.info(
                "Токены успешно обновлены",
                extra={"user_id": user_id}
            )

            # 4. Установка куков, если требуется
            if response and use_cookies:
                CookieManager.set_auth_cookies(response, access_token, new_refresh_token)

                return TokenResponseSchema(
                    message="Токен успешно обновлен",
                    access_token=None,
                    refresh_token=None,
                    expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
                )

            return TokenResponseSchema(
                message="Токен успешно обновлен",
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=self.settings.ACCESS_TOKEN_MAX_AGE,
            )

        except (TokenExpiredError, TokenInvalidError) as e:
            self.logger.warning(
                "Ошибка при обновлении токена: %s",
                type(e).__name__,
                extra={"error_type": type(e).__name__}
            )
            raise

    async def _validate_and_get_user_by_refresh_token(
        self, refresh_token: str
    ) -> Tuple[UserModel, UUID]:
        """
        Валидирует refresh токен и получает пользователя.

        Args:
            refresh_token: Refresh токен.

        Returns:
            Tuple[UserModel, UUID]: Модель пользователя и его ID.
        """
        payload = TokenManager.decode_token(refresh_token)
        user_id = TokenManager.validate_refresh_token(payload)

        if not await self.redis_manager.check_refresh_token(user_id, refresh_token):
            self.logger.warning(
                "Попытка использовать неизвестный refresh токен",
                extra={"user_id": user_id}
            )
            raise TokenInvalidError()

        user_model = await self.repository.get_item_by_id(user_id)
        if not user_model:
            self.logger.warning(
                "Пользователь не найден при обновлении токена",
                extra={"user_id": user_id}
            )
            raise UserNotFoundError(field="id", value=str(user_id))

        return user_model, user_id

    async def _generate_and_save_new_tokens(
        self, user_schema: UserCredentialsSchema, user_id: UUID, old_refresh_token: str
    ) -> Tuple[str, str]:
        """
        Генерирует и сохраняет новые access и refresh токены.

        Args:
            user_schema: Схема пользователя.
            user_id: ID пользователя.
            old_refresh_token: Старый refresh токен для удаления.

        Returns:
            Tuple[str, str]: Новый access токен и новый refresh токен.
        """
        access_token = await self.create_token(user_schema)
        new_refresh_token = await self.create_refresh_token(user_id)
        await self.redis_manager.remove_refresh_token(user_id, old_refresh_token)
        return access_token, new_refresh_token

    # ==================== ВЫХОД ====================

    async def logout(
        self,
        authorization: str,
        response: Optional[Response] = None,
        clear_cookies: bool = False,
    ) -> LogoutResponseSchema:
        """
        Выход из системы с удалением токенов.

        Args:
            authorization: Bearer токен из заголовка.
            response: HTTP ответ для очистки куков.
            clear_cookies: Очистить ли cookies при выходе.

        Returns:
            LogoutResponseSchema: Информация о выходе.

        Raises:
            TokenMissingError: Если токен отсутствует.
        """
        if not authorization:
            self.logger.warning("Попытка выхода без access token")
            raise TokenMissingError()

        token = TokenManager.get_token_from_header(authorization)

        # Удаление токена из Redis
        await self.redis_manager.remove_token(token)

        # Очистка куков, если требуется
        if response and clear_cookies:
            CookieManager.clear_auth_cookies(response)

        self.logger.info("Пользователь вышел из системы")

        return LogoutResponseSchema(
            success=True,
            message="Выход выполнен успешно",
            data=LogoutDataSchema(logged_out_at=datetime.now(timezone.utc)),
        )

    # ==================== ТЕКУЩИЙ ПОЛЬЗОВАТЕЛЬ ====================

    async def get_current_user(
        self,
        authorization: str,
    ) -> CurrentUserResponseSchema:
        """
        Получает информацию о текущем аутентифицированном пользователе.

        Args:
            authorization: Bearer токен из заголовка.

        Returns:
            CurrentUserResponseSchema: Данные текущего пользователя.

        Raises:
            TokenMissingError: Если токен отсутствует.
            TokenInvalidError: Если токен недействителен.
        """
        if not authorization:
            self.logger.warning("Попытка получить текущего пользователя без токена")
            raise TokenMissingError()

        token = TokenManager.get_token_from_header(authorization)

        # Получение пользователя по токену
        user_data = await self.redis_manager.get_user_by_token(token)

        if not user_data:
            self.logger.warning("Пользователь не найден по токену")
            raise TokenInvalidError()

        # Конвертация в CurrentUserSchema
        current_user = UserCurrentSchema(
            id=user_data.id,
            username=user_data.username if hasattr(user_data, 'username') else user_data.email.split('@')[0],
            email=user_data.email,
            role=user_data.role if hasattr(user_data, 'role') else "user"
        )

        return CurrentUserResponseSchema(
            success=True,
            message=None,
            data=current_user
        )
