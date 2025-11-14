"""
Модуль интеграции с хранилищами (S3/MinIO).

Предоставляет классы для работы с файловым хранилищем:
- AbstractStorageBackend: Абстрактный интерфейс storage backend
- BaseS3Storage: Базовая реализация для S3-совместимых хранилищ
- DocumentS3Storage: Специализированный storage для документов с превью и QR-кодами
"""

from .base import AbstractStorageBackend, BaseS3Storage
from .documents import DocumentS3Storage

__all__ = [
    "AbstractStorageBackend",
    "BaseS3Storage",
    "DocumentS3Storage",
]
