"""Response схемы для n8n workflows."""

from typing import List

from src.schemas.base import BaseResponseSchema
from src.schemas.v1.n8n_workflows.base import N8nWorkflowDetailSchema


class N8nWorkflowResponseSchema(BaseResponseSchema):
    """Схема ответа для одного workflow.

    Используется для возврата одного workflow.
    """

    data: N8nWorkflowDetailSchema


class N8nWorkflowListResponseSchema(BaseResponseSchema):
    """Схема ответа для списка workflows.

    Используется для возврата списка workflows workspace.
    """

    data: List[N8nWorkflowDetailSchema]
