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
    session = None
    session_gen = None
    
    try:
        logger.debug("Создание сессии базы данных")
        session_gen = get_db_session()
        session = await session_gen.__anext__()
        
        try:
            yield session
        except GeneratorExit:
            # Нормальное завершение генератора
            pass
        except Exception:
            # Исключение из downstream кода - пробрасываем дальше
            raise
        finally:
            # Всегда закрываем сессию
            try:
                await session_gen.__anext__()
            except StopAsyncIteration:
                pass
                
    except RuntimeError as e:
        # Ловим только ошибки инициализации/подключения к базе
        logger.error("Ошибка подключения к базе данных: %s", e)
        raise ServiceUnavailableException("Database (Postgres)")


# Типизированная зависимость
AsyncSessionDep = Annotated[AsyncSession, Depends(get_async_session)]
