"""
Базовые схемы для работы с проблемами (Issues) в API v1.

Этот модуль содержит основные Pydantic схемы для валидации данных проблем.
Схемы используются как базовые классы для request и response схем.

Схемы:
    - IssueStatusSchema: Enum-схема для статусов проблем (RED/GREEN)
    - IssueBaseSchema: Базовая схема с общими полями проблемы
    - IssueAuthorSchema: Схема для отображения автора проблемы

Использование:
    >>> # Валидация статуса
    >>> status = IssueStatusSchema(status="red")

    >>> # Базовая схема проблемы
    >>> issue_base = IssueBaseSchema(
    ...     title="Ошибка E401",
    ...     description="Проблема с оборудованием",
    ...     category="hardware"
    ... )

Note:
    Все схемы наследуются от CommonBaseSchema и используют Field() для
    детального описания полей и валидации.

See Also:
    - src.schemas.v1.issues.requests: Схемы для входящих запросов
    - src.schemas.v1.issues.responses: Схемы для HTTP ответов
    - src.models.v1.issues: Модели Issues для базы данных
"""

import uuid

from pydantic import Field

from src.schemas.base import CommonBaseSchema


class IssueStatusSchema(CommonBaseSchema):
    """
    Схема для статуса проблемы.

    Attributes:
        status: Статус проблемы ('red' - не решена, 'green' - решена).

    Example:
        >>> status = IssueStatusSchema(status="red")
        >>> status.status
        'red'
    """

    status: str = Field(
        description="Статус проблемы (red/green)",
        examples=["red", "green"],
    )


class IssueAuthorSchema(CommonBaseSchema):
    """
    Схема для отображения автора проблемы.

    Используется в response-схемах для предоставления информации об авторе.

    Attributes:
        id: UUID автора.
        username: Имя пользователя.
        email: Email адрес.

    Example:
        >>> author = IssueAuthorSchema(
        ...     id=uuid4(),
        ...     username="john_doe",
        ...     email="john@example.com"
        ... )
    """

    id: uuid.UUID = Field(description="UUID автора")
    username: str = Field(description="Имя пользователя")
    email: str = Field(description="Email адрес")


class IssueBaseSchema(CommonBaseSchema):
    """
    Базовая схема проблемы с общими полями.

    Содержит основные атрибуты проблемы, используется как базовый класс
    для схем создания, обновления и отображения проблем.

    Attributes:
        title: Заголовок проблемы (до 255 символов).
        description: Подробное описание проблемы.
        category: Категория проблемы (hardware/software/process).
        status: Статус проблемы (red/green).

    Note:
        Не содержит полей solution, author_id, resolved_at - они
        добавляются в конкретных схемах по необходимости.

    Example:
        >>> issue = IssueBaseSchema(
        ...     title="Ошибка E401 на станке",
        ...     description="При запуске возникает ошибка",
        ...     category="hardware",
        ...     status="red"
        ... )
    """

    title: str = Field(
        max_length=255,
        description="Заголовок проблемы",
        examples=["Ошибка E401 на станке №3"],
    )
    description: str = Field(
        description="Подробное описание проблемы",
        examples=["При запуске станка возникает ошибка E401, индикатор мигает красным"],
    )
    category: str = Field(
        max_length=50,
        description="Категория проблемы",
        examples=["hardware", "software", "process"],
    )
    status: str = Field(
        default="red",
        description="Статус проблемы (red - не решена, green - решена)",
        examples=["red", "green"],
    )
