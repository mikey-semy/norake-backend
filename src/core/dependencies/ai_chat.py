"""
Зависимости для AI Chat Service.

Предоставляет dependency injection для AIChatService с автоматической
инъекцией RAGSearchService, DocumentServiceRepository и Settings.
"""

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.core.dependencies.search import RAGSearchServiceDep
from src.services.v1.ai_chat import AIChatService


async def get_ai_chat_service(
    session: AsyncSessionDep,
    rag_service: RAGSearchServiceDep,
) -> AIChatService:
    """
    Провайдер для AIChatService с dependency injection.

    Автоматически инжектит:
    - AsyncSession для работы с БД
    - RAGSearchService для RAG context retrieval
    - Settings для конфигурации OpenRouter

    Args:
        session: Асинхронная сессия БД из AsyncSessionDep
        rag_service: Сервис RAG поиска из RAGSearchServiceDep

    Returns:
        AIChatService: Настроенный экземпляр сервиса AI чатов

    Example:
        ```python
        @router.post("/chat/{chat_id}/message")
        async def send_message(
            chat_id: str,
            chat_service: AIChatServiceDep,
        ):
            return await chat_service.send_message(chat_id, "Hello")
        ```
    """
    return AIChatService(
        session=session,
        rag_service=rag_service,
    )


# Typed dependency для использования в роутерах
AIChatServiceDep = Annotated[AIChatService, Depends(get_ai_chat_service)]
