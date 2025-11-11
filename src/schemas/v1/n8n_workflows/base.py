"""Базовые схемы для n8n workflows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.models.v1.n8n_workflows import N8nWorkflowType


class N8nWorkflowBaseSchema(BaseModel):
    """Базовая схема n8n workflow.

    Содержит общие поля для всех операций с workflows.
    """

    workflow_name: str = Field(..., min_length=1, max_length=200)
    workflow_type: N8nWorkflowType
    webhook_url: str = Field(..., min_length=1, max_length=500)
    trigger_config: dict = Field(..., description="JSONB конфигурация триггера")
    n8n_workflow_id: str | None = Field(None, max_length=100)


class N8nWorkflowDetailSchema(N8nWorkflowBaseSchema):
    """Детальная схема n8n workflow.

    Используется для отображения полной информации о workflow.
    """

    id: UUID
    workspace_id: UUID
    is_active: bool
    execution_count: int
    last_triggered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
