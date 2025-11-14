"""
Скрипт для проверки file_size всех документов в базе.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from src.core.connections.database import get_db_session
from src.models.v1.document_services import DocumentServiceModel

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def check_document_sizes():
    """Проверить file_size всех документов."""
    logger.info("🔍 Проверка file_size всех документов")

    async for session in get_db_session():
        # Получаем все документы
        query = select(DocumentServiceModel)
        result = await session.execute(query)
        documents = result.scalars().all()

        logger.info(f"📊 Найдено {len(documents)} документов")
        logger.info("=" * 80)

        zero_count = 0
        non_zero_count = 0

        for doc in documents:
            size_mb = doc.file_size / (1024 * 1024) if doc.file_size > 0 else 0
            status = "✅" if doc.file_size > 0 else "❌"

            logger.info(f"{status} {doc.id} | {doc.title[:50]:50s} | {size_mb:8.2f} MB | {doc.file_size:,} bytes")

            if doc.file_size == 0:
                zero_count += 1
            else:
                non_zero_count += 1

        logger.info("=" * 80)
        logger.info(f"✅ Документов с file_size > 0: {non_zero_count}")
        logger.info(f"❌ Документов с file_size = 0: {zero_count}")


if __name__ == "__main__":
    asyncio.run(check_document_sizes())
