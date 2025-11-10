"""
Модуль embeddings для генерации векторных представлений текста.

Модуль предоставляет базовые классы и реализации для работы с embeddings:
- BaseEmbeddings: Абстрактный базовый класс для embeddings клиентов
- OpenRouterEmbeddings: Клиент для генерации embeddings через OpenRouter

Example:
    >>> from src.core.integrations.ai.embeddings import OpenRouterEmbeddings
    >>>
    >>> async with OpenRouterEmbeddings() as embedder:
    ...     vectors = await embedder.embed(["text1", "text2"])
"""

from src.core.integrations.ai.embeddings.base import BaseEmbeddings
from src.core.integrations.ai.embeddings.openrouter import OpenRouterEmbeddings

__all__ = [
    "BaseEmbeddings",
    "OpenRouterEmbeddings",
]
