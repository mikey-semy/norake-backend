"""Dependency providers для n8n workflows."""

from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.repository.v1.n8n_workflows import N8nWorkflowRepository
from src.services.v1.n8n_workflows import N8nWorkflowService


async def get_n8n_workflow_repository(
    session: AsyncSessionDep,
) -> N8nWorkflowRepository:
    """Получить repository для n8n workflows.

    Args:
        session: Async сессия БД.

    Returns:
        N8nWorkflowRepository: Repository для workflows.
    """
    return N8nWorkflowRepository(session)


async def get_n8n_workflow_service(
    repository: Annotated[N8nWorkflowRepository, Depends(get_n8n_workflow_repository)],
) -> N8nWorkflowService:
    """Получить service для n8n workflows.

    Args:
        repository: Repository для workflows.

    Returns:
        N8nWorkflowService: Service для workflows.
    """
    return N8nWorkflowService(repository=repository)


N8nWorkflowServiceDep = Annotated[N8nWorkflowService, Depends(get_n8n_workflow_service)]
