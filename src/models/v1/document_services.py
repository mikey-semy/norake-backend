"""
Модуль document_services.py содержит модели для работы с Document Services.

Этот модуль предоставляет:
   ServiceFunctionType - enum для типов функций документного сервиса.
   DocumentFileType - enum для типов файлов.
   CoverType - enum для типов обложек.
   DocumentServiceModel - модель документного сервиса с полями и связями.
"""

import enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import ARRAY, BigInteger, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..base import BaseModel

if TYPE_CHECKING:
    from .users import UserModel
    from .workspaces import WorkspaceModel
    from .document_processing import DocumentProcessingModel
    from .knowledge_bases import KnowledgeBaseModel


class ServiceFunctionType(str, enum.Enum):
    """
    Enum для типов функций документного сервиса.

    Attributes:
        VIEW_PDF: Просмотр PDF в браузере.
        AI_CHAT: AI-чат с документом (Telegram integration).
        QR_CODE: Генерация QR-кода для быстрого доступа.
        SHARE: Публичная ссылка для шаринга.
        DOWNLOAD: Скачивание оригинального файла.
        CRUD_TABLE: CRUD для таблиц в spreadsheet (future feature).

    Example:
        >>> function = {"name": ServiceFunctionType.VIEW_PDF, "enabled": True}
        >>> DocumentServiceModel(available_functions=[function])
    """

    VIEW_PDF = "view_pdf"
    AI_CHAT = "ai_chat"
    QR_CODE = "qr_code"
    SHARE = "share"
    DOWNLOAD = "download"
    CRUD_TABLE = "crud_table"


class DocumentFileType(str, enum.Enum):
    """
    Enum для типов файлов документных сервисов.

    Attributes:
        PDF: PDF документ.
        DOC: Microsoft Word документ (.doc).
        DOCX: Microsoft Word документ (.docx).
        TXT: Простой текстовый файл (.txt).
        MD: Markdown документ (.md).
        SPREADSHEET: Excel/Google Sheets таблица.
        TEXT: Общий текстовый документ.
        IMAGE: Изображение.

    Example:
        >>> doc = DocumentServiceModel(file_type=DocumentFileType.PDF)
        >>> doc.file_type
        <DocumentFileType.PDF: 'pdf'>
    """

    PDF = "pdf"
    DOC = "doc"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"
    SPREADSHEET = "spreadsheet"
    TEXT = "text"
    IMAGE = "image"


class CoverType(str, enum.Enum):
    """
    Enum для типов обложек документных сервисов.

    Attributes:
        GENERATED: Автоматически сгенерированная обложка (thumbnail из PDF).
        ICON: Иконка (emoji/SVG).
        IMAGE: Загруженное изображение обложки.

    Example:
        >>> doc = DocumentServiceModel(cover_type=CoverType.GENERATED)
        >>> doc.cover_type
        <CoverType.GENERATED: 'generated'>
    """

    GENERATED = "generated"
    ICON = "icon"
    IMAGE = "image"


class DocumentServiceModel(BaseModel):
    """
    Модель документного сервиса (Document Service).

    Attributes:
        title (str): Название документного сервиса (до 255 символов).
        description (Optional[str]): Описание сервиса.
        tags (List[str]): Массив тегов для поиска и категоризации.
        file_url (str): URL файла в S3/MinIO хранилище.
        file_size (int): Размер файла в байтах.
        file_type (DocumentFileType): Тип файла (PDF/SPREADSHEET/TEXT/IMAGE).
        cover_type (CoverType): Тип обложки (GENERATED/ICON/IMAGE).
        cover_url (Optional[str]): URL обложки (для GENERATED и IMAGE).
        cover_icon (Optional[str]): Emoji или SVG иконка (для ICON).
        available_functions (dict): JSONB с настройками доступных функций.
        author_id (UUID): Foreign Key на users.id (создатель сервиса).
        workspace_id (Optional[UUID]): Foreign Key на workspaces.id (опционально).
        is_public (bool): Публичный доступ без аутентификации (default: False).
        view_count (int): Счётчик просмотров сервиса.

        author (UserModel): Relationship к пользователю-автору.
        workspace (Optional[WorkspaceModel]): Relationship к workspace (опционально).

    Properties:
        is_pdf (bool): Проверяет, является ли сервис PDF документом.
        has_function (function_name: str) -> bool: Проверяет наличие функции.

    Note:
        available_functions имеет структуру:
        [
            {
                "name": "view_pdf",
                "enabled": true,
                "label": "Открыть PDF",
                "icon": "📄",
                "config": {"viewer": "embedded"}
            },
            {
                "name": "qr_code",
                "enabled": true,
                "label": "QR-код",
                "icon": "📱",
                "config": {"qr_url": "https://..."}
            }
        ]

        При создании документа:
        - file_type определяется автоматически по MIME type
        - cover_type может быть выбран пользователем или установлен в GENERATED
        - available_functions заполняется дефолтными значениями для file_type

    Example:
        >>> doc = DocumentServiceModel(
        ...     title="Инструкция по эксплуатации",
        ...     file_type=DocumentFileType.PDF,
        ...     cover_type=CoverType.GENERATED,
        ...     author_id=user.id,
        ...     is_public=True,
        ...     available_functions=[
        ...         {"name": "view_pdf", "enabled": True},
        ...         {"name": "download", "enabled": True}
        ...     ]
        ... )
    """

    __tablename__ = "document_services"

    # Основные поля
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, doc="Название документного сервиса"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Описание сервиса"
    )

    tags: Mapped[List[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        server_default="{}",
        doc="Массив тегов для поиска",
    )

    # Файловые поля
    file_url: Mapped[str] = mapped_column(
        String(500), nullable=False, doc="URL файла в S3/MinIO"
    )

    file_size: Mapped[int] = mapped_column(
        BigInteger, nullable=False, doc="Размер файла в байтах"
    )

    file_type: Mapped[str] = mapped_column(
        Enum("pdf", "spreadsheet", "text", "image", name="documentfiletype", create_constraint=True),
        nullable=False,
        index=True,
        doc="Тип файла (PDF/SPREADSHEET/TEXT/IMAGE)",
    )

    # Обложка
    cover_type: Mapped[str] = mapped_column(
        Enum("generated", "icon", "image", name="covertype", create_constraint=True),
        nullable=False,
        default="generated",
        server_default="generated",
        doc="Тип обложки (GENERATED/ICON/IMAGE)",
    )

    cover_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, doc="URL обложки (для GENERATED и IMAGE)"
    )

    cover_icon: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, doc="Emoji или SVG иконка (для ICON)"
    )

    # Функции сервиса
    available_functions: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="[]",
        doc="JSONB с настройками доступных функций",
    )

    # Связи с пользователем и workspace
    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="ID автора сервиса",
    )

    workspace_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID workspace (опционально)",
    )

    knowledge_base_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="ID базы знаний для RAG функции (опционально)",
    )

    # Видимость и статистика
    is_public: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default="false",
        index=True,
        doc="Публичный доступ без аутентификации",
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        doc="Счётчик просмотров",
    )

    # Relationships
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="document_services",
        foreign_keys=[author_id],
        doc="Автор документного сервиса",
    )

    workspace: Mapped[Optional["WorkspaceModel"]] = relationship(
        "WorkspaceModel",
        back_populates="document_services",
        foreign_keys=[workspace_id],
        doc="Workspace документного сервиса (опционально)",
    )

    knowledge_base: Mapped[Optional["KnowledgeBaseModel"]] = relationship(
        "KnowledgeBaseModel",
        back_populates="document_services",
        foreign_keys=[knowledge_base_id],
        doc="База знаний для RAG функции (опционально)",
    )

    processing: Mapped[Optional["DocumentProcessingModel"]] = relationship(
        "DocumentProcessingModel",
        back_populates="document_service",
        uselist=False,
        cascade="all, delete-orphan",
        doc="Метаданные обработки документа (1-to-1)",
    )

    @property
    def is_pdf(self) -> bool:
        """
        Проверяет, является ли сервис PDF документом.

        Returns:
            bool: True если file_type == "pdf"
        """
        return self.file_type == "pdf"

    def has_function(self, function_name: str) -> bool:
        """
        Проверяет наличие и активность функции в available_functions.

        Args:
            function_name: Название функции (например: "view_pdf")

        Returns:
            bool: True если функция существует и enabled=True

        Example:
            >>> doc.has_function("view_pdf")
            True
            >>> doc.has_function("ai_chat")
            False
        """
        if not isinstance(self.available_functions, list):
            return False

        for func in self.available_functions:
            if func.get("name") == function_name and func.get("enabled"):
                return True

        return False

    def __repr__(self) -> str:
        """Строковое представление документного сервиса."""
        return (
            f"<DocumentServiceModel("
            f"id={self.id}, "
            f"title='{self.title}', "
            f"file_type={self.file_type.value}, "
            f"author_id={self.author_id}, "
            f"is_public={self.is_public}"
            f")>"
        )
