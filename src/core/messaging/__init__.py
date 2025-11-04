"""
Модуль для работы с системой сообщений.

Содержит обработчики событий RabbitMQ и интеграцию с FastStream.
"""
import logging
from fastapi import FastAPI

# Импортируем обработчики, чтобы они зарегистрировались
from . import handlers

from .handlers import rabbit_router

logger = logging.getLogger(__name__)

def setup_messaging(app: FastAPI):
    """
    Настраивает маршрутизатор RabbitMQ в приложении FastAPI.

    Args:
        app (FastAPI): Экземпляр приложения FastAPI.

    Returns:
        None
    """
    app.include_router(rabbit_router)
