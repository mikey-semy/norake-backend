"""Request схемы для n8n workflows."""

from pydantic import Field

from src.schemas.v1.n8n_workflows.base import N8nWorkflowBaseSchema


class N8nWorkflowCreateSchema(N8nWorkflowBaseSchema):
    """Схема создания n8n workflow.

    Используется для POST запросов при создании нового workflow.
    """

    pass


class N8nWorkflowUpdateSchema(N8nWorkflowBaseSchema):
    """Схема обновления n8n workflow.

    Все поля опциональны для частичного обновления.
    """

    workflow_name: str | None = Field(None, min_length=1, max_length=200)
    webhook_url: str | None = Field(None, min_length=1, max_length=500)
    trigger_config: dict | None = None
    is_active: bool | None = None
