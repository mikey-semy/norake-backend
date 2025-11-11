"""
Исключения для работы с проблемами (Issues).

Содержит доменные исключения, специфичные для бизнес-логики Issues.
"""

from uuid import UUID

from src.core.exceptions.base import BaseAPIException


class IssueNotFoundError(BaseAPIException):
    """
    Исключение: проблема не найдена.

    Выбрасывается когда запрошенная проблема не существует в БД.
    """

    def __init__(self, issue_id: UUID):
        """
        Инициализирует исключение с UUID проблемы.

        Args:
            issue_id: UUID проблемы, которая не была найдена.
        """
        super().__init__(
            status_code=404,
            detail=f"Проблема с ID {issue_id} не найдена",
            error_type="IssueNotFound",
            extra={"issue_id": str(issue_id)},
        )


class IssueAlreadyResolvedError(BaseAPIException):
    """
    Исключение: проблема уже решена.

    Выбрасывается при попытке повторно решить уже решённую проблему.
    """

    def __init__(self, issue_id: UUID):
        """
        Инициализирует исключение с UUID проблемы.

        Args:
            issue_id: UUID проблемы, которая уже решена.
        """
        super().__init__(
            status_code=400,
            detail=f"Проблема с ID {issue_id} уже решена",
            error_type="IssueAlreadyResolved",
            extra={"issue_id": str(issue_id), "status": "green"},
        )


class IssuePermissionDeniedError(BaseAPIException):
    """
    Исключение: недостаточно прав для операции.

    Выбрасывается когда пользователь пытается выполнить операцию,
    для которой у него нет прав (например, решить чужую проблему).
    """

    def __init__(self, issue_id: UUID, user_id: UUID, action: str):
        """
        Инициализирует исключение с деталями.

        Args:
            issue_id: UUID проблемы.
            user_id: UUID пользователя, пытающегося выполнить действие.
            action: Название действия (например, "resolve").
        """
        super().__init__(
            status_code=403,
            detail=f"Недостаточно прав для выполнения действия '{action}' с проблемой {issue_id}",
            error_type="IssuePermissionDenied",
            extra={
                "issue_id": str(issue_id),
                "user_id": str(user_id),
                "action": action,
            },
        )


class IssueValidationError(BaseAPIException):
    """
    Исключение: ошибка валидации данных проблемы.

    Выбрасывается при попытке создать/обновить проблему с невалидными данными.
    """

    def __init__(self, field: str, message: str):
        """
        Инициализирует исключение с деталями ошибки валидации.

        Args:
            field: Название поля с ошибкой.
            message: Сообщение об ошибке.
        """
        super().__init__(
            status_code=422,
            detail=f"Ошибка валидации поля '{field}': {message}",
            error_type="IssueValidation",
            extra={"field": field, "validation_error": message},
        )
