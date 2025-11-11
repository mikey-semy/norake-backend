"""
Схемы запросов для работы с проблемами (Issues) в API v1.

Этот модуль содержит Pydantic схемы для валидации входящих запросов
при работе с проблемами.

Схемы:
    - IssueCreateRequestSchema: Создание новой проблемы
    - IssueUpdateRequestSchema: Обновление существующей проблемы
    - IssueResolveRequestSchema: Решение проблемы (закрытие)
    - IssueQueryRequestSchema: Фильтрация и поиск проблем

Использование:
    >>> # Создание проблемы
    >>> create_data = IssueCreateRequestSchema(
    ...     title="Ошибка E401",
    ...     description="Проблема с оборудованием",
    ...     category="hardware"
    ... )
    
    >>> # Решение проблемы
    >>> resolve_data = IssueResolveRequestSchema(
    ...     solution="Заменён датчик положения"
    ... )

Note:
    Все схемы наследуются от BaseRequestSchema и не содержат
    системных полей (id, created_at, updated_at).

See Also:
    - src.schemas.v1.issues.base: Базовые схемы
    - src.schemas.v1.issues.responses: Схемы ответов
"""
from typing import Optional
from uuid import UUID

from pydantic import Field

from src.schemas.base import BaseRequestSchema


class IssueCreateRequestSchema(BaseRequestSchema):
    """
    Схема для создания новой проблемы.

    Attributes:
        title: Заголовок проблемы (до 255 символов).
        description: Подробное описание проблемы.
        category: Категория проблемы (hardware/software/process).
        workspace_id: UUID рабочего пространства (workspace).

    Note:
        Поля status, author_id, solution, resolved_at устанавливаются автоматически:
        - status = "red" (по умолчанию при создании)
        - author_id = текущий пользователь
        - solution = None
        - resolved_at = None

    Example:
        POST /api/v1/issues
        {
            "title": "Ошибка E401 на станке №3",
            "description": "При запуске станка возникает ошибка E401",
            "category": "hardware",
            "workspace_id": "123e4567-e89b-12d3-a456-426614174000"
        }
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
        description="Категория проблемы (hardware, software, process)",
        examples=["hardware", "software", "process"],
    )
    workspace_id: UUID = Field(
        description="UUID рабочего пространства",
        examples=["123e4567-e89b-12d3-a456-426614174000"],
    )


class IssueUpdateRequestSchema(BaseRequestSchema):
    """
    Схема для обновления существующей проблемы.

    Все поля опциональны - обновляются только переданные поля.

    Attributes:
        title: Новый заголовок проблемы.
        description: Новое описание проблемы.
        category: Новая категория проблемы.

    Note:
        Изменение статуса на 'green' выполняется через IssueResolveRequestSchema.

    Example:
        PATCH /api/v1/issues/{issue_id}
        {
            "title": "Ошибка E401 - обновлённое описание",
            "category": "software"
        }
    """

    title: Optional[str] = Field(
        None,
        max_length=255,
        description="Новый заголовок проблемы",
    )
    description: Optional[str] = Field(
        None,
        description="Новое описание проблемы",
    )
    category: Optional[str] = Field(
        None,
        max_length=50,
        description="Новая категория проблемы",
    )


class IssueResolveRequestSchema(BaseRequestSchema):
    """
    Схема для решения проблемы (закрытия с решением).

    Attributes:
        solution: Текст решения проблемы.

    Note:
        При решении проблемы автоматически:
        - status → 'green'
        - resolved_at → datetime.now(timezone.utc)

    Example:
        POST /api/v1/issues/{issue_id}/resolve
        {
            "solution": "Заменён датчик положения, проблема устранена"
        }
    """

    solution: str = Field(
        description="Текст решения проблемы",
        examples=["Заменён датчик положения, проблема устранена"],
    )


class IssueQueryRequestSchema(BaseRequestSchema):
    """
    Схема для фильтрации и поиска проблем.

    Все поля опциональны - используются для построения WHERE условий.

    Attributes:
        status: Фильтр по статусу (red/green).
        category: Фильтр по категории.
        author_id: Фильтр по автору (UUID).
        search: Поиск по title и description.
        limit: Количество результатов (по умолчанию 50).
        offset: Смещение для пагинации (по умолчанию 0).

    Example:
        GET /api/v1/issues?status=red&category=hardware&limit=10
    """

    status: Optional[str] = Field(
        None,
        description="Фильтр по статусу (red/green)",
        examples=["red", "green"],
    )
    category: Optional[str] = Field(
        None,
        description="Фильтр по категории",
        examples=["hardware", "software", "process"],
    )
    author_id: Optional[str] = Field(
        None,
        description="Фильтр по автору (UUID)",
    )
    search: Optional[str] = Field(
        None,
        description="Поиск по заголовку и описанию",
        examples=["ошибка E401"],
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Количество результатов (1-100)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Смещение для пагинации",
    )
