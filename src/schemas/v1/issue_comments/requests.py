"""
Pydantic схемы для входных данных (requests) комментариев к проблемам.

Содержит:
    CommentCreateSchema - схема для создания комментария.
"""

from pydantic import Field

from .base import CommentBaseSchema


class CommentCreateSchema(CommentBaseSchema):
    """
    Схема для создания нового комментария.

    Attributes:
        content (str): Текстовое содержимое комментария (обязательное).
        is_solution (bool): Флаг решения (опциональный, по умолчанию False).

    Example:
        >>> comment_create = CommentCreateSchema(
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

    pass  # Наследует все поля от CommentBaseSchema
