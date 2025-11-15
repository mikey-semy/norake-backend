"""
Модуль интеграции с OpenRouter AI для генерации embeddings.

Модуль предоставляет класс для работы с OpenRouter API для генерации векторных представлений текста:
- OpenRouterEmbeddings: Клиент для генерации embeddings через OpenRouter API

OpenRouter поддерживает различные embedding модели через единый API endpoint.
"""

import asyncio
import logging
from typing import List

import httpx

from src.core.exceptions import OpenRouterConfigError, OpenRouterError
from src.core.integrations.ai.embeddings.base import BaseEmbeddings
from src.core.settings import settings

logger = logging.getLogger(__name__)


class OpenRouterEmbeddings(BaseEmbeddings):
    """
    Клиент для генерации embeddings через OpenRouter API.

    Класс предоставляет методы для генерации векторных представлений текста
    с использованием различных embedding моделей через OpenRouter.

    Attributes:
        model (str): Название embedding модели (например, "openai/text-embedding-ada-002")
        base_url (str): Базовый URL OpenRouter API
        api_key (str): API ключ для аутентификации
        timeout (int): Таймаут для HTTP запросов в секундах
        max_retries (int): Максимальное количество повторных попыток при ошибках

    Example:
        >>> async with OpenRouterEmbeddings() as embedder:
        ...     # Генерация embeddings для нескольких текстов
        ...     vectors = await embedder.embed(["text1", "text2"])
        ...
        ...     # Генерация embedding для одного запроса
        ...     vector = await embedder.embed_query("single text")

    Raises:
        OpenRouterConfigError: Если отсутствует OPENROUTER_API_KEY в настройках
        OpenRouterError: При ошибках API или сети

    Note:
        Доступные модели можно получить через GET /api/v1/models/embeddings
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        max_retries: int | None = None,
    ) -> None:
        """
        Инициализирует OpenRouter embeddings клиент.

        Args:
            model: Название embedding модели (по умолчанию из settings.OPENROUTER_EMBEDDING_MODEL)
            api_key: API ключ (по умолчанию из settings.OPENROUTER_API_KEY)
            base_url: Базовый URL API (по умолчанию из settings.OPENROUTER_BASE_URL)
            timeout: Таймаут запросов в секундах (по умолчанию из settings.OPENROUTER_TIMEOUT)
            max_retries: Максимальное количество повторных попыток (по умолчанию из settings.OPENROUTER_MAX_RETRIES)

        Raises:
            OpenRouterConfigError: Если API ключ не указан и отсутствует в настройках
        """
        # Получаем значения из settings или используем переданные параметры
        api_key = api_key or settings.OPENROUTER_API_KEY
        if not api_key:
            raise OpenRouterConfigError(
                detail="OPENROUTER_API_KEY не установлен. Установите переменную окружения OPENROUTER_API_KEY или передайте api_key в конструктор",
            )

        base_url = base_url or settings.OPENROUTER_BASE_URL
        model = model or settings.OPENROUTER_EMBEDDING_MODEL
        timeout = timeout or settings.OPENROUTER_TIMEOUT
        max_retries = max_retries or settings.OPENROUTER_MAX_RETRIES

        # Инициализируем базовый класс
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )

        self.logger.info(
            "Инициализирован OpenRouter embeddings клиент (модель: %s)",
            self.model,
        )

    def _get_headers(self) -> dict[str, str]:
        """
        Возвращает HTTP заголовки для OpenRouter API.

        Returns:
            dict[str, str]: Словарь с заголовками включая Authorization, Content-Type,
                           HTTP-Referer и X-Title (требуются для OpenRouter)

        Note:
            OpenRouter требует HTTP-Referer и X-Title для ранжирования запросов.
        """
        headers = super()._get_headers()
        headers.update(
            {
                "HTTP-Referer": settings.APP_NAME,
                "X-Title": f"{settings.APP_NAME} Embeddings",
            }
        )
        return headers

    async def _make_request(
        self,
        endpoint: str,
        payload: dict,
    ) -> dict:
        """
        Выполняет HTTP запрос к OpenRouter API с retry логикой.

        Args:
            endpoint: Путь к API endpoint (например, '/embeddings')
            payload: Данные запроса в формате JSON

        Returns:
            dict: Ответ от API в формате JSON

        Raises:
            OpenRouterError: При ошибках HTTP, сети или некорректном ответе API

        Note:
            Автоматически повторяет запрос при ошибках 429 (rate limit)
            с экспоненциальной задержкой (2^attempt секунд).
        """
        client = self._get_client()
        headers = self._get_headers()

        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.debug(
                    "Запрос к OpenRouter API (попытка %d/%d): %s",
                    attempt,
                    self.max_retries,
                    endpoint,
                )

                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()

                result = response.json()
                self.logger.debug("Успешный ответ от OpenRouter API: %s", endpoint)
                return result

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                error_detail = e.response.text

                # Rate limiting - повторяем с задержкой
                if status_code == 429:
                    if attempt < self.max_retries:
                        delay = 2**attempt
                        self.logger.warning(
                            "Rate limit (429), повтор через %d сек (попытка %d/%d)",
                            delay,
                            attempt,
                            self.max_retries,
                        )
                        await asyncio.sleep(delay)
                        continue

                # Другие HTTP ошибки
                self.logger.error(
                    "HTTP ошибка %d при запросе к OpenRouter: %s",
                    status_code,
                    error_detail,
                )
                raise OpenRouterError(
                    detail=f"OpenRouter API вернул ошибку {status_code}: {error_detail}",
                    extra={"status_code": status_code, "response": error_detail},
                ) from e

            except httpx.RequestError as e:
                self.logger.error(
                    "Сетевая ошибка при запросе к OpenRouter (попытка %d/%d): %s",
                    attempt,
                    self.max_retries,
                    str(e),
                )

                if attempt < self.max_retries:
                    delay = 2**attempt
                    await asyncio.sleep(delay)
                    continue

                raise OpenRouterError(
                    detail=f"Ошибка соединения с OpenRouter API: {type(e).__name__}",
                    extra={"error_type": type(e).__name__},
                ) from e

        # Если все попытки исчерпаны
        raise OpenRouterError(
            detail=f"Не удалось выполнить запрос к OpenRouter после {self.max_retries} попыток",
        )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Генерирует embeddings для списка текстов.

        Args:
            texts: Список текстов для генерации embeddings

        Returns:
            List[List[float]]: Список векторных представлений (embeddings) для каждого текста

        Raises:
            OpenRouterError: При ошибках API, сети или некорректном формате ответа

        Example:
            >>> embedder = OpenRouterEmbeddings()
            >>> vectors = await embedder.embed(["первый текст", "второй текст"])
            >>> len(vectors)  # 2
            >>> len(vectors[0])  # 1536 (размерность embedding модели)

        Note:
            OpenRouter API поддерживает batch запросы для оптимизации.
            Ответ содержит embeddings в поле data[].embedding.
        """
        self.logger.info("Генерация embeddings для %d текстов", len(texts))

        payload = {
            "input": texts,
            "model": self.model,
        }

        try:
            response = await self._make_request("/embeddings", payload)

            # Извлекаем embeddings из ответа
            embeddings = [item["embedding"] for item in response["data"]]

            self.logger.info(
                "Успешно сгенерированы embeddings (размер: %d текстов, размерность: %d)",
                len(embeddings),
                len(embeddings[0]) if embeddings else 0,
            )
            return embeddings

        except (KeyError, IndexError, TypeError) as e:
            self.logger.error(
                "Некорректный формат ответа от OpenRouter API: %s",
                str(e),
            )
            raise OpenRouterError(
                detail=f"Некорректный формат ответа от OpenRouter API: {type(e).__name__}",
                extra={"error": str(e)},
            ) from e
