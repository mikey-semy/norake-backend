"""add_chat_metadata_to_ai_chats

Revision ID: 97d458ecce5a
Revises: 99067613cd7b
Create Date: 2025-11-15 19:02:24.661902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97d458ecce5a'
down_revision: Union[str, Sequence[str], None] = '99067613cd7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле chat_metadata в таблицу ai_chats
    op.add_column(
        'ai_chats',
        sa.Column(
            'chat_metadata',
            sa.dialects.postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default=sa.text("'{\"tokens_used\": 0, \"messages_count\": 0, \"estimated_cost\": 0.0, \"rag_queries_count\": 0}'::jsonb"),
            comment='Метаданные чата (статистика использования)',
        )
    )

    # Обновляем существующие записи
    op.execute("""
        UPDATE ai_chats
        SET chat_metadata = '{"tokens_used": 0, "messages_count": 0, "estimated_cost": 0.0, "rag_queries_count": 0}'::jsonb
        WHERE chat_metadata IS NULL
    """)

    # Делаем поле NOT NULL после заполнения
    op.alter_column(
        'ai_chats',
        'chat_metadata',
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ai_chats', 'chat_metadata')
