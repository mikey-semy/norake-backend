"""
Роутеры для работы с n8n Workflows.

Модуль предоставляет HTTP API для управления n8n workflows:
- N8nWorkflowProtectedRouter (ProtectedRouter) - защищённые endpoints с JWT

Все операции требуют аутентификации.
"""

from typing import List
from uuid import UUID

from fastapi import status

from src.core.dependencies.n8n_workflows import N8nWorkflowServiceDep
from src.core.security import CurrentUserDep
from src.models.v1.n8n_workflows import N8nWorkflowModel
from src.routers.base import ProtectedRouter
from src.schemas.v1.n8n_workflows import (
    N8nWorkflowCreateSchema,
    N8nWorkflowDetailSchema,
    N8nWorkflowListResponseSchema,
    N8nWorkflowResponseSchema,
)


class N8nWorkflowProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для n8n workflows.

    Предоставляет HTTP API для управления n8n workflows:

    Protected Endpoints (требуется JWT):
        POST /workflows/{workspace_id} - Создать workflow
        GET /workflows/{workspace_id} - Список workflows workspace

    Архитектурные особенности:
        - Все endpoints требуют JWT аутентификации
        - Роутер преобразует N8nWorkflowModel → Schema
        - Бизнес-логика в N8nWorkflowService
    """

    def __init__(self):
        """Инициализация N8nWorkflow роутера."""
        super().__init__(prefix="/workflows", tags=["N8n Workflows"])

    def configure(self):
        """Настройка endpoints роутера."""

        @self.router.post(
            "/{workspace_id}",
            response_model=N8nWorkflowResponseSchema,
            status_code=status.HTTP_201_CREATED,
            summary="Создать n8n workflow",
            description="Создание нового n8n workflow для workspace",
        )
        async def create_workflow(
            workspace_id: UUID,
            workflow_data: N8nWorkflowCreateSchema,
            service: N8nWorkflowServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> N8nWorkflowResponseSchema:
            """Создать новый n8n workflow.

            Args:
                workspace_id: UUID workspace.
                workflow_data: Данные для создания workflow.
                service: Service для работы с workflows.
                current_user: Текущий пользователь (из JWT).

            Returns:
                N8nWorkflowResponseSchema: Созданный workflow.
            """
            workflow: N8nWorkflowModel = await service.create_workflow(
                workspace_id=workspace_id,
                workflow_name=workflow_data.workflow_name,
                workflow_type=workflow_data.workflow_type,
                webhook_url=workflow_data.webhook_url,
                trigger_config=workflow_data.trigger_config,
                n8n_workflow_id=workflow_data.n8n_workflow_id,
            )

            schema = N8nWorkflowDetailSchema.model_validate(workflow)
            return N8nWorkflowResponseSchema(
                success=True,
                message="Workflow успешно создан",
                data=schema,
            )

        @self.router.get(
            "/{workspace_id}",
            response_model=N8nWorkflowListResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Получить workflows workspace",
            description="Получение всех workflows для workspace",
        )
        async def get_workspace_workflows(
            workspace_id: UUID,
            is_active: bool | None = None,
            service: N8nWorkflowServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> N8nWorkflowListResponseSchema:
            """Получить все workflows workspace.

            Args:
                workspace_id: UUID workspace.
                is_active: Фильтр по активности (опционально).
                service: Service для работы с workflows.
                current_user: Текущий пользователь (из JWT).

            Returns:
                N8nWorkflowListResponseSchema: Список workflows.
            """
            workflows: List[N8nWorkflowModel] = await service.get_workspace_workflows(
                workspace_id=workspace_id,
                is_active=is_active,
            )

            schemas = [N8nWorkflowDetailSchema.model_validate(w) for w in workflows]
            return N8nWorkflowListResponseSchema(
                success=True,
                message=f"Найдено workflows: {len(schemas)}",
                data=schemas,
            )
