"""
Базовый модуль для работы с S3-хранилищем.

Предоставляет абстрактный класс AbstractStorageBackend и базовую реализацию BaseS3Storage
для работы с S3-совместимыми хранилищами (AWS S3, MinIO).
"""

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, Optional

from botocore.exceptions import ClientError
from fastapi import UploadFile

from src.core.settings import settings


class AbstractStorageBackend(ABC):
    """
    Абстрактный интерфейс для работы с хранилищем файлов.

    Определяет контракт для реализаций storage backend'ов.
    """

    @abstractmethod
    async def upload_file(
        self, file: UploadFile, file_key: str, bucket_name: Optional[str] = None
    ) -> tuple[str, str]:
        """
        Загружает файл в хранилище.

        Args:
            file: Загружаемый файл
            file_key: Ключ (путь) файла в хранилище
            bucket_name: Название бакета (опционально)

        Returns:
            tuple[str, str]: (file_url, unique_filename) - URL файла и уникальное имя
        """
        pass

    @abstractmethod
    async def delete_file(
        self, file_key: str, bucket_name: Optional[str] = None
    ) -> bool:
        """
        Удаляет файл из хранилища.

        Args:
            file_key: Ключ (путь) файла в хранилище
            bucket_name: Название бакета (опционально)

        Returns:
            bool: True если файл был удален, False если файл не существовал
        """
        pass

    @abstractmethod
    async def file_exists(
        self, file_key: str, bucket_name: Optional[str] = None
    ) -> bool:
        """
        Проверяет существование файла в хранилище.

        Args:
            file_key: Ключ (путь) файла в хранилище
            bucket_name: Название бакета (опционально)

        Returns:
            bool: True если файл существует, False в противном случае
        """
        pass

    @abstractmethod
    async def get_file_url(
        self, file_key: str, bucket_name: Optional[str] = None
    ) -> str:
        """
        Получает публичный URL файла.

        Args:
            file_key: Ключ (путь) файла в хранилище
            bucket_name: Название бакета (опционально)

        Returns:
            str: Публичный URL файла
        """
        pass


class BaseS3Storage(AbstractStorageBackend):
    """
    Базовая реализация работы с S3-совместимым хранилищем.

    Attributes:
        _client: Клиент S3
        endpoint: URL endpoint хранилища
        bucket_name: Название бакета по умолчанию
        logger: Логгер для класса
    """

    def __init__(self, s3_client: Any):
        """
        Инициализация базового S3 хранилища.

        Args:
            s3_client: Клиент S3 для работы с хранилищем
        """
        self._client = s3_client
        self.endpoint = settings.AWS_ENDPOINT
        self.bucket_name = settings.AWS_BUCKET_NAME
        self.logger = logging.getLogger(self.__class__.__name__)

    async def bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """
        Проверяет существование бакета в S3.

        Args:
            bucket_name: Название бакета (если None, используется дефолтный)

        Returns:
            bool: True если бакет существует

        Raises:
            ValueError: При ошибке проверки бакета
        """
        if bucket_name is None:
            bucket_name = self.bucket_name
        try:
            await self._client.head_bucket(Bucket=bucket_name)
            return True
        except ClientError as error:
            if error.response["Error"]["Code"] == "404":
                return False
            error_message = f"Ошибка при проверке наличия бакета: {error}"
            self.logger.error(error_message)
            raise ValueError(error_message) from error

    async def file_exists(
        self, file_key: str, bucket_name: Optional[str] = None
    ) -> bool:
        """
        Проверяет существование файла в S3.

        Args:
            file_key: Ключ файла в S3
            bucket_name: Название бакета (если None, используется дефолтный)

        Returns:
            bool: True если файл существует

        Raises:
            ValueError: При ошибке проверки файла
        """
        if bucket_name is None:
            bucket_name = self.bucket_name
        try:
            await self._client.head_object(Bucket=bucket_name, Key=file_key)
            return True
        except ClientError as error:
            if error.response["Error"]["Code"] == "404":
                return False
            error_message = f"Ошибка при проверке наличия файла: {error}"
            self.logger.error(error_message)
            raise ValueError(error_message) from error

    async def upload_file(
        self,
        file: UploadFile,
        file_key: str = "",
        bucket_name: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Загружает файл в S3.

        Args:
            file: Загружаемый файл
            file_key: Префикс ключа файла (папка в S3)
            bucket_name: Название бакета (если None, используется дефолтный)

        Returns:
            tuple[str, str]: (file_url, unique_filename) - URL файла и уникальное имя с UUID

        Raises:
            ValueError: При ошибке загрузки файла
        """
        self.logger.info(
            "[FLOW] upload_file START: filename=%s, file_key=%s, bucket_name=%s (received)",
            file.filename,
            file_key,
            bucket_name,
        )
        
        if bucket_name is None:
            bucket_name = self.bucket_name
            self.logger.info(
                "[FLOW] upload_file: bucket_name was None, resolved to default=%s",
                bucket_name,
            )

        file_content = await file.read()
        self.logger.info(
            "[FLOW] upload_file PARAMS: name=%s, type=%s, size=%d, bucket=%s, key=%s",
            file.filename,
            file.content_type,
            len(file_content),
            bucket_name,
            file_key,
        )

        try:
            # Генерируем уникальное имя файла с UUID
            unique_filename = f"{uuid.uuid4()}_{file.filename}"
            full_file_key = (
                f"{file_key}/{unique_filename}" if file_key else unique_filename
            )
            
            self.logger.info(
                "[FLOW] upload_file: generated unique_filename=%s, full_file_key=%s",
                unique_filename,
                full_file_key,
            )

            # Загружаем файл в S3
            self.logger.info(
                "[FLOW] upload_file: calling put_object with Bucket=%s, Key=%s, ContentType=%s",
                bucket_name,
                full_file_key,
                file.content_type,
            )
            
            response = await self._client.put_object(
                Bucket=bucket_name,
                Key=full_file_key,
                Body=file_content,
                ContentType=file.content_type,
                ACL="public-read",
                CacheControl="max-age=31536000",  # Кеширование на 1 год
            )

            self.logger.info(
                "[FLOW] upload_file: put_object SUCCESS for %s as %s",
                file.filename,
                full_file_key,
            )
            self.logger.debug("[FLOW] upload_file: S3 response=%s", response)

            # Получаем URL файла
            self.logger.info(
                "[FLOW] upload_file: calling get_file_url with key=%s, bucket=%s",
                full_file_key,
                bucket_name,
            )
            file_url = await self.get_file_url(full_file_key, bucket_name)
            
            self.logger.info(
                "[FLOW] upload_file END: returning url=%s, filename=%s",
                file_url,
                unique_filename,
            )
            return file_url, unique_filename

        except ClientError as error:
            error_details = (
                error.response["Error"]
                if hasattr(error, "response")
                else "Нет деталей"
            )
            self.logger.error(
                "[FLOW] upload_file FAILED (ClientError): file=%s, error=%s\nДетали: %s\nBucket=%s, Key=%s",
                file.filename,
                error,
                error_details,
                bucket_name,
                full_file_key,
            )
            raise ValueError(f"Ошибка при загрузке файла: {error}") from error
        except Exception as error:
            self.logger.error(
                "Неожиданная ошибка при загрузке файла %s: %s", file.filename, error
            )
            raise RuntimeError(f"Ошибка при загрузке файла: {error}") from error

    async def get_file_url(
        self, file_key: str, bucket_name: Optional[str] = None
    ) -> str:
        """
        Получает публичный URL файла в S3.

        Args:
            file_key: Ключ файла в S3
            bucket_name: Название бакета (если None, используется дефолтный)

        Returns:
            str: Публичный URL файла

        Raises:
            ValueError: При ошибке получения URL
        """
        if bucket_name is None:
            bucket_name = self.bucket_name
        try:
            if not await self.file_exists(file_key, bucket_name):
                self.logger.warning(
                    "Запрошена ссылка на несуществующий файл: %s", file_key
                )
            return f"{self.endpoint}/{bucket_name}/{file_key}"
        except ClientError as error:
            error_message = f"Ошибка при получении ссылки на файл: {error}"
            self.logger.error(error_message)
            raise ValueError(error_message) from error
        except Exception as error:
            error_message = f"Ошибка при получении ссылки на файл: {error}"
            self.logger.error(error_message)
            raise RuntimeError(error_message) from error

    async def delete_file(
        self, file_key: str, bucket_name: Optional[str] = None
    ) -> bool:
        """
        Удаляет файл из S3.

        Args:
            file_key: Ключ файла в S3
            bucket_name: Название бакета (если None, используется дефолтный)

        Returns:
            bool: True если файл был удален, False если файл не существовал

        Raises:
            ValueError: При критической ошибке удаления файла
        """
        if bucket_name is None:
            bucket_name = self.bucket_name
        try:
            # Проверяем существование файла перед удалением
            file_exists = await self.file_exists(file_key, bucket_name)
            if not file_exists:
                self.logger.warning(
                    "Файл %s не найден в S3, но продолжаем операцию", file_key
                )
                return False  # Файл не был удален, т.к. его не было

            # Удаляем файл
            response = await self._client.delete_object(
                Bucket=bucket_name, Key=file_key
            )

            # Проверяем результат удаления
            http_status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if http_status == 204:  # 204 No Content - успешное удаление
                self.logger.info("Файл %s успешно удален из S3", file_key)
                return True
            elif http_status == 200:  # 200 OK - тоже может быть успешным
                # Дополнительно проверяем, что файл действительно удален
                still_exists = await self.file_exists(file_key, bucket_name)
                if not still_exists:
                    self.logger.info(
                        "Файл %s успешно удален из S3 (проверено)", file_key
                    )
                    return True
                else:
                    self.logger.error(
                        "Файл %s остался в S3 после удаления", file_key
                    )
                    return False
            else:
                self.logger.warning("Неожиданный статус удаления: %s", http_status)
                return False

        except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "NoSuchKey":
                self.logger.warning("Файл %s уже отсутствует в S3", file_key)
                return False  # Файл уже отсутствует
            else:
                error_message = f"Ошибка при удалении файла из бакета: {error}"
                self.logger.error(error_message)
                raise ValueError(error_message) from error
        except Exception as error:
            error_message = f"Ошибка при удалении файла из бакета: {error}"
            self.logger.error(error_message)
            raise RuntimeError(error_message) from error
