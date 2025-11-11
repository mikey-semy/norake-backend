"""
Модуль интеграций с внешними сервисами.

Экспортируемые интеграции:
    - BaseAIClient (базовый класс для AI клиентов)
    - BaseEmbeddings (базовый класс для embeddings)
    - OpenRouterEmbeddings (клиент для генерации embeddings через OpenRouter)

Исключения (re-export из core.exceptions):
    - OpenRouterError
    - OpenRouterConfigError
"""

from src.core.exceptions import OpenRouterConfigError, OpenRouterError
from src.core.integrations.ai import (
    BaseAIClient,
    BaseEmbeddings,
    OpenRouterEmbeddings,
)

__all__ = [
    # AI
    "BaseAIClient",
    "BaseEmbeddings",
    "OpenRouterEmbeddings",
    # Exceptions
    "OpenRouterError",
    "OpenRouterConfigError",
]
