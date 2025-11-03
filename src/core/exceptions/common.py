"""
Общие исключения для API.

Содержит базовые исключения, которые могут использоваться в различных частях приложения.
"""

from typing import Any, Dict, Optional

from starlette.status import (HTTP_400_BAD_REQUEST, HTTP_403_FORBIDDEN,
                              HTTP_404_NOT_FOUND, HTTP_409_CONFLICT)

from src.core.exceptions.base import BaseAPIException


class NotFoundError(BaseAPIException):
    """
    Исключение для случая, когда запрашиваемый ресурс не найден.

    Attributes:
        status_code (int): HTTP_404_NOT_FOUND.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "not_found".
    """

    def __init__(
        self,
        detail: str = "Ресурс не найден",
        field: Optional[str] = None,
        value: Optional[Any] = None,
        extra: Optional[Dict[Any, Any]] = None,
    ):
        """
        Инициализация исключения NotFoundError.

        Args:
            detail (str): Сообщение об ошибке.
            field (str, optional): Название поля, по которому искали.
            value (Any, optional): Значение, которое не было найдено.
            extra (Dict, optional): Дополнительные данные.
        """
        if extra is None:
            extra = {}

        if field and value:
            extra.update({"field": field, "value": value})

        super().__init__(
            status_code=HTTP_404_NOT_FOUND,
            detail=detail,
            error_type="not_found",
            extra=extra,
        )


class BadRequestError(BaseAPIException):
    """
    Исключение для некорректных запросов.

    Attributes:
        status_code (int): HTTP_400_BAD_REQUEST.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "bad_request".
    """

    def __init__(
        self,
        detail: str = "Некорректный запрос",
        extra: Optional[Dict[Any, Any]] = None,
    ):
        super().__init__(
            status_code=HTTP_400_BAD_REQUEST,
            detail=detail,
            error_type="bad_request",
            extra=extra,
        )


class ConflictError(BaseAPIException):
    """
    Исключение для конфликтов данных (например, дублирование уникальных полей).

    Attributes:
        status_code (int): HTTP_409_CONFLICT.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "conflict".
    """

    def __init__(
        self,
        detail: str = "Конфликт данных",
        extra: Optional[Dict[Any, Any]] = None,
    ):
        super().__init__(
            status_code=HTTP_409_CONFLICT,
            detail=detail,
            error_type="conflict",
            extra=extra,
        )


class ForbiddenError(BaseAPIException):
    """
    Исключение для случая, когда доступ запрещен.

    Attributes:
        status_code (int): HTTP_403_FORBIDDEN.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "forbidden".
    """

    def __init__(
        self,
        detail: str = "Доступ запрещен",
        extra: Optional[Dict[Any, Any]] = None,
    ):
        super().__init__(
            status_code=HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="forbidden",
            extra=extra,
        )
