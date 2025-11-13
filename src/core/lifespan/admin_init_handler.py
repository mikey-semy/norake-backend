"""
Обработчик инициализации дефолтного администратора.

Автоматически создаёт дефолтного админа из ENV переменных при первом запуске.
"""
from fastapi import FastAPI

from src.core.connections.database import DatabaseContextManager
from src.core.lifespan.base import register_startup_handler
from src.services.v1.admin_init import AdminInitService


@register_startup_handler
async def initialize_default_admin(app: FastAPI):  # noqa: ARG001
    """
    Создаёт дефолтного администратора из настроек при старте приложения.

    Вызывается автоматически через lifespan manager.
    Если админ уже существует - пропускается.

    ВАЖНО: Использует DatabaseContextManager для избежания circular import!

    Args:
        app (FastAPI): Экземпляр FastAPI приложения
    """
    # Используем DatabaseContextManager напрямую (не через dependency!)
    db_manager = DatabaseContextManager()

    try:
        session = await db_manager.connect()

        # Создаём сервис инициализации
        admin_init_service = AdminInitService(session=session)

        # Пытаемся создать дефолтного админа
        await admin_init_service.create_default_admin_if_not_exists()

        # ВАЖНО: Фиксируем изменения в БД
        await db_manager.commit()

    finally:
        # Закрываем сессию
        await db_manager.close()

