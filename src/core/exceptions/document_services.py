"""
Исключения для работы с сервисами документов (Document Services Exceptions).

Определяет кастомные исключения для валидации, доступа и операций
с document services.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from .base import BaseAPIException


class DocumentServiceNotFoundError(BaseAPIException):
    """Сервис документа не найден."""

    def __init__(
        self,
        service_id: UUID,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            service_id: UUID сервиса документа.
            extra: Дополнительная информация.
        """
        detail = f"Сервис документа {service_id} не найден"
        super().__init__(
            status_code=404,
            detail=detail,
            error_type="DOCUMENT_SERVICE_NOT_FOUND",
            extra={"service_id": str(service_id), **(extra or {})},
        )


class DocumentServicePermissionDeniedError(BaseAPIException):
    """Нет прав на действие с сервисом документа."""

    def __init__(
        self,
        service_id: UUID,
        user_id: UUID,
        action: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            service_id: UUID сервиса документа.
            user_id: UUID пользователя.
            action: Действие (view, update, delete, add_function и т.д.).
            extra: Дополнительная информация.
        """
        detail = f"Нет прав на действие '{action}' для сервиса {service_id}"
        super().__init__(
            status_code=403,
            detail=detail,
            error_type="DOCUMENT_SERVICE_PERMISSION_DENIED",
            extra={
                "service_id": str(service_id),
                "user_id": str(user_id),
                "action": action,
                **(extra or {}),
            },
        )


class DocumentServiceValidationError(BaseAPIException):
    """Ошибка валидации данных сервиса документа."""

    def __init__(
        self,
        detail: str,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            detail: Описание ошибки валидации.
            extra: Дополнительная информация.
        """
        super().__init__(
            status_code=400,
            detail=detail,
            error_type="DOCUMENT_SERVICE_VALIDATION_ERROR",
            extra=extra or {},
        )


class DocumentUploadError(BaseAPIException):
    """Ошибка загрузки файла документа в S3."""

    def __init__(
        self,
        detail: str = "Не удалось загрузить файл в хранилище",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            detail: Описание ошибки загрузки.
            extra: Дополнительная информация (filename, size и т.д.).
        """
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="DOCUMENT_UPLOAD_ERROR",
            extra=extra or {},
        )


class ThumbnailGenerationError(BaseAPIException):
    """Ошибка генерации thumbnail для PDF."""

    def __init__(
        self,
        detail: str = "Не удалось создать превью для PDF",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            detail: Описание ошибки генерации.
            extra: Дополнительная информация.
        """
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="THUMBNAIL_GENERATION_ERROR",
            extra=extra or {},
        )


class QRCodeGenerationError(BaseAPIException):
    """Ошибка генерации QR-кода."""

    def __init__(
        self,
        detail: str = "Не удалось сгенерировать QR-код",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            detail: Описание ошибки генерации.
            extra: Дополнительная информация.
        """
        super().__init__(
            status_code=500,
            detail=detail,
            error_type="QR_CODE_GENERATION_ERROR",
            extra=extra or {},
        )


class FunctionNotAvailableError(BaseAPIException):
    """Функция не доступна для данного сервиса."""

    def __init__(
        self,
        function_name: str,
        service_id: UUID,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            function_name: Имя функции (view_pdf, ai_chat и т.д.).
            service_id: UUID сервиса документа.
            extra: Дополнительная информация.
        """
        detail = f"Функция '{function_name}' не доступна для сервиса {service_id}"
        super().__init__(
            status_code=400,
            detail=detail,
            error_type="FUNCTION_NOT_AVAILABLE",
            extra={
                "function_name": function_name,
                "service_id": str(service_id),
                **(extra or {}),
            },
        )


class DocumentAccessDeniedError(BaseAPIException):
    """Доступ к документу запрещён."""

    def __init__(
        self,
        service_id: UUID,
        reason: str = "Доступ к приватному сервису документа запрещён",
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            service_id: UUID сервиса документа.
            reason: Причина отказа в доступе.
            extra: Дополнительная информация.
        """
        super().__init__(
            status_code=403,
            detail=reason,
            error_type="DOCUMENT_ACCESS_DENIED",
            extra={"service_id": str(service_id), **(extra or {})},
        )


class FileTypeValidationError(BaseAPIException):
    """Недопустимый тип файла."""

    def __init__(
        self,
        content_type: str,
        expected_types: list[str],
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            content_type: MIME тип загружаемого файла.
            expected_types: Список разрешённых MIME типов.
            extra: Дополнительная информация.
        """
        detail = (
            f"Недопустимый тип файла '{content_type}'. "
            f"Разрешённые типы: {', '.join(expected_types)}"
        )
        super().__init__(
            status_code=400,
            detail=detail,
            error_type="FILE_TYPE_VALIDATION_ERROR",
            extra={
                "content_type": content_type,
                "expected_types": expected_types,
                **(extra or {}),
            },
        )


class FileSizeExceededError(BaseAPIException):
    """Превышен максимальный размер файла."""

    def __init__(
        self,
        file_size: int,
        max_size: int,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            file_size: Размер загружаемого файла (в байтах).
            max_size: Максимально допустимый размер (в байтах).
            extra: Дополнительная информация.
        """
        detail = (
            f"Размер файла ({file_size // (1024 * 1024)} MB) "
            f"превышает максимально допустимый ({max_size // (1024 * 1024)} MB)"
        )
        super().__init__(
            status_code=400,
            detail=detail,
            error_type="FILE_SIZE_EXCEEDED",
            extra={
                "file_size": file_size,
                "max_size": max_size,
                **(extra or {}),
            },
        )
