"""Экспорт схем n8n workflows."""

from src.schemas.v1.n8n_workflows.base import (
    N8nWorkflowBaseSchema,
    N8nWorkflowDetailSchema,
)
from src.schemas.v1.n8n_workflows.requests import (
    N8nWorkflowCreateSchema,
    N8nWorkflowUpdateSchema,
)
from src.schemas.v1.n8n_workflows.responses import (
    N8nWorkflowListResponseSchema,
    N8nWorkflowResponseSchema,
)

__all__ = [
    "N8nWorkflowBaseSchema",
    "N8nWorkflowDetailSchema",
    "N8nWorkflowCreateSchema",
    "N8nWorkflowUpdateSchema",
    "N8nWorkflowResponseSchema",
    "N8nWorkflowListResponseSchema",
]
