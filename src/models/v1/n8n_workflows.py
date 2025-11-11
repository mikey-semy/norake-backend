"""
Модели для n8n Workflow интеграции.

Модуль содержит SQLAlchemy модели для хранения и управления n8n workflows:
- N8nWorkflowModel: Конфигурация workflow с webhook URL и trigger config

n8n workflows используются для автоматизации:
- Auto-categorize Issues (AI-анализ и присвоение категорий)
- KB Indexing Pipeline (chunking + embeddings + vector store)
- Smart Search Helper (RAG-based поиск)
- Weekly Digest (автоматическая рассылка обновлений)
"""

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.v1.workspaces import WorkspaceModel


class N8nWorkflowType(str, enum.Enum):
    """
    Типы n8n workflows.

    Attributes:
        AUTO_CATEGORIZE: Автоматическая категоризация issues через AI
        KB_INDEXING: Индексация документов KB (chunking + embeddings)
        SMART_SEARCH: Умный поиск с RAG
        WEEKLY_DIGEST: Еженедельный дайджест обновлений

    Example:
        >>> workflow = N8nWorkflowModel(workflow_type=N8nWorkflowType.AUTO_CATEGORIZE)
        >>> workflow.workflow_type.value
        'auto_categorize'
    """

    AUTO_CATEGORIZE = "auto_categorize"
    KB_INDEXING = "kb_indexing"
    SMART_SEARCH = "smart_search"
    WEEKLY_DIGEST = "weekly_digest"


class N8nWorkflowModel(BaseModel):
    """
    Модель n8n Workflow.

    Представляет конфигурацию n8n workflow для workspace.
    Хранит webhook URL, trigger config и метаданные workflow.

    Attributes:
        workspace_id: UUID workspace, которому принадлежит workflow
        workflow_name: Название workflow
        workflow_type: Тип workflow (auto_categorize/kb_indexing/smart_search/weekly_digest)
        n8n_workflow_id: ID workflow в n8n (опционально)
        webhook_url: URL webhook для триггера workflow
        trigger_config: Конфигурация триггера в JSONB
        is_active: Активен ли workflow
        last_triggered_at: Дата последнего запуска workflow
        execution_count: Количество выполнений workflow
        workspace: Связь с WorkspaceModel (Many-to-One)

    Trigger Config JSONB Schema:
        {
            "auto_categorize": {
                "model": "gpt-4",
                "categories": ["hardware", "software", "process"],
                "confidence_threshold": 0.8
            },
            "kb_indexing": {
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "embedding_model": "text-embedding-ada-002"
            },
            "smart_search": {
                "top_k": 5,
                "similarity_threshold": 0.7,
                "rerank": true
            },
            "weekly_digest": {
                "schedule": "0 9 * * 1",
                "recipients": ["email@example.com"],
                "include_stats": true
            }
        }

    Example:
        >>> workflow = N8nWorkflowModel(
        ...     workspace_id=workspace_id,
        ...     workflow_name="Auto-categorize Issues",
        ...     workflow_type=N8nWorkflowType.AUTO_CATEGORIZE,
        ...     webhook_url="https://n8n.example.com/webhook/abc123",
        ...     trigger_config={
        ...         "model": "gpt-4",
        ...         "categories": ["hardware", "software"],
        ...         "confidence_threshold": 0.8
        ...     },
        ...     is_active=True
        ... )
    """

    __tablename__ = "n8n_workflows"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID workspace, которому принадлежит workflow",
    )

    workflow_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Название workflow",
    )

    workflow_type: Mapped[N8nWorkflowType] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Тип workflow (auto_categorize/kb_indexing/smart_search/weekly_digest)",
    )

    n8n_workflow_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="ID workflow в n8n (опционально)",
    )

    webhook_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URL webhook для триггера workflow",
    )

    trigger_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Конфигурация триггера workflow (JSONB)",
    )

    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        index=True,
        comment="Активен ли workflow",
    )

    last_triggered_at: Mapped[str | None] = mapped_column(
        nullable=True,
        comment="Дата последнего запуска workflow",
    )

    execution_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Количество выполнений workflow",
    )

    # Relationships
    workspace: Mapped["WorkspaceModel"] = relationship(
        "WorkspaceModel",
        back_populates="n8n_workflows",
        lazy="joined",
    )

    def __repr__(self) -> str:
        """
        Строковое представление N8nWorkflowModel.

        Returns:
            str: Представление в формате N8nWorkflow(id=..., name=..., type=...)
        """
        return (
            f"N8nWorkflow(id={self.id}, name='{self.workflow_name}', "
            f"type={self.workflow_type.value}, active={self.is_active})"
        )
