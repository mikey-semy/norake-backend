"""
Dependency providers для IssueCommentService.

Содержит:
    get_issue_comment_service - провайдер для инъекции IssueCommentService.
    IssueCommentServiceDep - типизированная зависимость для FastAPI.
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.services.v1.issue_comments import IssueCommentService

logger = logging.getLogger(__name__)


async def get_issue_comment_service(
    session: AsyncSessionDep,
) -> IssueCommentService:
    """
    Создаёт и возвращает экземпляр IssueCommentService.

    Args:
        session (AsyncSessionDep): Асинхронная сессия базы данных.

    Returns:
        IssueCommentService: Инициализированный сервис комментариев.

    Example:
        >>> # В роутере
        >>> async def create_comment(
        ...     service: IssueCommentServiceDep = None
        ... ):
        ...     comment = await service.create_comment(...)
        ...     return comment
    """
    logger.debug("🔍 Создание экземпляра IssueCommentService")
    return IssueCommentService(session=session)


# Типизированная зависимость для использования в роутерах
IssueCommentServiceDep = Annotated[
    IssueCommentService,
    Depends(get_issue_comment_service),
]
