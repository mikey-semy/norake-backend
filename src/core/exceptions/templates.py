"""
Исключения для работы с шаблонами (Templates).

Содержит специфичные исключения для валидации, прав доступа и бизнес-логики
работы с шаблонами проблем.

Classes:
    TemplateNotFoundError: Шаблон не найден.
    TemplatePermissionDeniedError: Нет прав для операции с шаблоном.
    TemplateValidationError: Ошибка валидации данных шаблона.
    TemplateInactiveError: Попытка использовать неактивный шаблон.
"""

from uuid import UUID

from src.core.exceptions.base import BaseAPIException


class TemplateNotFoundError(BaseAPIException):
    """
    Исключение при отсутствии шаблона с указанным ID.

    Attributes:
        template_id: UUID шаблона, который не найден.
        message: Сообщение об ошибке.
        status_code: HTTP статус 404 (Not Found).
        error_type: Тип ошибки для клиента.
    """

    def __init__(self, template_id: UUID):
        """
        Args:
            template_id: UUID шаблона, который не найден.
        """
        self.template_id = template_id
        super().__init__(
            detail=f"Шаблон с ID {template_id} не найден",
            status_code=404,
            error_type="TEMPLATE_NOT_FOUND",
            extra={"template_id": str(template_id)},
        )


class TemplatePermissionDeniedError(BaseAPIException):
    """
    Исключение при попытке операции без необходимых прав.

    Только владелец (author) и admin могут редактировать/удалять шаблон.

    Attributes:
        template_id: UUID шаблона.
        user_id: UUID пользователя, пытающегося выполнить действие.
        action: Название действия (update, delete, deactivate).
        message: Сообщение об ошибке.
        status_code: HTTP статус 403 (Forbidden).
        error_type: Тип ошибки для клиента.
    """

    def __init__(self, template_id: UUID, user_id: UUID, action: str):
        """
        Args:
            template_id: UUID шаблона.
            user_id: UUID пользователя.
            action: Название действия.
        """
        self.template_id = template_id
        self.user_id = user_id
        self.action = action
        super().__init__(
            detail=f"Недостаточно прав для действия '{action}' с шаблоном {template_id}",
            status_code=403,
            error_type="TEMPLATE_PERMISSION_DENIED",
            extra={
                "template_id": str(template_id),
                "user_id": str(user_id),
                "action": action,
            },
        )


class TemplateValidationError(BaseAPIException):
    """
    Исключение при невалидных данных шаблона.

    Используется для валидации полей: title, category, fields (JSONB).

    Attributes:
        field: Название поля с ошибкой.
        reason: Причина ошибки валидации.
        message: Сообщение об ошибке.
        status_code: HTTP статус 400 (Bad Request).
        error_type: Тип ошибки для клиента.
    """

    def __init__(self, field: str, reason: str):
        """
        Args:
            field: Название поля с ошибкой.
            reason: Причина ошибки валидации.
        """
        self.field = field
        self.reason = reason
        super().__init__(
            detail=f"Ошибка валидации поля '{field}': {reason}",
            status_code=400,
            error_type="TEMPLATE_VALIDATION_ERROR",
            extra={"field": field, "reason": reason},
        )


class TemplateInactiveError(BaseAPIException):
    """
    Исключение при попытке использовать неактивный (деактивированный) шаблон.

    Деактивированные шаблоны (is_active=False) нельзя использовать для создания проблем.

    Attributes:
        template_id: UUID неактивного шаблона.
        message: Сообщение об ошибке.
        status_code: HTTP статус 400 (Bad Request).
        error_type: Тип ошибки для клиента.
    """

    def __init__(self, template_id: UUID):
        """
        Args:
            template_id: UUID неактивного шаблона.
        """
        self.template_id = template_id
        super().__init__(
            detail=f"Шаблон {template_id} деактивирован и не может быть использован",
            status_code=400,
            error_type="TEMPLATE_INACTIVE",
            extra={"template_id": str(template_id)},
        )
