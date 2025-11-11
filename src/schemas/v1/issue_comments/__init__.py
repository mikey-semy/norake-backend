"""
Pydantic схемы для комментариев к проблемам.

Экспортируемые схемы:
    Base: CommentBaseSchema
    Requests: CommentCreateSchema
    Responses: CommentDetailSchema, CommentListItemSchema, CommentResponseSchema, CommentListResponseSchema
"""

from src.schemas.v1.issue_comments.base import CommentBaseSchema
from src.schemas.v1.issue_comments.requests import CommentCreateSchema
from src.schemas.v1.issue_comments.responses import (
    CommentDetailSchema,
    CommentListItemSchema,
    CommentListResponseSchema,
    CommentResponseSchema,
)

__all__ = [
    # Base
    "CommentBaseSchema",
    # Requests
    "CommentCreateSchema",
    # Responses
    "CommentDetailSchema",
    "CommentListItemSchema",
    "CommentResponseSchema",
    "CommentListResponseSchema",
]
