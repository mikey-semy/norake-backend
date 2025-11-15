"""
Зависимости для Document KB Integration Service.

Модуль предоставляет FastAPI Depends провайдеры для инъекции
DocumentKBIntegrationService с необходимыми зависимостями.
"""

from typing import Annotated

from fastapi import Depends

from src.core.dependencies import AsyncSessionDep
from src.core.dependencies.storage import S3ClientDep
from src.core.integrations.ai.embeddings.openrouter import OpenRouterEmbeddings
from src.core.integrations.storages.documents import DocumentS3Storage
from src.core.settings.base import settings
from src.services.v1.document_kb_integration import DocumentKBIntegrationService


async def get_document_kb_integration_service(
    session: AsyncSessionDep,
    s3_client: S3ClientDep,
) -> DocumentKBIntegrationService:
    """
    Провайдер зависимости для DocumentKBIntegrationService.

    Инъектирует сервис со всеми необходимыми зависимостями:
    - AsyncSession для работы с БД
    - DocumentS3Storage для чтения файлов
    - OpenRouterEmbeddings для генерации embeddings
    - Settings для RAG конфигурации

    Args:
        session: Асинхронная сессия SQLAlchemy
        s3_client: S3 клиент для работы с хранилищем

    Returns:
        DocumentKBIntegrationService: Настроенный сервис интеграции

    Example:
        >>> @router.post("/activate-rag")
        ... async def activate_rag(
        ...     service: DocumentKBIntegrationServiceDep = None,
        ... ):
        ...     return await service.activate_rag_for_document_service(...)
    """
    s3_storage = DocumentS3Storage(s3_client=s3_client)
    embeddings = OpenRouterEmbeddings(
        api_key=settings.OPENROUTER_API_KEY,
    )

    return DocumentKBIntegrationService(
        session=session,
        s3_storage=s3_storage,
        embeddings=embeddings,
    )


DocumentKBIntegrationServiceDep = Annotated[
    DocumentKBIntegrationService,
    Depends(get_document_kb_integration_service),
]
