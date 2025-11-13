"""
Роутеры для работы с Workspace.

Модуль предоставляет HTTP API для управления workspace, разделённое на:
- WorkspaceProtectedRouter (ProtectedRouter) - защищённые endpoints с JWT

Все операции требуют аутентификации.
Обработка исключений: автоматическая обработка через глобальный exception handler.
Роутеры преобразуют domain objects (WorkspaceModel) в Pydantic схемы для ответа.
"""

from uuid import UUID

from fastapi import status

from src.core.dependencies.workspaces import WorkspaceServiceDep
from src.core.security import CurrentUserDep
from src.routers.base import ProtectedRouter
from src.schemas.v1.workspaces import (
    MemberAddSchema,
    MemberListResponseSchema,
    MemberResponseSchema,
    MemberUpdateSchema,
    WorkspaceCreateSchema,
    WorkspaceDetailSchema,
    WorkspaceListItemSchema,
    WorkspaceListResponseSchema,
    WorkspaceResponseSchema,
    WorkspaceUpdateSchema,
)


class WorkspaceProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для работы с Workspace.

    Предоставляет HTTP API для управления workspace и участниками:

    Protected Endpoints (требуется JWT):
        POST /workspaces - Создать workspace
        GET /workspaces/me - Список моих workspace
        GET /workspaces/{id} - Детали workspace
        PATCH /workspaces/{id} - Обновить workspace
        PUT /workspaces/{id} - Обновить workspace (alias для PATCH)
        DELETE /workspaces/{id} - Удалить workspace
        POST /workspaces/{id}/members - Добавить участника
        GET /workspaces/{id}/members - Список участников
        PATCH /workspaces/{id}/members/{user_id} - Изменить роль участника
        DELETE /workspaces/{id}/members/{user_id} - Удалить участника

    Архитектурные особенности:
        - Все endpoints требуют JWT аутентификации
        - Роутер преобразует WorkspaceModel → Schema
        - Бизнес-логика в WorkspaceService
        - Проверка прав доступа в Service
    """

    def __init__(self):
        """Инициализирует WorkspaceProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="workspaces", tags=["Workspaces"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== CREATE ====================

        @self.router.post(
            path="",
            response_model=WorkspaceResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""
            ## 🏢 Создать новый Workspace

            Создаёт новый workspace с автоматическими назначениями:
            - Генерация уникального slug из name
            - Создатель становится владельцем (owner_id)
            - Создатель автоматически добавляется как OWNER-участник

            ### 🔒 Требуется JWT токен

            ### Request Body:
            * **name**: Название workspace (3-100 символов)
            * **description**: Описание workspace (опционально, макс 500 символов)
            * **visibility**: Видимость (public/private, по умолчанию private)
            * **settings**: Настройки workspace в JSON (опционально)

            ### Returns:
            * **WorkspaceResponseSchema**: Созданный workspace с деталями

            ### Примеры использования:
            ```bash
            curl -X POST /api/v1/workspaces \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "name": "Marketing Team",
                "description": "Workspace for marketing activities",
                "visibility": "private"
              }'
            ```
            """,
        )
        async def create_workspace(
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
            data: WorkspaceCreateSchema = ...,
        ) -> WorkspaceResponseSchema:
            """
            Создать новый workspace.

            Автоматически назначает текущего пользователя владельцем.
            """
            workspace = await workspace_service.create_workspace(
                user_id=current_user.id,
                data=data,
            )

            # Преобразование domain object → schema
            schema = WorkspaceDetailSchema.model_validate(workspace)
            return WorkspaceResponseSchema(
                success=True,
                data=schema,
                message="Workspace создан успешно",
            )

        # ==================== LIST MY WORKSPACES ====================

        @self.router.get(
            path="/me",
            response_model=WorkspaceListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📋 Получить список моих Workspace

            Возвращает все workspace где пользователь:
            - Владелец (owner_id)
            - Участник (через WorkspaceMember)

            ### 🔒 Требуется JWT токен

            ### Returns:
            * **WorkspaceListResponseSchema**: Список workspace пользователя

            ### Примеры использования:
            ```bash
            curl -X GET /api/v1/workspaces/me \\
              -H "Authorization: Bearer <token>"
            ```
            """,
        )
        async def list_my_workspaces(
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> WorkspaceListResponseSchema:
            """
            Получить список workspace текущего пользователя.

            Включает owned + member workspace.
            """
            workspaces = await workspace_service.list_user_workspaces(
                user_id=current_user.id,
            )

            # Преобразование domain objects → schemas
            schemas = [
                WorkspaceListItemSchema(
                    id=w.id,
                    slug=w.slug,
                    name=w.name,
                    description=w.description,
                    visibility=w.visibility,
                    owner_id=w.owner_id,
                    member_count=len(w.members) if w.members else 0,
                    ai_modules_enabled=w.ai_modules_enabled,
                )
                for w in workspaces
            ]

            return WorkspaceListResponseSchema(
                success=True,
                data=schemas,
                total=len(schemas),
            )

        # ==================== GET BY ID ====================

        @self.router.get(
            path="/{workspace_id}",
            response_model=WorkspaceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔍 Получить детали Workspace

            Возвращает полную информацию о workspace:
            - Основные данные (name, slug, description)
            - Владелец (owner)
            - Список участников (members)
            - Настройки (settings)

            ### 🔒 Требуется JWT токен
            ### ✅ Проверка доступа:
            - PUBLIC workspace: доступны всем
            - PRIVATE workspace: только участникам

            ### Path параметры:
            * **workspace_id**: UUID workspace

            ### Returns:
            * **WorkspaceResponseSchema**: Детальная информация о workspace

            ### Примеры использования:
            ```bash
            curl -X GET /api/v1/workspaces/<uuid> \\
              -H "Authorization: Bearer <token>"
            ```
            """,
        )
        async def get_workspace(
            workspace_id: UUID,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> WorkspaceResponseSchema:
            """
            Получить workspace по ID.

            Проверяет права доступа пользователя.
            """
            workspace = await workspace_service.get_workspace(
                workspace_id=workspace_id,
                user_id=current_user.id,
            )

            # Преобразование domain object → schema
            schema = WorkspaceDetailSchema.model_validate(workspace)
            return WorkspaceResponseSchema(
                success=True,
                data=schema,
            )

        # ==================== UPDATE ====================

        @self.router.patch(
            path="/{workspace_id}",
            response_model=WorkspaceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ✏️ Обновить Workspace

            Обновляет данные workspace.
            Все поля опциональны - передавайте только изменяемые.

            ### 🔒 Требуется JWT токен
            ### ⚠️ Требуется роль: OWNER или ADMIN

            ### Path параметры:
            * **workspace_id**: UUID workspace

            ### Request Body (все опционально):
            * **name**: Новое название workspace
            * **description**: Новое описание
            * **visibility**: Новая видимость (public/private)
            * **settings**: Обновлённые настройки

            ### Returns:
            * **WorkspaceResponseSchema**: Обновлённый workspace

            ### Примеры использования:
            ```bash
            curl -X PATCH /api/v1/workspaces/<uuid> \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "name": "New Marketing Team",
                "visibility": "public"
              }'
            ```
            """,
        )
        async def update_workspace(
            workspace_id: UUID,
            data: WorkspaceUpdateSchema,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> WorkspaceResponseSchema:
            """
            Обновить workspace.

            Только OWNER или ADMIN могут обновлять.
            """
            workspace = await workspace_service.update_workspace(
                workspace_id=workspace_id,
                user_id=current_user.id,
                data=data,
            )

            # Преобразование domain object → schema
            schema = WorkspaceDetailSchema.model_validate(workspace)
            return WorkspaceResponseSchema(
                success=True,
                data=schema,
                message="Workspace обновлён успешно",
            )

        # ==================== ADD MEMBER ====================

        @self.router.post(
            path="/{workspace_id}/members",
            response_model=MemberResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""
            ## 👥 Добавить участника в Workspace

            Добавляет нового участника в workspace с указанной ролью.

            ### 🔒 Требуется JWT токен
            ### ⚠️ Требуется роль: OWNER или ADMIN

            ### Path параметры:
            * **workspace_id**: UUID workspace

            ### Request Body:
            * **user_id**: UUID добавляемого пользователя
            * **role**: Роль (admin/member, нельзя добавить второго owner)

            ### Returns:
            * **MemberResponseSchema**: Созданная запись участника

            ### Примеры использования:
            ```bash
            curl -X POST /api/v1/workspaces/<uuid>/members \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "user_id": "<user-uuid>",
                "role": "admin"
              }'
            ```
            """,
        )
        async def add_member(
            workspace_id: UUID,
            data: MemberAddSchema,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> MemberResponseSchema:
            """
            Добавить участника в workspace.

            Только OWNER или ADMIN могут добавлять участников.
            """
            member = await workspace_service.add_member(
                workspace_id=workspace_id,
                requester_id=current_user.id,
                data=data,
            )

            # Преобразование domain object → schema
            from src.schemas.v1.workspaces import WorkspaceMemberDetailSchema

            schema = WorkspaceMemberDetailSchema.model_validate(member)
            return MemberResponseSchema(
                success=True,
                data=schema,
                message="Участник добавлен в workspace",
            )

        # ==================== GET MEMBERS ====================

        @self.router.get(
            path="/{workspace_id}/members",
            response_model=MemberListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 👥 Получить список участников Workspace

            Возвращает всех участников workspace с их ролями.

            ### 🔒 Требуется JWT токен
            ### ✅ Проверка доступа:
            - PUBLIC workspace: доступно всем
            - PRIVATE workspace: только участникам

            ### Path параметры:
            * **workspace_id**: UUID workspace

            ### Returns:
            * **MemberListResponseSchema**: Список участников workspace

            ### Примеры использования:
            ```bash
            curl -X GET /api/v1/workspaces/<uuid>/members \\
              -H "Authorization: Bearer <token>"
            ```
            """,
        )
        async def get_members(
            workspace_id: UUID,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ):
            """
            Получить список участников workspace.

            Проверяет доступ к workspace.
            """
            from src.schemas.v1.workspaces import MemberListResponseSchema

            members = await workspace_service.get_workspace_members(
                workspace_id=workspace_id,
                user_id=current_user.id,
            )

            # Преобразование domain objects → schemas
            from src.schemas.v1.workspaces import WorkspaceMemberDetailSchema

            schemas = [
                WorkspaceMemberDetailSchema.model_validate(m) for m in members
            ]

            return MemberListResponseSchema(
                success=True,
                data=schemas,
                total=len(schemas),
            )

        # ==================== UPDATE MEMBER ROLE ====================

        @self.router.patch(
            path="/{workspace_id}/members/{user_id}",
            response_model=MemberResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ✏️ Изменить роль участника Workspace

            Изменяет роль участника (admin/member).
            Нельзя изменить роль OWNER или назначить роль OWNER.

            ### 🔒 Требуется JWT токен
            ### ⚠️ Требуется роль: OWNER или ADMIN

            ### Path параметры:
            * **workspace_id**: UUID workspace
            * **user_id**: UUID участника, чью роль меняем

            ### Request Body:
            * **role**: Новая роль (admin/member)

            ### Returns:
            * **MemberResponseSchema**: Обновлённый участник

            ### Примеры использования:
            ```bash
            curl -X PATCH /api/v1/workspaces/<workspace-uuid>/members/<user-uuid> \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "role": "member"
              }'
            ```
            """,
        )
        async def update_member_role(
            workspace_id: UUID,
            user_id: UUID,
            data: MemberUpdateSchema,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> MemberResponseSchema:
            """
            Изменить роль участника workspace.

            Только OWNER или ADMIN могут изменять роли.
            """
            from src.models.v1.workspaces import WorkspaceMemberRole

            # Конвертация строки в enum
            role_map = {
                "admin": WorkspaceMemberRole.ADMIN,
                "member": WorkspaceMemberRole.MEMBER,
            }
            new_role = role_map.get(data.role)

            member = await workspace_service.update_member_role(
                workspace_id=workspace_id,
                requester_id=current_user.id,
                member_user_id=user_id,
                new_role=new_role,
            )

            # Преобразование domain object → schema
            from src.schemas.v1.workspaces import WorkspaceMemberDetailSchema

            schema = WorkspaceMemberDetailSchema.model_validate(member)
            return MemberResponseSchema(
                success=True,
                data=schema,
                message="Роль участника обновлена",
            )

        # ==================== REMOVE MEMBER ====================

        @self.router.delete(
            path="/{workspace_id}/members/{user_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            description="""
            ## ❌ Удалить участника из Workspace

            Удаляет участника из workspace.
            Нельзя удалить OWNER.

            ### 🔒 Требуется JWT токен
            ### ⚠️ Требуется роль: OWNER или ADMIN

            ### Path параметры:
            * **workspace_id**: UUID workspace
            * **user_id**: UUID удаляемого участника

            ### Returns:
            * **204 No Content**: Участник успешно удалён

            ### Примеры использования:
            ```bash
            curl -X DELETE /api/v1/workspaces/<workspace-uuid>/members/<user-uuid> \\
              -H "Authorization: Bearer <token>"
            ```
            """,
        )
        async def remove_member(
            workspace_id: UUID,
            user_id: UUID,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> None:
            """
            Удалить участника из workspace.

            Только OWNER или ADMIN могут удалять участников.
            """
            await workspace_service.remove_member(
                workspace_id=workspace_id,
                requester_id=current_user.id,
                member_user_id=user_id,
            )

            # 204 No Content - ничего не возвращаем

        # ==================== DELETE WORKSPACE ====================

        @self.router.delete(
            path="/{workspace_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            description="""
            ## 🗑️ Удалить Workspace

            Удаляет workspace и все связанные данные.
            Каскадно удаляются: участники, issues, KB, n8n workflows.

            ### 🔒 Требуется JWT токен
            ### ⚠️ Требуется роль: OWNER

            ### Path параметры:
            * **workspace_id**: UUID workspace

            ### Returns:
            * **204 No Content**: Workspace успешно удалён

            ### Примеры использования:
            ```bash
            curl -X DELETE /api/v1/workspaces/<uuid> \\
              -H "Authorization: Bearer <token>"
            ```
            """,
        )
        async def delete_workspace(
            workspace_id: UUID,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> None:
            """
            Удалить workspace.

            Только OWNER может удалить workspace.
            """
            await workspace_service.delete_workspace(
                workspace_id=workspace_id,
                user_id=current_user.id,
            )

            # 204 No Content - ничего не возвращаем

        # ==================== PUT ALIAS FOR UPDATE ====================

        @self.router.put(
            path="/{workspace_id}",
            response_model=WorkspaceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ✏️ Обновить Workspace (PUT alias)

            Идентичен PATCH endpoint - частичное обновление workspace.
            Добавлен для совместимости с фронтендом.

            ### 🔒 Требуется JWT токен
            ### ⚠️ Требуется роль: OWNER или ADMIN

            ### Path параметры:
            * **workspace_id**: UUID workspace

            ### Request Body (все опционально):
            * **name**: Новое название workspace
            * **description**: Новое описание
            * **visibility**: Новая видимость (public/private)
            * **settings**: Обновлённые настройки

            ### Returns:
            * **WorkspaceResponseSchema**: Обновлённый workspace

            ### Примеры использования:
            ```bash
            curl -X PUT /api/v1/workspaces/<uuid> \\
              -H "Authorization: Bearer <token>" \\
              -H "Content-Type: application/json" \\
              -d '{
                "name": "New Marketing Team",
                "visibility": "public"
              }'
            ```
            """,
        )
        async def update_workspace_put(
            workspace_id: UUID,
            data: WorkspaceUpdateSchema,
            workspace_service: WorkspaceServiceDep = None,
            current_user: CurrentUserDep = None,
        ) -> WorkspaceResponseSchema:
            """
            Обновить workspace (PUT alias для PATCH).

            Реализация идентична PATCH endpoint.
            """
            workspace = await workspace_service.update_workspace(
                workspace_id=workspace_id,
                user_id=current_user.id,
                data=data,
            )

            # Преобразование domain object → schema
            schema = WorkspaceDetailSchema.model_validate(workspace)
            return WorkspaceResponseSchema(
                success=True,
                data=schema,
                message="Workspace обновлён успешно",
            )
