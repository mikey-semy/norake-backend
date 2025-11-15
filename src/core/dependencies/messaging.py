"""
Зависимости для работы с системой обмена сообщениями в FastAPI.
"""
import logging
from typing import Annotated, AsyncGenerator

from fastapi import Depends
from aio_pika.abc import AbstractRobustConnection

from src.core.connections.messaging import RabbitMQClient, RabbitMQContextManager
from src.core.dependencies.base import BaseDependency
from src.core.exceptions.base import BaseAPIException
from src.core.exceptions.dependencies import ServiceUnavailableException

logger = logging.getLogger("src.dependencies.messaging")


class MessagingDependency(BaseDependency):
    """
    Зависимость для работы с системой обмена сообщениями.
    
    Наследует BaseDependency и предоставляет методы для получения
    подключений к RabbitMQ с обработкой ошибок.
    """
    
    def __init__(self) -> None:
        super().__init__()
        self._client = RabbitMQClient()
    
    async def get_dependency(self) -> AbstractRobustConnection:
        """
        Получает подключение к RabbitMQ.
        
        Returns:
            AbstractRobustConnection: Подключение к RabbitMQ
            
        Raises:
            ServiceUnavailableException: Если не удается подключиться к RabbitMQ
        """
        try:
            self.logger.debug("Получение подключения к RabbitMQ")
            return await self._client.connect()
        except Exception as e:
            await self.handle_exception(e, "RabbitMQ")


async def get_rabbitmq_connection() -> AsyncGenerator[AbstractRobustConnection, None]:
    """
    Зависимость для получения подключения к RabbitMQ.

    Yields:
        AbstractRobustConnection: Подключение к RabbitMQ

    Raises:
        ServiceUnavailableException: Если не удается подключиться к RabbitMQ.
        BaseAPIException: Пробрасывает бизнес-исключения без изменений.
    """
    dependency = MessagingDependency()
    try:
        logger.debug("Создание подключения к RabbitMQ")
        connection = await dependency.get_dependency()
        yield connection
    except BaseAPIException:
        # Пробрасываем бизнес-исключения (например, OpenRouterAPIError 429)
        raise
    except Exception as e:
        logger.error("Ошибка подключения к RabbitMQ: %s", e)
        raise ServiceUnavailableException("Messaging (RabbitMQ)")


async def get_rabbitmq_context() -> AsyncGenerator[AbstractRobustConnection, None]:
    """
    Зависимость для получения подключения к RabbitMQ через контекстный менеджер.

    Yields:
        AbstractRobustConnection: Подключение к RabbitMQ

    Raises:
        ServiceUnavailableException: Если не удается подключиться к RabbitMQ.
        BaseAPIException: Пробрасывает бизнес-исключения без изменений.
    """
    try:
        logger.debug("Создание подключения к RabbitMQ через контекстный менеджер")
        async with RabbitMQContextManager() as connection:
            yield connection
    except BaseAPIException:
        # Пробрасываем бизнес-исключения (например, OpenRouterAPIError 429)
        raise
    except Exception as e:
        logger.error("Ошибка подключения к RabbitMQ через контекстный менеджер: %s", e)
        raise ServiceUnavailableException("Messaging (RabbitMQ)")


# Типизированные зависимости
RabbitMQConnectionDep = Annotated[AbstractRobustConnection, Depends(get_rabbitmq_connection)]
RabbitMQContextDep = Annotated[AbstractRobustConnection, Depends(get_rabbitmq_context)]
