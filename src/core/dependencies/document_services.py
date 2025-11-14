"""
Зависимости для сервиса документов (Document Service Dependencies).

Провайдеры для DocumentServiceService с инжекцией зависимостей.
"""

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.core.dependencies.storage import S3ClientOptionalDep
from src.core.settings.base import settings
from src.services.v1.document_services import DocumentServiceService


async def get_document_service(
    session: AsyncSessionDep,
    s3_client: S3ClientOptionalDep,
) -> DocumentServiceService:
    """
    Создать экземпляр DocumentServiceService с зависимостями.

    Args:
        session: Асинхронная сессия базы данных.
        s3_client: S3 клиент для работы с хранилищем (опционально).

    Returns:
        Настроенный DocumentServiceService.

    Example:
        В роутере:
        >>> async def endpoint(
        ...     document_service: DocumentServiceServiceDep = None
        ... ):
        ...     return await document_service.list_document_services(query)
    """
    return DocumentServiceService(session=session, s3_client=s3_client, settings=settings)


# Аннотация типа для dependency injection
DocumentServiceServiceDep = Annotated[
    DocumentServiceService,
    Depends(get_document_service),
]
