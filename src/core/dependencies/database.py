"""
Зависимости для работы с базой данных в FastAPI.
"""

import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.connections.database import get_db_session
from src.core.exceptions.dependencies import ServiceUnavailableException

logger = logging.getLogger("src.dependencies.database")


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для получения асинхронной сессии базы данных.

    Yields:
        AsyncSession: Асинхронная сессия SQLAlchemy

    Raises:
        ServiceUnavailableException: Если не удается подключиться к Postgres.
    """
    try:
        logger.debug("Создание сессии базы данных")
        async for session in get_db_session():
            yield session
    except RuntimeError as e:
        # Ловим только ошибки инициализации/подключения к базе
        logger.error("❌ Ошибка подключения к базе данных: %s", e)
        raise ServiceUnavailableException("Database (Postgres)")
    except Exception:
        # Все остальные ошибки (включая ValidationError) пробрасываем!
        raise


# Типизированная зависимость
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
