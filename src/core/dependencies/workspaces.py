"""
Зависимости для сервиса Workspace.

Этот модуль содержит провайдер (фабрику) для создания экземпляра сервиса
workspace с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_workspace_service: Провайдер для WorkspaceService

Typed Dependencies:
    - WorkspaceServiceDep: Типизированная зависимость для WorkspaceService

Usage:
    ```python
    from src.core.dependencies import WorkspaceServiceDep

    @router.post("/api/v1/workspaces")
    async def create_workspace(
        workspace_service: WorkspaceServiceDep = None,
        data: WorkspaceCreateSchema = ...,
        current_user: CurrentUserDep = None,
    ) -> WorkspaceResponseSchema:
        workspace = await workspace_service.create_workspace(current_user.id, data)
        return WorkspaceResponseSchema(data=workspace)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.services.v1.workspaces import WorkspaceService

logger = logging.getLogger(__name__)


async def get_workspace_service(
    session: AsyncSessionDep,
) -> WorkspaceService:
    """
    Провайдер для WorkspaceService.

    Создает экземпляр WorkspaceService с внедренными зависимостями:
    - Сессия базы данных (для работы с WorkspaceModel и WorkspaceMemberModel)

    Args:
        session: Асинхронная сессия базы данных.

    Returns:
        WorkspaceService: Готовый к использованию экземпляр сервиса.

    Example:
        >>> # Автоматическое внедрение через FastAPI Depends
        >>> @router.post("/workspaces")
        >>> async def create(
        ...     service: WorkspaceServiceDep = None,
        ... ) -> WorkspaceResponseSchema:
        ...     return await service.create_workspace(...)
    """
    logger.debug("Создание экземпляра WorkspaceService")
    return WorkspaceService(session=session)


# Типизированная зависимость для использования в роутерах
WorkspaceServiceDep = Annotated[
    WorkspaceService,
    Depends(get_workspace_service),
]
