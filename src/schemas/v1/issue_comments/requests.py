"""
Pydantic схемы для входных данных (requests) комментариев к проблемам.

Содержит:
    CommentCreateRequestSchema - схема для создания комментария.
    CommentUpdateRequestSchema - схема для обновления комментария.
"""

from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseRequestSchema


class CommentCreateRequestSchema(BaseRequestSchema):
    """
    Схема для создания нового комментария.

    Attributes:
        content (str): Текстовое содержимое комментария (обязательное).
        is_solution (bool): Флаг решения (опциональный, по умолчанию False).
        parent_id (Optional[UUID]): UUID родительского комментария для вложенности.

    Example:
        >>> comment_create = CommentCreateRequestSchema(
        ...     content="Проблема решена после перезагрузки",
        ...     is_solution=True
        ... )
        >>> comment_create.content
        'Проблема решена после перезагрузки'
        >>> comment_create.is_solution
        True

    Note:
        issue_id и author_id берутся из контекста запроса (URL и CurrentUserDep),
        поэтому не включены в схему создания.
    """

    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Текстовое содержимое комментария",
        examples=["Попробуйте перезагрузить сервер"],
    )

    is_solution: bool = Field(
        default=False,
        description="Флаг, отмечающий комментарий как решение проблемы",
        examples=[False, True],
    )

    parent_id: Optional[UUID] = Field(
        default=None,
        description="UUID родительского комментария для вложенных ответов",
        examples=["123e4567-e89b-12d3-a456-426614174001"],
    )


class CommentUpdateRequestSchema(BaseRequestSchema):
    """
    Схема для обновления комментария.

    Все поля опциональны.

    Attributes:
        content (Optional[str]): Новое текстовое содержимое.
        is_solution (Optional[bool]): Новое значение флага решения.

    Example:
        >>> comment_update = CommentUpdateRequestSchema(
        ...     is_solution=True
        ... )
    """

    content: Optional[str] = Field(
        None,
        min_length=1,
        max_length=5000,
        description="Новое текстовое содержимое комментария",
    )

    is_solution: Optional[bool] = Field(
        None,
        description="Новое значение флага решения",
    )
