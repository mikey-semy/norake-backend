"""
Embeddings dependencies для dependency injection.

Предоставляет провайдеры для OpenRouterEmbeddings клиента.
"""

from typing import Annotated

from fastapi import Depends

from src.core.integrations.ai.embeddings.openrouter import OpenRouterEmbeddings


async def get_embeddings() -> OpenRouterEmbeddings:
    """
    Создаёт и возвращает OpenRouterEmbeddings клиент.

    Returns:
        OpenRouterEmbeddings: Клиент для генерации embeddings через OpenRouter API

    Example:
        >>> async with get_embeddings() as embedder:
        ...     vectors = await embedder.embed(["text1", "text2"])
    """
    embeddings = OpenRouterEmbeddings()
    try:
        yield embeddings
    finally:
        await embeddings.close()


# Typed dependency annotation для использования в роутерах/сервисах
EmbeddingsDep = Annotated[OpenRouterEmbeddings, Depends(get_embeddings)]
