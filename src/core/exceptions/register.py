"""
Исключения для процесса регистрации пользователей.

Все исключения наследуются от BaseAPIException и автоматически
конвертируются в HTTP responses через global exception handler.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from starlette.status import (
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from src.core.exceptions.base import BaseAPIException


class UserAlreadyExistsError(BaseAPIException):
    """
    Исключение когда пользователь с таким email/username уже существует.

    HTTP Status: 409 Conflict
    """

    def __init__(
        self,
        field: str,
        value: str,
        detail: Optional[str] = None,
        extra: Optional[Dict[Any, Any]] = None,
    ):
        """
        Args:
            field: Поле, по которому найден дубликат (email, username).
            value: Значение поля.
            detail: Дополнительное описание ошибки.
            extra: Дополнительные данные для клиента.
        """
        if extra is None:
            extra = {}

        extra["field"] = field
        extra["value"] = value

        if not detail:
            detail = f"Пользователь с {field}='{value}' уже зарегистрирован"

        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail,
            error_type="user_already_exists",
            extra=extra,
        )

class UserCreationError(BaseAPIException):
    """
    Исключение при ошибке создания пользователя.

    HTTP Status: 500 Internal Server Error
    """

    def __init__(
        self,
        reason: Optional[str] = None,
        detail: Optional[str] = None,
        extra: Optional[Dict[Any, Any]] = None,
    ):
        """
        Args:
            reason: Причина ошибки.
            detail: Описание ошибки.
            extra: Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if reason:
            extra["reason"] = reason

        if not detail:
            detail = "Не удалось создать пользователя"

        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_type="user_creation_error",
            extra=extra,
        )

class RoleAssignmentError(BaseAPIException):
    """
    Исключение при ошибке присвоения роли пользователю.

    HTTP Status: 500 Internal Server Error
    """

    def __init__(
        self,
        user_id: Optional[UUID] = None,
        role_code: Optional[str] = None,
        detail: Optional[str] = None,
        extra: Optional[Dict[Any, Any]] = None,
    ):
        """
        Args:
            user_id: ID пользователя.
            role_code: Код роли (user, admin).
            detail: Описание ошибки.
            extra: Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if user_id:
            extra["user_id"] = str(user_id)

        if role_code:
            extra["role_code"] = role_code

        if not detail:
            detail = f"Не удалось присвоить роль '{role_code}' пользователю"

        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_type="role_assignment_error",
            extra=extra,
        )
