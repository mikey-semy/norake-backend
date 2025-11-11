"""add_workspace_id_to_issues

Revision ID: e4782245b314
Revises: ba18f87e5afd
Create Date: 2025-11-11 04:59:43.715017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4782245b314'
down_revision: Union[str, Sequence[str], None] = 'ba18f87e5afd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add workspace_id column to issues table
    op.add_column(
        'issues',
        sa.Column('workspace_id', sa.UUID(), nullable=True)
    )

    # Create foreign key constraint
    op.create_foreign_key(
        'fk_issues_workspace_id',
        'issues',
        'workspaces',
        ['workspace_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Create index for better query performance
    op.create_index(
        'ix_issues_workspace_id',
        'issues',
        ['workspace_id']
    )

    # Make workspace_id NOT NULL after data migration (if needed)
    # Note: В реальном сценарии нужно сначала заполнить workspace_id для существующих Issues
    # Для демо/dev окружения можем сразу сделать NOT NULL если нет данных
    op.alter_column(
        'issues',
        'workspace_id',
        nullable=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('ix_issues_workspace_id', table_name='issues')

    # Drop foreign key
    op.drop_constraint('fk_issues_workspace_id', 'issues', type_='foreignkey')

    # Drop column
    op.drop_column('issues', 'workspace_id')
