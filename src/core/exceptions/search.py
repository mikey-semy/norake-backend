"""
Исключения для работы с поиском (Search).

Содержит domain-specific исключения для SearchService.
"""

from src.core.exceptions.base import BaseAPIException


class SearchError(BaseAPIException):
    """
    Базовое исключение для ошибок поиска.

    Attributes:
        query: Поисковый запрос, вызвавший ошибку
        details: Дополнительная информация об ошибке
    """

    def __init__(
        self,
        query: str,
        details: str = "Ошибка выполнения поиска",
    ):
        """
        Инициализация SearchError.

        Args:
            query: Поисковый запрос
            details: Детальное описание ошибки
        """
        message = f"Ошибка поиска для запроса '{query}': {details}"
        super().__init__(
            status_code=500,
            detail=message,
            error_type="search_error",
        )
        self.query = query
        self.details = details


class SearchTimeoutError(SearchError):
    """
    Исключение при превышении времени ожидания поиска.

    Attributes:
        query: Поисковый запрос
        timeout_seconds: Время ожидания в секундах
    """

    def __init__(self, query: str, timeout_seconds: float):
        """
        Инициализация SearchTimeoutError.

        Args:
            query: Поисковый запрос
            timeout_seconds: Превышенное время ожидания
        """
        details = f"Превышено время ожидания ({timeout_seconds}s)"
        super().__init__(query=query, details=details)
        self.timeout_seconds = timeout_seconds
