"""
Зависимости для работы с S3/MinIO хранилищем в FastAPI.
"""

import logging
from typing import Annotated, Any, AsyncGenerator

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
        logger.error("Ошибка подключения к S3: %s", e)
        raise ServiceUnavailableException("Storage (S3/MinIO)") from e


# Типизированная зависимость для использования в роутерах и сервисах
S3ClientDep = Annotated[Any, Depends(get_s3_client)]
