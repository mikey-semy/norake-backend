"""add_doc_docx_txt_md_to_file_types

Revision ID: b4f3c8a2d1e9
Revises: 9acb61d0983f
Create Date: 2025-11-14 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b4f3c8a2d1e9'
down_revision: Union[str, Sequence[str], None] = '9acb61d0983f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Добавляет новые типы файлов в enum DocumentFileType.
    
    Расширяет существующий enum 'documentfiletype' новыми значениями:
    - 'doc' - Microsoft Word (.doc)
    - 'docx' - Microsoft Word (.docx)
    - 'txt' - Plain text (.txt)
    - 'md' - Markdown (.md)
    """
    # Для PostgreSQL нужно использовать ALTER TYPE ... ADD VALUE
    # Каждое значение добавляется отдельной командой
    op.execute("ALTER TYPE documentfiletype ADD VALUE IF NOT EXISTS 'doc'")
    op.execute("ALTER TYPE documentfiletype ADD VALUE IF NOT EXISTS 'docx'")
    op.execute("ALTER TYPE documentfiletype ADD VALUE IF NOT EXISTS 'txt'")
    op.execute("ALTER TYPE documentfiletype ADD VALUE IF NOT EXISTS 'md'")


def downgrade() -> None:
    """
    Откат миграции невозможен для PostgreSQL enum.
    
    PostgreSQL не поддерживает удаление значений из enum типа.
    Если необходим откат, нужно пересоздать тип с нуля.
    """
    # PostgreSQL не позволяет удалять значения из enum
    # Для отката нужно пересоздавать таблицу и тип
    pass
