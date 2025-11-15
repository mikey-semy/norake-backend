"""
Схемы для AI чатов.

Экспортирует все схемы для работы с AI чатами через RAG и OpenRouter.
"""

from .base import (
    ChatBaseSchema,
    ChatMessageSchema,
    ChatMetadataSchema,
    ChatModelSettingsSchema,
)
from .requests import (
    ChatAddDocumentsRequestSchema,
    ChatCreateRequestSchema,
    ChatModelSwitchRequestSchema,
)
from .responses import (
    ChatCreateResponseSchema,
    ChatDeleteResponseSchema,
    ChatDetailResponseSchema,
    ChatDetailSchema,
    ChatListItemSchema,
    ChatListResponseSchema,
    ChatUpdateResponseSchema,
    MessageResponseSchema,
    MessageSendResponseSchema,
    ModelInfoSchema,
    ModelsListResponseSchema,
)

__all__ = [
    # Base schemas
    "ChatBaseSchema",
    "ChatMessageSchema",
    "ChatMetadataSchema",
    "ChatModelSettingsSchema",
    # Request schemas
    "ChatCreateRequestSchema",
    "ChatModelSwitchRequestSchema",
    "ChatAddDocumentsRequestSchema",
    # Response schemas
    "ModelInfoSchema",
    "ChatListItemSchema",
    "ChatDetailSchema",
    "MessageResponseSchema",
    # Response wrappers
    "ModelsListResponseSchema",
    "ChatCreateResponseSchema",
    "ChatListResponseSchema",
    "ChatDetailResponseSchema",
    "MessageSendResponseSchema",
    "ChatUpdateResponseSchema",
    "ChatDeleteResponseSchema",
]
