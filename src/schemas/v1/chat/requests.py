"""
Request схемы для AI чатов.

Содержит схемы для входящих данных от клиента:
- Создание нового чата
- Отправка сообщения
- Переключение модели
- Добавление документов
"""

from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseRequestSchema


class ChatCreateRequestSchema(BaseRequestSchema):
    """
    Схема для создания нового AI чата.

    Требует указания модели, опционально workspace и документы для RAG.
    """

    model_key: str = Field(
        ...,
        description="Ключ модели из Settings.OPENROUTER_CHAT_MODELS",
        examples=["qwen_coder", "deepseek_r1", "kimi_dev"],
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Название чата",
        examples=["Анализ договора поставки", "Обсуждение проекта"],
    )
    workspace_id: UUID | None = Field(
        default=None,
        description="UUID workspace для командного доступа (None = личный чат)",
        examples=["550e8400-e29b-41d4-a716-446655440000", None],
    )
    document_service_ids: list[UUID] | None = Field(
        default=None,
        description="UUID документов для RAG контекста",
        examples=[
            ["550e8400-e29b-41d4-a716-446655440000"],
            [],
            None,
        ],
    )
    system_prompt: str | None = Field(
        default=None,
        max_length=2000,
        description="Кастомный системный промпт для AI ассистента",
        examples=[
            "Ты эксперт по анализу юридических документов",
            "Ты помощник программиста на Python",
            None,
        ],
    )


class ChatModelSwitchRequestSchema(BaseRequestSchema):
    """
    Схема для переключения модели чата.

    Позволяет сменить AI модель с сохранением истории сообщений.
    Полезно для перехода с быстрой модели на более мощную.
    """

    model_key: str = Field(
        ...,
        description="Новый ключ модели из Settings.OPENROUTER_CHAT_MODELS",
        examples=["deepseek_r1", "kimi_dev", "tongyi_research"],
    )


class ChatAddDocumentsRequestSchema(BaseRequestSchema):
    """
    Схема для добавления документов в чат.

    Поддерживает drag-and-drop сценарий: пользователь перетаскивает
    дополнительные файлы в чат для расширения RAG контекста.
    """

    document_service_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="UUID документов для добавления в RAG контекст",
        examples=[
            ["550e8400-e29b-41d4-a716-446655440000"],
            [
                "550e8400-e29b-41d4-a716-446655440000",
                "650e8400-e29b-41d4-a716-446655440001",
            ],
        ],
    )
