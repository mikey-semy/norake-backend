"""
Репозиторий для работы с пользователями.

Обеспечивает доступ к данным пользователей для операций аутентификации
и управления пользователями. Следует архитектуре BaseRepository.
"""

from typing import Optional, Dict

from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from src.repository.base import BaseRepository
from src.models.v1.users import UserModel
from src.core.settings import settings


class UserRepository(BaseRepository[UserModel]):
    """
    Репозиторий для работы с пользователями.

    Предоставляет методы для получения пользователей по различным
    идентификаторам (email, phone, username) в зависимости от настроек.
    """

    def __init__(self, session):
        super().__init__(session, UserModel)

    async def get_user_by_identifier(self, identifier: str) -> Optional[UserModel]:
        """
        Получение пользователя по email, телефону или имени.

        Автоматически определяет тип идентификатора на основе
        настроек USERNAME_ALLOWED_TYPES.

        ВАЖНО: Загружает связанные user_roles через selectinload для
        предотвращения lazy loading и ошибок MissingGreenlet.

        Args:
            identifier: email, телефон или имя пользователя.

        Returns:
            UserModel или None, если пользователь не найден.

        Example:
            >>> user = await repo.get_user_by_identifier("user@example.com")
            >>> user = await repo.get_user_by_identifier("+79991234567")
        """
        # Получаем разрешенные типы идентификаторов из настроек
        allowed = set(settings.USERNAME_ALLOWED_TYPES)

        # Определяем поле для поиска
        field_name = None

        # Email (содержит @)
        if "email" in allowed and "@" in identifier:
            field_name = "email"

        # Phone (начинается с +)
        elif "phone" in allowed and identifier.startswith("+"):
            field_name = "phone"

        # Username (имя пользователя) - по умолчанию
        elif "username" in allowed:
            field_name = "username"

        # Если ничего не подошло — пользователь не найден
        if not field_name:
            return None

        # Выполняем запрос с eager loading для user_roles
        field = getattr(UserModel, field_name)
        statement = (
            select(UserModel)
            .where(field == identifier)
            .options(selectinload(UserModel.user_roles))
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_user_with_roles_by_id(self, user_id) -> Optional[UserModel]:
        """
        Получение пользователя по ID с загрузкой ролей.

        Использует eager loading для предотвращения lazy loading
        и ошибок MissingGreenlet при доступе к user.role.

        Args:
            user_id: UUID идентификатор пользователя.

        Returns:
            UserModel с загруженными user_roles или None.

        Example:
            >>> user = await repo.get_user_with_roles_by_id(uuid)
            >>> print(user.role)  # Безопасный доступ без lazy load
        """
        statement = (
            select(UserModel)
            .where(UserModel.id == user_id)
            .options(selectinload(UserModel.user_roles))
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def find_by_email_or_username(
        self, email: str, username: str
    ) -> Optional[UserModel]:
        """
        Поиск пользователя по email ИЛИ username.

        Используется для валидации уникальности при регистрации.
        Выполняет один SQL запрос с OR-условием для оптимизации.

        Args:
            email: Email для проверки.
            username: Username для проверки.

        Returns:
            UserModel если найден пользователь с таким email или username,
            None если оба поля свободны.

        Example:
            >>> existing = await repo.find_by_email_or_username(
            ...     "test@example.com", "testuser"
            ... )
            >>> if existing:
            ...     print(f"Занято поле: {existing.email or existing.username}")
        """
        statement = select(UserModel).where(
            or_(
                UserModel.email == email,
                UserModel.username == username,
            )
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_user_with_role(
        self, user_data: Dict, role_code: str
    ) -> UserModel:
        """
        Создать пользователя и присвоить ему роль в одной транзакции.

        Атомарная операция создания пользователя и назначения роли.
        Используется при регистрации для гарантии целостности данных.

        Args:
            user_data: Данные пользователя для создания
                (username, email, password_hash, is_active).
            role_code: Код роли для присвоения (из RoleCode enum).

        Returns:
            Созданный UserModel с присвоенной ролью.

        Raises:
            SQLAlchemyError: При ошибках работы с БД.

        Example:
            >>> user = await repo.create_user_with_role(
            ...     {"username": "john", "email": "j@ex.com",
            ...      "password_hash": "hash", "is_active": True},
            ...     "user"
            ... )
        """
        from src.models.v1.roles import UserRoleModel

        # 1. Создаём пользователя
        user = await self.create_item(user_data)

        # 2. Создаём связь пользователь-роль
        role = UserRoleModel(
            user_id=user.id,
            role_code=role_code,
        )

        self.session.add(role)
        await self.session.flush()

        return user
