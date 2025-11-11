"""
Базовые Pydantic схемы для комментариев к проблемам.

Содержит:
    CommentBaseSchema - базовая схема с общими полями.
"""

from pydantic import BaseModel, ConfigDict, Field


class CommentBaseSchema(BaseModel):
    """
    Базовая схема комментария к проблеме.

    Attributes:
        content (str): Текстовое содержимое комментария.
        is_solution (bool): Флаг, отмечающий комментарий как решение проблемы.

    Example:
        >>> comment_data = CommentBaseSchema(
        ...     content="Попробуйте перезагрузить сервер",
        ...     is_solution=False
        ... )
        >>> comment_data.content
        'Попробуйте перезагрузить сервер'
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "content": "Попробуйте перезагрузить сервер и проверить логи",
                "is_solution": False,
            }
        },
    )

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
