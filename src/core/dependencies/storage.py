"""
Зависимости для работы с S3/MinIO хранилищем в FastAPI.
"""

import logging
from typing import Annotated, Any, AsyncGenerator, Optional

from fastapi import Depends

from src.core.connections.storage import S3ContextManager
from src.core.exceptions.dependencies import ServiceUnavailableException

logger = logging.getLogger("src.dependencies.storage")


async def get_s3_client() -> AsyncGenerator[Any, None]:
    """
    Зависимость для получения S3 клиента через контекстный менеджер.

    Yields:
        Any: aioboto3 S3 client (initialized via context manager)

    Raises:
        ServiceUnavailableException: Если не удаётся подключиться к S3/MinIO
    """
    try:
        logger.debug("Создание подключения к S3 через контекстный менеджер")
        async with S3ContextManager() as s3:
            logger.debug("S3 подключение успешно установлено")
            yield s3
    except Exception as e:
        logger.error("❌ Ошибка подключения к S3: %s", e)
        raise ServiceUnavailableException("Storage (S3/MinIO)") from e


async def get_s3_client_optional() -> AsyncGenerator[Optional[Any], None]:
    """
    Опциональная зависимость для получения S3 клиента.

    Возвращает None если credentials не заданы, вместо исключения.
    Используется когда S3 не обязателен для работы сервиса.

    Yields:
        Optional[Any]: aioboto3 S3 client или None если подключение невозможно
    """
    try:
        logger.debug("Попытка создания подключения к S3 (optional)")
        async with S3ContextManager() as s3:
            logger.debug("S3 подключение успешно установлено")
            yield s3
    except ValueError as e:
        # Credentials не заданы - это OK для опционального клиента
        logger.info("✨ S3 клиент недоступен (credentials не заданы): %s", e)
        yield None
    except Exception as e:
        # Другие ошибки подключения также логируем, но не падаем
        logger.warning("⚠️  S3 клиент недоступен: %s", e)
        yield None


# Типизированная зависимость для использования в роутерах и сервисах
S3ClientDep = Annotated[Any, Depends(get_s3_client)]
S3ClientOptionalDep = Annotated[Optional[Any], Depends(get_s3_client_optional)]
