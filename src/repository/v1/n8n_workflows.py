"""Repository для работы с n8n workflows."""

from typing import List
from uuid import UUID

from src.models.v1.n8n_workflows import N8nWorkflowModel
from src.repository.base import BaseRepository


class N8nWorkflowRepository(BaseRepository[N8nWorkflowModel]):
    """Repository для работы с n8n workflows.

    Предоставляет методы для CRUD операций с n8n workflows
    и получения workflows по workspace.

    Attributes:
        model_class: SQLAlchemy модель N8nWorkflowModel.
    """

    model_class = N8nWorkflowModel

    async def get_by_workspace(
        self,
        workspace_id: UUID,
        is_active: bool | None = None,
    ) -> List[N8nWorkflowModel]:
        """Получить все workflows для workspace.

        Args:
            workspace_id: UUID workspace.
            is_active: Фильтр по активности (опционально).

        Returns:
            List[N8nWorkflowModel]: Список workflows workspace.
        """
        filters = {"workspace_id": workspace_id}
        if is_active is not None:
            filters["is_active"] = is_active

        return await self.filter_by_ordered(
            "created_at",
            ascending=False,
            **filters,
        )

    async def get_by_type(
        self,
        workspace_id: UUID,
        workflow_type: str,
    ) -> List[N8nWorkflowModel]:
        """Получить workflows по типу.

        Args:
            workspace_id: UUID workspace.
            workflow_type: Тип workflow.

        Returns:
            List[N8nWorkflowModel]: Список workflows указанного типа.
        """
        return await self.filter_by_ordered(
            "created_at",
            ascending=False,
            workspace_id=workspace_id,
            workflow_type=workflow_type,
        )

    async def increment_execution_count(self, workflow_id: UUID) -> N8nWorkflowModel:
        """Увеличить счетчик выполнений workflow.

        Args:
            workflow_id: UUID workflow.

        Returns:
            N8nWorkflowModel: Обновлённый workflow.
        """
        workflow = await self.get_item_by_id(workflow_id)
        if workflow:
            return await self.update_item(
                workflow_id,
                {"execution_count": workflow.execution_count + 1},
            )
        return workflow
