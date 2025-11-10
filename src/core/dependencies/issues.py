"""
Зависимости для сервиса проблем (Issues).

Этот модуль содержит провайдер (фабрику) для создания экземпляра сервиса
проблем с автоматическим внедрением зависимостей через FastAPI Depends.

Providers:
    - get_issue_service: Провайдер для IssueService

Typed Dependencies:
    - IssueServiceDep: Типизированная зависимость для IssueService

Usage:
    ```python
    from src.core.dependencies import IssueServiceDep

    @router.post("/issues")
    async def create_issue(
        issue_service: IssueServiceDep = None,
        data: IssueCreateRequestSchema = ...,
    ) -> IssueResponseSchema:
        issue = await issue_service.create_issue(...)
        return IssueResponseSchema(success=True, data=issue)
    ```
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.services.v1.issues import IssueService

logger = logging.getLogger(__name__)


async def get_issue_service(
    session: AsyncSessionDep,
) -> IssueService:
    """
    Провайдер для IssueService.

    Создаёт экземпляр IssueService с внедрёнными зависимостями:
    - Сессия базы данных (для работы с IssueModel)

    Args:
        session: Асинхронная сессия базы данных.

    Returns:
        IssueService: Настроенный экземпляр сервиса проблем.

    Raises:
        ServiceUnavailableException: Если не удается создать сервис.

    Example:
        ```python
        # Автоматическое внедрение через FastAPI
        @router.get("/issues")
        async def list_issues(
            issue_service: IssueServiceDep = None,
        ):
            issues = await issue_service.list_issues()
            return issues
        ```
    """
    try:
        logger.debug("Создание экземпляра IssueService")
        return IssueService(session=session)
    except Exception as e:
        logger.error(
            "Ошибка при создании IssueService: %s", str(e), exc_info=True
        )
        raise


# Типизированная зависимость для удобства использования
IssueServiceDep = Annotated[IssueService, Depends(get_issue_service)]
