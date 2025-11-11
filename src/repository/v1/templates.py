"""
Репозиторий для работы с шаблонами (Templates).

Предоставляет методы доступа к данным шаблонов с поддержкой JSONB запросов,
фильтрации по видимости, активности и авторству.

Classes:
    TemplateRepository: Репозиторий с CRUD методами для TemplateModel.

Example:
    >>> repository = TemplateRepository(session=session)
    >>> active_templates = await repository.get_active_templates()
    >>> user_templates = await repository.get_user_templates(user_id)
"""

import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.v1.templates import TemplateModel, TemplateVisibility
from src.repository.base import BaseRepository

logger = logging.getLogger(__name__)


class TemplateRepository(BaseRepository[TemplateModel]):
    """
    Репозиторий для работы с шаблонами проблем.

    Наследует BaseRepository[TemplateModel] и добавляет специфичные методы
    для работы с шаблонами: фильтрация по активности, авторству, видимости,
    поиск по JSONB полям.

    Attributes:
        session: Асинхронная сессия базы данных.
        model: TemplateModel класс.

    Example:
        >>> repository = TemplateRepository(session=session)
        >>> # Получить все активные публичные шаблоны
        >>> templates = await repository.get_active_templates()
        >>> # Получить шаблоны пользователя
        >>> user_templates = await repository.get_user_templates(user_id)
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует репозиторий шаблонов.

        Args:
            session: Асинхронная сессия базы данных.
        """
        super().__init__(session=session, model=TemplateModel)
        self.logger = logging.getLogger(__name__)

    async def get_active_templates(
        self, visibility: Optional[TemplateVisibility] = None
    ) -> List[TemplateModel]:
        """
        Получает все активные шаблоны.

        Возвращает только шаблоны с is_active=True. Можно фильтровать
        по видимости (public/private/team).

        Args:
            visibility: Фильтр по видимости (опционально).
                       Если None - возвращает все активные шаблоны.

        Returns:
            Список активных TemplateModel.

        Example:
            >>> # Все активные шаблоны
            >>> all_templates = await repository.get_active_templates()
            >>> # Только публичные активные
            >>> public = await repository.get_active_templates(
            ...     visibility=TemplateVisibility.PUBLIC
            ... )
        """
        filters = {"is_active": True}
        if visibility:
            filters["visibility"] = visibility

        templates = await self.filter_by_ordered(
            "usage_count", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d активных шаблонов (visibility=%s)",
            len(templates),
            visibility.value if visibility else "any",
        )
        return templates

    async def get_user_templates(
        self, user_id: UUID, include_inactive: bool = False
    ) -> List[TemplateModel]:
        """
        Получает все шаблоны пользователя.

        Возвращает шаблоны, созданные конкретным пользователем.
        По умолчанию возвращает только активные.

        Args:
            user_id: UUID автора шаблонов.
            include_inactive: Включать ли неактивные шаблоны.
                             По умолчанию False.

        Returns:
            Список TemplateModel, созданных пользователем.

        Example:
            >>> # Только активные шаблоны пользователя
            >>> templates = await repository.get_user_templates(user_id)
            >>> # Все шаблоны (включая неактивные)
            >>> all_templates = await repository.get_user_templates(
            ...     user_id, include_inactive=True
            ... )
        """
        filters = {"author_id": user_id}
        if not include_inactive:
            filters["is_active"] = True

        templates = await self.filter_by_ordered(
            "created_at", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d шаблонов пользователя %s (include_inactive=%s)",
            len(templates),
            user_id,
            include_inactive,
        )
        return templates

    async def get_public_templates(self) -> List[TemplateModel]:
        """
        Получает все публичные активные шаблоны.

        Возвращает только шаблоны с visibility=PUBLIC и is_active=True,
        отсортированные по популярности (usage_count).

        Returns:
            Список публичных активных TemplateModel.

        Example:
            >>> public_templates = await repository.get_public_templates()
            >>> for template in public_templates:
            ...     print(f"{template.title} - использован {template.usage_count} раз")
        """
        return await self.get_active_templates(
            visibility=TemplateVisibility.PUBLIC
        )

    async def get_templates_by_category(
        self, category: str, visibility: Optional[TemplateVisibility] = None
    ) -> List[TemplateModel]:
        """
        Получает активные шаблоны по категории.

        Фильтрует шаблоны по категории (hardware, software, process).
        Можно дополнительно фильтровать по видимости.

        Args:
            category: Категория шаблонов (hardware, software, process).
            visibility: Фильтр по видимости (опционально).

        Returns:
            Список TemplateModel для указанной категории.

        Example:
            >>> hardware = await repository.get_templates_by_category("hardware")
            >>> public_software = await repository.get_templates_by_category(
            ...     "software", visibility=TemplateVisibility.PUBLIC
            ... )
        """
        filters = {"category": category, "is_active": True}
        if visibility:
            filters["visibility"] = visibility

        templates = await self.filter_by_ordered(
            "usage_count", ascending=False, **filters
        )

        self.logger.info(
            "Получено %d шаблонов для категории '%s' (visibility=%s)",
            len(templates),
            category,
            visibility.value if visibility else "any",
        )
        return templates

    async def increment_usage_count(self, template_id: UUID) -> TemplateModel:
        """
        Увеличивает счётчик использований шаблона.

        Вызывается когда проблема создаётся на основе шаблона.
        Инкрементирует usage_count на 1.

        Args:
            template_id: UUID шаблона.

        Returns:
            Обновлённый TemplateModel с увеличенным usage_count.

        Raises:
            ValueError: Если шаблон не найден (через get_item_by_id).

        Example:
            >>> # После создания Issue с template_id
            >>> template = await repository.increment_usage_count(template_id)
            >>> print(f"Использован {template.usage_count} раз")
        """
        # Получить текущее значение usage_count
        template = await self.get_item_by_id(template_id)
        if not template:
            raise ValueError(f"Шаблон с ID {template_id} не найден")

        # Увеличить счётчик через update_item
        updated = await self.update_item(
            template_id, {"usage_count": template.usage_count + 1}
        )

        self.logger.info(
            "Увеличен счётчик использований шаблона %s до %d",
            template_id,
            updated.usage_count,
        )
        return updated

    async def deactivate_template(self, template_id: UUID) -> TemplateModel:
        """
        Деактивирует шаблон (soft delete).

        Устанавливает is_active=False вместо удаления из БД.
        Деактивированные шаблоны не показываются в списках по умолчанию.

        Args:
            template_id: UUID шаблона для деактивации.

        Returns:
            Обновлённый TemplateModel с is_active=False.

        Raises:
            ValueError: Если шаблон не найден (через update_item).

        Example:
            >>> deactivated = await repository.deactivate_template(template_id)
            >>> assert deactivated.is_active is False
        """
        deactivated = await self.update_item(template_id, {"is_active": False})
        self.logger.info("Деактивирован шаблон %s", template_id)
        return deactivated

    async def activate_template(self, template_id: UUID) -> TemplateModel:
        """
        Активирует деактивированный шаблон.

        Устанавливает is_active=True для повторного использования.

        Args:
            template_id: UUID шаблона для активации.

        Returns:
            Обновлённый TemplateModel с is_active=True.

        Raises:
            ValueError: Если шаблон не найден (через update_item).

        Example:
            >>> activated = await repository.activate_template(template_id)
            >>> assert activated.is_active is True
        """
        activated = await self.update_item(template_id, {"is_active": True})
        self.logger.info("Активирован шаблон %s", template_id)
        return activated

    async def get_by_category(self, category: str) -> List[TemplateModel]:
        """
        Получает шаблоны по категории.

        Используется в TemplateService.list_templates() при фильтрации.
        Возвращает все шаблоны указанной категории (без фильтра по активности).

        Args:
            category: Категория шаблона (hardware/software/process).

        Returns:
            Список TemplateModel с указанной категорией.

        Example:
            >>> hardware = await repository.get_by_category("hardware")
        """
        return await self.filter_by(category=category)

    async def get_by_visibility(
        self, visibility: TemplateVisibility
    ) -> List[TemplateModel]:
        """
        Получает шаблоны по уровню видимости.

        Используется в TemplateService.list_templates() при фильтрации.
        Возвращает все шаблоны с указанным visibility (без фильтра по активности).

        Args:
            visibility: Уровень видимости (PUBLIC/PRIVATE/TEAM).

        Returns:
            Список TemplateModel с указанным visibility.

        Example:
            >>> public = await repository.get_by_visibility(TemplateVisibility.PUBLIC)
        """
        return await self.filter_by(visibility=visibility)
