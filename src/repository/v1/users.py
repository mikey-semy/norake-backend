"""
Репозиторий для работы с пользователями.

Обеспечивает доступ к данным пользователей для операций аутентификации
и управления пользователями. Следует архитектуре BaseRepository.
"""

from typing import Optional

from src.repository.base import BaseRepository
from src.models.v1.users import UserModel
from src.core.settings import settings


class UserRepository(BaseRepository[UserModel]):
    """
    Репозиторий для работы с пользователями.

    Предоставляет методы для получения пользователей по различным
    идентификаторам (email, phone, username) в зависимости от настроек.

    Example:
        >>> repository = UserRepository(session=session, model=UserModel)
        >>> user = await repository.get_user_by_identifier("buyer@company.com")
        >>> print(user.full_name)
    """

    async def get_user_by_identifier(self, identifier: str) -> Optional[UserModel]:
        """
        Получение пользователя по email, телефону или имени.

        Автоматически определяет тип идентификатора на основе
        настроек USERNAME_ALLOWED_TYPES.

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

        # Email (содержит @)
        if "email" in allowed and "@" in identifier:
            return await self.get_item_by_field("email", identifier)

        # Phone (начинается с +)
        if "phone" in allowed and identifier.startswith("+"):
            return await self.get_item_by_field("phone", identifier)

        # Username (имя пользователя) - по умолчанию
        if "username" in allowed:
            return await self.get_item_by_field("username", identifier)

        # Если ничего не подошло — пользователь не найден
        return None
