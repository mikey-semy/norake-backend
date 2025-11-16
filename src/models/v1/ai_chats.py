"""
Модели для AI Chat системы.

Модуль содержит SQLAlchemy модели для хранения чатов с AI:
- AIChatModel: Чат с историей сообщений и привязкой к документам

История сообщений хранится в JSONB для гибкости и производительности.
Документы для RAG передаются через ARRAY[UUID] для быстрого доступа.
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.v1.users import UserModel
    from src.models.v1.workspaces import WorkspaceModel


class AIChatModel(BaseModel):
    """
    Модель AI чата с историей сообщений.

    Представляет чат пользователя с AI моделью через OpenRouter.
    Хранит историю сообщений в JSONB, привязанные документы для RAG,
    настройки модели (temperature, max_tokens) и метаданные.

    Attributes:
        chat_id: Уникальный readable идентификатор чата (user-friendly)
        user_id: UUID пользователя, создавшего чат
        workspace_id: UUID workspace (опционально)
        title: Название чата
        model_key: Ключ модели из OPENROUTER_CHAT_MODELS (qwen_coder/kimi_dev/...)
        document_service_ids: Массив UUID документов для RAG контекста
        messages: История сообщений в JSONB формате
        model_settings: Настройки модели (temperature, max_tokens, system_prompt)
        metadata: Дополнительные метаданные (tokens_used, estimated_cost)
        is_active: Активен ли чат
        user: Связь с UserModel (Many-to-One)
        workspace: Связь с WorkspaceModel (Many-to-One, опционально)

    Example:
        >>> chat = AIChatModel(
        ...     chat_id="chat-abc123",
        ...     user_id=user_id,
        ...     title="Code Review Assistant",
        ...     model_key="qwen_coder",
        ...     document_service_ids=[doc1_id, doc2_id],
        ...     messages=[
        ...         {"role": "system", "content": "You are a code reviewer"},
        ...         {"role": "user", "content": "Review this code"},
        ...         {"role": "assistant", "content": "Here's my review..."}
        ...     ],
        ...     model_settings={"temperature": 0.2, "max_tokens": 4000}
        ... )
    """

    __tablename__ = "ai_chats"

    chat_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Уникальный readable идентификатор чата",
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID пользователя, создавшего чат",
    )

    workspace_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="UUID workspace (опционально)",
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Название чата",
    )

    model_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Ключ модели из OPENROUTER_CHAT_MODELS",
    )

    document_service_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=False,
        default=list,
        comment="Массив UUID документов для RAG контекста",
    )

    messages: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="История сообщений в формате [{'role': str, 'content': str, 'message_metadata': dict, 'timestamp': str}]",
    )

    model_settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {"temperature": 0.7, "max_tokens": 4000},
        comment="Настройки модели (temperature, max_tokens, system_prompt)",
    )

    chat_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "tokens_used": 0,
            "messages_count": 0,
            "estimated_cost": 0.0,
            "rag_queries_count": 0,
        },
        comment="Метаданные чата (статистика использования)",
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Активен ли чат",
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="ai_chats",
        lazy="joined",
    )

    workspace: Mapped["WorkspaceModel | None"] = relationship(
        "WorkspaceModel",
        back_populates="ai_chats",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "char_length(chat_id) >= 5",
            name="check_chat_id_min_length",
        ),
        CheckConstraint(
            "char_length(title) >= 1",
            name="check_title_not_empty",
        ),
        CheckConstraint(
            "jsonb_array_length(messages) >= 0",
            name="check_messages_is_array",
        ),
        Index(
            "ix_ai_chats_user_active",
            "user_id",
            "is_active",
        ),
        Index(
            "ix_ai_chats_workspace_user",
            "workspace_id",
            "user_id",
        ),
        Index(
            "ix_ai_chats_model_key",
            "model_key",
        ),
    )

    def __repr__(self) -> str:
        """
        Строковое представление AIChatModel.

        Returns:
            str: Представление в формате AIChat(chat_id=..., title=..., model=...)
        """
        return (
            f"AIChat(chat_id='{self.chat_id}', title='{self.title[:30]}...', "
            f"model={self.model_key}, messages={len(self.messages)})"
        )
