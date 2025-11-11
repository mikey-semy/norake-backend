"""
Исключения для работы с Knowledge Bases.

Этот модуль содержит кастомные исключения для операций с базами знаний (KB).
"""

from uuid import UUID

from .base import BaseAPIException


class KnowledgeBaseNotFoundError(BaseAPIException):
    """
    Исключение: Knowledge Base не найдена.

    Args:
        kb_id: UUID не найденной knowledge base

    Raises:
        HTTP 404 Not Found
    """

    def __init__(self, kb_id: UUID, **kwargs):
        """
        Инициализация исключения.

        Args:
            kb_id: UUID knowledge base
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        self.kb_id = kb_id
        detail = f"Knowledge Base с ID {kb_id} не найдена"
        super().__init__(
            detail=detail,
            status_code=404,
            error_type="knowledge_base_not_found",
            **kwargs,
        )


class DocumentNotFoundError(BaseAPIException):
    """
    Исключение: Документ не найден.

    Args:
        document_id: UUID не найденного документа

    Raises:
        HTTP 404 Not Found
    """

    def __init__(self, document_id: UUID, **kwargs):
        """
        Инициализация исключения.

        Args:
            document_id: UUID документа
            **kwargs: Дополнительные параметры для BaseAPIException
        """
        self.document_id = document_id
        detail = f"Документ с ID {document_id} не найден"
        super().__init__(
            detail=detail,
            status_code=404,
            error_type="document_not_found",
            **kwargs,
        )
