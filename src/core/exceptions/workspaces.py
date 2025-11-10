"""
Исключения для работы с Workspace.

Модуль содержит domain-специфичные исключения для операций с workspace
и их участниками.
"""

from uuid import UUID

from fastapi import status

from src.core.exceptions.base import BaseAPIException


class WorkspaceNotFoundError(BaseAPIException):
    """
    Исключение при отсутствии workspace.

    Используется когда workspace не найден по ID или slug.

    Attributes:
        workspace_id: UUID workspace (если искали по ID)
        slug: Slug workspace (если искали по slug)

    Example:
        >>> raise WorkspaceNotFoundError(workspace_id=uuid)
        >>> raise WorkspaceNotFoundError(slug="marketing-team")
    """

    def __init__(
        self,
        workspace_id: UUID | None = None,
        slug: str | None = None,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            workspace_id: UUID workspace
            slug: Slug workspace
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        if workspace_id:
            message = f"Workspace с ID {workspace_id} не найден"
        elif slug:
            message = f"Workspace с slug '{slug}' не найден"
        else:
            message = "Workspace не найден"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            **kwargs,
        )


class WorkspaceAccessDeniedError(BaseAPIException):
    """
    Исключение при отсутствии доступа к workspace.

    Используется когда пользователь не имеет доступа к workspace
    (не является участником).

    Attributes:
        workspace_id: UUID workspace
        user_id: UUID пользователя

    Example:
        >>> raise WorkspaceAccessDeniedError(
        ...     workspace_id=workspace_id,
        ...     user_id=user_id
        ... )
    """

    def __init__(
        self,
        workspace_id: UUID,
        user_id: UUID,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        message = f"Нет доступа к workspace {workspace_id} для пользователя {user_id}"

        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs,
        )


class WorkspacePermissionDeniedError(BaseAPIException):
    """
    Исключение при недостаточных правах в workspace.

    Используется когда пользователь не имеет прав для операции
    (например, только OWNER/ADMIN может добавлять участников).

    Attributes:
        workspace_id: UUID workspace
        user_id: UUID пользователя
        required_role: Требуемая роль

    Example:
        >>> raise WorkspacePermissionDeniedError(
        ...     workspace_id=workspace_id,
        ...     user_id=user_id,
        ...     required_role="admin"
        ... )
    """

    def __init__(
        self,
        workspace_id: UUID,
        user_id: UUID,
        required_role: str,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя
            required_role: Требуемая роль для операции
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        message = (
            f"Недостаточно прав для операции в workspace {workspace_id}. "
            f"Требуется роль: {required_role}"
        )

        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs,
        )


class WorkspaceSlugExistsError(BaseAPIException):
    """
    Исключение при попытке создать workspace с занятым slug.

    Используется когда slug уже занят другим workspace.

    Attributes:
        slug: Занятый slug

    Example:
        >>> raise WorkspaceSlugExistsError(slug="marketing-team")
    """

    def __init__(
        self,
        slug: str,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            slug: Занятый slug
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        message = f"Workspace с slug '{slug}' уже существует"

        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            **kwargs,
        )


class WorkspaceMemberExistsError(BaseAPIException):
    """
    Исключение при попытке добавить уже существующего участника.

    Используется когда пользователь уже является участником workspace.

    Attributes:
        workspace_id: UUID workspace
        user_id: UUID пользователя

    Example:
        >>> raise WorkspaceMemberExistsError(
        ...     workspace_id=workspace_id,
        ...     user_id=user_id
        ... )
    """

    def __init__(
        self,
        workspace_id: UUID,
        user_id: UUID,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        message = (
            f"Пользователь {user_id} уже является "
            f"участником workspace {workspace_id}"
        )

        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            **kwargs,
        )


class WorkspaceOwnerConflictError(BaseAPIException):
    """
    Исключение при попытке добавить второго OWNER.

    Используется когда пытаются добавить участника с ролью OWNER,
    но у workspace уже есть владелец.

    Attributes:
        workspace_id: UUID workspace

    Example:
        >>> raise WorkspaceOwnerConflictError(workspace_id=workspace_id)
    """

    def __init__(
        self,
        workspace_id: UUID,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            workspace_id: UUID workspace
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        message = f"Workspace {workspace_id} уже имеет владельца (OWNER). Может быть только один OWNER."

        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            **kwargs,
        )


class WorkspaceMemberNotFoundError(BaseAPIException):
    """
    Исключение при отсутствии участника workspace.

    Используется когда участник не найден в workspace.

    Attributes:
        workspace_id: UUID workspace
        user_id: UUID пользователя

    Example:
        >>> raise WorkspaceMemberNotFoundError(
        ...     workspace_id=workspace_id,
        ...     user_id=user_id
        ... )
    """

    def __init__(
        self,
        workspace_id: UUID,
        user_id: UUID,
        **kwargs,
    ):
        """
        Инициализация исключения.

        Args:
            workspace_id: UUID workspace
            user_id: UUID пользователя
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        message = f"Участник {user_id} не найден в workspace {workspace_id}"

        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            **kwargs,
        )
