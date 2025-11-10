"""
Сервис для управления шаблонами проблем (Template Service).

Содержит бизнес-логику для работы с шаблонами: валидация, контроль доступа,
CRUD-операции. Только владелец (author) может редактировать/удалять шаблоны.

Classes:
    TemplateService: Сервис с методами create, get, update, delete, list.
"""

from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    TemplateNotFoundError,
    TemplatePermissionDeniedError,
    TemplateValidationError,
)
from src.models.v1.templates import TemplateModel, TemplateVisibility
from src.repository.v1.templates import TemplateRepository
from src.schemas.v1.templates.requests import (
    TemplateCreateRequestSchema,
    TemplateUpdateRequestSchema,
    TemplateQueryRequestSchema,
)

# Разрешённые категории шаблонов (синхронизировано с IssueModel)
ALLOWED_CATEGORIES = ["hardware", "software", "process"]

# Валидация типов полей в JSONB
ALLOWED_FIELD_TYPES = ["text", "number", "select", "multiselect", "date"]


class TemplateService:
    """
    Сервис для управления шаблонами проблем.

    Предоставляет методы для создания, получения, обновления, удаления,
    активации/деактивации и листинга шаблонов с валидацией и контролем прав.

    Attributes:
        repository: Репозиторий для работы с базой данных.

    Methods:
        create_template: Создать новый шаблон.
        get_template: Получить шаблон по ID.
        update_template: Обновить существующий шаблон.
        delete_template: Удалить (деактивировать) шаблон.
        list_templates: Получить список шаблонов с фильтрацией.
        activate_template: Активировать деактивированный шаблон.
        deactivate_template: Деактивировать активный шаблон.
        get_active_templates: Получить только активные шаблоны.
        get_user_templates: Получить шаблоны конкретного пользователя.
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.repository = TemplateRepository(session)

    async def create_template(
        self,
        template_data: TemplateCreateRequestSchema,
        author_id: UUID,
    ) -> TemplateModel:
        """
        Создать новый шаблон проблемы.

        Валидирует данные (title, category, fields), устанавливает автора,
        начальные значения usage_count=0, is_active=True.

        Args:
            template_data: Данные для создания шаблона.
            author_id: UUID пользователя-создателя.

        Returns:
            Созданный TemplateModel.

        Raises:
            TemplateValidationError: При невалидных данных.
        """
        # Валидация title
        self._validate_title(template_data.title)

        # Валидация category
        self._validate_category(template_data.category)

        # Валидация fields (JSONB)
        self._validate_fields(template_data.fields)

        # Подготовка данных для создания
        create_data = {
            "title": template_data.title,
            "description": template_data.description,
            "category": template_data.category,
            "fields": template_data.fields,
            "visibility": template_data.visibility or TemplateVisibility.PRIVATE,
            "author_id": author_id,
            "usage_count": 0,
            "is_active": True,
        }

        # Создание через репозиторий
        template = await self.repository.create_item(create_data)
        return template

    async def get_template(
        self,
        template_id: UUID,
        user_id: UUID,
    ) -> TemplateModel:
        """
        Получить шаблон по ID.

        Проверяет видимость: публичные доступны всем, приватные только автору.

        Args:
            template_id: UUID шаблона.
            user_id: UUID текущего пользователя.

        Returns:
            TemplateModel.

        Raises:
            TemplateNotFoundError: Если шаблон не найден.
            TemplatePermissionDeniedError: Если нет прав на просмотр приватного шаблона.
        """
        template = await self.repository.get_item_by_id(template_id)
        if not template:
            raise TemplateNotFoundError(template_id=template_id)

        # Проверка прав на просмотр приватных шаблонов
        if template.visibility == TemplateVisibility.PRIVATE:
            if template.author_id != user_id:
                raise TemplatePermissionDeniedError(
                    template_id=template_id,
                    user_id=user_id,
                    action="view",
                )

        return template

    async def update_template(
        self,
        template_id: UUID,
        template_data: TemplateUpdateRequestSchema,
        user_id: UUID,
    ) -> TemplateModel:
        """
        Обновить существующий шаблон.

        Только владелец (author) может редактировать шаблон.
        Валидирует изменяемые поля.

        Args:
            template_id: UUID шаблона.
            template_data: Данные для обновления.
            user_id: UUID текущего пользователя.

        Returns:
            Обновлённый TemplateModel.

        Raises:
            TemplateNotFoundError: Если шаблон не найден.
            TemplatePermissionDeniedError: Если пользователь не владелец.
            TemplateValidationError: При невалидных данных.
        """
        # Получить существующий шаблон
        template = await self.repository.get_item_by_id(template_id)
        if not template:
            raise TemplateNotFoundError(template_id=template_id)

        # Проверка прав (только владелец)
        self._check_permission(template, user_id, "update")

        # Подготовка данных для обновления (exclude_unset=True)
        update_data = template_data.model_dump(exclude_unset=True)

        # Валидация изменяемых полей
        if "title" in update_data:
            self._validate_title(update_data["title"])

        if "category" in update_data:
            self._validate_category(update_data["category"])

        if "fields" in update_data:
            self._validate_fields(update_data["fields"])

        # Обновление через репозиторий
        updated_template = await self.repository.update_item(template_id, update_data)
        return updated_template

    async def delete_template(
        self,
        template_id: UUID,
        user_id: UUID,
    ) -> TemplateModel:
        """
        Удалить (деактивировать) шаблон.

        Soft delete: устанавливает is_active=False вместо физического удаления.
        Только владелец (author) может удалять шаблон.

        Args:
            template_id: UUID шаблона.
            user_id: UUID текущего пользователя.

        Returns:
            Деактивированный TemplateModel.

        Raises:
            TemplateNotFoundError: Если шаблон не найден.
            TemplatePermissionDeniedError: Если пользователь не владелец.
        """
        # Получить существующий шаблон
        template = await self.repository.get_item_by_id(template_id)
        if not template:
            raise TemplateNotFoundError(template_id=template_id)

        # Проверка прав (только владелец)
        self._check_permission(template, user_id, "delete")

        # Soft delete: деактивация
        deactivated = await self.repository.update_item(template_id, {"is_active": False})
        return deactivated

    async def list_templates(
        self,
        query: TemplateQueryRequestSchema,
        user_id: UUID,
    ) -> List[TemplateModel]:
        """
        Получить список шаблонов с фильтрацией.

        Фильтрует по категории, видимости, активности. Приватные шаблоны
        возвращаются только их владельцам.

        Args:
            query: Параметры фильтрации (category, visibility, is_active).
            user_id: UUID текущего пользователя.

        Returns:
            Список TemplateModel.
        """
        # Если фильтр по категории
        if query.category:
            templates = await self.repository.get_by_category(query.category)
        # Если фильтр по видимости
        elif query.visibility:
            templates = await self.repository.get_by_visibility(query.visibility)
        # Если фильтр is_active
        elif query.is_active is not None:
            if query.is_active:
                templates = await self.repository.get_active_templates()
            else:
                templates = await self.repository.filter_by(is_active=False)
        # Без фильтров: все публичные + приватные текущего юзера
        else:
            public_templates = await self.repository.get_by_visibility(
                TemplateVisibility.PUBLIC
            )
            user_templates = await self.repository.get_user_templates(user_id)
            # Объединение без дубликатов (по ID)
            templates_dict = {t.id: t for t in public_templates}
            templates_dict.update({t.id: t for t in user_templates})
            templates = list(templates_dict.values())

        # Фильтрация приватных шаблонов (только свои)
        filtered = [
            t
            for t in templates
            if t.visibility == TemplateVisibility.PUBLIC or t.author_id == user_id
        ]

        return filtered

    async def activate_template(
        self,
        template_id: UUID,
        user_id: UUID,
    ) -> TemplateModel:
        """
        Активировать деактивированный шаблон.

        Только владелец (author) может активировать шаблон.

        Args:
            template_id: UUID шаблона.
            user_id: UUID текущего пользователя.

        Returns:
            Активированный TemplateModel.

        Raises:
            TemplateNotFoundError: Если шаблон не найден.
            TemplatePermissionDeniedError: Если пользователь не владелец.
            TemplateValidationError: Если шаблон уже активен.
        """
        # Получить существующий шаблон
        template = await self.repository.get_item_by_id(template_id)
        if not template:
            raise TemplateNotFoundError(template_id=template_id)

        # Проверка прав (только владелец)
        self._check_permission(template, user_id, "activate")

        # Проверка текущего статуса
        if template.is_active:
            raise TemplateValidationError(
                field="is_active",
                reason="Шаблон уже активен",
            )

        # Активация
        activated = await self.repository.update_item(template_id, {"is_active": True})
        return activated

    async def deactivate_template(
        self,
        template_id: UUID,
        user_id: UUID,
    ) -> TemplateModel:
        """
        Деактивировать активный шаблон.

        Только владелец (author) может деактивировать шаблон.

        Args:
            template_id: UUID шаблона.
            user_id: UUID текущего пользователя.

        Returns:
            Деактивированный TemplateModel.

        Raises:
            TemplateNotFoundError: Если шаблон не найден.
            TemplatePermissionDeniedError: Если пользователь не владелец.
            TemplateValidationError: Если шаблон уже деактивирован.
        """
        # Получить существующий шаблон
        template = await self.repository.get_item_by_id(template_id)
        if not template:
            raise TemplateNotFoundError(template_id=template_id)

        # Проверка прав (только владелец)
        self._check_permission(template, user_id, "deactivate")

        # Проверка текущего статуса
        if not template.is_active:
            raise TemplateValidationError(
                field="is_active",
                reason="Шаблон уже деактивирован",
            )

        # Деактивация
        deactivated = await self.repository.update_item(template_id, {"is_active": False})
        return deactivated

    async def get_active_templates(self) -> List[TemplateModel]:
        """
        Получить все активные публичные шаблоны.

        Используется для отображения доступных шаблонов при создании проблем.

        Returns:
            Список активных публичных TemplateModel.
        """
        return await self.repository.get_active_templates()

    async def get_user_templates(self, user_id: UUID) -> List[TemplateModel]:
        """
        Получить все шаблоны конкретного пользователя.

        Включает как публичные, так и приватные шаблоны автора.

        Args:
            user_id: UUID пользователя-автора.

        Returns:
            Список TemplateModel пользователя.
        """
        return await self.repository.get_user_templates(user_id)

    # ========== Приватные методы валидации и проверки прав ==========

    def _validate_title(self, title: str) -> None:
        """
        Валидация названия шаблона.

        Args:
            title: Название шаблона.

        Raises:
            TemplateValidationError: Если title не соответствует требованиям.
        """
        if not title or not title.strip():
            raise TemplateValidationError(
                field="title",
                reason="Название шаблона не может быть пустым",
            )

        if len(title) < 3:
            raise TemplateValidationError(
                field="title",
                reason="Название шаблона должно быть минимум 3 символа",
            )

        if len(title) > 200:
            raise TemplateValidationError(
                field="title",
                reason="Название шаблона не должно превышать 200 символов",
            )

    def _validate_category(self, category: str) -> None:
        """
        Валидация категории шаблона.

        Args:
            category: Категория шаблона.

        Raises:
            TemplateValidationError: Если category не из списка разрешённых.
        """
        if category not in ALLOWED_CATEGORIES:
            raise TemplateValidationError(
                field="category",
                reason=f"Категория должна быть одной из: {', '.join(ALLOWED_CATEGORIES)}",
            )

    def _validate_fields(self, fields: dict) -> None:
        """
        Валидация полей шаблона (JSONB структура).

        Проверяет что fields - это список объектов с ключами:
        name, type, label, required, options (для select/multiselect).

        Args:
            fields: JSONB словарь с полями шаблона.

        Raises:
            TemplateValidationError: При невалидной структуре fields.
        """
        if not isinstance(fields, dict):
            raise TemplateValidationError(
                field="fields",
                reason="Поля шаблона должны быть объектом (dict)",
            )

        # Проверка наличия ключа "fields" в JSONB
        if "fields" not in fields:
            raise TemplateValidationError(
                field="fields",
                reason="Отсутствует ключ 'fields' в структуре",
            )

        field_list = fields["fields"]
        if not isinstance(field_list, list):
            raise TemplateValidationError(
                field="fields",
                reason="Ключ 'fields' должен содержать массив (list)",
            )

        # Валидация каждого поля
        for idx, field in enumerate(field_list):
            if not isinstance(field, dict):
                raise TemplateValidationError(
                    field="fields",
                    reason=f"Поле #{idx} должно быть объектом (dict)",
                )

            # Обязательные ключи
            required_keys = ["name", "type", "label", "required"]
            for key in required_keys:
                if key not in field:
                    raise TemplateValidationError(
                        field="fields",
                        reason=f"Поле #{idx} не содержит обязательный ключ '{key}'",
                    )

            # Валидация типа поля
            field_type = field["type"]
            if field_type not in ALLOWED_FIELD_TYPES:
                raise TemplateValidationError(
                    field="fields",
                    reason=f"Поле #{idx}: тип '{field_type}' не разрешён. Допустимые: {', '.join(ALLOWED_FIELD_TYPES)}",
                )

            # Для select/multiselect требуется options
            if field_type in ["select", "multiselect"]:
                if "options" not in field:
                    raise TemplateValidationError(
                        field="fields",
                        reason=f"Поле #{idx}: тип '{field_type}' требует ключ 'options'",
                    )
                if not isinstance(field["options"], list) or len(field["options"]) == 0:
                    raise TemplateValidationError(
                        field="fields",
                        reason=f"Поле #{idx}: 'options' должен быть непустым массивом",
                    )

    def _check_permission(
        self,
        template: TemplateModel,
        user_id: UUID,
        action: str,
    ) -> None:
        """
        Проверка прав на операцию с шаблоном.

        Только владелец (author) может изменять/удалять шаблон.
        В будущем можно добавить проверку роли admin.

        Args:
            template: TemplateModel для проверки.
            user_id: UUID пользователя, выполняющего действие.
            action: Название действия (update, delete, activate, deactivate).

        Raises:
            TemplatePermissionDeniedError: Если пользователь не владелец.
        """
        if template.author_id != user_id:
            raise TemplatePermissionDeniedError(
                template_id=template.id,
                user_id=user_id,
                action=action,
            )
