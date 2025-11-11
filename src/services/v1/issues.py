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
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    IssueAlreadyResolvedError,
    IssueNotFoundError,
    IssuePermissionDeniedError,
    IssueValidationError,
)
from src.models.v1.issues import IssueModel, IssueStatus
from src.repository.v1.issues import IssueRepository
from src.services.base import BaseService


class IssueService(BaseService):
    """
    Сервис для работы с проблемами (Issues).

    Содержит бизнес-логику: валидацию, проверку прав доступа,
    орке

страцию действий. Возвращает domain objects (IssueModel).

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

    # TODO: Вынести в конфиг или БД - сейчас хардкод в 3 местах (IssueService, TemplateService, TemplateBaseSchema)
    # Планируется: динамические категории через admin API или settings
    # Соответствует категориям в n8n workflow auto-categorize-issues.json
    ALLOWED_CATEGORIES = [
        "hardware",
        "software",
        "process",
        "documentation",
        "safety",
        "quality",
        "maintenance",
        "training",
        "other",
    ]

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
        if category not in self.ALLOWED_CATEGORIES:
            raise IssueValidationError(
                "category",
                f"Категория должна быть одной из: {', '.join(self.ALLOWED_CATEGORIES)}",
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
        title: str,
        description: str,
        category: str,
        template_id: Optional[UUID] = None,
    ) -> IssueModel:
        """
        Создать новую проблему.

        Статус автоматически устанавливается в RED.
        Если указан template_id, увеличивает счётчик использований шаблона.

        Args:
            author_id: UUID автора проблемы.
            title: Заголовок проблемы.
            description: Подробное описание.
            category: Категория (hardware/software/process/documentation/safety/
                quality/maintenance/training/other).
            template_id: UUID шаблона (опционально).

        Returns:
            IssueModel: Созданная проблема.

        Raises:
            IssueValidationError: При невалидных данных.

        Example:
            >>> issue = await service.create_issue(
            ...     author_id=user_id,
            ...     title="Ошибка E401",
            ...     description="Проблема с оборудованием",
            ...     category="hardware",
            ...     template_id=template_uuid  # опционально
            ... )
        """
        # Валидация
        self._validate_title(title)
        self._validate_category(category)

        # Создание
        issue_data = {
            "title": title,
            "description": description,
            "category": category,
            "status": IssueStatus.RED,  # Всегда RED при создании
            "author_id": author_id,
        }

        issue = await self.repository.create_item(issue_data)

        # Увеличить usage_count шаблона если указан
        if template_id:
            try:
                from src.repository.v1.templates import TemplateRepository
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

        self.logger.info(
            "Создана проблема %s пользователем %s", issue.id, author_id
        )

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
            from src.models.v1.n8n_workflows import N8nWorkflowModel
            from src.core.integrations.n8n import n8n_webhook_client

            workflow_repo = N8nWorkflowRepository(
                session=self.session,
                model=N8nWorkflowModel,
            )

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
    ) -> IssueModel:
        """
        Обновить существующую проблему.

        Только автор (или admin) может обновлять проблему.

        Args:
            issue_id: UUID проблемы.
            user_id: UUID пользователя, выполняющего действие.
            title: Новый заголовок (опционально).
            description: Новое описание (опционально).
            category: Новая категория (опционально).

        Returns:
            IssueModel: Обновлённая проблема.

        Raises:
            IssueNotFoundError: Если проблема не найдена.
            IssuePermissionDeniedError: Если нет прав.
            IssueValidationError: При невалидных данных.

        Example:
            >>> updated = await service.update_issue(
            ...     issue_id=issue_id,
            ...     user_id=user_id,
            ...     title="Новый заголовок"
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
