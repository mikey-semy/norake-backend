"""
Базовый модуль для embeddings.

Модуль определяет абстрактный базовый класс для всех embeddings клиентов:
- BaseEmbeddings: Абстрактный базовый класс для генерации векторных представлений текста

Этот класс обеспечивает единый интерфейс для работы с различными embeddings провайдерами.
"""

from abc import ABC, abstractmethod
from typing import List

from src.core.integrations.ai.base import BaseAIClient


class BaseEmbeddings(BaseAIClient, ABC):
    """
    Базовый класс для всех embeddings клиентов.

    Абстрактный базовый класс, определяющий интерфейс для генерации embeddings.
    Наследует BaseAIClient для HTTP функциональности и добавляет методы для embeddings.

    Attributes:
        model (str): Название embedding модели
        base_url (str): Базовый URL API провайдера (от BaseAIClient)
        api_key (str): API ключ для аутентификации (от BaseAIClient)
        timeout (int): Таймаут для HTTP запросов (от BaseAIClient)
        max_retries (int): Максимальное количество повторных попыток (от BaseAIClient)

    Example:
        >>> class CustomEmbeddings(BaseEmbeddings):
        ...     async def embed(self, texts: List[str]) -> List[List[float]]:
        ...         # Реализация метода
        ...         pass
        ...
        >>> async with CustomEmbeddings(api_key="sk-xxx", model="model-name") as embedder:
        ...     vectors = await embedder.embed(["text1", "text2"])
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Инициализирует базовый embeddings клиент.

        Args:
            base_url: Базовый URL API провайдера
            api_key: API ключ для аутентификации
            model: Название embedding модели
            timeout: Таймаут для HTTP запросов в секундах (по умолчанию 30)
            max_retries: Максимальное количество повторных попыток (по умолчанию 3)
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.model = model

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Генерирует embeddings для списка текстов (абстрактный метод).

        Args:
            texts: Список текстов для генерации embeddings

        Returns:
            List[List[float]]: Список векторных представлений для каждого текста

        Raises:
            NotImplementedError: Когда метод не реализован в подклассе

        Note:
            Подклассы должны реализовать этот метод для генерации embeddings.
        """
        pass

    async def embed_query(self, text: str) -> List[float]:
        """
        Генерирует embedding для одного текста (query).

        Args:
            text: Текст для генерации embedding

        Returns:
            List[float]: Векторное представление текста

        Note:
            Базовая реализация использует метод embed().
            Переопределите для оптимизации одиночных запросов.
        """
        embeddings = await self.embed([text])
        return embeddings[0]
