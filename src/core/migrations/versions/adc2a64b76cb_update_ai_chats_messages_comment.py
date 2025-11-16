"""update_ai_chats_messages_comment

Revision ID: adc2a64b76cb
Revises: 97d458ecce5a
Create Date: 2025-11-16 06:23:51.705309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'adc2a64b76cb'
down_revision: Union[str, Sequence[str], None] = '97d458ecce5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: обновляет комментарий поля messages в ai_chats."""
    op.execute("""
        COMMENT ON COLUMN ai_chats.messages IS
        'История сообщений в формате [{''role'': str, ''content'': str, ''message_metadata'': dict, ''timestamp'': str}]'
    """)


def downgrade() -> None:
    """Downgrade schema: восстанавливает старый комментарий."""
    op.execute("""
        COMMENT ON COLUMN ai_chats.messages IS
        'История сообщений в формате [{''role'': str, ''content'': str, ''metadata'': dict, ''timestamp'': str}]'
    """)
