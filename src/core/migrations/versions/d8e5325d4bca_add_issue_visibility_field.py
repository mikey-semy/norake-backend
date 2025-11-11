"""add_issue_visibility_field

Revision ID: d8e5325d4bca
Revises: e4782245b314
Create Date: 2025-11-11 15:59:11.193964

Добавляет поле visibility в таблицу issues для управления видимостью проблем:
- PUBLIC: доступно всем без аутентификации
- WORKSPACE: видно только участникам воркспейса
- PRIVATE: видно только автору и админам

Миграция создаёт enum type и добавляет столбец с default='public' и backfill
существующих записей.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8e5325d4bca'
down_revision: Union[str, Sequence[str], None] = 'e4782245b314'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.
    
    Добавляет enum тип issue_visibility и столбец visibility в таблицу issues.
    Все существующие записи получают значение 'public' по умолчанию.
    """
    # Создаём enum тип для visibility
    issue_visibility_enum = sa.Enum(
        'public', 'workspace', 'private',
        name='issue_visibility',
        create_type=True
    )
    issue_visibility_enum.create(op.get_bind(), checkfirst=True)
    
    # Добавляем столбец visibility с default='public'
    op.add_column(
        'issues',
        sa.Column(
            'visibility',
            sa.Enum('public', 'workspace', 'private', name='issue_visibility'),
            nullable=False,
            server_default='public',
        )
    )
    
    # Создаём индекс для быстрой фильтрации по visibility
    op.create_index(
        'ix_issues_visibility',
        'issues',
        ['visibility'],
        unique=False
    )
    
    # Backfill: обновляем все NULL значения на 'public' (на всякий случай)
    op.execute("UPDATE issues SET visibility = 'public' WHERE visibility IS NULL")


def downgrade() -> None:
    """
    Downgrade schema.
    
    Удаляет столбец visibility и enum тип issue_visibility.
    """
    # Удаляем индекс
    op.drop_index('ix_issues_visibility', table_name='issues')
    
    # Удаляем столбец
    op.drop_column('issues', 'visibility')
    
    # Удаляем enum тип
    sa.Enum(name='issue_visibility').drop(op.get_bind(), checkfirst=True)
