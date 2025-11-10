"""
Модуль интеграции с AI сервисами.

Модуль предоставляет базовые классы и реализации для работы с различными AI провайдерами:
- BaseAIClient: Абстрактный базовый класс для всех AI клиентов
- BaseEmbeddings: Базовый класс для embeddings клиентов
- OpenRouterEmbeddings: Клиент для генерации embeddings через OpenRouter

Подмодули:
    - embeddings: Генерация векторных представлений текста

Example:
    >>> from src.core.integrations.ai import OpenRouterEmbeddings
    >>>
    >>> async with OpenRouterEmbeddings() as embedder:
    ...     vectors = await embedder.embed(["text1", "text2"])
"""

from src.core.integrations.ai.base import BaseAIClient
from src.core.integrations.ai.embeddings import (
    BaseEmbeddings,
    OpenRouterEmbeddings,
)

# Повторный экспорт исключений для удобства
from src.core.exceptions import OpenRouterConfigError, OpenRouterError

__all__ = [
    # Базовые классы
    "BaseAIClient",
    "BaseEmbeddings",
    # OpenRouter
    "OpenRouterEmbeddings",
    # Исключения
    "OpenRouterError",
    "OpenRouterConfigError",
]
