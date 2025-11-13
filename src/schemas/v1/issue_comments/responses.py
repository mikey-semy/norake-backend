"""
Pydantic схемы для выходных данных (responses) комментариев к проблемам.

Содержит:
    UserBriefSchema - краткая информация о пользователе.
    CommentDetailSchema - полная схема комментария для детального просмотра.
    CommentListItemSchema - упрощенная схема для списков комментариев.
    CommentResponseSchema - обертка для единичного ответа API.
    CommentListResponseSchema - обертка для списка комментариев.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseResponseSchema, BaseSchema, CommonBaseSchema


class UserBriefSchema(CommonBaseSchema):
    """
    Краткая информация о пользователе.

    Используется для отображения автора комментария без избыточной информации.
    Не содержит id, created_at, updated_at - только бизнес-данные.

    Attributes:
        username (str): Имя пользователя.
        email (str): Email адрес пользователя.

    Example:
        >>> author = UserBriefSchema(
        ...     username="john_doe",
        ...     email="john@example.com"
        ... )
    """

    username: str = Field(..., description="Имя пользователя")
    email: str = Field(..., description="Email пользователя")


class CommentDetailSchema(BaseSchema):
    """
    Детальная схема комментария с полной информацией.

    Наследует id, created_at, updated_at из BaseSchema.

    Attributes:
        issue_id (UUID): ID проблемы, к которой относится комментарий.
        author_id (UUID): ID автора комментария.
        author (UserBriefSchema): Информация об авторе комментария.
        content (str): Текстовое содержимое комментария.
        is_solution (bool): Флаг, отмечающий комментарий как решение.
        parent_id (Optional[UUID]): UUID родительского комментария для вложенности.
        replies (List['CommentDetailSchema']): Список вложенных ответов.

    Example:
        >>> comment = CommentDetailSchema(
        ...     id=uuid4(),
        ...     issue_id=uuid4(),
        ...     author_id=uuid4(),
        ...     author=UserBriefSchema(...),
        ...     content="Решение найдено",
        ...     is_solution=True,
        ...     parent_id=None,
        ...     replies=[],
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now()
        ... )
    """

    issue_id: UUID = Field(..., description="ID проблемы")
    author_id: UUID = Field(..., description="ID автора комментария")
    author: UserBriefSchema = Field(..., description="Автор комментария")
    content: str = Field(
        ...,
        description="Текстовое содержимое комментария",
    )
    is_solution: bool = Field(
        default=False,
        description="Флаг, отмечающий комментарий как решение",
    )
    parent_id: Optional[UUID] = Field(
        default=None,
        description="UUID родительского комментария",
    )
    replies: List['CommentDetailSchema'] = Field(
        default_factory=list,
        description="Список вложенных ответов",
    )


class CommentListItemSchema(BaseSchema):
    """
    Упрощенная схема комментария для списков.

    Наследует id, created_at, updated_at из BaseSchema.

    Attributes:
        issue_id (UUID): ID проблемы.
        author_id (UUID): ID автора (без вложенного объекта).
        content (str): Текстовое содержимое комментария.
        is_solution (bool): Флаг решения.
        parent_id (Optional[UUID]): UUID родительского комментария.
        replies_count (int): Количество вложенных ответов.

    Note:
        Для списков не загружаем полный объект автора для оптимизации.
    """

    issue_id: UUID = Field(..., description="ID проблемы")
    author_id: UUID = Field(..., description="ID автора комментария")
    content: str = Field(..., description="Текстовое содержимое комментария")
    is_solution: bool = Field(default=False, description="Флаг решения")
    parent_id: Optional[UUID] = Field(
        default=None, description="UUID родительского комментария"
    )
    replies_count: int = Field(
        default=0, description="Количество вложенных ответов"
    )


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

    data: Optional[CommentDetailSchema] = Field(
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

    data: Optional[List[CommentDetailSchema]] = Field(
        None, description="Список комментариев"
    )
