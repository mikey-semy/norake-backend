"""
Модуль схем для работы с проблемами (Issues) в API v1.

Экспортируемые схемы:
    Base:
        - IssueStatusSchema
        - IssueAuthorSchema
        - IssueBaseSchema
    
    Requests:
        - IssueCreateRequestSchema
        - IssueUpdateRequestSchema
        - IssueResolveRequestSchema
        - IssueQueryRequestSchema
    
    Responses:
        - IssueDetailSchema
        - IssueListItemSchema
        - IssueResponseSchema
        - IssueListResponseSchema
"""

from .base import IssueAuthorSchema, IssueBaseSchema, IssueStatusSchema
from .requests import (
    IssueCreateRequestSchema,
    IssueQueryRequestSchema,
    IssueResolveRequestSchema,
    IssueUpdateRequestSchema,
)
from .responses import (
    IssueDetailSchema,
    IssueListItemSchema,
    IssueListResponseSchema,
    IssueResponseSchema,
)

__all__ = [
    # Base
    "IssueStatusSchema",
    "IssueAuthorSchema",
    "IssueBaseSchema",
    # Requests
    "IssueCreateRequestSchema",
    "IssueUpdateRequestSchema",
    "IssueResolveRequestSchema",
    "IssueQueryRequestSchema",
    # Responses
    "IssueDetailSchema",
    "IssueListItemSchema",
    "IssueResponseSchema",
    "IssueListResponseSchema",
]
