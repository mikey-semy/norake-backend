"""
Модуль document_processing.py содержит модели для обработки документов.

Этот модуль предоставляет:
   ProcessingStatus - enum для статусов обработки.
   ExtractionMethod - enum для методов извлечения текста.
   DocumentProcessingModel - модель для хранения результатов обработки PDF.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .document_services import DocumentServiceModel


class ProcessingStatus(str, enum.Enum):
    """
    Enum для статусов обработки документов.

    Attributes:
        PENDING: Ожидает обработки.
        PROCESSING: В процессе обработки.
        COMPLETED: Обработка завершена успешно.
        FAILED: Обработка завершилась с ошибкой.

    Example:
        >>> processing.status = ProcessingStatus.COMPLETED
        >>> processing.status.value
        'completed'
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExtractionMethod(str, enum.Enum):
    """
    Enum для методов извлечения текста из PDF.

    Attributes:
        PDFPLUMBER: Извлечение текста через pdfplumber (для текстовых PDF).
        PYMUPDF: Извлечение через PyMuPDF/fitz (альтернатива).
        OCR: Оптическое распознавание текста (для сканов).

    Example:
        >>> processing.extraction_method = ExtractionMethod.PDFPLUMBER
    """

    PDFPLUMBER = "pdfplumber"
    PYMUPDF = "pymupdf"
    OCR = "ocr"


class DocumentProcessingModel(BaseModel):
    """
    Модель для хранения результатов обработки документов.

    Хранит извлечённый текст, метаданные обработки, статус и ошибки.
    Связана 1-to-1 с DocumentServiceModel.

    Attributes:
        id: UUID записи (primary key).
        document_service_id: UUID связанного DocumentServiceModel (foreign key).
        status: Статус обработки (ProcessingStatus enum).
        extraction_method: Метод извлечения текста (ExtractionMethod enum).
        extracted_text: Полный извлечённый текст документа.
        page_count: Количество страниц в документе.
        language: Язык документа (ISO 639-1 код: "ru", "en" и т.д.).
        extracted_at: Дата и время завершения обработки.
        error_message: Текст ошибки (если status=FAILED).
        processing_time_seconds: Время обработки в секундах.

        document_service: Relationship с DocumentServiceModel (1-to-1).

    Example:
        >>> processing = DocumentProcessingModel(
        ...     document_service_id=doc_id,
        ...     status=ProcessingStatus.COMPLETED,
        ...     extraction_method=ExtractionMethod.PDFPLUMBER,
        ...     extracted_text="Текст документа...",
        ...     page_count=150,
        ...     language="ru"
        ... )
    """

    __tablename__ = "document_processing"

    # Foreign Key to DocumentServiceModel (1-to-1)
    document_service_id: Mapped[UUID] = mapped_column(
        ForeignKey("document_services.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
        doc="UUID связанного документного сервиса",
    )

    # Processing metadata
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        nullable=False,
        default=ProcessingStatus.PENDING,
        server_default=ProcessingStatus.PENDING.value,
        doc="Статус обработки",
    )

    extraction_method: Mapped[Optional[ExtractionMethod]] = mapped_column(
        Enum(ExtractionMethod),
        nullable=True,
        doc="Метод извлечения текста",
    )

    # Extracted content
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Полный извлечённый текст документа",
    )

    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Количество страниц в документе",
    )

    language: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        doc="Язык документа (ISO 639-1 код)",
    )

    # Timestamps
    extracted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата и время завершения обработки",
    )

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Текст ошибки (если status=FAILED)",
    )

    processing_time_seconds: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Время обработки в секундах",
    )

    # Relationships
    document_service: Mapped["DocumentServiceModel"] = relationship(
        "DocumentServiceModel",
        back_populates="processing",
        foreign_keys=[document_service_id],
        doc="Связанный документный сервис",
    )

    def __repr__(self) -> str:
        """Строковое представление записи обработки."""
        return (
            f"<DocumentProcessingModel("
            f"id={self.id}, "
            f"document_service_id={self.document_service_id}, "
            f"status={self.status.value}, "
            f"page_count={self.page_count}"
            f")>"
        )
