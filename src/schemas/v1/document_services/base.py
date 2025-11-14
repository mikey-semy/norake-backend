"""
Базовые схемы для работы с сервисами документов (Document Services) в API v1.

Этот модуль содержит основные Pydantic схемы для валидации сервисов документов
с поддержкой динамических JSONB полей для функций.

Схемы:
    - ServiceFunctionSchema: Схема для конфигурации функции сервиса
    - DocumentServiceBaseSchema: Базовая схема с общими полями сервиса документа

Использование:
    >>> # Конфигурация функции
    >>> function = ServiceFunctionSchema(
    ...     name="view_pdf",
    ...     enabled=True,
    ...     label="Открыть PDF",
    ...     icon="📄",
    ...     config={"viewer_type": "inline"}
    ... )

    >>> # Базовая схема сервиса
    >>> service_base = DocumentServiceBaseSchema(
    ...     title="Техническая документация",
    ...     description="Руководство по эксплуатации оборудования",
    ...     tags=["технический", "оборудование"],
    ...     available_functions=[function]
    ... )

Note:
    Все схемы наследуются от CommonBaseSchema и используют Field() для
    детального описания полей и валидации. JSONB поля валидируются через
    List[ServiceFunctionSchema].

See Also:
    - src.schemas.v1.document_services.requests: Схемы для входящих запросов
    - src.schemas.v1.document_services.responses: Схемы для HTTP ответов
    - src.models.v1.document_services: Модели DocumentService для базы данных
"""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from src.models.v1.document_services import (
    CoverType,
    DocumentFileType,
    ServiceFunctionType,
)
from src.schemas.base import CommonBaseSchema


class ServiceFunctionSchema(CommonBaseSchema):
    """
    Схема для конфигурации функции сервиса документа (JSONB).

    Описывает структуру одной функции, прикреплённой к сервису документа.
    Функции хранятся в JSONB и определяют возможности взаимодействия с документом.

    Attributes:
        name: Имя функции (VIEW_PDF, AI_CHAT, QR_CODE, SHARE, DOWNLOAD, CRUD_TABLE).
        enabled: Активна ли функция для данного сервиса.
        label: Отображаемое название функции для пользователя.
        icon: Иконка функции (emoji или имя icon).
        config: Конфигурация функции (специфичная для каждого типа).

    Example:
        >>> # Функция просмотра PDF
        >>> view_pdf = ServiceFunctionSchema(
        ...     name="view_pdf",
        ...     enabled=True,
        ...     label="Открыть PDF",
        ...     icon="📄",
        ...     config={"viewer_type": "inline", "allow_download": True}
        ... )

        >>> # Функция AI чата
        >>> ai_chat = ServiceFunctionSchema(
        ...     name="ai_chat",
        ...     enabled=True,
        ...     label="AI Ассистент",
        ...     icon="🤖",
        ...     config={"model": "gpt-4", "context_size": 8192}
        ... )
    """

    name: str = Field(
        ...,
        description="Имя функции (view_pdf, ai_chat, qr_code, share, download, crud_table)",
        examples=["view_pdf", "ai_chat", "qr_code"],
    )

    enabled: bool = Field(
        default=True,
        description="Активна ли функция",
    )

    label: str = Field(
        ...,
        description="Отображаемое название функции",
        min_length=1,
        max_length=100,
        examples=["Открыть PDF", "AI Ассистент", "Скачать QR-код"],
    )

    icon: Optional[str] = Field(
        default=None,
        description="Иконка функции (emoji или имя icon)",
        max_length=50,
        examples=["📄", "🤖", "📥"],
    )

    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Конфигурация функции (специфичная для каждого типа)",
        examples=[
            {"viewer_type": "inline", "allow_download": True},
            {"model": "gpt-4", "context_size": 8192},
        ],
    )

    @field_validator("name")
    @classmethod
    def validate_function_name(cls, value: str) -> str:
        """
        Валидирует имя функции на соответствие ServiceFunctionType.

        Args:
            value: Имя функции для валидации.

        Returns:
            Валидированное имя функции.

        Raises:
            ValueError: Если имя функции не соответствует допустимым значениям.
        """
        valid_names = [f.value for f in ServiceFunctionType]
        if value not in valid_names:
            raise ValueError(
                f"Недопустимое имя функции '{value}'. "
                f"Допустимые значения: {', '.join(valid_names)}"
            )
        return value


class DocumentServiceBaseSchema(CommonBaseSchema):
    """
    Базовая схема для сервиса документа.

    Содержит общие поля для создания и обновления сервисов документов.
    Используется как основа для request/response схем.

    Attributes:
        title: Название сервиса документа.
        description: Описание содержимого и назначения.
        tags: Теги для поиска и категоризации.
        file_type: Тип файла (PDF, SPREADSHEET, TEXT, IMAGE).
        cover_type: Тип обложки (GENERATED, ICON, IMAGE).
        cover_icon: Имя иконки для обложки (если cover_type=ICON).
        available_functions: Список доступных функций (JSONB).
        is_public: Публичный ли сервис (доступен всем без авторизации).

    Note:
        Поля file_url, file_size, cover_url устанавливаются автоматически
        при загрузке файла через service layer.

    Example:
        >>> # Базовый сервис документа
        >>> service = DocumentServiceBaseSchema(
        ...     title="Техническая документация",
        ...     description="Руководство по эксплуатации оборудования XYZ",
        ...     tags=["технический", "оборудование", "руководство"],
        ...     file_type=DocumentFileType.PDF,
        ...     cover_type=CoverType.GENERATED,
        ...     available_functions=[
        ...         ServiceFunctionSchema(
        ...             name="view_pdf",
        ...             enabled=True,
        ...             label="Открыть PDF",
        ...             icon="📄"
        ...         )
        ...     ],
        ...     is_public=False
        ... )
    """

    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Название сервиса документа",
        examples=["Техническая документация", "Прайс-лист 2025"],
    )

    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Описание содержимого и назначения документа",
        examples=["Руководство по эксплуатации оборудования XYZ"],
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Теги для поиска и категоризации",
        examples=[["технический", "оборудование"], ["прайс", "цены", "2025"]],
    )

    file_type: DocumentFileType = Field(
        default=DocumentFileType.PDF,
        description="Тип файла документа",
    )

    cover_type: CoverType = Field(
        default=CoverType.GENERATED,
        description="Тип обложки документа",
    )

    cover_icon: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Имя иконки для обложки (если cover_type=ICON)",
        examples=["📄", "📊", "📋"],
    )

    available_functions: List[ServiceFunctionSchema] = Field(
        default_factory=list,
        description="Список доступных функций (JSONB)",
    )

    is_public: bool = Field(
        default=False,
        description="Публичный ли сервис (доступен всем без авторизации)",
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: List[str]) -> List[str]:
        """
        Валидирует список тегов.

        Args:
            value: Список тегов.

        Returns:
            Валидированный список тегов.

        Raises:
            ValueError: Если тег пустой или слишком длинный.
        """
        if not value:
            return value

        for tag in value:
            if not tag or len(tag) > 50:
                raise ValueError(
                    f"Тег '{tag}' должен быть от 1 до 50 символов"
                )

        # Удаляем дубликаты, сохраняя порядок
        return list(dict.fromkeys(value))

    @field_validator("available_functions")
    @classmethod
    def validate_unique_functions(cls, value: List[ServiceFunctionSchema]) -> List[ServiceFunctionSchema]:
        """
        Валидирует уникальность имён функций.

        Args:
            value: Список функций.

        Returns:
            Валидированный список функций.

        Raises:
            ValueError: Если есть дубликаты имён функций.
        """
        if not value:
            return value

        function_names = [f.name for f in value]
        if len(function_names) != len(set(function_names)):
            raise ValueError("Имена функций должны быть уникальными")

        return value
