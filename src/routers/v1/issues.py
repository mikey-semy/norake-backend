"""
Роутеры для работы с проблемами (Issues).

Модуль предоставляет HTTP API для управления проблемами, разделённое на:
- IssuePublicRouter (BaseRouter) - публичные GET endpoints
- IssueProtectedRouter (ProtectedRouter) - защищённые POST/PATCH endpoints

Обработка исключений: автоматическая обработка через глобальный exception handler.
Роутеры преобразуют domain objects (IssueModel) в Pydantic схемы для ответа.
"""

from typing import Optional
from uuid import UUID

from fastapi import Query, status

from src.core.dependencies.issues import IssueServiceDep
from src.core.security import CurrentUserDep
from src.models.v1.issues import IssueStatus
from src.routers.base import BaseRouter, ProtectedRouter
from src.schemas.v1.issues import (
    IssueCreateRequestSchema,
    IssueDetailSchema,
    IssueListItemSchema,
    IssueListResponseSchema,
    IssueResolveRequestSchema,
    IssueResponseSchema,
    IssueUpdateRequestSchema,
)


class IssuePublicRouter(BaseRouter):
    """
    Публичный роутер для чтения проблем (Issues).

    Предоставляет HTTP API для просмотра коллективной памяти проблем:

    Public Endpoints (без аутентификации):
        GET /issues - Список проблем с фильтрацией
        GET /issues/{id} - Детали проблемы
        GET /issues/history - История решённых проблем

    Архитектурные особенности:
        - Все endpoints публичные для чтения истории проблем
        - Роутер преобразует IssueModel → Schema
        - Бизнес-логика в IssueService
    """

    def __init__(self):
        """Инициализирует IssuePublicRouter с префиксом и тегами."""
        super().__init__(prefix="issues", tags=["Issues"])

    def configure(self):
        """Настройка публичных endpoint'ов роутера."""

        # ==================== LIST ====================

        @self.router.get(
            path="",
            response_model=IssueListResponseSchema,
            status_code=status.HTTP_200_OK,
            deprecated=True,
            description="""
            ## ⚠️ DEPRECATED: Используйте /document-services
            
            ## 📋 Получить список проблем с фильтрацией

            **⚠️ УСТАРЕЛО**: Этот эндпоинт будет удалён в будущих версиях.
            Используйте `/api/v1/document-services` для новых интеграций.

            Возвращает список проблем с опциональными фильтрами.
            Все фильтры комбинируются через AND.

            ### 🌐 Публичный доступ (без токена)

            ### Query параметры:
            * **status**: Фильтр по статусу (red/green)
            * **category**: Фильтр по категории (hardware/software/process)
            * **author_id**: Фильтр по автору (UUID)
            * **search**: Поиск по title/description
            * **limit**: Количество результатов (1-100, по умолчанию 50)
            * **offset**: Смещение для пагинации (по умолчанию 0)

            ### Returns:
            * **IssueListResponseSchema**: Список проблем (brief версии)

            ### Примеры использования:
            * Все проблемы: GET /issues
            * Только RED: GET /issues?status=red
            * По категории: GET /issues?category=hardware
            * Поиск: GET /issues?search=ошибка+E401
            * Пагинация: GET /issues?limit=10&offset=20
            """,
            responses={
                200: {"description": "Список проблем успешно получен"},
            },
        )
        async def list_issues(
            status_filter: Optional[IssueStatus] = Query(
                None, alias="status", description="Фильтр по статусу (red/green)"
            ),
            category: Optional[str] = Query(
                None, description="Фильтр по категории"
            ),
            author_id: Optional[UUID] = Query(
                None, description="Фильтр по автору"
            ),
            search: Optional[str] = Query(
                None, description="Поиск по title/description"
            ),
            limit: int = Query(
                50, ge=1, le=100, description="Количество результатов (1-100)"
            ),
            offset: int = Query(
                0, ge=0, description="Смещение для пагинации"
            ),
            issue_service: IssueServiceDep = None,
        ) -> IssueListResponseSchema:
            """
            Получает список проблем с фильтрами.

            🌐 **Публичный эндпоинт**: Не требует аутентификации.

            Args:
                status_filter: Фильтр по статусу (RED/GREEN).
                category: Фильтр по категории.
                author_id: Фильтр по автору.
                search: Поиск по тексту.
                limit: Максимальное количество результатов.
                offset: Смещение для пагинации.
                issue_service: Сервис для работы с проблемами.

            Returns:
                IssueListResponseSchema: Обёртка со списком проблем.

            Note:
                Возвращает IssueListItemSchema (brief версия без автора).
            """
            # Получаем список через сервис
            issues = await issue_service.list_issues(
                status=status_filter,
                category=category,
                author_id=author_id,
                search=search,
                limit=limit,
                offset=offset,
            )

            # Преобразуем список domain objects → schemas
            issues_schemas = [
                IssueListItemSchema.model_validate(issue) for issue in issues
            ]

            return IssueListResponseSchema(
                success=True,
                data=issues_schemas,
                count=len(issues_schemas),
            )

        # ==================== GET ONE ====================

        @self.router.get(
            path="/{issue_id}",
            response_model=IssueResponseSchema,
            status_code=status.HTTP_200_OK,
            deprecated=True,
            description="""
            ## ⚠️ DEPRECATED: Используйте /document-services
            
            ## 🔍 Получить детали проблемы

            **⚠️ УСТАРЕЛО**: Этот эндпоинт будет удалён в будущих версиях.
            Используйте `/api/v1/document-services/{id}` для новых интеграций.

            Возвращает полную информацию о проблеме, включая автора.

            ### 🌐 Публичный доступ (без токена)

            ### Path параметры:
            * **issue_id**: UUID проблемы

            ### Returns:
            * **IssueResponseSchema**: Полная информация о проблеме

            ### Включает:
            * Все поля проблемы (title, description, category, status, solution)
            * Информация об авторе (id, username, email)
            * Временные метки (created_at, updated_at, resolved_at)
            """,
            responses={
                200: {"description": "Проблема найдена"},
                404: {"description": "Проблема не найдена"},
            },
        )
        async def get_issue(
            issue_id: UUID,
            issue_service: IssueServiceDep = None,
        ) -> IssueResponseSchema:
            """
            Получает детали проблемы по ID.

            🌐 **Публичный эндпоинт**: Не требует аутентификации.

            Args:
                issue_id: UUID проблемы.
                issue_service: Сервис для работы с проблемами.

            Returns:
                IssueResponseSchema: Обёртка с полной информацией о проблеме.

            Raises:
                IssueNotFoundError: Если проблема не найдена (обрабатывается глобально).

            Note:
                Возвращает IssueDetailSchema с информацией об авторе.
            """
            # Получаем проблему через сервис
            issue = await issue_service.get_issue(issue_id)

            # Преобразуем domain object → schema
            issue_schema = IssueDetailSchema.model_validate(issue)

            return IssueResponseSchema(success=True, data=issue_schema)

        # ==================== HISTORY ====================

        @self.router.get(
            path="/history",
            response_model=IssueListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📜 История решённых проблем

            Возвращает список последних решённых проблем (статус GREEN)
            отсортированных по дате решения (DESC).

            ### 🌐 Публичный доступ (без токена)

            ### Query параметры:
            * **limit**: Количество результатов (1-100, по умолчанию 50)
            * **offset**: Смещение для пагинации (по умолчанию 0)

            ### Returns:
            * **IssueListResponseSchema**: Список последних решённых проблем

            ### Сортировка:
            * По полю resolved_at в порядке убывания (новые первыми)
            * Только проблемы со статусом GREEN

            ### Use Cases:
            * Просмотр истории решений
            * Поиск похожих решённых проблем
            * Обучение на опыте решения проблем
            """,
            responses={
                200: {"description": "История успешно получена"},
            },
        )
        async def get_history(
            limit: int = Query(
                50, ge=1, le=100, description="Количество результатов (1-100)"
            ),
            offset: int = Query(
                0, ge=0, description="Смещение для пагинации"
            ),
            issue_service: IssueServiceDep = None,
        ) -> IssueListResponseSchema:
            """
            Получает историю последних решённых проблем.

            🌐 **Публичный эндпоинт**: Не требует аутентификации.

            Args:
                limit: Максимальное количество результатов.
                offset: Смещение для пагинации.
                issue_service: Сервис для работы с проблемами.

            Returns:
                IssueListResponseSchema: Обёртка со списком последних проблем.

            Note:
                Использует get_recent_issues под капотом (сортировка по created_at DESC).
                TODO: Добавить фильтр по status=GREEN и сортировку по resolved_at.
            """
            # Получаем последние проблемы через сервис
            issues = await issue_service.get_recent_issues(
                limit=limit,
                offset=offset,
            )

            # Преобразуем список domain objects → schemas
            issues_schemas = [
                IssueListItemSchema.model_validate(issue) for issue in issues
            ]

            return IssueListResponseSchema(
                success=True,
                data=issues_schemas,
                count=len(issues_schemas),
            )


class IssueProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для создания и управления проблемами.

    Все эндпоинты в этом роутере автоматически защищены через ProtectedRouter.
    CurrentUserDep доступен глобально через зависимости роутера.

    Protected Endpoints (требуется токен):
        POST /issues - Создать проблему
        PATCH /issues/{id}/resolve - Решить проблему (только автор)

    Архитектурные особенности:
        - Все endpoints требуют аутентификации (ProtectedRouter)
        - current_user доступен через глобальную зависимость
        - Роутер преобразует IssueModel → Schema
        - Проверка прав доступа в сервисном слое
    """

    def __init__(self):
        """Инициализирует IssueProtectedRouter с автоматической защитой."""
        super().__init__(prefix="issues", tags=["Issues"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== CREATE ====================

        @self.router.post(
            path="",
            response_model=IssueResponseSchema,
            status_code=status.HTTP_201_CREATED,
            deprecated=True,
            description="""
            ## ⚠️ DEPRECATED: Используйте /document-services
            
            ## 📝 Создать новую проблему

            **⚠️ УСТАРЕЛО**: Этот эндпоинт будет удалён в будущих версиях.
            Используйте `POST /api/v1/document-services` для новых интеграций.

            Создаёт запись о проблеме в коллективной памяти.
            Статус автоматически устанавливается в RED.

            ### 🔒 Требуется аутентификация (ProtectedRouter)

            ### Параметры:
            * **title**: Краткое название проблемы (обязательно, макс 255 символов)
            * **description**: Подробное описание проблемы
            * **category**: Категория (hardware, software, process)

            ### Returns:
            * **IssueResponseSchema**: Созданная проблема с деталями

            ### Business Rules:
            * Автор автоматически берётся из current_user (глобальная зависимость)
            * Статус всегда RED при создании
            * Title не может быть пустым
            * Category валидируется из списка разрешённых

            ### Примеры категорий:
            * **hardware** - Проблемы с оборудованием
            * **software** - Ошибки в ПО
            * **process** - Проблемы с процессами
            """,
            responses={
                201: {"description": "Проблема успешно создана"},
                401: {"description": "Требуется аутентификация"},
                422: {"description": "Ошибка валидации данных"},
            },
        )
        async def create_issue(
            data: IssueCreateRequestSchema,
            current_user: CurrentUserDep = None,
            issue_service: IssueServiceDep = None,
        ) -> IssueResponseSchema:
            """
            Создаёт новую проблему.

            🔒 **Защищённый эндпоинт** (ProtectedRouter): Автоматическая проверка токена.

            Args:
                data: Данные для создания проблемы.
                current_user: Текущий пользователь (из глобальной зависимости ProtectedRouter).
                issue_service: Сервис для работы с проблемами.

            Returns:
                IssueResponseSchema: Обёртка с созданной проблемой.

            Raises:
                IssueValidationError: При невалидных данных (обрабатывается глобально).

            Note:
                Сервис возвращает IssueModel, роутер преобразует в IssueDetailSchema.
                current_user доступен через ProtectedRouter (не нужно вручную проверять токен).
            """
            # Создаём проблему через сервис (возвращает domain object)
            issue = await issue_service.create_issue(
                author_id=current_user.id,
                workspace_id=data.workspace_id,
                title=data.title,
                description=data.description,
                category=data.category,
                template_id=data.template_id,
                custom_fields=data.custom_fields,
            )

            # Преобразуем domain object → schema
            issue_schema = IssueDetailSchema.model_validate(issue)

            return IssueResponseSchema(success=True, data=issue_schema)

        # ==================== RESOLVE ====================

        @self.router.patch(
            path="/{issue_id}/resolve",
            response_model=IssueResponseSchema,
            status_code=status.HTTP_200_OK,
            deprecated=True,
            description="""
            ## ⚠️ DEPRECATED: Используйте /document-services
            
            ## ✅ Решить проблему

            **⚠️ УСТАРЕЛО**: Этот эндпоинт будет удалён в будущих версиях.

            Закрывает проблему с решением (меняет статус на GREEN).

            ### 🔒 Требуется аутентификация (ProtectedRouter)

            ### Business Rules:
            * Только автор проблемы может её решить
            * Нельзя повторно решить уже решённую проблему (GREEN)
            * Решение (solution) не может быть пустым

            ### Path параметры:
            * **issue_id**: UUID проблемы для решения

            ### Body параметры:
            * **solution**: Текст решения проблемы (обязательно)

            ### Returns:
            * **IssueResponseSchema**: Обновлённая проблема со статусом GREEN

            ### Автоматически:
            * Статус меняется на GREEN
            * Заполняется поле solution
            * Устанавливается resolved_at (текущее время)
            """,
            responses={
                200: {"description": "Проблема успешно решена"},
                400: {"description": "Проблема уже решена"},
                401: {"description": "Требуется аутентификация"},
                403: {"description": "Нет прав на решение проблемы"},
                404: {"description": "Проблема не найдена"},
            },
        )
        async def resolve_issue(
            issue_id: UUID,
            data: IssueResolveRequestSchema,
            current_user: CurrentUserDep = None,
            issue_service: IssueServiceDep = None,
        ) -> IssueResponseSchema:
            """
            Решает проблему (закрывает с решением).

            🔒 **Защищённый эндпоинт** (ProtectedRouter): Автоматическая проверка токена.

            Args:
                issue_id: UUID проблемы для решения.
                data: Данные с решением.
                current_user: Текущий пользователь (из глобальной зависимости ProtectedRouter).
                issue_service: Сервис для работы с проблемами.

            Returns:
                IssueResponseSchema: Обёртка с решённой проблемой.

            Raises:
                IssueNotFoundError: Если проблема не найдена (обрабатывается глобально).
                IssuePermissionDeniedError: Если пользователь не автор (обрабатывается глобально).
                IssueAlreadyResolvedError: Если проблема уже решена (обрабатывается глобально).
                IssueValidationError: Если solution пустой (обрабатывается глобально).

            Note:
                Проверка прав доступа происходит в сервисном слое.
                current_user доступен через ProtectedRouter.
            """
            # Решаем проблему через сервис
            resolved_issue = await issue_service.resolve_issue(
                issue_id=issue_id,
                solution=data.solution,
                user_id=current_user.id,
            )

            # Преобразуем domain object → schema
            issue_schema = IssueDetailSchema.model_validate(resolved_issue)

            return IssueResponseSchema(success=True, data=issue_schema)

        # ==================== UPDATE ====================

        @self.router.patch(
            path="/{issue_id}",
            response_model=IssueResponseSchema,
            status_code=status.HTTP_200_OK,
            deprecated=True,
            description="""
            ## ⚠️ DEPRECATED: Используйте /document-services
            
            ## ✏️ Обновить проблему

            **⚠️ УСТАРЕЛО**: Этот эндпоинт будет удалён в будущих версиях.

            Обновляет данные проблемы (title, description, custom_fields и т.д.).

            ### 🔒 Требуется аутентификация (ProtectedRouter)

            ### Business Rules:
            * Только автор проблемы может её обновлять
            * Все поля опциональные (обновляются только переданные)
            * custom_fields валидируются по template_id (если проблема связана с шаблоном)
            * Нельзя изменить resolved_at и created_at напрямую

            ### Path параметры:
            * **issue_id**: UUID проблемы для обновления

            ### Body параметры:
            * **title**: Новый заголовок (опционально)
            * **description**: Новое описание (опционально)
            * **category**: Новая категория (опционально)
            * **status**: Новый статус (опционально)
            * **visibility**: Новая видимость (опционально)
            * **custom_fields**: Обновлённые динамические поля (опционально)

            ### Returns:
            * **IssueResponseSchema**: Обновлённая проблема

            ### Примеры использования:
            * Изменить заголовок: PATCH /issues/{id} {"title": "Новый заголовок"}
            * Обновить custom_fields: PATCH /issues/{id} {"custom_fields": {"error_code": "E402"}}
            """,
            responses={
                200: {"description": "Проблема успешно обновлена"},
                401: {"description": "Требуется аутентификация"},
                403: {"description": "Доступ запрещён (не автор проблемы)"},
                404: {"description": "Проблема не найдена"},
                422: {"description": "Ошибка валидации данных"},
            },
        )
        async def update_issue(
            issue_id: UUID,
            data: IssueUpdateRequestSchema,
            current_user: CurrentUserDep = None,
            issue_service: IssueServiceDep = None,
        ) -> IssueResponseSchema:
            """
            Обновляет данные проблемы.

            🔒 **Защищённый эндпоинт** (ProtectedRouter): Автоматическая проверка токена.

            Args:
                issue_id: UUID проблемы для обновления.
                data: Данные для обновления (все поля опциональные).
                current_user: Текущий пользователь (из глобальной зависимости ProtectedRouter).
                issue_service: Сервис для работы с проблемами.

            Returns:
                IssueResponseSchema: Обёртка с обновлённой проблемой.

            Raises:
                IssueNotFoundError: Если проблема не найдена (обрабатывается глобально).
                IssuePermissionDeniedError: Если пользователь не автор (обрабатывается глобально).
                IssueValidationError: Если данные невалидны (обрабатывается глобально).
                TemplateNotFoundError: Если template_id не найден (обрабатывается глобально).

            Note:
                Проверка прав доступа происходит в сервисном слое.
                custom_fields валидируются по шаблону (если проблема связана с template_id).
            """
            # Обновляем проблему через сервис
            updated_issue = await issue_service.update_issue(
                issue_id=issue_id,
                user_id=current_user.id,
                title=data.title,
                description=data.description,
                category=data.category,
                status=data.status,
                visibility=data.visibility,
                custom_fields=data.custom_fields,
            )

            # Преобразуем domain object → schema
            issue_schema = IssueDetailSchema.model_validate(updated_issue)

            return IssueResponseSchema(success=True, data=issue_schema)
