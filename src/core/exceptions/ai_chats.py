"""
Исключения для AI Chat системы.

Модуль содержит кастомные исключения для работы с AI чатами:
- ChatNotFoundError: Чат не найден
- InvalidModelKeyError: Неизвестный ключ модели
- OpenRouterAPIError: Ошибка OpenRouter API
- DocumentProcessingError: Ошибка обработки документа для RAG
"""

from src.core.exceptions.base import BaseAPIException


class ChatNotFoundError(BaseAPIException):
    """
    Исключение для случая, когда чат не найден.

    Example:
        >>> raise ChatNotFoundError(
        ...     detail="Чат chat-abc123 не найден",
        ...     extra={"chat_id": "chat-abc123"}
        ... )
    """

    def __init__(self, detail: str, extra: dict | None = None):
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="CHAT_NOT_FOUND",
            extra=extra,
        )


class InvalidModelKeyError(BaseAPIException):
    """
    Исключение для случая, когда указан неизвестный ключ модели.

    Example:
        >>> raise InvalidModelKeyError(
        ...     detail="Неизвестный ключ модели: unknown_model",
        ...     extra={"model_key": "unknown_model"}
        ... )
    """

    def __init__(self, detail: str, extra: dict | None = None):
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="INVALID_MODEL_KEY",
            extra=extra,
        )


class OpenRouterAPIError(BaseAPIException):
    """
    Исключение для ошибок OpenRouter API.

    Example:
        >>> raise OpenRouterAPIError(
        ...     detail="Ошибка запроса к OpenRouter",
        ...     extra={"model": "qwen/qwq-32b-preview", "error": "timeout"}
        ... )
    """

    def __init__(self, detail: str, extra: dict | None = None):
        super().__init__(
            status_code=503,
            detail=detail,
            error_code="OPENROUTER_API_ERROR",
            extra=extra,
        )


class DocumentProcessingError(BaseAPIException):
    """
    Исключение для ошибок обработки документа для RAG.

    Example:
        >>> raise DocumentProcessingError(
        ...     detail="Не удалось извлечь текст из файла",
        ...     extra={"s3_key": "documents/file.pdf"}
        ... )
    """

    def __init__(self, detail: str, extra: dict | None = None):
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="DOCUMENT_PROCESSING_ERROR",
            extra=extra,
        )
