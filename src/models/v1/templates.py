"""
Модели для работы с шаблонами проблем (Templates).

Шаблоны позволяют создавать настраиваемые формы для Issues с динамической
структурой полей через JSONB. Поддерживают видимость (public/private),
отслеживают использование и могут быть добавлены в избранное.

Classes:
    TemplateVisibility: Enum для видимости шаблона.
    TemplateModel: Модель шаблона с JSONB полями.

Example:
    >>> template = TemplateModel(
    ...     title="Проблема с оборудованием",
    ...     category="hardware",
    ...     fields={
    ...         "fields": [
    ...             {
    ...                 "name": "equipment_model",
    ...                 "label": "Модель оборудования",
    ...                 "type": "text",
    ...                 "required": True
    ...             }
    ...         ]
    ...     },
    ...     author_id=user_id
    ... )
"""

import enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import BaseModel

if TYPE_CHECKING:
    from src.models.v1.issues import IssueModel
    from src.models.v1.users import UserModel


class TemplateVisibility(str, enum.Enum):
    """
    Enum для видимости шаблона.

    Определяет, кто может видеть и использовать шаблон:
    - PUBLIC: доступен всем пользователям
    - PRIVATE: доступен только автору
    - TEAM: доступен команде (будет в v0.2)

    Attributes:
        PUBLIC: Шаблон доступен всем.
        PRIVATE: Шаблон доступен только создателю.
        TEAM: Шаблон доступен команде (в будущем).
    """

    PUBLIC = "public"
    PRIVATE = "private"
    TEAM = "team"


class TemplateModel(BaseModel):
    """
    Модель шаблона для создания проблем с настраиваемыми полями.

    Шаблон определяет структуру формы для создания Issue через JSONB поле.
    Поддерживает различные типы полей: text, textarea, number, select,
    radio, checkbox, date, time. Отслеживает количество использований.

    Attributes:
        title: Название шаблона (например, "Проблема с оборудованием").
        description: Описание назначения шаблона (опционально).
        category: Категория проблем (hardware, software, process).
        fields: JSONB структура с определением полей формы.
        visibility: Видимость шаблона (public/private/team).
        author_id: UUID создателя шаблона (FK users.id).
        usage_count: Счётчик использований шаблона.
        is_active: Флаг активности (можно деактивировать старые шаблоны).
        author: Relationship к создателю шаблона.

    JSONB Structure (fields):
        {
            "fields": [
                {
                    "name": "equipment_model",
                    "label": "Модель оборудования",
                    "type": "text",
                    "required": true,
                    "placeholder": "Например: KUKA KR 500-3",
                    "help_text": "Укажите полное название модели"
                },
                {
                    "name": "error_code",
                    "label": "Код ошибки",
                    "type": "text",
                    "required": false,
                    "pattern": "^[A-Z]{1,3}\\d{1,4}$"
                },
                {
                    "name": "location",
                    "label": "Местоположение",
                    "type": "select",
                    "options": ["Цех 1", "Цех 2", "Цех 3"],
                    "required": true
                }
            ]
        }

    Supported Field Types:
        - text: текстовое поле
        - textarea: многострочный текст
        - number: числовое поле
        - select: выпадающий список
        - radio: радиокнопки
        - checkbox: чекбокс
        - date: календарь
        - time: время

    Example:
        >>> # Создание шаблона для оборудования
        >>> template = TemplateModel(
        ...     title="Проблема с оборудованием",
        ...     description="Для проблем с производственным оборудованием",
        ...     category="hardware",
        ...     fields={
        ...         "fields": [
        ...             {
        ...                 "name": "equipment_model",
        ...                 "label": "Модель оборудования",
        ...                 "type": "text",
        ...                 "required": True
        ...             },
        ...             {
        ...                 "name": "location",
        ...                 "label": "Местоположение",
        ...                 "type": "select",
        ...                 "options": ["Цех 1", "Цех 2", "Цех 3"],
        ...                 "required": True
        ...             }
        ...         ]
        ...     },
        ...     visibility=TemplateVisibility.PUBLIC,
        ...     author_id=user_id
        ... )
        >>> session.add(template)
        >>> await session.commit()
    """

    __tablename__ = "templates"

    # Основная информация
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Название шаблона"
    )

    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Описание назначения шаблона"
    )

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Категория проблем (hardware, software, process)",
    )

    # Динамические поля (JSONB)
    fields: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="JSON структура с определением полей формы",
    )

    # Видимость и владение
    visibility: Mapped[TemplateVisibility] = mapped_column(
        String(20),
        nullable=False,
        default=TemplateVisibility.PRIVATE,
        index=True,
        comment="Видимость шаблона (public/private/team)",
    )

    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID создателя шаблона",
    )

    # Метрики
    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Счётчик использований шаблона",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Флаг активности шаблона",
    )

    # Relationships
    author: Mapped["UserModel"] = relationship(
        "UserModel",
        foreign_keys=[author_id],
        back_populates="templates",
    )

    issues: Mapped[list["IssueModel"]] = relationship(
        "IssueModel",
        back_populates="template",
        lazy="selectin",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:
        """Строковое представление шаблона."""
        return (
            f"<TemplateModel("
            f"id={self.id}, "
            f"title={self.title!r}, "
            f"category={self.category!r}, "
            f"visibility={self.visibility.value}, "
            f"usage_count={self.usage_count}"
            f")>"
        )
