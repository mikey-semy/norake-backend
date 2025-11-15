from typing import AsyncGenerator, Any, Annotated

import logging
from fastapi import Depends

from src.core.connections.storage import S3ContextManager
from src.core.exceptions.dependencies import ServiceUnavailableException

logger = logging.getLogger("src.dependencies.storage")


async def get_s3_client() -> AsyncGenerator[Any, None]:
    """
    Dependency для получения S3 клиента через контекстный менеджер.

    Yields:
        Any: aioboto3 S3 client (initialized via context manager)

    Raises:
        ServiceUnavailableException: если не удаётся подключиться к S3
        BaseAPIException: пробрасывает бизнес-исключения без изменений
    """
    try:
        logger.debug("Создание подключения к S3 через контекстный менеджер")
        async with S3ContextManager() as s3:
            logger.debug("S3 подключение успешно установлено")
            yield s3
    except ServiceUnavailableException:
        # Пробрасываем 503 без изменений
        raise
    except Exception as e:
        logger.error("❌ Ошибка подключения к S3: %s", str(e))
        raise ServiceUnavailableException("Storage (S3)") from e


# Типизированная зависимость (для использования в роутерах)
S3ClientDep = Annotated[Any, Depends(get_s3_client)]
