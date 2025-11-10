"""
Роутеры для работы с шаблонами (Templates).

Модуль предоставляет HTTP API для управления шаблонами проблем:
- TemplateProtectedRouter (ProtectedRouter) - защищённые CRUD endpoints

Все endpoints требуют JWT авторизации. Роутеры преобразуют domain objects
(TemplateModel) в Pydantic схемы для ответа.

Routes:
    GET    /templates          - Список шаблонов с фильтрацией
    GET    /templates/{id}     - Детали шаблона
    POST   /templates          - Создать шаблон
    PATCH  /templates/{id}     - Обновить шаблон
    DELETE /templates/{id}     - Удалить (деактивировать) шаблон
    POST   /templates/{id}/activate   - Активировать шаблон
    POST   /templates/{id}/deactivate - Деактивировать шаблон
"""

from typing import Optional
from uuid import UUID

from fastapi import Query, status

from src.core.dependencies.templates import TemplateServiceDep
from src.core.security import CurrentUserDep
from src.models.v1.templates import TemplateVisibility
from src.routers.base import ProtectedRouter
from src.schemas.v1.templates import (
    TemplateCreateRequestSchema,
    TemplateDetailSchema,
    TemplateListItemSchema,
    TemplateListResponseSchema,
    TemplateQueryRequestSchema,
    TemplateResponseSchema,
    TemplateUpdateRequestSchema,
)


class TemplateProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для управления шаблонами (Templates).

    Предоставляет HTTP API для CRUD операций с шаблонами проблем.
    Все endpoints требуют JWT авторизации.

    Protected Endpoints (требуется JWT):
        GET    /templates          - Список шаблонов с фильтрацией
        GET    /templates/{id}     - Детали шаблона
        POST   /templates          - Создать шаблон
        PATCH  /templates/{id}     - Обновить шаблон (только владелец)
        DELETE /templates/{id}     - Удалить шаблон (только владелец)
        POST   /templates/{id}/activate   - Активировать (только владелец)
        POST   /templates/{id}/deactivate - Деактивировать (только владелец)

    Архитектурные особенности:
        - Роутер преобразует TemplateModel → Schema
        - Бизнес-логика и права доступа в TemplateService
        - NO try-catch: глобальный exception handler обрабатывает ошибки
    """

    def __init__(self):
        """Инициализирует TemplateProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="templates", tags=["Templates"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== LIST ====================

        @self.router.get(
            path="",
            response_model=TemplateListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📋 Получить список шаблонов с фильтрацией

            Возвращает список шаблонов с опциональными фильтрами:
            - Публичные шаблоны доступны всем
            - Приватные шаблоны видны только владельцу

            ### 🔒 Требуется JWT токен

            ### Query параметры:
            * **category**: Фильтр по категории (hardware/software/process)
            * **visibility**: Фильтр по видимости (public/private/team)
            * **is_active**: Фильтр по активности (true/false)

            ### Returns:
            * **TemplateListResponseSchema**: Список шаблонов

            ### Примеры:
            * Все доступные: GET /templates
            * По категории: GET /templates?category=hardware
            * Только публичные: GET /templates?visibility=public
            * Активные: GET /templates?is_active=true
            """,
            responses={
                200: {"description": "Список шаблонов успешно получен"},
                401: {"description": "Не авторизован"},
            },
        )
        async def list_templates(
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
            category: Optional[str] = Query(None, description="Фильтр по категории"),
            visibility: Optional[TemplateVisibility] = Query(
                None, description="Фильтр по видимости"
            ),
            is_active: Optional[bool] = Query(
                None, description="Фильтр по активности"
            ),
        ) -> TemplateListResponseSchema:
            """Получить список шаблонов с фильтрами."""
            # Подготовка query
            query = TemplateQueryRequestSchema(
                category=category, visibility=visibility, is_active=is_active
            )

            # Получение через сервис
            templates = await template_service.list_templates(query, current_user.id)

            # Преобразование в схемы
            items = [TemplateListItemSchema.model_validate(t) for t in templates]
            return TemplateListResponseSchema(success=True, data=items)

        # ==================== GET ONE ====================

        @self.router.get(
            path="/{template_id}",
            response_model=TemplateResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📄 Получить детали шаблона по ID

            Возвращает полную информацию о шаблоне.
            Приватные шаблоны доступны только владельцу.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **template_id**: UUID шаблона

            ### Returns:
            * **TemplateResponseSchema**: Детали шаблона

            ### Errors:
            * **404**: Шаблон не найден
            * **403**: Нет прав на просмотр приватного шаблона
            """,
            responses={
                200: {"description": "Шаблон найден"},
                404: {"description": "Шаблон не найден"},
                403: {"description": "Нет прав доступа"},
                401: {"description": "Не авторизован"},
            },
        )
        async def get_template(
            template_id: UUID,
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
        ) -> TemplateResponseSchema:
            """Получить шаблон по ID."""
            template = await template_service.get_template(template_id, current_user.id)
            schema = TemplateDetailSchema.model_validate(template)
            return TemplateResponseSchema(success=True, data=schema)

        # ==================== CREATE ====================

        @self.router.post(
            path="",
            response_model=TemplateResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""
            ## ➕ Создать новый шаблон

            Создаёт шаблон с валидацией полей (title, category, JSONB fields).
            Автор устанавливается автоматически из JWT токена.

            ### 🔒 Требуется JWT токен

            ### Body:
            * **title**: Название шаблона (3-200 символов)
            * **description**: Описание назначения
            * **category**: Категория (hardware/software/process)
            * **fields**: JSONB структура с динамическими полями
            * **visibility**: Уровень видимости (PUBLIC/PRIVATE/TEAM)

            ### Returns:
            * **TemplateResponseSchema**: Созданный шаблон

            ### Errors:
            * **400**: Невалидные данные
            """,
            responses={
                201: {"description": "Шаблон создан"},
                400: {"description": "Ошибка валидации"},
                401: {"description": "Не авторизован"},
            },
        )
        async def create_template(
            template_data: TemplateCreateRequestSchema,
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
        ) -> TemplateResponseSchema:
            """Создать новый шаблон."""
            template = await template_service.create_template(
                template_data, current_user.id
            )
            schema = TemplateDetailSchema.model_validate(template)
            return TemplateResponseSchema(
                success=True, data=schema, message="Шаблон создан"
            )

        # ==================== UPDATE ====================

        @self.router.patch(
            path="/{template_id}",
            response_model=TemplateResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ✏️ Обновить существующий шаблон

            Обновляет шаблон с валидацией изменяемых полей.
            Только владелец (author) может обновлять шаблон.

            ### 🔒 Требуется JWT токен (только владелец)

            ### Path параметры:
            * **template_id**: UUID шаблона

            ### Body (все поля опциональны):
            * **title**: Новое название (3-200 символов)
            * **description**: Новое описание
            * **category**: Новая категория
            * **fields**: Обновлённая JSONB структура
            * **visibility**: Новая видимость

            ### Returns:
            * **TemplateResponseSchema**: Обновлённый шаблон

            ### Errors:
            * **404**: Шаблон не найден
            * **403**: Нет прав (не владелец)
            * **400**: Невалидные данные
            """,
            responses={
                200: {"description": "Шаблон обновлён"},
                404: {"description": "Шаблон не найден"},
                403: {"description": "Нет прав (не владелец)"},
                400: {"description": "Ошибка валидации"},
                401: {"description": "Не авторизован"},
            },
        )
        async def update_template(
            template_id: UUID,
            template_data: TemplateUpdateRequestSchema,
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
        ) -> TemplateResponseSchema:
            """Обновить шаблон."""
            template = await template_service.update_template(
                template_id, template_data, current_user.id
            )
            schema = TemplateDetailSchema.model_validate(template)
            return TemplateResponseSchema(
                success=True, data=schema, message="Шаблон обновлён"
            )

        # ==================== DELETE ====================

        @self.router.delete(
            path="/{template_id}",
            response_model=TemplateResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🗑️ Удалить шаблон (soft delete)

            Деактивирует шаблон (is_active=False) вместо физического удаления.
            Только владелец (author) может удалять шаблон.

            ### 🔒 Требуется JWT токен (только владелец)

            ### Path параметры:
            * **template_id**: UUID шаблона

            ### Returns:
            * **TemplateResponseSchema**: Деактивированный шаблон

            ### Errors:
            * **404**: Шаблон не найден
            * **403**: Нет прав (не владелец)
            """,
            responses={
                200: {"description": "Шаблон удалён (деактивирован)"},
                404: {"description": "Шаблон не найден"},
                403: {"description": "Нет прав (не владелец)"},
                401: {"description": "Не авторизован"},
            },
        )
        async def delete_template(
            template_id: UUID,
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
        ) -> TemplateResponseSchema:
            """Удалить (деактивировать) шаблон."""
            template = await template_service.delete_template(
                template_id, current_user.id
            )
            schema = TemplateDetailSchema.model_validate(template)
            return TemplateResponseSchema(
                success=True, data=schema, message="Шаблон удалён"
            )

        # ==================== ACTIVATE ====================

        @self.router.post(
            path="/{template_id}/activate",
            response_model=TemplateResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔄 Активировать деактивированный шаблон

            Устанавливает is_active=True для повторного использования.
            Только владелец (author) может активировать шаблон.

            ### 🔒 Требуется JWT токен (только владелец)

            ### Path параметры:
            * **template_id**: UUID шаблона

            ### Returns:
            * **TemplateResponseSchema**: Активированный шаблон

            ### Errors:
            * **404**: Шаблон не найден
            * **403**: Нет прав (не владелец)
            * **400**: Шаблон уже активен
            """,
            responses={
                200: {"description": "Шаблон активирован"},
                404: {"description": "Шаблон не найден"},
                403: {"description": "Нет прав (не владелец)"},
                400: {"description": "Шаблон уже активен"},
                401: {"description": "Не авторизован"},
            },
        )
        async def activate_template(
            template_id: UUID,
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
        ) -> TemplateResponseSchema:
            """Активировать шаблон."""
            template = await template_service.activate_template(
                template_id, current_user.id
            )
            schema = TemplateDetailSchema.model_validate(template)
            return TemplateResponseSchema(
                success=True, data=schema, message="Шаблон активирован"
            )

        # ==================== DEACTIVATE ====================

        @self.router.post(
            path="/{template_id}/deactivate",
            response_model=TemplateResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ⏸️ Деактивировать активный шаблон

            Устанавливает is_active=False для временного отключения.
            Только владелец (author) может деактивировать шаблон.

            ### 🔒 Требуется JWT токен (только владелец)

            ### Path параметры:
            * **template_id**: UUID шаблона

            ### Returns:
            * **TemplateResponseSchema**: Деактивированный шаблон

            ### Errors:
            * **404**: Шаблон не найден
            * **403**: Нет прав (не владелец)
            * **400**: Шаблон уже деактивирован
            """,
            responses={
                200: {"description": "Шаблон деактивирован"},
                404: {"description": "Шаблон не найден"},
                403: {"description": "Нет прав (не владелец)"},
                400: {"description": "Шаблон уже деактивирован"},
                401: {"description": "Не авторизован"},
            },
        )
        async def deactivate_template(
            template_id: UUID,
            current_user: CurrentUserDep = None,
            template_service: TemplateServiceDep = None,
        ) -> TemplateResponseSchema:
            """Деактивировать шаблон."""
            template = await template_service.deactivate_template(
                template_id, current_user.id
            )
            schema = TemplateDetailSchema.model_validate(template)
            return TemplateResponseSchema(
                success=True, data=schema, message="Шаблон деактивирован"
            )
