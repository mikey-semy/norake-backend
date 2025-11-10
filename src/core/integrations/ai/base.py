"""
Базовый модуль для AI интеграций.

Модуль определяет абстрактный базовый класс для всех AI клиентов в приложении:
- BaseAIClient: Абстрактный базовый класс для реализации AI клиентов

Этот класс обеспечивает единый интерфейс для работы с различными AI провайдерами.
"""

import logging
from abc import ABC
from typing import Optional

import httpx


class BaseAIClient(ABC):
    """
    Базовый класс для всех AI клиентов.

    Абстрактный базовый класс, определяющий интерфейс для AI клиентов.
    Предоставляет базовую функциональность для HTTP запросов, логирования и управления клиентом.

    Attributes:
        base_url (str): Базовый URL API провайдера
        api_key (str): API ключ для аутентификации
        timeout (int): Таймаут для HTTP запросов в секундах
        max_retries (int): Максимальное количество повторных попыток при ошибках
        _client (Optional[httpx.AsyncClient]): HTTP клиент для выполнения запросов
        logger (logging.Logger): Логгер для класса AI клиента

    Example:
        >>> class CustomAIClient(BaseAIClient):
        ...     async def custom_method(self):
        ...         # Реализация метода
        ...         pass
        ...
        >>> async with CustomAIClient(api_key="sk-xxx") as client:
        ...     result = await client.custom_method()
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Инициализирует базовый AI клиент.

        Args:
            base_url: Базовый URL API провайдера
            api_key: API ключ для аутентификации
            timeout: Таймаут для HTTP запросов в секундах (по умолчанию 30)
            max_retries: Максимальное количество повторных попыток (по умолчанию 3)
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_headers(self) -> dict[str, str]:
        """
        Возвращает базовые HTTP заголовки для запросов.

        Returns:
            dict[str, str]: Словарь с HTTP заголовками

        Note:
            Включает Authorization и Content-Type по умолчанию.
            Переопределите метод для добавления кастомных заголовков.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.AsyncClient:
        """
        Возвращает или создает HTTP клиент.

        Returns:
            httpx.AsyncClient: Асинхронный HTTP клиент для выполнения запросов

        Note:
            Создает новый клиент при первом обращении (lazy initialization).
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """
        Закрывает HTTP клиент и освобождает ресурсы.

        Note:
            Метод должен вызываться после завершения работы с клиентом.
            При использовании context manager вызывается автоматически.
        """
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            self.logger.debug("HTTP клиент закрыт")

    async def __aenter__(self) -> "BaseAIClient":
        """
        Асинхронный вход в контекстный менеджер.

        Returns:
            BaseAIClient: Экземпляр AI клиента

        Example:
            >>> async with client:
            ...     result = await client.some_method()
        """
        self.logger.debug("Вход в контекстный менеджер AI клиента")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Асинхронный выход из контекстного менеджера.

        Args:
            exc_type: Тип исключения (если возникло)
            exc_val: Значение исключения (если возникло)
            exc_tb: Traceback исключения (если возникло)

        Note:
            Автоматически закрывает HTTP клиент при выходе из контекста.
        """
        await self.close()
        self.logger.debug("Выход из контекстного менеджера AI клиента")
