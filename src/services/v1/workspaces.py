"""
Сервис для работы с Workspace.

Модуль содержит бизнес-логику для операций с workspace и их участниками:
- Создание workspace с автоматической генерацией slug
- Управление участниками (добавление, удаление, изменение ролей)
- Проверка прав доступа и ролей
- Получение workspace пользователя

Следует архитектурному паттерну: Router → Service → Repository → Model
"""

import logging
import re
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions.users import UserNotFoundError
from src.core.exceptions.workspaces import (
    WorkspaceAccessDeniedError,
    WorkspaceMemberExistsError,
    WorkspaceMemberNotFoundError,
    WorkspaceNotFoundError,
    WorkspaceOwnerConflictError,
    WorkspacePermissionDeniedError,
    WorkspaceSlugExistsError,
)
from src.models.v1.workspaces import (
    WorkspaceMemberModel,
    WorkspaceMemberRole,
    WorkspaceModel,
)
from src.repository.v1.users import UserRepository
from src.repository.v1.workspaces import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from src.schemas.v1.workspaces import (
    MemberAddRequestSchema,
    WorkspaceCreateRequestSchema,
    WorkspaceUpdateRequestSchema,
)

logger = logging.getLogger(__name__)


class WorkspaceService:
    """
    Сервис для работы с Workspace.

    Предоставляет бизнес-логику для операций с workspace:
    - CRUD операции
    - Управление участниками
    - Валидация прав доступа
    - Генерация уникальных slug

    Attributes:
        session: Асинхронная сессия SQLAlchemy
        workspace_repo: Репозиторий для работы с workspace
        member_repo: Репозиторий для работы с участниками
        user_repo: Репозиторий для работы с пользователями

    Example:
        >>> service = WorkspaceService(session)
        >>> workspace = await service.create_workspace(
        ...     user_id=current_user.id,
        ...     data=WorkspaceCreateRequestSchema(name="Marketing Team")
        ... )
    """

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            session: Асинхронная сессия SQLAlchemy
        """
        self.session = session
        self.workspace_repo = WorkspaceRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)
        self.user_repo = UserRepository(session)

    async def create_workspace(
        self,
        user_id: UUID,
        data: WorkspaceCreateRequestSchema,
    ) -> WorkspaceModel:
        """
        Создать новый workspace.

        Автоматически:
        - Генерирует уникальный slug из name
        - Назначает создателя владельцем (owner_id)
        - Добавляет создателя как участника с ролью OWNER

        Args:
            user_id: UUID создателя workspace
            data: Данные для создания workspace

        Returns:
            WorkspaceModel: Созданный workspace

        Raises:
            UserNotFoundError: Если пользователь не найден
            WorkspaceSlugExistsError: Если не удалось сгенерировать уникальный slug

        Example:
            >>> workspace = await service.create_workspace(
            ...     user_id=user.id,
            ...     data=WorkspaceCreateRequestSchema(name="Marketing Team")
            ... )
            >>> workspace.slug
            'marketing-team'
            >>> workspace.owner_id == user.id
            True
        """
        # Проверка существования пользователя
        user = await self.user_repo.get_item_by_id(user_id)
        if not user:
            logger.warning("Попытка создать workspace от несуществующего пользователя: %s", user_id)
            raise UserNotFoundError(field="id", value=str(user_id))

        # Генерация уникального slug
        slug = await self._generate_unique_slug(data.name)
        logger.info("Сгенерирован slug '%s' для workspace '%s'", slug, data.name)

        # Создание workspace
        workspace_data = data.model_dump()
        workspace_data["slug"] = slug
        workspace_data["owner_id"] = user_id

        workspace = await self.workspace_repo.create_item(workspace_data)
        logger.info("Создан workspace: %s (slug: %s)", workspace.id, workspace.slug)

        # Добавление создателя как OWNER-участника
        member_data = {
            "workspace_id": workspace.id,
            "user_id": user_id,
            "role": WorkspaceMemberRole.OWNER,
        }
        await self.member_repo.create_item(member_data)
        logger.info("Добавлен OWNER-участник %s в workspace %s", user_id, workspace.id)

        return workspace

    async def get_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceModel:
        """
        Получить workspace по ID.

        Проверяет права доступа пользователя.
        Пользователь должен быть участником workspace или workspace должен быть PUBLIC.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя

        Returns:
            WorkspaceModel: Workspace с eager loading owner и members

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspaceAccessDeniedError: Если нет прав доступа

        Example:
            >>> workspace = await service.get_workspace(
            ...     workspace_id=workspace_id,
            ...     user_id=current_user.id
            ... )
        """
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка прав доступа
        await self._check_access(workspace, user_id)

        return workspace

    async def get_workspace_by_slug(
        self,
        slug: str,
        user_id: UUID,
    ) -> WorkspaceModel:
        """
        Получить workspace по slug.

        Проверяет права доступа пользователя.

        Args:
            slug: URL-friendly идентификатор workspace
            user_id: UUID пользователя

        Returns:
            WorkspaceModel: Workspace

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspaceAccessDeniedError: Если нет прав доступа

        Example:
            >>> workspace = await service.get_workspace_by_slug(
            ...     slug="marketing-team",
            ...     user_id=current_user.id
            ... )
        """
        workspace = await self.workspace_repo.get_by_slug(slug)
        if not workspace:
            logger.warning("Workspace с slug '%s' не найден", slug)
            raise WorkspaceNotFoundError(slug=slug)

        # Проверка прав доступа
        await self._check_access(workspace, user_id)

        return workspace

    async def list_user_workspaces(
        self,
        user_id: UUID,
    ) -> List[WorkspaceModel]:
        """
        Получить все workspace пользователя.

        Возвращает workspace где пользователь:
        - Владелец (owner_id)
        - Участник (через WorkspaceMember)

        Args:
            user_id: UUID пользователя

        Returns:
            List[WorkspaceModel]: Список workspace пользователя

        Example:
            >>> workspaces = await service.list_user_workspaces(current_user.id)
            >>> for workspace in workspaces:
            ...     print(workspace.name, workspace.slug)
        """
        workspaces = await self.workspace_repo.get_user_workspaces(
            user_id=user_id,
            include_member=True,
        )

        logger.info("Найдено %d workspace для пользователя %s", len(workspaces), user_id)
        return workspaces

    async def update_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        data: WorkspaceUpdateRequestSchema,
    ) -> WorkspaceModel:
        """
        Обновить workspace.

        Только OWNER или ADMIN могут обновлять workspace.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя
            data: Данные для обновления

        Returns:
            WorkspaceModel: Обновлённый workspace

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspacePermissionDeniedError: Если нет прав

        Example:
            >>> workspace = await service.update_workspace(
            ...     workspace_id=workspace_id,
            ...     user_id=current_user.id,
            ...     data=WorkspaceUpdateRequestSchema(name="New Name")
            ... )
        """
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка прав (OWNER или ADMIN)
        await self._check_admin_permission(workspace_id, user_id)

        # Обновление
        update_data = data.model_dump(exclude_unset=True)
        updated = await self.workspace_repo.update_item(workspace_id, update_data)

        logger.info("Обновлён workspace %s пользователем %s", workspace_id, user_id)
        return updated

    async def add_member(
        self,
        workspace_id: UUID,
        requester_id: UUID,
        data: MemberAddRequestSchema,
    ) -> WorkspaceMemberModel:
        """
        Добавить участника в workspace.

        Только OWNER или ADMIN могут добавлять участников.
        Нельзя добавить второго OWNER.

        Args:
            workspace_id: UUID workspace
            requester_id: UUID пользователя, добавляющего участника
            data: Данные нового участника

        Returns:
            WorkspaceMemberModel: Созданная запись участника

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            UserNotFoundError: Если добавляемый пользователь не найден
            WorkspacePermissionDeniedError: Если нет прав
            WorkspaceMemberExistsError: Если пользователь уже участник
            WorkspaceOwnerConflictError: Если пытаются добавить второго OWNER

        Example:
            >>> member = await service.add_member(
            ...     workspace_id=workspace_id,
            ...     requester_id=current_user.id,
            ...     data=MemberAddRequestSchema(user_id=user_id, role="admin")
            ... )
        """
        # Проверка workspace
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка прав (OWNER или ADMIN)
        await self._check_admin_permission(workspace_id, requester_id)

        # Проверка существования пользователя
        user = await self.user_repo.get_item_by_id(data.user_id)
        if not user:
            logger.warning("Пользователь %s не найден", data.user_id)
            raise UserNotFoundError(field="id", value=str(data.user_id))

        # Проверка что пользователь ещё не участник
        existing = await self.member_repo.get_member(workspace_id, data.user_id)
        if existing:
            logger.warning(
                "Пользователь %s уже участник workspace %s",
                data.user_id,
                workspace_id,
            )
            raise WorkspaceMemberExistsError(
                workspace_id=workspace_id,
                user_id=data.user_id,
            )

        # Проверка что не добавляют второго OWNER
        if data.role.lower() == WorkspaceMemberRole.OWNER.value:
            logger.warning(
                "Попытка добавить второго OWNER в workspace %s",
                workspace_id,
            )
            raise WorkspaceOwnerConflictError(workspace_id=workspace_id)

        # Создание участника
        member_data = {
            "workspace_id": workspace_id,
            "user_id": data.user_id,
            "role": WorkspaceMemberRole(data.role.lower()),
        }
        member = await self.member_repo.create_item(member_data)

        logger.info(
            "Добавлен участник %s с ролью %s в workspace %s",
            data.user_id,
            data.role,
            workspace_id,
        )
        return member

    async def remove_member(
        self,
        workspace_id: UUID,
        requester_id: UUID,
        member_user_id: UUID,
    ) -> bool:
        """
        Удалить участника из workspace.

        Только OWNER или ADMIN могут удалять участников.
        Нельзя удалить OWNER.

        Args:
            workspace_id: UUID workspace
            requester_id: UUID пользователя, удаляющего участника
            member_user_id: UUID удаляемого участника

        Returns:
            bool: True если участник удалён

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspacePermissionDeniedError: Если нет прав
            WorkspaceMemberNotFoundError: Если участник не найден
            WorkspaceOwnerConflictError: Если пытаются удалить OWNER

        Example:
            >>> removed = await service.remove_member(
            ...     workspace_id=workspace_id,
            ...     requester_id=current_user.id,
            ...     member_user_id=user_id
            ... )
        """
        # Проверка workspace
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка прав (OWNER или ADMIN)
        await self._check_admin_permission(workspace_id, requester_id)

        # Проверка существования участника
        member = await self.member_repo.get_member(workspace_id, member_user_id)
        if not member:
            logger.warning(
                "Участник %s не найден в workspace %s",
                member_user_id,
                workspace_id,
            )
            raise WorkspaceMemberNotFoundError(
                workspace_id=workspace_id,
                user_id=member_user_id,
            )

        # Нельзя удалить OWNER
        if member.role == WorkspaceMemberRole.OWNER:
            logger.warning(
                "Попытка удалить OWNER из workspace %s",
                workspace_id,
            )
            raise WorkspaceOwnerConflictError(workspace_id=workspace_id)

        # Удаление
        removed = await self.member_repo.remove_member(workspace_id, member_user_id)
        logger.info(
            "Удалён участник %s из workspace %s",
            member_user_id,
            workspace_id,
        )
        return removed

    async def get_workspace_members(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> List[WorkspaceMemberModel]:
        """
        Получить список участников workspace.

        Требуется доступ к workspace (PUBLIC или membership).

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя, запрашивающего список

        Returns:
            List[WorkspaceMemberModel]: Список участников

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspaceAccessDeniedError: Если нет доступа к workspace

        Example:
            >>> members = await service.get_workspace_members(
            ...     workspace_id=workspace_id,
            ...     user_id=current_user.id
            ... )
        """
        # Проверка workspace
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка доступа
        await self._check_access(workspace, user_id)

        # Получение участников
        members = await self.member_repo.get_workspace_members(workspace_id)
        logger.info(
            "Получены %d участников workspace %s",
            len(members),
            workspace_id,
        )
        return members

    async def update_member_role(
        self,
        workspace_id: UUID,
        requester_id: UUID,
        member_user_id: UUID,
        new_role: WorkspaceMemberRole,
    ) -> WorkspaceMemberModel:
        """
        Изменить роль участника workspace.

        Только OWNER или ADMIN могут изменять роли.
        Нельзя изменить роль OWNER.
        Нельзя назначить роль OWNER (только передача владения отдельным методом).

        Args:
            workspace_id: UUID workspace
            requester_id: UUID пользователя, изменяющего роль
            member_user_id: UUID участника, чью роль меняем
            new_role: Новая роль (ADMIN или MEMBER)

        Returns:
            WorkspaceMemberModel: Обновлённый участник

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspacePermissionDeniedError: Если нет прав
            WorkspaceMemberNotFoundError: Если участник не найден
            WorkspaceOwnerConflictError: Если пытаются изменить роль OWNER или назначить OWNER

        Example:
            >>> member = await service.update_member_role(
            ...     workspace_id=workspace_id,
            ...     requester_id=current_user.id,
            ...     member_user_id=user_id,
            ...     new_role=WorkspaceMemberRole.MEMBER
            ... )
        """
        # Проверка workspace
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка прав (OWNER или ADMIN)
        await self._check_admin_permission(workspace_id, requester_id)

        # Проверка существования участника
        member = await self.member_repo.get_member(workspace_id, member_user_id)
        if not member:
            logger.warning(
                "Участник %s не найден в workspace %s",
                member_user_id,
                workspace_id,
            )
            raise WorkspaceMemberNotFoundError(
                workspace_id=workspace_id,
                user_id=member_user_id,
            )

        # Нельзя изменить роль OWNER
        if member.role == WorkspaceMemberRole.OWNER:
            logger.warning(
                "Попытка изменить роль OWNER в workspace %s",
                workspace_id,
            )
            raise WorkspaceOwnerConflictError(workspace_id=workspace_id)

        # Нельзя назначить роль OWNER
        if new_role == WorkspaceMemberRole.OWNER:
            logger.warning(
                "Попытка назначить роль OWNER в workspace %s",
                workspace_id,
            )
            raise WorkspaceOwnerConflictError(workspace_id=workspace_id)

        # Обновление роли через repository
        updated_member = await self.member_repo.update_member_role(
            workspace_id,
            member_user_id,
            new_role,
        )

        if not updated_member:
            logger.error(
                "Не удалось обновить роль участника %s в workspace %s",
                member_user_id,
                workspace_id,
            )
            raise WorkspaceMemberNotFoundError(
                workspace_id=workspace_id,
                user_id=member_user_id,
            )

        logger.info(
            "Изменена роль участника %s в workspace %s на %s",
            member_user_id,
            workspace_id,
            new_role.value,
        )
        return updated_member

    async def delete_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Удалить workspace.

        Только OWNER может удалить workspace.
        Удаляются все связанные данные (members, issues, KB и т.д.) каскадно.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя, удаляющего workspace

        Returns:
            bool: True если workspace удалён

        Raises:
            WorkspaceNotFoundError: Если workspace не найден
            WorkspacePermissionDeniedError: Если пользователь не OWNER

        Example:
            >>> deleted = await service.delete_workspace(
            ...     workspace_id=workspace_id,
            ...     user_id=current_user.id
            ... )
        """
        # Проверка workspace
        workspace = await self.workspace_repo.get_item_by_id(workspace_id)
        if not workspace:
            logger.warning("Workspace %s не найден", workspace_id)
            raise WorkspaceNotFoundError(workspace_id=workspace_id)

        # Проверка прав (только OWNER)
        role = await self.member_repo.get_user_role(workspace_id, user_id)
        if role != WorkspaceMemberRole.OWNER:
            logger.warning(
                "Пользователь %s не является OWNER workspace %s (роль: %s)",
                user_id,
                workspace_id,
                role,
            )
            raise WorkspacePermissionDeniedError(
                workspace_id=workspace_id,
                user_id=user_id,
                required_role="owner",
            )

        # Удаление workspace (каскадное удаление members через FK)
        await self.workspace_repo.delete_item(workspace_id)
        logger.info(
            "Удалён workspace %s пользователем %s",
            workspace_id,
            user_id,
        )
        return True

    async def _generate_unique_slug(self, name: str, max_attempts: int = 10) -> str:
        """
        Сгенерировать уникальный slug из name.

        Преобразует name в lowercase-hyphenated формат.
        При коллизиях добавляет числовой суффикс.

        Args:
            name: Название workspace
            max_attempts: Максимальное количество попыток

        Returns:
            str: Уникальный slug

        Raises:
            WorkspaceSlugExistsError: Если не удалось сгенерировать уникальный slug

        Example:
            >>> slug = await self._generate_unique_slug("Marketing Team")
            >>> slug
            'marketing-team'
        """
        # Базовый slug: lowercase, только буквы/цифры/дефисы
        base_slug = re.sub(r"[^\w\s-]", "", name.lower())
        base_slug = re.sub(r"[\s_]+", "-", base_slug).strip("-")

        # Проверка уникальности
        slug = base_slug
        for attempt in range(max_attempts):
            if not await self.workspace_repo.slug_exists(slug):
                return slug

            # Добавление числового суффикса
            slug = f"{base_slug}-{attempt + 1}"

        logger.error(
            "Не удалось сгенерировать уникальный slug для '%s' за %d попыток",
            name,
            max_attempts,
        )
        raise WorkspaceSlugExistsError(slug=base_slug)

    async def _check_access(
        self,
        workspace: WorkspaceModel,
        user_id: UUID,
    ) -> None:
        """
        Проверить права доступа пользователя к workspace.

        Доступ разрешён если:
        - Workspace PUBLIC
        - Пользователь является участником

        Args:
            workspace: Workspace для проверки
            user_id: UUID пользователя

        Raises:
            WorkspaceAccessDeniedError: Если нет прав доступа

        Example:
            >>> await self._check_access(workspace, user_id)
        """
        from src.models.v1.workspaces import WorkspaceVisibility

        # PUBLIC workspace доступен всем
        if workspace.visibility == WorkspaceVisibility.PUBLIC:
            return

        # Проверка членства
        is_member = await self.member_repo.is_member(workspace.id, user_id)
        if not is_member:
            logger.warning(
                "Пользователь %s не имеет доступа к workspace %s",
                user_id,
                workspace.id,
            )
            raise WorkspaceAccessDeniedError(
                workspace_id=workspace.id,
                user_id=user_id,
            )

    async def _check_admin_permission(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Проверить административные права пользователя.

        Пользователь должен быть OWNER или ADMIN.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя

        Raises:
            WorkspacePermissionDeniedError: Если нет прав

        Example:
            >>> await self._check_admin_permission(workspace_id, user_id)
        """
        role = await self.member_repo.get_user_role(workspace_id, user_id)
        if role not in [WorkspaceMemberRole.OWNER, WorkspaceMemberRole.ADMIN]:
            logger.warning(
                "Пользователь %s не имеет административных прав в workspace %s (роль: %s)",
                user_id,
                workspace_id,
                role,
            )
            raise WorkspacePermissionDeniedError(
                workspace_id=workspace_id,
                user_id=user_id,
                required_role="owner/admin",
            )
