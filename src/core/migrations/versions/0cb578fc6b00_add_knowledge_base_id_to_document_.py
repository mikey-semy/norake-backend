"""add_knowledge_base_id_to_document_services

Revision ID: 0cb578fc6b00
Revises: f72872285c60
Create Date: 2025-11-15 15:01:40.268380

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '0cb578fc6b00'
down_revision: Union[str, Sequence[str], None] = 'f72872285c60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Добавить knowledge_base_id FK в document_services для связи с KnowledgeBase.

    Этот FK позволяет активировать RAG функцию для DocumentService,
    связывая документ с базой знаний и её векторным хранилищем.
    """
    op.add_column(
        'document_services',
        sa.Column(
            'knowledge_base_id',
            UUID(as_uuid=True),
            sa.ForeignKey('knowledge_bases.id', ondelete='SET NULL'),
            nullable=True,
            comment='ID базы знаний для RAG функции'
        )
    )
    op.create_index(
        'ix_document_services_knowledge_base_id',
        'document_services',
        ['knowledge_base_id'],
    )


def downgrade() -> None:
    """Удалить knowledge_base_id FK из document_services."""
    op.drop_index('ix_document_services_knowledge_base_id', table_name='document_services')
    op.drop_column('document_services', 'knowledge_base_id')
