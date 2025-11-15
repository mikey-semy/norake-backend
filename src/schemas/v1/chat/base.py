"""
Базовые схемы для AI чатов.

Содержит доменные модели чатов БЕЗ системных полей (id, timestamps).
Используется как основа для request/response схем.
"""

from pydantic import Field

from src.schemas.base import CommonBaseSchema


class ChatMessageSchema(CommonBaseSchema):
    """
    Схема одного сообщения в чате.

    Представляет сообщение от пользователя или AI ассистента.
    """

    role: str = Field(
        ...,
        description="Роль отправителя: 'user' или 'assistant'",
        examples=["user", "assistant"],
    )
    content: str = Field(
        ...,
        description="Содержимое сообщения",
        examples=["Проанализируй этот документ"],
    )
    message_metadata: dict = Field(
        default_factory=dict,
        description="Дополнительные метаданные сообщения",
        examples=[{"tokens_used": 150, "rag_chunks_used": 3}],
    )
    timestamp: str = Field(
        ...,
        description="Время отправки сообщения в ISO формате",
        examples=["2025-11-15T10:30:00Z"],
    )


class ChatModelSettingsSchema(CommonBaseSchema):
    """
    Настройки модели для чата.

    Управляет поведением AI модели (температура, лимиты токенов, system prompt).
    """

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Температура генерации (0.0 = детерминированный, 2.0 = креативный)",
        examples=[0.7, 0.2, 1.0],
    )
    max_tokens: int = Field(
        default=4000,
        gt=0,
        le=128000,
        description="Максимальное количество токенов в ответе",
        examples=[4000, 8000, 16000],
    )
    system_prompt: str | None = Field(
        default=None,
        description="Кастомный системный промпт для AI ассистента",
        examples=["Ты эксперт по анализу документов"],
    )


class ChatMetadataSchema(CommonBaseSchema):
    """
    Метаданные чата для аналитики.

    Хранит статистику использования: токены, количество сообщений, RAG запросы.
    """

    tokens_used: int = Field(
        default=0,
        ge=0,
        description="Суммарное количество использованных токенов",
        examples=[1500, 5000, 10000],
    )
    messages_count: int = Field(
        default=0,
        ge=0,
        description="Количество сообщений в чате",
        examples=[5, 10, 20],
    )
    estimated_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Примерная стоимость использования в USD",
        examples=[0.05, 0.15, 0.50],
    )
    rag_queries_count: int = Field(
        default=0,
        ge=0,
        description="Количество выполненных RAG поисковых запросов",
        examples=[3, 8, 15],
    )


class ChatBaseSchema(CommonBaseSchema):
    """
    Базовая схема чата БЕЗ системных полей.

    Содержит только бизнес-логику: название, модель, документы, сообщения.
    Используется как основа для создания request/response схем.
    """

    chat_id: str = Field(
        ...,
        min_length=5,
        max_length=100,
        description="Читаемый идентификатор чата (например: 'chat-abc123')",
        examples=["chat-abc123", "chat-xyz789"],
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Название чата",
        examples=["Анализ договора поставки", "Обсуждение проекта"],
    )
    model_key: str = Field(
        ...,
        description="Ключ модели из Settings.OPENROUTER_CHAT_MODELS",
        examples=["qwen_coder", "deepseek_r1", "kimi_dev"],
    )
    document_service_ids: list[str] = Field(
        default_factory=list,
        description="UUID документов для RAG контекста",
        examples=[
            ["550e8400-e29b-41d4-a716-446655440000"],
            [],
        ],
    )
    is_active: bool = Field(
        default=True,
        description="Активность чата (False = мягкое удаление)",
        examples=[True, False],
    )
