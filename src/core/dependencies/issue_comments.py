"""
Dependency providers для IssueCommentRepository и IssueCommentService.

Содержит:
    get_issue_comment_repository - провайдер для инъекции IssueCommentRepository.
    get_issue_comment_service - провайдер для инъекции IssueCommentService.
    IssueCommentRepositoryDep - типизированная зависимость для FastAPI.
    IssueCommentServiceDep - типизированная зависимость для FastAPI.
"""

import logging
from typing import Annotated

from fastapi import Depends

from src.core.dependencies.database import AsyncSessionDep
from src.repository.v1.issue_comments import IssueCommentRepository
from src.services.v1.issue_comments import IssueCommentService

logger = logging.getLogger(__name__)


async def get_issue_comment_repository(
    session: AsyncSessionDep,
) -> IssueCommentRepository:
    """
    Создаёт и возвращает экземпляр IssueCommentRepository.

    Args:
        session (AsyncSessionDep): Асинхронная сессия базы данных.

    Returns:
        IssueCommentRepository: Инициализированный репозиторий комментариев.

    Example:
        >>> # В роутере
        >>> async def get_comments(
        ...     repo: IssueCommentRepositoryDep = None
        ... ):
        ...     comments = await repo.get_issue_comments(issue_id)
        ...     return comments
    """
    logger.debug("🔍 Создание экземпляра IssueCommentRepository")
    return IssueCommentRepository(session=session)


# Типизированная зависимость для репозитория
IssueCommentRepositoryDep = Annotated[
    IssueCommentRepository,
    Depends(get_issue_comment_repository),
]


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
