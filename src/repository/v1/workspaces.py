"""
Repository для работы с Workspace и WorkspaceMember.

Модуль предоставляет репозитории для работы с workspace и их участниками:
- WorkspaceRepository: CRUD операции для workspace
- WorkspaceMemberRepository: Управление участниками workspace

Используется BaseRepository для стандартных CRUD операций.
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from src.models.v1.workspaces import (
    WorkspaceMemberModel,
    WorkspaceMemberRole,
    WorkspaceModel,
    WorkspaceVisibility,
)
from src.repository.base import BaseRepository


class WorkspaceRepository(BaseRepository[WorkspaceModel]):
    """
    Репозиторий для работы с Workspace.

    Предоставляет методы для CRUD операций с workspace,
    включая фильтрацию по владельцу, видимости, slug.

    Attributes:
        model_class: WorkspaceModel - класс модели для операций

    Methods:
        get_by_slug: Получить workspace по slug
        get_user_workspaces: Получить все workspace пользователя (owned + member)
        get_public_workspaces: Получить список публичных workspace
        slug_exists: Проверить существование slug

    Example:
        >>> repo = WorkspaceRepository(session)
        >>> workspace = await repo.get_by_slug("marketing-team")
        >>> user_workspaces = await repo.get_user_workspaces(user_id)
    """

    model_class = WorkspaceModel

    async def get_by_slug(self, slug: str) -> Optional[WorkspaceModel]:
        """
        Получить workspace по slug.

        Args:
            slug: URL-friendly идентификатор workspace

        Returns:
            Optional[WorkspaceModel]: Workspace если найден, иначе None

        Example:
            >>> workspace = await repo.get_by_slug("marketing-team")
            >>> workspace.slug
            'marketing-team'
        """
        return await self.get_item_by_field("slug", slug)

    async def get_user_workspaces(
        self,
        user_id: UUID,
        include_member: bool = True,
    ) -> List[WorkspaceModel]:
        """
        Получить все workspace пользователя.

        Возвращает workspace где пользователь:
        - Владелец (owner_id == user_id)
        - Участник (если include_member=True)

        Args:
            user_id: UUID пользователя
            include_member: Включать ли workspace где пользователь участник

        Returns:
            List[WorkspaceModel]: Список workspace пользователя

        Example:
            >>> # Все workspace (owned + member)
            >>> workspaces = await repo.get_user_workspaces(user_id)
            >>>
            >>> # Только owned workspace
            >>> owned = await repo.get_user_workspaces(user_id, include_member=False)
        """
        if not include_member:
            # Только owned workspace
            return await self.filter_by(owner_id=user_id)

        # Owned + member workspace
        query = (
            select(WorkspaceModel)
            .outerjoin(WorkspaceModel.members)
            .where(
                (WorkspaceModel.owner_id == user_id)
                | (WorkspaceMemberModel.user_id == user_id)
            )
            .options(
                selectinload(WorkspaceModel.owner),
                selectinload(WorkspaceModel.members),
            )
            .distinct()
        )

        return await self.execute_and_return_scalars(query)

    async def get_public_workspaces(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WorkspaceModel]:
        """
        Получить список публичных workspace.

        Args:
            limit: Максимальное количество записей
            offset: Смещение для пагинации

        Returns:
            List[WorkspaceModel]: Список публичных workspace

        Example:
            >>> workspaces = await repo.get_public_workspaces(limit=20)
            >>> all(w.visibility == WorkspaceVisibility.PUBLIC for w in workspaces)
            True
        """
        query = (
            select(WorkspaceModel)
            .where(WorkspaceModel.visibility == WorkspaceVisibility.PUBLIC)
            .options(selectinload(WorkspaceModel.owner))
            .limit(limit)
            .offset(offset)
        )

        return await self.execute_and_return_scalars(query)

    async def slug_exists(self, slug: str) -> bool:
        """
        Проверить существование slug.

        Args:
            slug: URL-friendly идентификатор

        Returns:
            bool: True если slug занят, False если свободен

        Example:
            >>> exists = await repo.slug_exists("marketing-team")
            >>> if exists:
            ...     print("Slug уже занят")
        """
        return await self.exists_by_field("slug", slug)


class WorkspaceMemberRepository(BaseRepository[WorkspaceMemberModel]):
    """
    Репозиторий для работы с участниками Workspace.

    Предоставляет методы для управления участниками workspace:
    добавление, удаление, изменение ролей, проверка членства.

    Attributes:
        model_class: WorkspaceMemberModel - класс модели для операций

    Methods:
        get_workspace_members: Получить всех участников workspace
        get_member: Получить запись участника
        get_user_role: Получить роль пользователя в workspace
        is_member: Проверить членство пользователя
        has_role: Проверить роль пользователя
        remove_member: Удалить участника из workspace

    Example:
        >>> repo = WorkspaceMemberRepository(session)
        >>> members = await repo.get_workspace_members(workspace_id)
        >>> role = await repo.get_user_role(workspace_id, user_id)
    """

    model_class = WorkspaceMemberModel

    async def get_workspace_members(
        self,
        workspace_id: UUID,
    ) -> List[WorkspaceMemberModel]:
        """
        Получить всех участников workspace.

        Args:
            workspace_id: UUID workspace

        Returns:
            List[WorkspaceMemberModel]: Список участников с eager loading user

        Example:
            >>> members = await repo.get_workspace_members(workspace_id)
            >>> for member in members:
            ...     print(member.user.username, member.role)
        """
        query = (
            select(WorkspaceMemberModel)
            .where(WorkspaceMemberModel.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMemberModel.user))
        )

        return await self.execute_and_return_scalars(query)

    async def get_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Optional[WorkspaceMemberModel]:
        """
        Получить запись участника workspace.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя

        Returns:
            Optional[WorkspaceMemberModel]: Запись участника если найдена

        Example:
            >>> member = await repo.get_member(workspace_id, user_id)
            >>> if member:
            ...     print(f"Роль: {member.role.value}")
        """
        query = select(WorkspaceMemberModel).where(
            and_(
                WorkspaceMemberModel.workspace_id == workspace_id,
                WorkspaceMemberModel.user_id == user_id,
            )
        )

        return await self.execute_and_return_scalar(query)

    async def get_user_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Optional[WorkspaceMemberRole]:
        """
        Получить роль пользователя в workspace.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя

        Returns:
            Optional[WorkspaceMemberRole]: Роль пользователя или None

        Example:
            >>> role = await repo.get_user_role(workspace_id, user_id)
            >>> if role == WorkspaceMemberRole.ADMIN:
            ...     print("Пользователь - администратор")
        """
        member = await self.get_member(workspace_id, user_id)
        return member.role if member else None

    async def is_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Проверить членство пользователя в workspace.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя

        Returns:
            bool: True если пользователь участник

        Example:
            >>> if await repo.is_member(workspace_id, user_id):
            ...     print("Пользователь имеет доступ")
        """
        member = await self.get_member(workspace_id, user_id)
        return member is not None

    async def has_role(
        self,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceMemberRole,
    ) -> bool:
        """
        Проверить роль пользователя в workspace.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя
            role: Роль для проверки

        Returns:
            bool: True если пользователь имеет указанную роль

        Example:
            >>> is_owner = await repo.has_role(
            ...     workspace_id, user_id, WorkspaceMemberRole.OWNER
            ... )
        """
        user_role = await self.get_user_role(workspace_id, user_id)
        return user_role == role

    async def remove_member(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Удалить участника из workspace.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя

        Returns:
            bool: True если участник удалён, False если не найден

        Example:
            >>> removed = await repo.remove_member(workspace_id, user_id)
            >>> if removed:
            ...     print("Участник удалён из workspace")
        """
        member = await self.get_member(workspace_id, user_id)
        if not member:
            return False

        await self.delete_item(member.id)
        return True
