"""
Скрипт для исправления file_size у существующих документов.

Проходит по всем документам с file_size = 0 и обновляет размер,
получая его из S3.
"""

import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import select, update

from src.core.connections.database import get_db_session
from src.core.connections.storage import S3ContextManager
from src.core.integrations.storages.base import BaseS3Storage
from src.core.settings.base import settings
from src.models.v1.document_services import DocumentServiceModel
# Добавляем корневую директорию проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def fix_document_sizes():
    """Исправить file_size для всех документов с нулевым размером."""
    logger.info("🔧 Начало исправления file_size для документов")

    # Создаём сессию базы данных через get_db_session
    async for session in get_db_session():
        # Получаем S3 клиент через контекстный менеджер
        async with S3ContextManager() as s3_client:
            storage = BaseS3Storage(s3_client)

            # Получаем все документы с file_size = 0
            query = select(DocumentServiceModel).where(
                DocumentServiceModel.file_size == 0
            )
            result = await session.execute(query)
            documents = result.scalars().all()

            logger.info(f"📊 Найдено {len(documents)} документов с file_size = 0")

            fixed_count = 0
            error_count = 0

            for doc in documents:
                try:
                    # Извлекаем ключ файла из URL
                    # Формат: https://storage.yandexcloud.net/bucket/documents/public/uuid_filename.pdf
                    file_url = doc.file_url
                    file_key = file_url.split(f"{settings.AWS_BUCKET_NAME}/", 1)[-1]

                    logger.info(f"🔍 Обработка документа {doc.id}: {doc.title}")
                    logger.info(f"   Файл: {file_key}")

                    # Получаем метаданные файла из S3
                    try:
                        response = await s3_client.head_object(
                            Bucket=settings.AWS_BUCKET_NAME,
                            Key=file_key
                        )
                        file_size = response.get("ContentLength", 0)

                        if file_size > 0:
                            # Обновляем file_size в базе
                            await session.execute(
                                update(DocumentServiceModel)
                                .where(DocumentServiceModel.id == doc.id)
                                .values(file_size=file_size)
                            )
                            await session.commit()

                            logger.info(
                                f"✅ Обновлён file_size для {doc.id}: {file_size} bytes "
                                f"({file_size / (1024 * 1024):.2f} MB)"
                            )
                            fixed_count += 1
                        else:
                            logger.warning(f"⚠️ file_size = 0 в S3 для {doc.id}")
                            error_count += 1

                    except Exception as e:
                        logger.error(f"❌ Ошибка получения файла из S3 для {doc.id}: {e}")
                        error_count += 1

                except Exception as e:
                    logger.error(f"❌ Ошибка обработки документа {doc.id}: {e}")
                    error_count += 1

            logger.info("=" * 60)
            logger.info(f"✅ Исправлено документов: {fixed_count}")
            logger.info(f"❌ Ошибок: {error_count}")
            logger.info(f"📊 Всего обработано: {len(documents)}")


if __name__ == "__main__":
    asyncio.run(fix_document_sizes())
