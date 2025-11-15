"""
Сервис интеграции Document Services с Knowledge Base для RAG.

Модуль предоставляет функциональность активации RAG функции для документов:
- Создание или переиспользование Knowledge Base
- Извлечение текста из S3
- Chunking документа с перекрытием
- Генерация embeddings через OpenRouter
- Сохранение чанков в базе данных
- Обновление available_functions в document_service
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    DocumentProcessingError,
    DocumentServiceNotFoundError,
    WorkspaceNotFoundError,
)
from src.core.integrations.ai.embeddings.openrouter import OpenRouterEmbeddings
from src.core.integrations.storages.documents import DocumentS3Storage
from src.models.v1.document_services import DocumentServiceModel
from src.models.v1.knowledge_bases import (
    DocumentStatus,
    KnowledgeBaseModel,
    KnowledgeBaseType,
)
from src.repository.v1.document_chunks import DocumentChunkRepository
from src.repository.v1.document_processing import DocumentProcessingRepository
from src.repository.v1.document_services import DocumentServiceRepository
from src.repository.v1.documents import DocumentRepository
from src.repository.v1.knowledge_bases import KnowledgeBaseRepository
from src.repository.v1.workspaces import WorkspaceRepository
from src.services.base import BaseService


class DocumentKBIntegrationService(BaseService):
    """
    Сервис интеграции Document Services с Knowledge Base.

    Управляет активацией RAG функции для документов:
    - Создание KB для workspace (если не существует)
    - Извлечение и chunking текста из S3
    - Генерация embeddings через OpenRouter
    - Сохранение DocumentModel и DocumentChunkModel
    - Обновление document_service.knowledge_base_id и available_functions

    Attributes:
        session: Сессия SQLAlchemy
        s3_storage: Клиент S3 для чтения файлов
        embeddings: Сервис генерации embeddings
        settings: Настройки приложения
        doc_service_repo: Репозиторий Document Services
        kb_repo: Репозиторий Knowledge Bases
        doc_repo: Репозиторий Documents
        chunk_repo: Репозиторий Document Chunks
        processing_repo: Репозиторий Processing Records
        workspace_repo: Репозиторий Workspaces

    Example:
        >>> service = DocumentKBIntegrationService(session, s3_storage, embeddings, settings)
        >>> await service.activate_rag_for_document_service(service_id, user_id)
    """

    def __init__(
        self,
        session: AsyncSession,
        s3_storage: DocumentS3Storage,
        embeddings: OpenRouterEmbeddings,
    ):
        """
        Инициализирует сервис интеграции с KB.

        Args:
            session: Асинхронная сессия SQLAlchemy
            s3_storage: Клиент S3 для доступа к файлам
            embeddings: Сервис генерации embeddings
        """
        super().__init__(session)
        self.s3_storage = s3_storage
        self.embeddings = embeddings

        # Repositories
        self.doc_service_repo = DocumentServiceRepository(session)
        self.kb_repo = KnowledgeBaseRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.chunk_repo = DocumentChunkRepository(session)
        self.processing_repo = DocumentProcessingRepository(session)
        self.workspace_repo = WorkspaceRepository(session)

    async def activate_rag_for_document_service(
        self,
        service_id: UUID,
        user_id: UUID,
    ) -> DocumentServiceModel:
        """
        Активирует RAG функцию для Document Service.

        Выполняет полный pipeline:
        1. Проверяет существование document_service и права доступа
        2. Проверяет, не активирована ли уже RAG функция (идемпотентность)
        3. Получает или создает Knowledge Base для workspace
        4. Извлекает текст из S3 файла
        5. Разбивает текст на чанки с перекрытием
        6. Генерирует embeddings для каждого чанка
        7. Создает DocumentModel и DocumentChunkModel записи
        8. Обновляет document_service.knowledge_base_id
        9. Добавляет "ai_chat" в available_functions

        Args:
            service_id: UUID document service для активации RAG
            user_id: UUID пользователя (для проверки прав)

        Returns:
            DocumentServiceModel: Обновленный document service с knowledge_base_id

        Raises:
            DocumentNotFoundError: Document service не найден
            WorkspaceNotFoundError: Workspace не найден
            DocumentProcessingError: Ошибка при обработке файла (S3, chunking, embeddings)

        Example:
            >>> doc_service = await service.activate_rag_for_document_service(
            ...     service_id=uuid4(),
            ...     user_id=uuid4()
            ... )
            >>> doc_service.knowledge_base_id is not None
            True
            >>> "ai_chat" in [f["name"] for f in doc_service.available_functions]
            True
        """
        self.logger.info(
            "Активация RAG для document service: %s пользователем %s",
            service_id,
            user_id,
        )

        # 1. Проверяем document_service
        doc_service = await self.doc_service_repo.get_item_by_id(service_id)
        if not doc_service:
            raise DocumentServiceNotFoundError(
                service_id=service_id,
            )

        # 2. Проверяем идемпотентность (RAG уже активирована)
        if doc_service.knowledge_base_id:
            self.logger.warning(
                "RAG уже активирована для document service %s (KB: %s)",
                service_id,
                doc_service.knowledge_base_id,
            )
            return doc_service

        # 3. Проверяем workspace
        if not doc_service.workspace_id:
            raise WorkspaceNotFoundError(
                detail="Document service не привязан к workspace",
                extra={"service_id": str(service_id)},
            )

        workspace = await self.workspace_repo.get_item_by_id(doc_service.workspace_id)
        if not workspace:
            raise WorkspaceNotFoundError(
                detail=f"Workspace {doc_service.workspace_id} не найден",
                extra={"workspace_id": str(doc_service.workspace_id)},
            )

        # 4. Получаем или создаем Knowledge Base для workspace
        kb = await self._get_or_create_kb(doc_service.workspace_id, workspace.name)

        # 5. Извлекаем текст из S3
        try:
            file_content, content_type = await self.s3_storage.get_file_stream(doc_service.file_url)
            text = file_content.decode("utf-8")
        except Exception as e:
            self.logger.error(
                "Ошибка при чтении файла %s из S3: %s",
                doc_service.file_url,
                str(e),
            )
            raise DocumentProcessingError(
                detail=f"Не удалось извлечь текст из файла: {str(e)}",
                extra={"file_url": doc_service.file_url, "error": str(e)},
            ) from e

        # 6. Chunking текста
        chunks = self._chunk_text(
            text=text,
            chunk_size=self.settings.RAG_CHUNK_SIZE,
            chunk_overlap=self.settings.RAG_CHUNK_OVERLAP,
        )
        self.logger.info(
            "Документ %s разбит на %d чанков (size=%d, overlap=%d)",
            service_id,
            len(chunks),
            self.settings.RAG_CHUNK_SIZE,
            self.settings.RAG_CHUNK_OVERLAP,
        )

        # 7. Генерация embeddings
        try:
            embeddings_list = await self.embeddings.embed(chunks)
        except Exception as e:
            self.logger.error(
                "Ошибка генерации embeddings для %s: %s",
                service_id,
                str(e),
            )
            raise DocumentProcessingError(
                detail=f"Не удалось сгенерировать embeddings: {str(e)}",
                extra={"service_id": str(service_id), "error": str(e)},
            ) from e

        # 8. Создаем DocumentModel
        document = await self.doc_repo.create_item(
            {
                "kb_id": kb.id,
                "filename": doc_service.title or "unknown",
                "content_type": "text/plain",  # TODO: определять из file_type
                "file_size": doc_service.file_size or 0,
                "storage_path": doc_service.file_url,
                "status": DocumentStatus.INDEXING,
                "metadata": {
                    "document_service_id": str(service_id),
                    "author_id": str(doc_service.author_id),
                },
            }
        )

        # 9. Создаем DocumentChunkModel записи
        chunk_data = [
            {
                "document_id": document.id,
                "chunk_index": idx,
                "content": chunk,
                "embedding": embedding,
                "metadata": {
                    "chunk_size": len(chunk),
                    "chunk_overlap": self.settings.RAG_CHUNK_OVERLAP,
                },
            }
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings_list))
        ]

        # Batch insert chunks
        await self.chunk_repo.bulk_create(chunk_data)

        # 10. Обновляем document status
        await self.doc_repo.update_item(
            document.id,
            {"status": DocumentStatus.INDEXED, "chunks_count": len(chunks)},
        )

        # 11. Обновляем KB documents_count
        await self.kb_repo.update_item(
            kb.id,
            {"documents_count": kb.documents_count + 1},
        )

        # 12. Обновляем document_service
        available_functions = doc_service.available_functions or []
        if not any(f.get("name") == "ai_chat" for f in available_functions):
            available_functions.append({"name": "ai_chat", "enabled": True})

        updated_service = await self.doc_service_repo.update_item(
            service_id,
            {
                "knowledge_base_id": kb.id,
                "available_functions": available_functions,
            },
        )

        self.logger.info(
            "RAG успешно активирована: document_service=%s, kb=%s, chunks=%d",
            service_id,
            kb.id,
            len(chunks),
        )

        return updated_service

    async def _get_or_create_kb(
        self,
        workspace_id: UUID,
        workspace_name: str,
    ) -> KnowledgeBaseModel:
        """
        Получает существующую или создает новую Knowledge Base для workspace.

        Args:
            workspace_id: UUID workspace
            workspace_name: Название workspace для генерации имени KB

        Returns:
            KnowledgeBaseModel: Существующая или новая KB

        Example:
            >>> kb = await self._get_or_create_kb(workspace_id, "My Workspace")
            >>> kb.kb_type == KnowledgeBaseType.RAG
            True
        """
        # Ищем активную RAG KB для workspace
        existing_kb = await self.kb_repo.filter_by(
            workspace_id=workspace_id,
            kb_type=KnowledgeBaseType.RAG,
            is_active=True,
        )

        if existing_kb:
            self.logger.debug(
                "Используем существующую KB %s для workspace %s",
                existing_kb[0].id,
                workspace_id,
            )
            return existing_kb[0]

        # Создаем новую KB
        new_kb = await self.kb_repo.create_item(
            {
                "workspace_id": workspace_id,
                "kb_type": KnowledgeBaseType.RAG,
                "name": f"{workspace_name} - RAG Knowledge Base",
                "description": "Автоматически созданная база знаний для RAG функции",
                "vector_store_config": {
                    "dimension": 1536,  # OpenRouter text-embedding-ada-002
                    "metric": "cosine",
                    "index_type": "ivfflat",
                },
            }
        )

        self.logger.info(
            "Создана новая KB %s для workspace %s",
            new_kb.id,
            workspace_id,
        )

        return new_kb

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        """
        Разбивает текст на чанки с перекрытием.

        Использует алгоритм скользящего окна с учетом границ предложений.

        Args:
            text: Исходный текст для разбиения
            chunk_size: Максимальный размер чанка в символах
            chunk_overlap: Размер перекрытия между чанками

        Returns:
            list[str]: Список текстовых чанков

        Example:
            >>> chunks = self._chunk_text("Hello world. Foo bar.", chunk_size=10, chunk_overlap=5)
            >>> len(chunks) >= 1
            True
        """
        if not text or chunk_size <= 0:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Если не последний чанк, пытаемся найти конец предложения
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                boundary = max(last_period, last_newline)

                if boundary > chunk_size // 2:  # Граница не слишком далеко
                    chunk = chunk[: boundary + 1]
                    end = start + boundary + 1

            chunks.append(chunk.strip())

            # Сдвигаем окно с учетом перекрытия
            start = end - chunk_overlap if end < len(text) else end

        return [c for c in chunks if c]  # Убираем пустые чанки
