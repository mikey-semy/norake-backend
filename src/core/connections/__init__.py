"""
Модуль подключений.

Предоставляет клиенты и контекстные менеджеры для различных внешних сервисов:
- S3Client, S3ContextManager: Работа с S3/MinIO хранилищем
"""

from .storage import S3Client, S3ContextManager

__all__ = [
    "S3Client",
    "S3ContextManager",
]
