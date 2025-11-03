from typing import Any, Dict, Optional

from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from src.core.exceptions.base import BaseAPIException


class ServiceUnavailableError(BaseAPIException):
    """
    Исключение для случая, когда все сервисы (например, БД и Redis) недоступны.
    """

    def __init__(
        self,
        message: str = "Все сервисы недоступны",
        extra: Optional[Dict[Any, Any]] = None,
    ):
        super().__init__(
            status_code=HTTP_503_SERVICE_UNAVAILABLE,
            detail=message,
            error_type="service_unavailable",
            extra=extra,
        )
