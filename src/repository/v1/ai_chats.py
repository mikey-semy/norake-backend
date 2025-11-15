"""
Репозиторий для работы с AI чатами.

Модуль предоставляет CRUD операции для AIChatModel:
- Базовые операции через BaseRepository
- Поиск чатов по chat_id, user_id, workspace_id
- Получение активных чатов пользователя
- Фильтрация по модели и workspace
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.ai_chats import AIChatModel
from src.repository.base import BaseRepository


class AIChatRepository(BaseRepository[AIChatModel]):
    """
    Репозиторий для работы с AI чатами.

    Наследует BaseRepository и добавляет специфичные методы:
    - get_by_chat_id: Получение чата по readable идентификатору
    - get_user_active_chats: Список активных чатов пользователя
    - get_workspace_chats: Чаты в workspace
    - exists_by_chat_id: Проверка существования по chat_id

    Example:
        >>> repo = AIChatRepository(session)
        >>> chat = await repo.get_by_chat_id("chat-abc123")
        >>> active_chats = await repo.get_user_active_chats(user_id)
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий с моделью AIChatModel.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        super().__init__(model=AIChatModel, session=session)

    async def get_by_chat_id(self, chat_id: str) -> AIChatModel | None:
        """
        Получает чат по readable идентификатору.

        Args:
            chat_id: Readable идентификатор чата (например, "chat-abc123")

        Returns:
            AIChatModel | None: Чат или None если не найден

        Example:
            >>> chat = await repo.get_by_chat_id("chat-abc123")
            >>> chat.title
            'Code Review Assistant'
        """
        return await self.get_item_by_field("chat_id", chat_id)

    async def exists_by_chat_id(self, chat_id: str) -> bool:
        """
        Проверяет существование чата по chat_id.

        Args:
            chat_id: Readable идентификатор чата

        Returns:
            bool: True если чат существует

        Example:
            >>> exists = await repo.exists_by_chat_id("chat-abc123")
            >>> exists
            True
        """
        return await self.exists_by_field("chat_id", chat_id)

    async def get_user_active_chats(
        self,
        user_id: UUID,
        limit: int = 50,
    ) -> list[AIChatModel]:
        """
        Получает список активных чатов пользователя.

        Возвращает чаты отсортированные по дате обновления (новые сначала).

        Args:
            user_id: UUID пользователя
            limit: Максимальное количество чатов (по умолчанию 50)

        Returns:
            list[AIChatModel]: Список активных чатов

        Example:
            >>> chats = await repo.get_user_active_chats(user_id, limit=10)
            >>> len(chats) <= 10
            True
            >>> all(chat.is_active for chat in chats)
            True
        """
        return await self.filter_by_ordered(
            "updated_at",
            ascending=False,
            user_id=user_id,
            is_active=True,
            limit=limit,
        )

    async def get_workspace_chats(
        self,
        workspace_id: UUID,
        is_active: bool = True,
        limit: int = 100,
    ) -> list[AIChatModel]:
        """
        Получает чаты workspace.

        Args:
            workspace_id: UUID workspace
            is_active: Фильтр по активности (по умолчанию True)
            limit: Максимальное количество чатов (по умолчанию 100)

        Returns:
            list[AIChatModel]: Список чатов workspace

        Example:
            >>> chats = await repo.get_workspace_chats(workspace_id)
            >>> all(chat.workspace_id == workspace_id for chat in chats)
            True
        """
        return await self.filter_by_ordered(
            "created_at",
            ascending=False,
            workspace_id=workspace_id,
            is_active=is_active,
            limit=limit,
        )

    async def get_by_model_key(
        self,
        model_key: str,
        user_id: UUID | None = None,
        limit: int = 50,
    ) -> list[AIChatModel]:
        """
        Получает чаты по ключу модели.

        Опционально фильтрует по пользователю.

        Args:
            model_key: Ключ модели (qwen_coder, kimi_dev и т.д.)
            user_id: UUID пользователя для фильтрации (опционально)
            limit: Максимальное количество чатов (по умолчанию 50)

        Returns:
            list[AIChatModel]: Список чатов использующих модель

        Example:
            >>> chats = await repo.get_by_model_key("qwen_coder", user_id=user_id)
            >>> all(chat.model_key == "qwen_coder" for chat in chats)
            True
        """
        filters = {"model_key": model_key, "is_active": True}
        if user_id:
            filters["user_id"] = user_id

        return await self.filter_by_ordered(
            "updated_at",
            ascending=False,
            limit=limit,
            **filters,
        )

    async def count_user_chats(
        self,
        user_id: UUID,
        is_active: bool | None = None,
    ) -> int:
        """
        Подсчитывает количество чатов пользователя.

        Args:
            user_id: UUID пользователя
            is_active: Фильтр по активности (None - все чаты)

        Returns:
            int: Количество чатов

        Example:
            >>> count = await repo.count_user_chats(user_id, is_active=True)
            >>> count >= 0
            True
        """
        filters = {"user_id": user_id}
        if is_active is not None:
            filters["is_active"] = is_active

        return await self.count_items(**filters)

    async def update_messages(
        self,
        chat_id: str,
        messages: list[dict],
    ) -> AIChatModel | None:
        """
        Обновляет историю сообщений чата.

        Также обновляет metadata.messages_count.

        Args:
            chat_id: Readable идентификатор чата
            messages: Новый массив сообщений

        Returns:
            AIChatModel | None: Обновленный чат или None

        Example:
            >>> chat = await repo.update_messages(
            ...     "chat-abc123",
            ...     [{"role": "user", "content": "Hello"}]
            ... )
            >>> len(chat.messages) == 1
            True
        """
        chat = await self.get_by_chat_id(chat_id)
        if not chat:
            return None

        # Обновляем messages и chat_metadata
        metadata = chat.chat_metadata or {}
        metadata["messages_count"] = len(messages)

        return await self.update_item(
            chat.id,
            {"messages": messages, "chat_metadata": metadata},
        )
