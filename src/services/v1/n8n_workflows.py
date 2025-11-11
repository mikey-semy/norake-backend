"""Service для работы с n8n workflows."""

from datetime import datetime
from typing import List
from uuid import UUID

from src.models.v1.n8n_workflows import N8nWorkflowModel, N8nWorkflowType
from src.repository.v1.n8n_workflows import N8nWorkflowRepository


class N8nWorkflowService:
    """Service для работы с n8n workflows.

    Обрабатывает бизнес-логику для n8n workflows,
    включая валидацию и управление жизненным циклом.

    Attributes:
        repository: Repository для доступа к данным workflows.
    """

    def __init__(self, repository: N8nWorkflowRepository) -> None:
        """Инициализация сервиса n8n workflows.

        Args:
            repository: N8nWorkflowRepository для доступа к БД.
        """
        self.repository = repository

    async def create_workflow(
        self,
        workspace_id: UUID,
        workflow_name: str,
        workflow_type: N8nWorkflowType,
        webhook_url: str,
        trigger_config: dict,
        n8n_workflow_id: str | None = None,
    ) -> N8nWorkflowModel:
        """Создать новый n8n workflow.

        Args:
            workspace_id: UUID workspace.
            workflow_name: Название workflow.
            workflow_type: Тип workflow (enum).
            webhook_url: URL webhook для триггера.
            trigger_config: Конфигурация триггера (JSONB).
            n8n_workflow_id: ID workflow в n8n (опционально).

        Returns:
            N8nWorkflowModel: Созданный workflow.

        Raises:
            ValueError: Если данные невалидны.
        """
        # Базовая валидация
        if not workflow_name or not webhook_url:
            raise ValueError("Название и webhook URL обязательны")

        if not trigger_config or not isinstance(trigger_config, dict):
            raise ValueError("trigger_config должен быть словарём")

        workflow_data = {
            "workspace_id": workspace_id,
            "workflow_name": workflow_name,
            "workflow_type": workflow_type.value,
            "webhook_url": webhook_url,
            "trigger_config": trigger_config,
            "n8n_workflow_id": n8n_workflow_id,
            "is_active": True,
            "execution_count": 0,
        }

        return await self.repository.create_item(workflow_data)

    async def get_workspace_workflows(
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
        return await self.repository.get_by_workspace(workspace_id, is_active)

    async def get_workflow_by_id(self, workflow_id: UUID) -> N8nWorkflowModel | None:
        """Получить workflow по ID.

        Args:
            workflow_id: UUID workflow.

        Returns:
            N8nWorkflowModel | None: Workflow или None.
        """
        return await self.repository.get_item_by_id(workflow_id)

    async def update_workflow(
        self,
        workflow_id: UUID,
        workflow_name: str | None = None,
        webhook_url: str | None = None,
        trigger_config: dict | None = None,
        is_active: bool | None = None,
    ) -> N8nWorkflowModel:
        """Обновить существующий workflow.

        Args:
            workflow_id: UUID workflow.
            workflow_name: Новое название (опционально).
            webhook_url: Новый webhook URL (опционально).
            trigger_config: Новая конфигурация (опционально).
            is_active: Новый статус активности (опционально).

        Returns:
            N8nWorkflowModel: Обновлённый workflow.

        Raises:
            ValueError: Если workflow не найден.
        """
        workflow = await self.repository.get_item_by_id(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} не найден")

        update_data = {}
        if workflow_name is not None:
            update_data["workflow_name"] = workflow_name
        if webhook_url is not None:
            update_data["webhook_url"] = webhook_url
        if trigger_config is not None:
            update_data["trigger_config"] = trigger_config
        if is_active is not None:
            update_data["is_active"] = is_active

        return await self.repository.update_item(workflow_id, update_data)

    async def trigger_workflow(self, workflow_id: UUID) -> N8nWorkflowModel:
        """Отметить выполнение workflow.

        Args:
            workflow_id: UUID workflow.

        Returns:
            N8nWorkflowModel: Обновлённый workflow.

        Raises:
            ValueError: Если workflow не найден или неактивен.
        """
        workflow = await self.repository.get_item_by_id(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} не найден")

        if not workflow.is_active:
            raise ValueError("Workflow неактивен")

        await self.repository.increment_execution_count(workflow_id)
        await self.repository.update_item(
            workflow_id,
            {"last_triggered_at": datetime.utcnow()},
        )

        return await self.repository.get_item_by_id(workflow_id)
