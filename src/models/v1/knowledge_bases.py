"""
Модели для Knowledge Base системы.

Модуль содержит SQLAlchemy модели для хранения и управления knowledge base:
- KnowledgeBaseModel: База знаний с конфигурацией vector store
- DocumentModel: Документы в knowledge base
- DocumentChunkModel: Чанки документов с embeddings (vector)

Используется pgvector расширение для хранения embeddings.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.v1.workspaces import WorkspaceModel


class KnowledgeBaseType(str, enum.Enum):
    """
    Типы Knowledge Base.

    Attributes:
        RAG: Retrieval-Augmented Generation (vector search)
        KAG: Knowledge-Augmented Generation (graph-based)

    Example:
        >>> kb = KnowledgeBaseModel(kb_type=KnowledgeBaseType.RAG)
        >>> kb.kb_type.value
        'rag'
    """

    RAG = "rag"
    KAG = "kag"


class DocumentStatus(str, enum.Enum):
    """
    Статусы обработки документа.

    Attributes:
        UPLOADED: Документ загружен, ожидает обработки
        INDEXING: Документ обрабатывается (chunking + embedding)
        INDEXED: Документ полностью проиндексирован
        FAILED: Ошибка при обработке документа

    Example:
        >>> doc = DocumentModel(status=DocumentStatus.UPLOADED)
        >>> doc.status == DocumentStatus.UPLOADED
        True
    """

    UPLOADED = "uploaded"
    INDEXING = "indexing"
    INDEXED = "indexed"
    FAILED = "failed"


class KnowledgeBaseModel(BaseModel):
    """
    Модель Knowledge Base.

    Представляет базу знаний (KB) в workspace для RAG/KAG поиска.
    Содержит конфигурацию vector store и метаданные документов.

    Attributes:
        workspace_id: UUID workspace, которому принадлежит KB
        kb_type: Тип KB (RAG/KAG)
        name: Название knowledge base
        description: Описание KB (опционально)
        vector_store_config: Конфигурация vector store в JSONB
        documents_count: Количество документов в KB
        is_active: Активна ли KB
        workspace: Связь с WorkspaceModel (Many-to-One)
        documents: Связь с DocumentModel (One-to-Many)

    Example:
        >>> kb = KnowledgeBaseModel(
        ...     workspace_id=workspace_id,
        ...     kb_type=KnowledgeBaseType.RAG,
        ...     name="Product Documentation",
        ...     vector_store_config={"dimension": 1536, "metric": "cosine"}
        ... )
    """

    __tablename__ = "knowledge_bases"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID workspace, которому принадлежит KB",
    )

    kb_type: Mapped[KnowledgeBaseType] = mapped_column(
        String(10),
        nullable=False,
        default=KnowledgeBaseType.RAG,
        comment="Тип knowledge base (rag/kag)",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Название knowledge base",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Описание knowledge base",
    )

    vector_store_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "dimension": 1536,
            "metric": "cosine",
            "index_type": "ivfflat",
        },
        comment="Конфигурация vector store (dimension, metric, index_type)",
    )

    documents_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Количество документов в KB",
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Активна ли knowledge base",
    )

    # Relationships
    workspace: Mapped["WorkspaceModel"] = relationship(
        "WorkspaceModel",
        back_populates="knowledge_bases",
        lazy="joined",
    )

    documents: Mapped[list["DocumentModel"]] = relationship(
        "DocumentModel",
        back_populates="knowledge_base",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "documents_count >= 0",
            name="check_documents_count_positive",
        ),
        Index(
            "ix_knowledge_bases_workspace_active",
            "workspace_id",
            "is_active",
        ),
    )

    def __repr__(self) -> str:
        """
        Строковое представление KnowledgeBaseModel.

        Returns:
            str: Представление в формате KnowledgeBase(id=..., name=..., kb_type=...)
        """
        return (
            f"KnowledgeBase(id={self.id}, name='{self.name}', "
            f"kb_type={self.kb_type.value}, documents={self.documents_count})"
        )


class DocumentModel(BaseModel):
    """
    Модель документа в Knowledge Base.

    Представляет документ, загруженный в KB для индексации.
    Документ разбивается на чанки (DocumentChunkModel) с embeddings.

    Attributes:
        kb_id: UUID knowledge base, которой принадлежит документ
        filename: Имя файла документа
        file_path: Путь к файлу в storage (опционально)
        file_size: Размер файла в байтах
        mime_type: MIME тип файла
        status: Статус обработки (uploaded/indexing/indexed/failed)
        chunks_count: Количество чанков документа
        doc_metadata: Дополнительные метаданные документа (JSONB)
        indexed_at: Дата завершения индексации
        error_message: Сообщение об ошибке (если status=failed)
        knowledge_base: Связь с KnowledgeBaseModel (Many-to-One)
        chunks: Связь с DocumentChunkModel (One-to-Many)

    Example:
        >>> doc = DocumentModel(
        ...     kb_id=kb_id,
        ...     filename="manual.pdf",
        ...     file_size=1024000,
        ...     mime_type="application/pdf",
        ...     status=DocumentStatus.UPLOADED
        ... )
    """

    __tablename__ = "documents"

    kb_id: Mapped[UUID] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID knowledge base",
    )

    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Имя файла документа",
    )

    file_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="Путь к файлу в storage",
    )

    file_size: Mapped[int] = mapped_column(
        nullable=False,
        comment="Размер файла в байтах",
    )

    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="MIME тип файла",
    )

    status: Mapped[DocumentStatus] = mapped_column(
        String(20),
        nullable=False,
        default=DocumentStatus.UPLOADED,
        index=True,
        comment="Статус обработки документа",
    )

    chunks_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Количество чанков документа",
    )

    doc_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Дополнительные метаданные документа",
    )

    indexed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Дата завершения индексации",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Сообщение об ошибке при обработке",
    )

    # Relationships
    knowledge_base: Mapped["KnowledgeBaseModel"] = relationship(
        "KnowledgeBaseModel",
        back_populates="documents",
        lazy="joined",
    )

    chunks: Mapped[list["DocumentChunkModel"]] = relationship(
        "DocumentChunkModel",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        CheckConstraint(
            "file_size > 0",
            name="check_file_size_positive",
        ),
        CheckConstraint(
            "chunks_count >= 0",
            name="check_chunks_count_positive",
        ),
        Index(
            "ix_documents_kb_status",
            "kb_id",
            "status",
        ),
    )

    def __repr__(self) -> str:
        """
        Строковое представление DocumentModel.

        Returns:
            str: Представление в формате Document(id=..., filename=..., status=...)
        """
        return (
            f"Document(id={self.id}, filename='{self.filename}', "
            f"status={self.status.value}, chunks={self.chunks_count})"
        )


class DocumentChunkModel(BaseModel):
    """
    Модель чанка документа с embedding.

    Представляет фрагмент документа с vector embedding для RAG поиска.
    Использует pgvector для хранения и поиска по embeddings.

    Attributes:
        document_id: UUID документа, которому принадлежит чанк
        chunk_index: Порядковый номер чанка в документе
        content: Текстовое содержимое чанка
        embedding: Vector embedding (1536 dimensions для OpenAI ada-002)
        token_count: Количество токенов в чанке
        chunk_metadata: Дополнительные метаданные чанка (JSONB)
        document: Связь с DocumentModel (Many-to-One)

    Example:
        >>> chunk = DocumentChunkModel(
        ...     document_id=doc_id,
        ...     chunk_index=0,
        ...     content="This is the first paragraph...",
        ...     embedding=[0.1, 0.2, ...],  # 1536 dimensions
        ...     token_count=150
        ... )
    """

    __tablename__ = "document_chunks"

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID документа",
    )

    chunk_index: Mapped[int] = mapped_column(
        nullable=False,
        comment="Порядковый номер чанка в документе",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Текстовое содержимое чанка",
    )

    embedding: Mapped[Vector] = mapped_column(
        Vector(1536),
        nullable=False,
        comment="Vector embedding для RAG поиска (1536 dimensions)",
    )

    token_count: Mapped[int] = mapped_column(
        nullable=False,
        comment="Количество токенов в чанке",
    )

    chunk_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Дополнительные метаданные чанка",
    )

    # Relationships
    document: Mapped["DocumentModel"] = relationship(
        "DocumentModel",
        back_populates="chunks",
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint(
            "chunk_index >= 0",
            name="check_chunk_index_positive",
        ),
        CheckConstraint(
            "token_count > 0",
            name="check_token_count_positive",
        ),
        Index(
            "ix_document_chunks_document_index",
            "document_id",
            "chunk_index",
            unique=True,
        ),
        # Vector similarity search index
        Index(
            "ix_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        """
        Строковое представление DocumentChunkModel.

        Returns:
            str: Представление в формате Chunk(id=..., index=..., tokens=...)
        """
        return (
            f"Chunk(id={self.id}, document_id={self.document_id}, "
            f"index={self.chunk_index}, tokens={self.token_count})"
        )
