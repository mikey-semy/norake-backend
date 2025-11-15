"""
Модуль интеграции с Ollama для генерации embeddings.

Модуль предоставляет класс для работы с локальным Ollama Docker контейнером:
- OllamaEmbeddings: Клиент для генерации embeddings через Ollama API

Ollama поддерживает модели: mxbai-embed-large (1024 dim), nomic-embed-text (768 dim).
"""

import logging
from typing import List

import httpx

from src.core.exceptions import ServiceUnavailableException
from src.core.integrations.ai.embeddings.base import BaseEmbeddings
from src.core.settings import settings

logger = logging.getLogger(__name__)


class OllamaEmbeddings(BaseEmbeddings):
    """
    Клиент для генерации embeddings через Ollama API.

    Класс предоставляет методы для генерации векторных представлений текста
    с использованием локальных embedding моделей через Ollama Docker контейнер.

    Attributes:
        model (str): Название embedding модели ("mxbai-embed-large" или "nomic-embed-text")
        base_url (str): Базовый URL Ollama API (по умолчанию http://ai.equiply.ru/ollama)
        api_key (str): API ключ для аутентификации (X-Api-Key header)
        timeout (int): Таймаут для HTTP запросов в секундах
        max_retries (int): Максимальное количество повторных попыток при ошибках

    Example:
        >>> async with OllamaEmbeddings() as embedder:
        ...     # Генерация embeddings для нескольких текстов
        ...     vectors = await embedder.embed(["text1", "text2"])
        ...
        ...     # Генерация embedding для одного запроса
        ...     vector = await embedder.embed_query("single text")

    Raises:
        ServiceUnavailableException: Если Ollama сервер недоступен
        ValueError: При некорректном формате ответа

    Note:
        Доступные модели в вашем Ollama:
        - mxbai-embed-large (669 MB, 1024 dimensions) - рекомендуется для качества
        - nomic-embed-text (274 MB, 768 dimensions) - компактная версия
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> None:
        """
        Инициализирует Ollama embeddings клиент.

        Args:
            base_url: Базовый URL Ollama API (если None - из settings.OLLAMA_EMBEDDINGS_BASE_URL)
            api_key: API ключ для аутентификации (если None - из settings.OLLAMA_EMBEDDINGS_API_KEY)
            model: Название модели (если None - из settings.OLLAMA_EMBEDDING_MODEL)
            timeout: Таймаут для HTTP запросов в секундах
            max_retries: Максимальное количество повторных попыток при ошибках

        Raises:
            ValueError: Если не указан API ключ или base_url
        """
        base_url = base_url or settings.OLLAMA_EMBEDDINGS_BASE_URL
        api_key = api_key or settings.OLLAMA_EMBEDDINGS_API_KEY
        model = model or settings.OLLAMA_EMBEDDING_MODEL

        if not api_key:
            raise ValueError(
                "OLLAMA_EMBEDDINGS_API_KEY должен быть указан в настройках или параметрах"
            )

        if not base_url:
            raise ValueError(
                "OLLAMA_EMBEDDINGS_BASE_URL должен быть указан в настройках или параметрах"
            )

        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )

        logger.info(
            "Инициализирован Ollama embeddings клиент: model=%s, base_url=%s",
            self.model,
            self.base_url,
        )

    def _get_headers(self) -> dict[str, str]:
        """
        Возвращает HTTP заголовки с X-Api-Key для Ollama.

        Returns:
            dict[str, str]: Словарь с HTTP заголовками

        Note:
            Ollama использует X-Api-Key вместо стандартного Authorization Bearer.
        """
        return {
            "X-Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Генерирует embeddings для списка текстов.

        Args:
            texts: Список текстов для генерации embeddings

        Returns:
            Список векторов (embeddings) для каждого текста

        Raises:
            ServiceUnavailableException: Если Ollama сервер недоступен
            ValueError: При некорректном формате ответа от API

        Example:
            >>> async with OllamaEmbeddings() as embedder:
            ...     vectors = await embedder.embed(["первый текст", "второй текст"])
            ...     print(f"Получено {len(vectors)} векторов размерности {len(vectors[0])}")
        """
        if not texts:
            return []

        logger.debug("Генерация embeddings для %d текстов через Ollama", len(texts))

        try:
            # Ollama embeddings API: POST /api/embeddings
            # Обрабатываем каждый текст отдельно (Ollama не поддерживает batch)
            embeddings = []
            client = self._get_client()

            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

                if "embedding" not in data:
                    raise ValueError(
                        f"Некорректный формат ответа от Ollama: {data}"
                    )

                embeddings.append(data["embedding"])

            logger.info(
                "Успешно сгенерировано %d embeddings через Ollama (model=%s)",
                len(embeddings),
                self.model,
            )
            return embeddings

        except httpx.HTTPStatusError as e:
            logger.error(
                "Ошибка Ollama API [%d]: %s",
                e.response.status_code,
                e.response.text,
            )
            raise ServiceUnavailableException(
                f"Ollama API вернул ошибку {e.response.status_code}"
            ) from e

        except httpx.RequestError as e:
            logger.error("Ошибка подключения к Ollama: %s", str(e))
            raise ServiceUnavailableException(
                "Не удалось подключиться к Ollama сервису"
            ) from e

        except Exception as e:
            logger.error("Неожиданная ошибка при генерации embeddings: %s", str(e))
            raise

    async def embed_query(self, text: str) -> List[float]:
        """
        Генерирует embedding для одного текста (оптимизированная версия).

        Args:
            text: Текст для генерации embedding

        Returns:
            Вектор (embedding) для текста

        Raises:
            ServiceUnavailableException: Если Ollama сервер недоступен
            ValueError: При некорректном формате ответа от API

        Example:
            >>> async with OllamaEmbeddings() as embedder:
            ...     vector = await embedder.embed_query("поисковый запрос")
            ...     print(f"Получен вектор размерности {len(vector)}")
        """
        embeddings = await self.embed([text])
        return embeddings[0]

    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Генерирует embeddings для списка документов (алиас для embed).

        Args:
            documents: Список документов для генерации embeddings

        Returns:
            Список векторов (embeddings) для каждого документа

        Example:
            >>> async with OllamaEmbeddings() as embedder:
            ...     vectors = await embedder.embed_documents(["doc1", "doc2"])
        """
        return await self.embed(documents)

    async def check_health(self) -> bool:
        """
        Проверяет доступность Ollama сервиса.

        Returns:
            True если сервис доступен, False иначе

        Example:
            >>> async with OllamaEmbeddings() as embedder:
            ...     if await embedder.check_health():
            ...         print("Ollama сервис доступен")
        """
        try:
            client = self._get_client()
            response = await client.get(
                f"{self.base_url}/api/tags", headers=self._get_headers()
            )
            response.raise_for_status()
            logger.info("Ollama сервис доступен: %s", self.base_url)
            return True
        except Exception as e:
            logger.warning("Ollama сервис недоступен: %s", str(e))
            return False

    def get_dimensions(self) -> int:
        """
        Возвращает размерность векторов для текущей модели.

        Returns:
            Размерность embedding вектора

        Example:
            >>> embedder = OllamaEmbeddings()
            >>> dims = embedder.get_dimensions()  # 1024 для mxbai-embed-large
        """
        # Известные размерности для Ollama моделей
        dimensions_map = {
            "mxbai-embed-large": 1024,
            "nomic-embed-text": 768,
        }
        return dimensions_map.get(self.model, settings.OLLAMA_EMBEDDING_DIMENSIONS)
