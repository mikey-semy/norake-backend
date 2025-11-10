"""
Исключения для OpenRouter интеграции.

Содержит исключения для работы с OpenRouter API.
"""

from typing import Any, Dict, Optional

from starlette.status import (
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from src.core.exceptions.base import BaseAPIException


class OpenRouterError(BaseAPIException):
    """
    Базовое исключение для ошибок OpenRouter API.

    Используется для всех ошибок связанных с OpenRouter:
    - Сетевые ошибки
    - Ошибки API (401, 429, 500)
    - Таймауты
    - Невалидные ответы

    Attributes:
        status_code (int): HTTP_503_SERVICE_UNAVAILABLE.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "openrouter_error".
    """

    def __init__(
        self,
        detail: str = "Ошибка при обращении к OpenRouter API",
        extra: Optional[Dict[Any, Any]] = None,
    ):
        """
        Инициализация исключения OpenRouterError.

        Args:
            detail (str): Сообщение об ошибке.
            extra (Dict, optional): Дополнительные данные (status_code, response).

        Example:
            >>> raise OpenRouterError("API вернул ошибку 429")
            >>> raise OpenRouterError(
            ...     "Сетевая ошибка",
            ...     extra={"endpoint": "/embeddings"}
            ... )
        """
        super().__init__(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_type="openrouter_error",
            extra=extra,
        )


class OpenRouterConfigError(BaseAPIException):
    """
    Исключение для ошибок конфигурации OpenRouter.

    Возникает когда не установлен API ключ или другие обязательные параметры.

    Attributes:
        status_code (int): HTTP_500_INTERNAL_SERVER_ERROR.
        detail (str): Подробное сообщение об ошибке.
        error_type (str): Тип ошибки "openrouter_config_error".
    """

    def __init__(
        self,
        detail: str = "Ошибка конфигурации OpenRouter",
        extra: Optional[Dict[Any, Any]] = None,
    ):
        """
        Инициализация исключения OpenRouterConfigError.

        Args:
            detail (str): Сообщение об ошибке.
            extra (Dict, optional): Дополнительные данные.

        Example:
            >>> raise OpenRouterConfigError("OPENROUTER_API_KEY не установлен")
        """
        super().__init__(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_type="openrouter_config_error",
            extra=extra,
        )
