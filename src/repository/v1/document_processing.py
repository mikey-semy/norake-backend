"""Репозиторий для работы с метаданными обработки документов.

Этот модуль предоставляет функциональность для управления записями обработки PDF:
- Получение статуса обработки по document_service_id
- Создание записей о начале обработки
- Обновление статуса обработки (PROCESSING → COMPLETED/FAILED)
- Сохранение извлечённого текста и метаданных

Типичный workflow:
    1. create_processing_record() при загрузке PDF
    2. update_status(PROCESSING) при начале обработки
    3. save_extracted_text() при успешной обработке
    4. update_status(FAILED) при ошибках
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1 import (
    DocumentProcessingModel,
    ExtractionMethod,
    ProcessingStatus,
)
from src.repository.base import BaseRepository


class DocumentProcessingRepository(BaseRepository[DocumentProcessingModel]):
    """Репозиторий для управления обработкой документов.

    Наследует базовые CRUD операции от BaseRepository и добавляет
    специфичные методы для работы с процессом обработки PDF:
    получение по document_service_id, обновление статуса, сохранение текста.

    Args:
        session: Асинхронная сессия SQLAlchemy для работы с БД.

    Attributes:
        session: Унаследованная от BaseRepository сессия БД.
        model: DocumentProcessingModel класс для типизации.
    """

    def __init__(self, session: AsyncSession):
        """Инициализирует репозиторий с сессией БД.

        Args:
            session: Асинхронная SQLAlchemy сессия.
        """
        super().__init__(session, DocumentProcessingModel)

    async def get_by_document_id(
        self, document_service_id: UUID
    ) -> Optional[DocumentProcessingModel]:
        """Получает запись обработки по ID документа.

        Использует уникальный индекс на document_service_id для быстрого поиска.
        Применяется для проверки статуса обработки при запросах функций.

        Args:
            document_service_id: UUID документа из document_services таблицы.

        Returns:
            DocumentProcessingModel если найдена, None если документ
            не имеет записи обработки (не PDF или не обработан).

        Example:
            >>> processing = await repo.get_by_document_id(doc_uuid)
            >>> if processing and processing.status == ProcessingStatus.COMPLETED:
            ...     print(f"Извлечено {processing.page_count} страниц")
        """
        return await self.get_item_by_field(
            "document_service_id", document_service_id
        )

    async def create_processing_record(
        self,
        document_service_id: UUID,
        status: ProcessingStatus = ProcessingStatus.PENDING,
    ) -> DocumentProcessingModel:
        """Создаёт начальную запись о процессе обработки.

        Вызывается сразу после создания DocumentServiceModel для PDF файлов.
        Устанавливает статус PENDING и создаёт запись в БД.

        Args:
            document_service_id: UUID документа для связи 1-to-1.
            status: Начальный статус, по умолчанию PENDING.

        Returns:
            Созданная DocumentProcessingModel с установленным id и timestamps.

        Raises:
            IntegrityError: Если запись с таким document_service_id уже существует
                (нарушение unique constraint).

        Example:
            >>> processing = await repo.create_processing_record(
            ...     document_service_id=doc_uuid,
            ...     status=ProcessingStatus.PENDING
            ... )
            >>> assert processing.status == ProcessingStatus.PENDING
        """
        processing_data = {
            "document_service_id": document_service_id,
            "status": status,
        }
        return await self.create_item(processing_data)

    async def update_status(
        self,
        document_service_id: UUID,
        status: ProcessingStatus,
        error_message: Optional[str] = None,
    ) -> Optional[DocumentProcessingModel]:
        """Обновляет статус обработки документа.

        Используется для перехода между состояниями:
        PENDING → PROCESSING → COMPLETED/FAILED.

        Args:
            document_service_id: UUID документа.
            status: Новый статус из ProcessingStatus enum.
            error_message: Сообщение об ошибке (только для FAILED).

        Returns:
            Обновлённая DocumentProcessingModel или None если запись не найдена.

        Example:
            >>> # Начало обработки
            >>> await repo.update_status(doc_uuid, ProcessingStatus.PROCESSING)
            >>>
            >>> # Обработка завершилась с ошибкой
            >>> await repo.update_status(
            ...     doc_uuid,
            ...     ProcessingStatus.FAILED,
            ...     error_message="PDF содержит только сканы, требуется OCR"
            ... )
        """
        processing = await self.get_by_document_id(document_service_id)
        if not processing:
            return None

        update_data = {"status": status}
        if error_message:
            update_data["error_message"] = error_message

        return await self.update_item(processing.id, update_data)

    async def save_extracted_text(
        self,
        document_service_id: UUID,
        extracted_text: str,
        page_count: int,
        extraction_method: ExtractionMethod,
        language: str = "ru",
        processing_time_seconds: Optional[float] = None,
    ) -> Optional[DocumentProcessingModel]:
        """Сохраняет результаты успешной обработки PDF.

        Вызывается после завершения извлечения текста PDFProcessor.
        Обновляет все поля результата и устанавливает статус COMPLETED.

        Args:
            document_service_id: UUID документа.
            extracted_text: Полный извлечённый текст со страниц.
            page_count: Количество страниц в PDF.
            extraction_method: Метод извлечения (PDFPLUMBER/PYMUPDF/OCR).
            language: ISO 639-1 код языка документа, по умолчанию "ru".
            processing_time_seconds: Время обработки в секундах (опционально).

        Returns:
            Обновлённая DocumentProcessingModel с COMPLETED статусом
            или None если запись не найдена.

        Example:
            >>> processing = await repo.save_extracted_text(
            ...     document_service_id=doc_uuid,
            ...     extracted_text="Полный текст документа...",
            ...     page_count=15,
            ...     extraction_method=ExtractionMethod.PDFPLUMBER,
            ...     language="ru",
            ...     processing_time_seconds=2.5
            ... )
            >>> assert processing.status == ProcessingStatus.COMPLETED
        """
        processing = await self.get_by_document_id(document_service_id)
        if not processing:
            return None

        update_data = {
            "status": ProcessingStatus.COMPLETED,
            "extracted_text": extracted_text,
            "page_count": page_count,
            "extraction_method": extraction_method,
            "language": language,
            "extracted_at": datetime.now(timezone.utc),
        }

        if processing_time_seconds is not None:
            update_data["processing_time_seconds"] = processing_time_seconds

        return await self.update_item(processing.id, update_data)

    async def exists_for_document(self, document_service_id: UUID) -> bool:
        """Проверяет существование записи обработки для документа.

        Быстрая проверка без загрузки всей записи.
        Используется в условиях до создания новой записи.

        Args:
            document_service_id: UUID документа.

        Returns:
            True если запись обработки существует, False иначе.

        Example:
            >>> if not await repo.exists_for_document(doc_uuid):
            ...     await repo.create_processing_record(doc_uuid)
        """
        return await self.exists_by_field(
            "document_service_id", document_service_id
        )

    async def get_completed_processing(
        self, document_service_id: UUID
    ) -> Optional[DocumentProcessingModel]:
        """Получает запись обработки только если она завершена успешно.

        Удобный метод для проверки доступности AI функций.
        Возвращает запись только со статусом COMPLETED.

        Args:
            document_service_id: UUID документа.

        Returns:
            DocumentProcessingModel если обработка завершена, None если
            обработка не завершена или завершилась с ошибкой.

        Example:
            >>> processing = await repo.get_completed_processing(doc_uuid)
            >>> if processing:
            ...     # Можно использовать extracted_text для поиска
            ...     results = search_in_text(processing.extracted_text, query)
        """
        query = select(DocumentProcessingModel).where(
            DocumentProcessingModel.document_service_id == document_service_id,
            DocumentProcessingModel.status == ProcessingStatus.COMPLETED,
        )
        return await self.execute_and_return_scalar(query)
