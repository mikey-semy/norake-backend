"""
Загрузка фикстур document_services из JSON файла.

Простой скрипт для импорта мануалов в базу данных.
"""

import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.connections.database import get_db_session
from src.models.v1.document_services import DocumentServiceModel
from src.models.v1.users import UserModel
from src.repository.v1.document_services import DocumentServiceRepository

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def load_fixtures(fixture_file: str = "document_services_manuals.json"):
    """
    Загружает document_services из JSON файла в базу данных.
    
    Args:
        fixture_file: Имя файла с фикстурами в fixtures_data/
    """
    logger.info("🔄 Начинаем загрузку фикстур document_services...")
    
    # Путь к фикстуре
    fixtures_path = Path(__file__).parent.parent / "fixtures_data" / fixture_file
    
    if not fixtures_path.exists():
        logger.error("❌ Файл фикстуры не найден: %s", fixtures_path)
        return
    
    # Читаем JSON
    with open(fixtures_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get("metadata", {})
    items = data.get("data", [])
    
    logger.info("📦 Найдено документов: %d", len(items))
    logger.info("📝 Описание: %s", metadata.get("description", ""))
    
    # Получаем сессию БД
    async for session in get_db_session():
        # Получаем admin пользователя для author_id
        admin_result = await session.execute(
            select(UserModel).where(UserModel.email == "admin@equiply.ru")
        )
        admin_user = admin_result.scalar_one_or_none()
        
        if not admin_user:
            logger.error("❌ Не найден админ пользователь admin@equiply.ru!")
            return
        
        logger.info("👤 Используем автора: %s (ID: %s)", admin_user.username, admin_user.id)
        
        repository = DocumentServiceRepository(session=session)
        
        created = 0
        skipped = 0
        
        for item in items:
            title = item.get("title")
            file_url = item.get("file_url")
            
            # Проверяем существование по file_url (уникальный идентификатор)
            existing = await session.execute(
                select(DocumentServiceModel).where(
                    DocumentServiceModel.file_url == file_url
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                logger.debug("⏭️ Уже существует: %s", title)
                continue
            
            # Создаём новый document
            try:
                new_doc = DocumentServiceModel(
                    title=title,
                    description=item.get("description"),
                    tags=item.get("tags", []),
                    file_url=file_url,
                    file_size=item.get("file_size", 0),  # 0 если не указан
                    file_type=item.get("file_type", "pdf"),
                    cover_type=item.get("cover_type", "generated"),
                    is_public=item.get("is_public", True),
                    author_id=admin_user.id,  # Используем админа
                    workspace_id=item.get("workspace_id")  # None если не указан
                )
                session.add(new_doc)
                await session.commit()
                created += 1
                logger.info("✅ Создан: %s", title)
            except Exception as e:
                logger.error("❌ Ошибка при создании '%s': %s", title, e)
                await session.rollback()
        
        logger.info("=" * 60)
        logger.info("📊 Статистика загрузки:")
        logger.info("   ✅ Создано: %d", created)
        logger.info("   ⏭️ Пропущено (уже существует): %d", skipped)
        logger.info("=" * 60)
        
        break  # Используем только первую сессию


if __name__ == "__main__":
    asyncio.run(load_fixtures())
