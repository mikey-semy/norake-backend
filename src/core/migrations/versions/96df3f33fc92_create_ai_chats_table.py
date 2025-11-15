"""create_ai_chats_table

Создание таблицы ai_chats для хранения AI чатов с OpenRouter.

Таблица содержит:
- chat_id: readable идентификатор чата
- user_id, workspace_id: привязка к пользователю и workspace
- model_key: ключ модели из OPENROUTER_CHAT_MODELS
- document_service_ids: ARRAY UUID документов для RAG
- messages: JSONB история сообщений
- model_settings: JSONB настройки модели (temperature, max_tokens)
- metadata: JSONB статистика использования

Revision ID: 96df3f33fc92
Revises: 0cb578fc6b00
Create Date: 2025-11-15 15:28:37.744940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '96df3f33fc92'
down_revision: Union[str, Sequence[str], None] = '0cb578fc6b00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создание таблицы ai_chats."""
    op.create_table(
        'ai_chats',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='UUID чата'),
        sa.Column(
            'chat_id',
            sa.String(100),
            nullable=False,
            unique=True,
            comment='Уникальный readable идентификатор чата',
        ),
        sa.Column(
            'user_id',
            UUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
            comment='UUID пользователя, создавшего чат',
        ),
        sa.Column(
            'workspace_id',
            UUID(as_uuid=True),
            sa.ForeignKey('workspaces.id', ondelete='SET NULL'),
            nullable=True,
            comment='UUID workspace (опционально)',
        ),
        sa.Column(
            'title',
            sa.String(500),
            nullable=False,
            comment='Название чата',
        ),
        sa.Column(
            'model_key',
            sa.String(50),
            nullable=False,
            comment='Ключ модели из OPENROUTER_CHAT_MODELS',
        ),
        sa.Column(
            'document_service_ids',
            ARRAY(UUID(as_uuid=True)),
            nullable=False,
            server_default='{}',
            comment='Массив UUID документов для RAG контекста',
        ),
        sa.Column(
            'messages',
            JSONB,
            nullable=False,
            server_default='[]',
            comment='История сообщений в формате JSONB',
        ),
        sa.Column(
            'model_settings',
            JSONB,
            nullable=False,
            server_default='{"temperature": 0.7, "max_tokens": 4000}',
            comment='Настройки модели (temperature, max_tokens)',
        ),
        sa.Column(
            'metadata',
            JSONB,
            nullable=False,
            server_default='{"tokens_used": 0, "messages_count": 0, "estimated_cost": 0.0, "rag_queries_count": 0}',
            comment='Метаданные чата (статистика использования)',
        ),
        sa.Column(
            'is_active',
            sa.Boolean,
            nullable=False,
            server_default='true',
            comment='Активен ли чат',
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='Дата создания',
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            onupdate=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
            comment='Дата обновления',
        ),
    )

    # Indexes
    op.create_index('ix_ai_chats_chat_id', 'ai_chats', ['chat_id'])
    op.create_index('ix_ai_chats_user_id', 'ai_chats', ['user_id'])
    op.create_index('ix_ai_chats_workspace_id', 'ai_chats', ['workspace_id'])
    op.create_index('ix_ai_chats_model_key', 'ai_chats', ['model_key'])
    op.create_index('ix_ai_chats_user_active', 'ai_chats', ['user_id', 'is_active'])
    op.create_index('ix_ai_chats_workspace_user', 'ai_chats', ['workspace_id', 'user_id'])

    # Constraints
    op.create_check_constraint(
        'check_chat_id_min_length',
        'ai_chats',
        'char_length(chat_id) >= 5',
    )
    op.create_check_constraint(
        'check_title_not_empty',
        'ai_chats',
        'char_length(title) >= 1',
    )
    op.create_check_constraint(
        'check_messages_is_array',
        'ai_chats',
        'jsonb_array_length(messages) >= 0',
    )


def downgrade() -> None:
    """Удаление таблицы ai_chats."""
    op.drop_table('ai_chats')
