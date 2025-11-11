"""
Модели для AI модулей и их интеграции с workspace.

Модуль предоставляет модели для pluggable AI modules системы:
- AIModuleModel - реестр доступных AI модулей (RAG, n8n workflows, и т.д.)
- WorkspaceModuleModel - подключение модулей к конкретным workspace

Архитектура:
    - Модули регистрируются глобально (AIModuleModel)
    - Workspace подключают нужные модули (WorkspaceModuleModel)
    - Конфигурация хранится в JSONB для гибкости
"""

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.v1.workspaces import WorkspaceModel


class AIModuleType(str, enum.Enum):
    """
    Типы AI модулей в системе.

    Attributes:
        RAG: Retrieval-Augmented Generation (векторный поиск + LLM)
        N8N_WORKFLOW: n8n workflow для автоматизации
        EMBEDDINGS: Сервис для генерации эмбеддингов
        LLM: Языковая модель для генерации текста
        SEARCH: Поисковый движок (Tavily, Google, и т.д.)
    """

    RAG = "rag"
    N8N_WORKFLOW = "n8n_workflow"
    EMBEDDINGS = "embeddings"
    LLM = "llm"
    SEARCH = "search"


class AIModuleModel(BaseModel):
    """
    Модель AI модуля (глобальный реестр).

    Хранит информацию о доступных AI модулях системы.
    Модули можно подключать к workspace через WorkspaceModuleModel.

    Attributes:
        module_type (AIModuleType): Тип модуля (RAG/N8N_WORKFLOW/и т.д.)
        name (str): Название модуля (например, "OpenRouter RAG")
        description (str): Описание функционала модуля
        provider (str): Провайдер сервиса (openrouter/openai/tavily/и т.д.)
        config_schema (dict): JSON Schema для валидации конфигурации
        default_config (dict): Конфигурация по умолчанию
        is_active (bool): Доступен ли модуль для использования
        version (str): Версия модуля

    Relationships:
        workspace_modules: Подключения модуля к workspace

    Example:
        >>> rag_module = AIModuleModel(
        ...     module_type=AIModuleType.RAG,
        ...     name="OpenRouter RAG",
        ...     provider="openrouter",
        ...     config_schema={
        ...         "type": "object",
        ...         "properties": {
        ...             "model": {"type": "string"},
        ...             "temperature": {"type": "number"}
        ...         }
        ...     },
        ...     default_config={"model": "openai/gpt-3.5-turbo", "temperature": 0.7}
        ... )
    """

    __tablename__ = "ai_modules"

    module_type: Mapped[AIModuleType] = mapped_column(
        Enum(AIModuleType, name="ai_module_type", create_type=True),
        nullable=False,
        index=True,
        comment="Тип модуля (RAG/N8N_WORKFLOW/и т.д.)",
    )

    name: Mapped[str] = mapped_column(
        String(200), nullable=False, unique=True, comment="Название модуля"
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание функционала"
    )

    provider: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="Провайдер (openrouter/openai)"
    )

    config_schema: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="JSON Schema для валидации конфига",
    )

    default_config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Конфигурация по умолчанию",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="Доступен ли модуль",
    )

    version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Версия модуля (например, 'v1.0')"
    )

    # Relationships
    workspace_modules: Mapped[list["WorkspaceModuleModel"]] = relationship(
        "WorkspaceModuleModel", back_populates="module", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Строковое представление модуля."""
        return f"<AIModule({self.name}, {self.module_type}, provider={self.provider})>"


class WorkspaceModuleModel(BaseModel):
    """
    Модель подключения AI модуля к workspace.

    Связывает workspace с AI модулем и хранит конфигурацию.
    Позволяет настраивать модули индивидуально для каждого workspace.

    Attributes:
        workspace_id (UUID): ID workspace
        module_id (UUID): ID AI модуля из реестра
        is_enabled (bool): Включён ли модуль для этого workspace
        config (dict): Конфигурация модуля (перекрывает default_config)
        priority (int): Приоритет модуля (для ранжирования результатов)

    Relationships:
        workspace: Workspace к которому подключён модуль
        module: AI модуль из глобального реестра

    Example:
        >>> # Подключить OpenRouter RAG к workspace
        >>> workspace_rag = WorkspaceModuleModel(
        ...     workspace_id=workspace.id,
        ...     module_id=rag_module.id,
        ...     is_enabled=True,
        ...     config={
        ...         "model": "openai/gpt-4",
        ...         "temperature": 0.5,
        ...         "max_tokens": 2000
        ...     },
        ...     priority=1
        ... )
    """

    __tablename__ = "workspace_modules"

    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID workspace",
    )

    module_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_modules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID AI модуля",
    )

    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
        comment="Включён ли модуль",
    )

    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="Конфигурация модуля для workspace",
    )

    priority: Mapped[int | None] = mapped_column(
        nullable=True, default=0, comment="Приоритет для ранжирования (выше = важнее)"
    )

    # Relationships
    workspace: Mapped["WorkspaceModel"] = relationship(
        "WorkspaceModel", back_populates="ai_modules"
    )

    module: Mapped["AIModuleModel"] = relationship(
        "AIModuleModel", back_populates="workspace_modules"
    )

    def __repr__(self) -> str:
        """Строковое представление подключения."""
        return f"<WorkspaceModule(workspace={self.workspace_id}, module={self.module_id}, enabled={self.is_enabled})>"
