"""
Базовые схемы для работы с шаблонами (Templates) в API v1.

Этот модуль содержит основные Pydantic схемы для валидации шаблонов проблем
с поддержкой динамических JSONB полей.

Схемы:
    - TemplateFieldSchema: Схема для динамических полей шаблона
    - TemplateVisibilitySchema: Enum-схема для видимости (PUBLIC/PRIVATE/TEAM)
    - TemplateBaseSchema: Базовая схема с общими полями шаблона

Использование:
    >>> # Динамическое поле шаблона
    >>> field = TemplateFieldSchema(
    ...     name="equipment_id",
    ...     label="ID оборудования",
    ...     type="text",
    ...     required=True
    ... )

    >>> # Базовая схема шаблона
    >>> template_base = TemplateBaseSchema(
    ...     title="Аппаратная проблема",
    ...     description="Шаблон для аппаратных неисправностей",
    ...     category="hardware",
    ...     fields=[field]
    ... )

Note:
    Все схемы наследуются от CommonBaseSchema и используют Field() для
    детального описания полей и валидации. JSONB поля валидируются через
    List[TemplateFieldSchema].

See Also:
    - src.schemas.v1.templates.requests: Схемы для входящих запросов
    - src.schemas.v1.templates.responses: Схемы для HTTP ответов
    - src.models.v1.templates: Модели Templates для базы данных
"""

from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from src.core.settings import settings
from src.models.v1.templates import TemplateVisibility
from src.schemas.base import CommonBaseSchema


class TemplateFieldSchema(CommonBaseSchema):
    """
    Схема для динамического поля шаблона (JSONB).

    Описывает структуру одного поля в шаблоне проблемы.
    Поля хранятся в JSONB и позволяют создавать динамические формы.

    Attributes:
        name: Имя поля (используется как ключ в форме).
        label: Отображаемое название поля для пользователя.
        type: Тип поля (text, number, date, select, textarea).
        required: Обязательное ли поле для заполнения.
        placeholder: Текст-подсказка в поле (опционально).
        options: Варианты выбора для select (опционально).
        validation: Правила валидации (regex, min, max и т.д.).

    Example:
        >>> # Текстовое обязательное поле
        >>> equipment_id = TemplateFieldSchema(
        ...     name="equipment_id",
        ...     label="ID оборудования",
        ...     type="text",
        ...     required=True,
        ...     placeholder="Введите номер оборудования"
        ... )

        >>> # Поле выбора
        >>> status = TemplateFieldSchema(
        ...     name="status",
        ...     label="Статус оборудования",
        ...     type="select",
        ...     required=True,
        ...     options=["работает", "остановлено", "в ремонте"]
        ... )
    """

    name: Optional[str] = Field(
        default=None,
        description="Имя поля (используется как ключ)",
        min_length=1,
        max_length=100,
        examples=["equipment_id", "error_code"],
    )

    label: str = Field(
        ...,
        description="Отображаемое название поля",
        min_length=1,
        max_length=200,
        examples=["ID оборудования", "Код ошибки"],
    )

    type: Optional[str] = Field(
        default="text",
        description="Тип поля (text, number, date, select, textarea)",
        examples=["text", "number", "select"],
    )

    required: bool = Field(
        default=False, description="Обязательное ли поле"
    )

    placeholder: Optional[str] = Field(
        default=None,
        description="Текст-подсказка в поле",
        max_length=200,
    )

    options: Optional[List[str]] = Field(
        default=None,
        description="Варианты выбора для select (если type=select)",
    )

    validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Правила валидации (regex, min, max и т.д.)",
    )

    @field_validator("name", mode="before")
    @classmethod
    def generate_name_from_label(cls, v: Optional[str], info) -> str:
        """
        Генерирует name из label если name отсутствует.

        Args:
            v: Значение name.
            info: ValidationInfo с контекстом.

        Returns:
            str: Name поля (оригинальное или сгенерированное).
        """
        if v:
            return v
        # Генерируем name из label: "Код ошибки" -> "код_ошибки"
        label = info.data.get("label", "")
        if label:
            return label.lower().replace(" ", "_").replace("-", "_")
        return "field"

    @field_validator("type")
    @classmethod
    def validate_field_type(cls, v: str) -> str:
        """
        Валидирует допустимые типы полей.

        Args:
            v: Тип поля для валидации.

        Returns:
            str: Валидированный тип поля.

        Raises:
            ValueError: Если тип не входит в список допустимых.
        """
        allowed_types = {"text", "number", "date", "select", "textarea", "radio", "checkbox", "time"}
        if v and v not in allowed_types:
            raise ValueError(
                f"Недопустимый тип поля '{v}'. "
                f"Разрешены: {', '.join(allowed_types)}"
            )
        return v or "text"

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, v: Optional[List[Any]]) -> Optional[List[str]]:
        """
        Нормализует options: преобразует объекты {label, value} в строки.

        Args:
            v: Список опций (может быть строками или объектами).

        Returns:
            Optional[List[str]]: Нормализованный список строк.

        Example:
            >>> # Input: [{"label": "LOW", "value": "low"}]
            >>> # Output: ["low"]
        """
        if not v:
            return v
        
        normalized = []
        for option in v:
            if isinstance(option, dict):
                # Извлекаем value из объекта {label, value}
                normalized.append(option.get("value", option.get("label", "")))
            else:
                normalized.append(str(option))
        return normalized

    @field_validator("options")
    @classmethod
    def validate_options(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """
        Валидирует options для select полей.

        Args:
            v: Список опций для валидации.

        Returns:
            Optional[List[str]]: Валидированный список опций.

        Note:
            Проверка наличия options для select отключена (soft validation).
        """
        return v


class TemplateVisibilitySchema(CommonBaseSchema):
    """
    Схема для видимости шаблона.

    Attributes:
        visibility: Уровень видимости (PUBLIC/PRIVATE/TEAM).

    Example:
        >>> visibility = TemplateVisibilitySchema(visibility="PUBLIC")
        >>> visibility.visibility
        <TemplateVisibility.PUBLIC: 'PUBLIC'>
    """

    visibility: TemplateVisibility = Field(
        default=TemplateVisibility.PRIVATE,
        description="Уровень видимости шаблона",
    )


class TemplateBaseSchema(CommonBaseSchema):
    """
    Базовая схема для шаблона проблемы.

    Содержит общие поля, используемые в request и response схемах.
    Поддерживает динамические JSONB поля через List[TemplateFieldSchema].

    Attributes:
        title: Название шаблона.
        description: Описание назначения шаблона.
        category: Категория (hardware/software/process/documentation/safety/
            quality/maintenance/training/other).
        fields: Список динамических полей шаблона (JSONB).
        visibility: Уровень видимости (PUBLIC/PRIVATE/TEAM).

    Example:
        >>> template = TemplateBaseSchema(
        ...     title="Аппаратная неисправность",
        ...     description="Шаблон для описания проблем с оборудованием",
        ...     category="hardware",
        ...     fields=[
        ...         TemplateFieldSchema(
        ...             name="equipment_id",
        ...             label="ID оборудования",
        ...             type="text",
        ...             required=True
        ...         )
        ...     ],
        ...     visibility=TemplateVisibility.PUBLIC
        ... )
    """

    title: str = Field(
        ...,
        description="Название шаблона",
        min_length=3,
        max_length=200,
        examples=["Аппаратная неисправность", "Ошибка ПО"],
    )

    description: Optional[str] = Field(
        default=None,
        description="Описание назначения шаблона",
        max_length=1000,
    )

    category: str = Field(
        ...,
        description="Категория шаблона (hardware, software, process, documentation, "
        "safety, quality, maintenance, training, other)",
        examples=["hardware", "software", "process", "documentation", "safety"],
    )

    fields: List[TemplateFieldSchema] = Field(
        default_factory=list,
        description="Динамические поля шаблона (JSONB)",
    )

    visibility: TemplateVisibility = Field(
        default=TemplateVisibility.PRIVATE,
        description="Уровень видимости шаблона",
    )

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """
        Валидирует категорию шаблона.

        Args:
            v: Категория для валидации.

        Returns:
            str: Валидированная категория.

        Raises:
            ValueError: Если категория не входит в список допустимых.
        """
        if v not in settings.ISSUE_CATEGORIES:
            raise ValueError(
                f"Недопустимая категория '{v}'. "
                f"Разрешены: {', '.join(settings.ISSUE_CATEGORIES)}"
            )
        return v
