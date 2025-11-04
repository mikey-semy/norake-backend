"""
Репозиторий для работы с пользователями.

Обеспечивает доступ к данным пользователей для операций аутентификации
и управления пользователями. Следует архитектуре BaseRepository.
"""

from typing import Optional

from sqlalchemy import select
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
