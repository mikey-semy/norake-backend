"""
Сервис для работы с проблемами (Issues).

Содержит бизнес-логику для управления проблемами: создание, решение,
фильтрация, поиск. Возвращает domain objects (IssueModel), НЕ схемы!

Classes:
    IssueService: Сервис с методами для работы с проблемами.

Example:
    >>> service = IssueService(session=session)
    >>> issue = await service.create_issue(author_id=user_id, title="...", ...)
    >>> resolved = await service.resolve_issue(issue_id, solution, user_id)
"""

import logging
import re
from datetime import date, time
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    IssueAlreadyResolvedError,
    IssueNotFoundError,
    IssuePermissionDeniedError,
    IssueValidationError,
    TemplateNotFoundError,
)
from src.core.settings import settings
from src.models.v1.issues import IssueModel, IssueStatus
from src.repository.v1.issues import IssueRepository
from src.repository.v1.templates import TemplateRepository
from src.services.base import BaseService


class IssueService(BaseService):
    """
    Сервис для работы с проблемами (Issues).

    Содержит бизнес-логику: валидацию, проверку прав доступа,
    оркестрацию действий. Возвращает domain objects (IssueModel).

    Attributes:
        repository: Репозиторий для работы с IssueModel.

    Methods:
        create_issue: Создать новую проблему.
        get_issue: Получить проблему по ID.
        update_issue: Обновить существующую проблему.
        resolve_issue: Решить проблему (только автор или admin).
        list_issues: Получить список проблем с фильтрами.
        search_issues: Поиск проблем по тексту.
        get_recent_issues: Получить последние проблемы.

    Business Rules:
        - При создании status всегда RED
        - Только автор или admin могут решить проблему
        - Нельзя повторно решить уже решённую проблему
        - Title не может быть пустым
        - Category должна быть из списка: hardware, software, process, documentation,
          safety, quality, maintenance, training, other

    Example:
        >>> service = IssueService(session=session)
        >>> # Создание проблемы
        >>> issue = await service.create_issue(
        ...     author_id=user_id,
        ...     title="Ошибка E401",
        ...     description="Проблема с оборудованием",
        ...     category="hardware"
        ... )
        >>> # Решение проблемы
        >>> resolved = await service.resolve_issue(
        ...     issue_id=issue.id,
        ...     solution="Заменён датчик",
        ...     user_id=user_id
        ... )
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализирует IssueService.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        super().__init__(session)
        self.repository = IssueRepository(session=session)
        self.logger = logging.getLogger(self.__class__.__name__)

    # ==================== VALIDATION ====================

    def _validate_title(self, title: str) -> None:
        """
        Валидирует заголовок проблемы.

        Args:
            title: Заголовок для проверки.

        Raises:
            IssueValidationError: Если title пустой или слишком длинный.
        """
        if not title or not title.strip():
            raise IssueValidationError("title", "Заголовок не может быть пустым")
        if len(title) > 255:
            raise IssueValidationError(
                "title", f"Заголовок слишком длинный ({len(title)}/255)"
            )

    def _validate_category(self, category: str) -> None:
        """
        Валидирует категорию проблемы.

        Args:
            category: Категория для проверки.

        Raises:
            IssueValidationError: Если категория не из разрешённого списка.
        """
        if category not in settings.ISSUE_CATEGORIES:
            raise IssueValidationError(
                "category",
                f"Категория должна быть одной из: {', '.join(settings.ISSUE_CATEGORIES)}",
            )

    async def _validate_custom_fields(
        self, template_id: UUID, custom_fields: dict
    ) -> None:
        """
        Валидирует custom_fields по schema из Template.

        Загружает Template и проверяет соответствие переданных custom_fields
        схеме fields из Template. Проверяет: обязательные поля, типы данных,
        форматы (pattern), опции (select/radio).

        Args:
            template_id: UUID шаблона для валидации.
            custom_fields: Словарь с пользовательскими данными для проверки.

        Raises:
            TemplateNotFoundError: Если шаблон не найден.
            IssueValidationError: Если custom_fields не соответствуют схеме.

        Example:
            >>> await service._validate_custom_fields(
            ...     template_id=template_uuid,
            ...     custom_fields={"equipment_model": "KUKA KR 500-3"}
            ... )

        Note:
            Поддерживаемые типы полей: text, textarea, number, select, radio,
            checkbox, date, time. Required поля должны быть обязательно заполнены.
        """
        # Загрузка template
        template_repo = TemplateRepository(self.session)
        template = await template_repo.get_item_by_id(template_id)

        if not template:
            raise TemplateNotFoundError(template_id)

        # Извлечение схемы полей
        fields_schema = template.fields.get("fields", [])
        if not fields_schema:
            self.logger.warning(
                "Template %s не содержит fields schema, валидация пропущена",
                template_id,
            )
            return

        # Проверка обязательных полей
        for field_def in fields_schema:
            field_name = field_def.get("name")
            is_required = field_def.get("required", False)

            if is_required and field_name not in custom_fields:
                raise IssueValidationError(
                    "custom_fields",
                    f"Обязательное поле '{field_name}' отсутствует",
                )

        # Проверка типов и форматов
        for field_name, field_value in custom_fields.items():
            # Найти определение поля в schema
            field_def = next(
                (f for f in fields_schema if f.get("name") == field_name), None
            )

            if not field_def:
                # Если поле не определено в schema, игнорируем (soft validation)
                self.logger.debug(
                    "Поле '%s' не найдено в schema template %s, пропускаем",
                    field_name,
                    template_id,
                )
                continue

            field_type = field_def.get("type", "text")

            # Валидация по типу
            if field_type == "number":
                if not isinstance(field_value, (int, float)):
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' должно быть числом",
                    )

            elif field_type in ("select", "radio"):
                options = field_def.get("options", [])
                if options and field_value not in options:
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' должно быть одним из: {', '.join(options)}",
                    )

            elif field_type == "checkbox":
                if not isinstance(field_value, bool):
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' должно быть boolean",
                    )

            elif field_type == "date":
                # Проверка формата даты (YYYY-MM-DD)
                if not isinstance(field_value, str):
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' должно быть строкой в формате YYYY-MM-DD",
                    )
                try:
                    date.fromisoformat(field_value)
                except ValueError:
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' имеет невалидный формат даты (ожидается YYYY-MM-DD)",
                    )

            elif field_type == "time":
                # Проверка формата времени (HH:MM)
                if not isinstance(field_value, str):
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' должно быть строкой в формате HH:MM",
                    )
                try:
                    time.fromisoformat(field_value)
                except ValueError:
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' имеет невалидный формат времени (ожидается HH:MM)",
                    )

            elif field_type in ("text", "textarea"):
                if not isinstance(field_value, str):
                    raise IssueValidationError(
                        "custom_fields",
                        f"Поле '{field_name}' должно быть строкой",
                    )

                # Проверка pattern если указан
                pattern = field_def.get("pattern")
                if pattern:
                    if not re.match(pattern, field_value):
                        help_text = field_def.get(
                            "help_text", f"Формат: {pattern}"
                        )
                        raise IssueValidationError(
                            "custom_fields",
                            f"Поле '{field_name}' не соответствует формату. {help_text}",
                        )

        self.logger.debug(
            "Валидация custom_fields успешна для template %s", template_id
        )

    async def _check_permission(
        self, issue: IssueModel, user_id: UUID, action: str
    ) -> None:
        """
        Проверяет права пользователя на выполнение действия с проблемой.

        Args:
            issue: Проблема для проверки прав.
            user_id: UUID пользователя.
            action: Название действия (для лога).

        Raises:
            IssuePermissionDeniedError: Если пользователь не автор и не admin.
        """
        # TODO: Добавить проверку роли admin когда будет доступ к UserModel
        if issue.author_id != user_id:
            raise IssuePermissionDeniedError(issue.id, user_id, action)

    # ==================== CREATE ====================

    async def create_issue(
        self,
        author_id: UUID,
        workspace_id: UUID,
        title: str,
        description: str,
        category: str,
        template_id: Optional[UUID] = None,
        custom_fields: Optional[dict] = None,
    ) -> IssueModel:
        """
        Создать новую проблему.

        Статус автоматически устанавливается в RED.
        Если указан template_id, увеличивает счётчик использований шаблона.
        Если переданы custom_fields, валидирует их по schema из Template.

        Args:
            author_id: UUID автора проблемы.
            workspace_id: UUID рабочего пространства.
            title: Заголовок проблемы.
            description: Подробное описание.
            category: Категория (hardware/software/process/documentation/safety/
                quality/maintenance/training/other).
            template_id: UUID шаблона (опционально).
            custom_fields: Динамические поля из шаблона (опционально).

        Returns:
            IssueModel: Созданная проблема.

        Raises:
            IssueValidationError: При невалидных данных.
            TemplateNotFoundError: Если template_id не найден.

        Example:
            >>> issue = await service.create_issue(
            ...     author_id=user_id,
            ...     workspace_id=workspace_id,
            ...     title="Ошибка E401",
            ...     description="Проблема с оборудованием",
            ...     category="hardware",
            ...     template_id=template_uuid,
            ...     custom_fields={"equipment_model": "KUKA KR 500-3"}
            ... )
        """
        # Валидация
        self._validate_title(title)
        self._validate_category(category)

        # Валидация custom_fields по schema template
        if template_id and custom_fields:
            await self._validate_custom_fields(template_id, custom_fields)

        # Создание
        issue_data = {
            "title": title,
            "description": description,
            "category": category,
            "status": IssueStatus.RED,  # Всегда RED при создании
            "author_id": author_id,
            "workspace_id": workspace_id,
        }

        # Добавить template_id и custom_fields если переданы
        if template_id:
            issue_data["template_id"] = template_id
        if custom_fields:
            issue_data["custom_fields"] = custom_fields

        issue = await self.repository.create_item(issue_data)

        # Увеличить usage_count шаблона если указан
        if template_id:
            try:
                template_repo = TemplateRepository(self.session)
                await template_repo.increment_usage_count(template_id)
                self.logger.info(
                    "Увеличен счётчик шаблона %s для проблемы %s",
                    template_id,
                    issue.id,
                )
            except Exception as e:
                # Не критично если не удалось обновить счётчик
                self.logger.warning(
                    "Не удалось обновить счётчик шаблона %s: %s",
                    template_id,
                    str(e),
                )

        self.logger.info("Создана проблема %s пользователем %s", issue.id, author_id)

        # Вызов n8n webhook для авто-категоризации (опционально)
        await self._trigger_autocategorize_webhook(issue)

        return issue

    async def _trigger_autocategorize_webhook(self, issue: IssueModel) -> None:
        """Вызвать n8n webhook для авто-категоризации Issue.

        Ищет активный workflow AUTO_CATEGORIZE для workspace Issue
        и вызывает его webhook в фоновом режиме.

        Args:
            issue: Созданная Issue для категоризации.
        """
        try:
            from src.repository.v1.n8n_workflows import N8nWorkflowRepository
            from src.core.integrations.n8n import n8n_webhook_client

            workflow_repo = N8nWorkflowRepository(self.session)

            # Ищем активный workflow AUTO_CATEGORIZE для workspace Issue
            workflows = await workflow_repo.filter_by(
                workspace_id=issue.workspace_id,
                workflow_type="AUTO_CATEGORIZE",
                is_active=True
            )

            if workflows:
                webhook_url = workflows[0].webhook_url
                n8n_webhook_client.trigger_autocategorize_background(
                    webhook_url=webhook_url,
                    issue_id=issue.id,
                    title=issue.title,
                    description=issue.description,
                )
                self.logger.debug(
                    "Вызван webhook auto-categorize для issue %s (workspace %s)",
                    issue.id,
                    issue.workspace_id,
                )
            else:
                self.logger.debug(
                    "Auto-categorize workflow не найден для workspace %s",
                    issue.workspace_id,
                )

        except Exception as e:
            # Не критично если не удалось вызвать webhook
            self.logger.warning(
                "Не удалось вызвать auto-categorize webhook: %s",
                str(e),
            )

    # ==================== READ ====================

    async def get_issue(self, issue_id: UUID) -> IssueModel:
        """
        Получить проблему по ID.

        Args:
            issue_id: UUID проблемы.

        Returns:
            IssueModel: Найденная проблема.

        Raises:
            IssueNotFoundError: Если проблема не найдена.

        Example:
            >>> issue = await service.get_issue(issue_id)
        """
        issue = await self.repository.get_item_by_id(issue_id)
        if not issue:
            raise IssueNotFoundError(issue_id)
        return issue

    # ==================== UPDATE ====================

    async def update_issue(
        self,
        issue_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        custom_fields: Optional[dict] = None,
    ) -> IssueModel:
        """
        Обновить существующую проблему.

        Только автор (или admin) может обновлять проблему.
        Если Issue привязан к template и переданы custom_fields, валидирует их по schema.

        Args:
            issue_id: UUID проблемы.
            user_id: UUID пользователя, выполняющего действие.
            title: Новый заголовок (опционально).
            description: Новое описание (опционально).
            category: Новая категория (опционально).
            custom_fields: Обновлённые динамические поля (опционально).

        Returns:
            IssueModel: Обновлённая проблема.

        Raises:
            IssueNotFoundError: Если проблема не найдена.
            IssuePermissionDeniedError: Если нет прав.
            IssueValidationError: При невалидных данных.
            TemplateNotFoundError: Если template_id Issue не найден.

        Example:
            >>> updated = await service.update_issue(
            ...     issue_id=issue_id,
            ...     user_id=user_id,
            ...     title="Новый заголовок",
            ...     custom_fields={"equipment_model": "KUKA KR 600-3"}
            ... )
        """
        # Проверка существования и прав
        issue = await self.get_issue(issue_id)
        await self._check_permission(issue, user_id, "update")

        # Валидация
        update_data: Dict = {}
        if title is not None:
            self._validate_title(title)
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if category is not None:
            self._validate_category(category)
            update_data["category"] = category

        # Валидация и обновление custom_fields
        if custom_fields is not None:
            # Если Issue привязан к template, валидируем custom_fields
            if issue.template_id:
                await self._validate_custom_fields(issue.template_id, custom_fields)
            update_data["custom_fields"] = custom_fields

        if not update_data:
            return issue  # Нечего обновлять

        # Обновление
        updated = await self.repository.update_item(issue_id, update_data)
        self.logger.info("Обновлена проблема %s пользователем %s", issue_id, user_id)
        return updated  # type: ignore

    # ==================== RESOLVE ====================

    async def resolve_issue(
        self,
        issue_id: UUID,
        solution: str,
        user_id: UUID,
    ) -> IssueModel:
        """
        Решить проблему (закрыть с решением).

        Только автор (или admin) может решить проблему.
        Нельзя повторно решить уже решённую проблему.

        Args:
            issue_id: UUID проблемы.
            solution: Текст решения.
            user_id: UUID пользователя, решающего проблему.

        Returns:
            IssueModel: Решённая проблема.

        Raises:
            IssueNotFoundError: Если проблема не найдена.
            IssuePermissionDeniedError: Если нет прав.
            IssueAlreadyResolvedError: Если проблема уже решена.

        Example:
            >>> resolved = await service.resolve_issue(
            ...     issue_id=issue_id,
            ...     solution="Заменён датчик",
            ...     user_id=user_id
            ... )
        """
        # Проверка существования и прав
        issue = await self.get_issue(issue_id)
        await self._check_permission(issue, user_id, "resolve")

        # Проверка статуса
        if issue.status == IssueStatus.GREEN:
            raise IssueAlreadyResolvedError(issue_id)

        # Валидация решения
        if not solution or not solution.strip():
            raise IssueValidationError("solution", "Решение не может быть пустым")

        # Решение через репозиторий
        resolved = await self.repository.resolve_issue(issue_id, solution)
        self.logger.info(
            "Проблема %s решена пользователем %s", issue_id, user_id
        )
        return resolved  # type: ignore

    # ==================== LIST & SEARCH ====================

    async def list_issues(
        self,
        status: Optional[IssueStatus] = None,
        category: Optional[str] = None,
        author_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IssueModel]:
        """
        Получить список проблем с фильтрами.

        Все фильтры опциональны и комбинируются через AND.

        Args:
            status: Фильтр по статусу (RED/GREEN).
            category: Фильтр по категории.
            author_id: Фильтр по автору.
            search: Поиск по title/description.
            limit: Максимальное количество результатов (1-100).
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список найденных проблем.

        Example:
            >>> issues = await service.list_issues(
            ...     status=IssueStatus.RED,
            ...     category="hardware",
            ...     limit=10
            ... )
        """
        issues = await self.repository.get_filtered(
            status=status,
            category=category,
            author_id=author_id,
            search=search,
            limit=min(limit, 100),  # Ограничение max 100
            offset=offset,
        )
        self.logger.info("Получено %d проблем по фильтрам", len(issues))
        return issues

    async def search_issues(
        self,
        query_text: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IssueModel]:
        """
        Поиск проблем по тексту (title/description).

        Args:
            query_text: Текст для поиска.
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список найденных проблем.

        Example:
            >>> found = await service.search_issues("ошибка E401")
        """
        issues = await self.repository.search_by_text(
            query_text=query_text,
            limit=limit,
            offset=offset,
        )
        self.logger.info("Найдено %d проблем по запросу '%s'", len(issues), query_text)
        return issues

    async def get_recent_issues(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IssueModel]:
        """
        Получить последние проблемы (по created_at DESC).

        Args:
            limit: Максимальное количество результатов.
            offset: Смещение для пагинации.

        Returns:
            List[IssueModel]: Список последних проблем.

        Example:
            >>> recent = await service.get_recent_issues(limit=10)
        """
        issues = await self.repository.get_recent(limit=limit, offset=offset)
        self.logger.info("Получено %d последних проблем", len(issues))
        return issues
