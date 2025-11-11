"""
Pydantic схемы для выходных данных (responses) комментариев к проблемам.

Содержит:
    CommentDetailSchema - полная схема комментария для детального просмотра.
    CommentListItemSchema - упрощенная схема для списков комментариев.
    CommentResponseSchema - обертка для единичного ответа API.
    CommentListResponseSchema - обертка для списка комментариев.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from pydantic import Field

from ..users.responses import UserDetailSchema
from ...base import BaseResponseSchema
from .base import CommentBaseSchema


class CommentDetailSchema(CommentBaseSchema):
    """
    Детальная схема комментария с полной информацией.

    Attributes:
        id (UUID): Уникальный идентификатор комментария.
        issue_id (UUID): ID проблемы, к которой относится комментарий.
        author (UserDetailSchema): Информация об авторе комментария.
        content (str): Текстовое содержимое комментария.
        is_solution (bool): Флаг, отмечающий комментарий как решение.
        created_at (datetime): Дата и время создания комментария.
        updated_at (datetime): Дата и время последнего обновления.

    Example:
        >>> comment = CommentDetailSchema(
        ...     id=uuid4(),
        ...     issue_id=uuid4(),
        ...     author=UserDetailSchema(...),
        ...     content="Решение найдено",
        ...     is_solution=True,
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now()
        ... )
    """

    id: UUID = Field(..., description="Уникальный идентификатор комментария")
    issue_id: UUID = Field(..., description="ID проблемы")
    author: UserDetailSchema = Field(..., description="Автор комментария")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата последнего обновления")


class CommentListItemSchema(CommentBaseSchema):
    """
    Упрощенная схема комментария для списков.

    Attributes:
        id (UUID): Уникальный идентификатор комментария.
        issue_id (UUID): ID проблемы.
        author_id (UUID): ID автора (без вложенного объекта).
        content (str): Текстовое содержимое комментария.
        is_solution (bool): Флаг решения.
        created_at (datetime): Дата создания.

    Note:
        Для списков не загружаем полный объект автора для оптимизации.
    """

    id: UUID = Field(..., description="Уникальный идентификатор комментария")
    issue_id: UUID = Field(..., description="ID проблемы")
    author_id: UUID = Field(..., description="ID автора комментария")
    created_at: datetime = Field(..., description="Дата создания")


class CommentResponseSchema(BaseResponseSchema):
    """
    Обёртка для единичного ответа API с комментарием.

    Attributes:
        data (CommentDetailSchema | None): Данные комментария или None при ошибке.

    Example:
        >>> response = CommentResponseSchema(
        ...     success=True,
        ...     message="Комментарий создан успешно",
        ...     data=CommentDetailSchema(...)
        ... )
    """

    data: CommentDetailSchema | None = Field(
        None, description="Данные комментария"
    )


class CommentListResponseSchema(BaseResponseSchema):
    """
    Обёртка для списка комментариев.

    Attributes:
        data (List[CommentDetailSchema] | None): Список комментариев или None при ошибке.

    Example:
        >>> response = CommentListResponseSchema(
        ...     success=True,
        ...     message="Комментарии получены успешно",
        ...     data=[CommentDetailSchema(...), CommentDetailSchema(...)]
        ... )
    """

    data: List[CommentDetailSchema] | None = Field(
        None, description="Список комментариев"
    )
