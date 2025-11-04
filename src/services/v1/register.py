"""
Сервис для регистрации новых пользователей.

Обрабатывает процесс регистрации:
1. Валидация уникальности email/username
2. Создание пользователя с ролью user
3. Присвоение роли
4. Генерация JWT токенов (access + refresh)

Все операции логируются и выбрасывают кастомные исключения.
"""

import logging
from typing import Dict, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.base import BaseService
from src.services.v1.token import TokenService
from src.repository.v1.users import UserRepository
from src.models.v1.users import UserModel

from src.models.v1.roles import RoleCode
from src.core.exceptions import (
    UserAlreadyExistsError,
    UserCreationError,
    RoleAssignmentError,
)
from src.core.security import PasswordManager
from src.schemas.v1.auth import UserCredentialsSchema


logger = logging.getLogger(__name__)


class RegisterService(BaseService):
    """
    Сервис для регистрации новых пользователей.

    Создаёт нового пользователя с ролью user
    и генерирует JWT токены через TokenService.
    Возвращает SQLAlchemy модели + токены, НЕ Pydantic схемы.

    Dependencies:
        - UserRepository: операции с пользователями
        - PasswordManager: хэширование паролей
        - TokenService: генерация и управление токенами

    Example:
        >>> service = RegisterService(session=session, token_service=token_service)
        >>> user, tokens = await service.register_user({
        ...     "username": "user123",
        ...     "email": "user@email.com",
        ...     "password": "SecurePass123!"
        ... })
        >>> print(user.username)  # "user123"
        >>> print(tokens["access_token"])  # "eyJ0eXAi..."
    """

    def __init__(self, session: AsyncSession, token_service: TokenService):
        """
        Инициализация RegisterService.

        Args:
            session: Асинхронная сессия базы данных.
            token_service: Сервис для работы с токенами.
        """
        super().__init__(session)
        self.token_service = token_service
        self.user_repository = UserRepository(session, UserModel)
        self.password_manager = PasswordManager()

    async def register_user(
        self, user_data: Dict
    ) -> Tuple[UserModel, Dict[str, str]]:
        """
        Зарегистрировать нового пользователя и выдать токены.

        Процесс регистрации:
        1. Валидация уникальности email/username одним запросом
        2. Хэширование пароля
        3. Создание пользователя с ролью user
        4. Генерация JWT токенов (access + refresh)

        Args:
            user_data: Данные пользователя (username, email, password).

        Returns:
            Tuple[UserModel, Dict[str, str]]:
                - UserModel: Созданный пользователь с relationships
                - Dict: {"access_token": str, "refresh_token": str}

        Raises:
            UserAlreadyExistsError: Email или username уже занят.
            UserCreationError: Ошибка создания пользователя.
            RoleAssignmentError: Ошибка присвоения роли.

        Example:
            >>> user, tokens = await service.register_user({
            ...     "username": "user123",
            ...     "email": "user@example.com",
            ...     "password": "StrongPass123!"
            ... })
            >>> print(tokens["access_token"])
        """
        email = user_data["email"]
        password = user_data["password"]

        # Генерация username из email если не предоставлен
        username = user_data.get("username")
        if not username:
            username = email.split("@")[0]

        self.logger.info(
            "Начало регистрации пользователя: %s (%s)", username, email
        )

        # 1. Валидация уникальности email/username одним запросом
        await self._validate_uniqueness(username, email)

        # 2. Хэширование пароля
        hashed_password = self.password_manager.hash_password(password)

        # 3. Создание пользователя с ролью user
        user = await self._create_user_with_role(
            username=username,
            email=email,
            hashed_password=hashed_password,
        )

        # 4. Генерация JWT токенов
        tokens = await self._generate_tokens(user)

        self.logger.info(
            "Пользователь '%s' успешно зарегистрирован (id=%s)", username, user.id
        )

        return user, tokens

    async def _validate_uniqueness(self, username: str, email: str) -> None:
        """
        Проверить уникальность username и email одним запросом.

        Оптимизация: объединяет две проверки в один SQL запрос.
        Использует OR-условие для email и username через репозиторий.

        Args:
            username: Username для проверки.
            email: Email для проверки.

        Raises:
            UserAlreadyExistsError: Поле уже занято (указывается какое именно).
        """
        # Используем метод репозитория для поиска
        existing_user = await self.user_repository.find_by_email_or_username(
            email=email, username=username
        )

        if existing_user:
            # Определяем какое именно поле дублируется
            if existing_user.email == email:
                self.logger.warning(
                    "Попытка регистрации с существующим email: %s", email
                )
                raise UserAlreadyExistsError(field="email", value=email)
            elif existing_user.username == username:
                self.logger.warning(
                    "Попытка регистрации с существующим username: %s", username
                )
                raise UserAlreadyExistsError(field="username", value=username)



    async def _create_user_with_role(
        self,
        username: str,
        email: str,
        hashed_password: str,
    ) -> UserModel:
        """
        Создать пользователя в БД и присвоить роль user.

        Объединяет создание пользователя и присвоение роли в одну транзакцию.
        Делегирует работу с БД в UserRepository.

        Args:
            username: Имя пользователя.
            email: Email пользователя.
            hashed_password: Хэшированный пароль.

        Returns:
            Созданный UserModel с ролью user.

        Raises:
            UserCreationError: Ошибка при создании пользователя.
            RoleAssignmentError: Ошибка при присвоении роли.
        """
        try:
            user_data = {
                "username": username,
                "email": email,
                "password_hash": hashed_password,
                "is_active": True,
            }

            # Используем метод репозитория для создания пользователя с ролью
            user = await self.user_repository.create_user_with_role(
                user_data=user_data,
                role_code=RoleCode.USER.value,
            )

            self.logger.info(
                "Пользователь '%s' создан с ролью user (id=%s)", username, user.id
            )

            return user

        except Exception as e:
            self.logger.error(
                "Ошибка создания пользователя '%s': %s", username, str(e), exc_info=True
            )
            # Определяем тип ошибки
            if "user" in locals():
                raise RoleAssignmentError(
                    user_id=user.id,
                    role_code=RoleCode.USER.value,
                    detail=str(e),
                ) from e
            else:
                raise UserCreationError(reason=str(e), detail=str(e)) from e

    async def _generate_tokens(self, user: UserModel) -> Dict[str, str]:
        """
        Сгенерировать JWT access и refresh токены для пользователя.

        Использует TokenService для генерации и сохранения токенов в Redis.
        Конвертирует UserModel в UserCredentialsSchema для генерации payload.

        Args:
            user: Созданный UserModel.

        Returns:
            Dict[str, str]: {"access_token": str, "refresh_token": str}

        Example:
            >>> tokens = await service._generate_tokens(user)
            >>> print(tokens["access_token"])  # "eyJ0eXAi..."
        """
        # Конвертируем UserModel в UserCredentialsSchema для токена
        user_credentials = UserCredentialsSchema(
            id=user.id,
            username=user.username,
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            role="user",  # Всегда user при регистрации
        )

        # Генерируем токены через TokenService
        access_token = await self.token_service.create_access_token(user_credentials)
        refresh_token = await self.token_service.create_refresh_token(user.id)

        self.logger.info(
            "JWT токены сгенерированы для пользователя %s", user.id,
            extra={"user_id": str(user.id), "username": user.username},
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
