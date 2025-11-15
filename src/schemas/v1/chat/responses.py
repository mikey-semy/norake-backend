"""
Response схемы для AI чатов.

Содержит схемы для исходящих данных к клиенту:
- Детальная информация о чате
- Список чатов
- Информация о моделях
- Ответы AI ассистента
"""

from uuid import UUID

from pydantic import Field, computed_field

from src.core.settings.base import settings
from src.schemas.base import BaseResponseSchema, BaseSchema, CommonBaseSchema
from src.schemas.v1.chat.base import (ChatMessageSchema,
                                       ChatMetadataSchema,
                                       ChatModelSettingsSchema)


class ModelInfoSchema(CommonBaseSchema):
    """
    Информация об AI модели.

    Описывает доступную модель OpenRouter: название, специализация, лимиты.
    """

    key: str = Field(
        ...,
        description="Ключ модели в Settings.OPENROUTER_CHAT_MODELS",
        examples=["qwen_coder", "deepseek_r1"],
    )
    id: str = Field(
        ...,
        description="ID модели в OpenRouter API",
        examples=["qwen/qwq-32b-preview", "deepseek/deepseek-r1"],
    )
    name: str = Field(
        ...,
        description="Человекочитаемое название модели",
        examples=["Qwen QwQ 32B", "DeepSeek R1"],
    )
    description: str = Field(
        ...,
        description="Краткое описание модели",
        examples=["Модель для анализа кода и отладки"],
    )
    specialization: str = Field(
        ...,
        description="Специализация модели",
        examples=["Code Analysis", "General Chat", "Research"],
    )
    context_window: int = Field(
        ...,
        description="Размер контекстного окна в токенах",
        examples=[32768, 65536, 200000],
    )
    temperature: float = Field(
        ...,
        description="Рекомендуемая температура генерации",
        examples=[0.2, 0.5, 0.7],
    )
    max_tokens: int = Field(
        ...,
        description="Максимальное количество токенов в ответе",
        examples=[4000, 8000, 16000],
    )


class ChatListItemSchema(BaseSchema):
    """
    Краткая информация о чате для списка.

    Используется в GET /chat для отображения списка чатов пользователя.
    С системными полями (id, created_at, updated_at) из BaseSchema.
    """

    chat_id: str = Field(
        ...,
        description="Читаемый идентификатор чата",
        examples=["chat-abc123"],
    )
    title: str = Field(
        ...,
        description="Название чата",
        examples=["Анализ договора поставки"],
    )
    model_key: str = Field(
        ...,
        description="Ключ используемой модели",
        examples=["qwen_coder"],
    )
    messages_count: int = Field(
        ...,
        description="Количество сообщений в чате",
        examples=[5, 10, 20],
    )
    workspace_id: UUID | None = Field(
        default=None,
        description="UUID workspace (None = личный чат)",
        examples=["550e8400-e29b-41d4-a716-446655440000", None],
    )

    @computed_field
    @property
    def model_name(self) -> str:
        """
        Человекочитаемое название модели.

        Автоматически извлекается из Settings.OPENROUTER_CHAT_MODELS
        по ключу model_key.

        Returns:
            str: Название модели или "Unknown Model" если ключ не найден

        Examples:
            >>> chat.model_key = "qwen_coder"
            >>> chat.model_name
            "Qwen QwQ 32B"
        """
        model_config = settings.OPENROUTER_CHAT_MODELS.get(self.model_key)
        return model_config["name"] if model_config else "Unknown Model"


class ChatDetailSchema(BaseSchema):
    """
    Детальная информация о чате.

    Содержит полную информацию: сообщения, настройки, документы, метаданные.
    С системными полями (id, created_at, updated_at) из BaseSchema.
    """

    chat_id: str = Field(
        ...,
        description="Читаемый идентификатор чата",
        examples=["chat-abc123"],
    )
    title: str = Field(
        ...,
        description="Название чата",
        examples=["Анализ договора поставки"],
    )
    model_key: str = Field(
        ...,
        description="Ключ используемой модели",
        examples=["qwen_coder"],
    )
    user_id: UUID = Field(
        ...,
        description="UUID владельца чата",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    workspace_id: UUID | None = Field(
        default=None,
        description="UUID workspace (None = личный чат)",
        examples=["550e8400-e29b-41d4-a716-446655440000", None],
    )
    document_service_ids: list[UUID] = Field(
        default_factory=list,
        description="UUID документов для RAG контекста",
        examples=[["550e8400-e29b-41d4-a716-446655440000"]],
    )
    messages: list[ChatMessageSchema] = Field(
        default_factory=list,
        description="История сообщений чата",
        examples=[
            [
                {
                    "role": "user",
                    "content": "Проанализируй документ",
                    "metadata": {},
                    "timestamp": "2025-11-15T10:30:00Z",
                }
            ]
        ],
    )
    model_settings: ChatModelSettingsSchema = Field(
        ...,
        description="Настройки AI модели",
        examples=[
            {"temperature": 0.7, "max_tokens": 4000, "system_prompt": None}
        ],
    )
    chat_metadata: ChatMetadataSchema = Field(
        ...,
        description="Метаданные и статистика чата",
        examples=[
            {
                "tokens_used": 1500,
                "messages_count": 10,
                "estimated_cost": 0.05,
                "rag_queries_count": 3,
            }
        ],
    )
    is_active: bool = Field(
        ...,
        description="Активность чата",
        examples=[True, False],
    )

    @computed_field
    @property
    def model_name(self) -> str:
        """
        Человекочитаемое название модели.

        Автоматически извлекается из Settings.OPENROUTER_CHAT_MODELS.

        Returns:
            str: Название модели или "Unknown Model"
        """
        model_config = settings.OPENROUTER_CHAT_MODELS.get(self.model_key)
        return model_config["name"] if model_config else "Unknown Model"


class MessageResponseSchema(CommonBaseSchema):
    """
    Ответ AI ассистента на сообщение пользователя.

    Возвращается после POST /chat/{chat_id}/message.
    БЕЗ системных полей (brief schema).
    """

    role: str = Field(
        ...,
        description="Роль отправителя (всегда 'assistant')",
        examples=["assistant"],
    )
    content: str = Field(
        ...,
        description="Текст ответа AI",
        examples=["На основе анализа документа можно выделить..."],
    )
    chat_metadata: dict = Field(
        ...,
        description="Метаданные ответа",
        examples=[
            {
                "tokens_used": 150,
                "rag_chunks_used": 3,
                "model_key": "qwen_coder",
            }
        ],
    )
    timestamp: str = Field(
        ...,
        description="Время генерации ответа в ISO формате",
        examples=["2025-11-15T10:30:15Z"],
    )


# Response wrappers

class ModelsListResponseSchema(BaseResponseSchema):
    """Обёртка для списка доступных моделей."""

    data: list[ModelInfoSchema] | None = Field(
        default=None,
        description="Список доступных AI моделей",
    )


class ChatCreateResponseSchema(BaseResponseSchema):
    """Обёртка для созданного чата."""

    data: ChatDetailSchema | None = Field(
        default=None,
        description="Детальная информация о созданном чате",
    )


class ChatListResponseSchema(BaseResponseSchema):
    """Обёртка для списка чатов пользователя."""

    data: list[ChatListItemSchema] | None = Field(
        default=None,
        description="Список чатов пользователя",
    )


class ChatDetailResponseSchema(BaseResponseSchema):
    """Обёртка для детальной информации о чате."""

    data: ChatDetailSchema | None = Field(
        default=None,
        description="Детальная информация о чате",
    )


class MessageSendResponseSchema(BaseResponseSchema):
    """Обёртка для ответа AI на сообщение."""

    data: MessageResponseSchema | None = Field(
        default=None,
        description="Ответ AI ассистента",
    )


class ChatUpdateResponseSchema(BaseResponseSchema):
    """Обёртка для обновлённой информации о чате."""

    data: ChatDetailSchema | None = Field(
        default=None,
        description="Обновлённая информация о чате",
    )


class ChatDeleteResponseSchema(BaseResponseSchema):
    """Обёртка для результата удаления чата."""

    data: dict | None = Field(
        default=None,
        description="Информация об удалённом чате",
        examples=[{"chat_id": "chat-abc123", "deleted": True}],
    )
