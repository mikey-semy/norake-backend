"""add_progress_percent_to_document_processing

Revision ID: 99067613cd7b
Revises: 96df3f33fc92
Create Date: 2025-11-15 18:39:58.436466

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '99067613cd7b'
down_revision: Union[str, Sequence[str], None] = '96df3f33fc92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем поле progress_percent для отслеживания прогресса RAG обработки
    op.add_column(
        'document_processing',
        sa.Column('progress_percent', sa.Integer(), nullable=True, server_default='0')
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем поле progress_percent
    op.drop_column('document_processing', 'progress_percent')
