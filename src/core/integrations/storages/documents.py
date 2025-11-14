"""
Модуль для работы с документами в S3-хранилище.

Предоставляет класс DocumentS3Storage для управления загрузкой, обработкой и хранением
документов (PDF, DOCX, и т.д.) с возможностью генерации превью и QR-кодов.
"""

import io
import logging
from typing import Any, Optional

import qrcode
from fastapi import UploadFile

try:
    from pdf2image import convert_from_bytes
    from PIL import Image

    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

from src.core.integrations.storages.base import BaseS3Storage


class DocumentS3Storage(BaseS3Storage):
    """
    Storage для работы с документами (PDF, DOCX и т.д.) в S3.

    Расширяет BaseS3Storage дополнительными методами для:
    - Генерации thumbnails из PDF
    - Создания QR-кодов для быстрого доступа
    - Управления метаданными документов

    Attributes:
        documents_folder (str): Папка для хранения документов в S3
        thumbnails_folder (str): Папка для хранения превью
        qrcodes_folder (str): Папка для хранения QR-кодов
        logger (logging.Logger): Логгер для класса
    """

    def __init__(self, s3_client: Any):
        """
        Инициализация документного storage.

        Args:
            s3_client: Клиент S3 для работы с хранилищем
        """
        super().__init__(s3_client)
        self.documents_folder = "documents"
        self.thumbnails_folder = "thumbnails"
        self.qrcodes_folder = "qrcodes"
        self.logger = logging.getLogger(self.__class__.__name__)

    async def upload_document(
        self,
        file: UploadFile,
        workspace_id: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> tuple[str, str, int, bytes]:
        """
        Загружает документ в S3 с организацией по workspace.

        Args:
            file: Загружаемый файл документа
            workspace_id: ID workspace (для организации файлов)
            bucket_name: Название бакета (опционально)

        Returns:
            tuple[str, str, int, bytes]: (file_url, unique_filename, file_size, file_content) -
                                         URL файла, уникальное имя, размер в байтах и содержимое
        """
        self.logger.info(
            "📼 [FLOW] upload_document START: filename=%s, workspace_id=%s, bucket_name=%s",
            file.filename,
            workspace_id,
            bucket_name,
        )

        # КРИТИЧНО: Читаем файл ДО загрузки, чтобы получить размер и контент
        file_content = await file.read()
        file_size = len(file_content)

        self.logger.debug(
            "📦 Прочитан файл: size=%d bytes",
            file_size,
        )

        # Возвращаем указатель в начало для upload_file
        await file.seek(0)

        # Определяем путь в зависимости от workspace
        if workspace_id:
            file_key = f"{self.documents_folder}/{workspace_id}"
        else:
            file_key = f"{self.documents_folder}/public"

        self.logger.debug(
            "📁 [FLOW] upload_document: generated file_key=%s",
            file_key,
        )

        # Загружаем документ
        self.logger.debug(
            "☁️  [FLOW] upload_document: calling upload_file with file_key=%s, bucket_name=%s",
            file_key,
            bucket_name,
        )

        file_url, unique_filename = await self.upload_file(
            file=file, file_key=file_key, bucket_name=bucket_name
        )

        self.logger.info(
            "✨ Документ загружен: url=%s, name=%s, size=%d bytes",
            file_url,
            unique_filename,
            file_size,
        )

        return file_url, unique_filename, file_size, file_content

    async def generate_pdf_thumbnail(
        self,
        file_content: bytes,
        filename: str,
        workspace_id: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Генерирует thumbnail (превью) из первой страницы PDF и загружает в S3.

        Args:
            file_content: Содержимое PDF файла в байтах
            filename: Имя исходного PDF файла
            workspace_id: ID workspace (для организации)
            bucket_name: Название бакета (опционально)

        Returns:
            Optional[str]: URL thumbnail изображения или None при ошибке

        Raises:
            RuntimeError: Если библиотека pdf2image не установлена
        """
        if not PDF_SUPPORT:
            self.logger.warning(
                "pdf2image/Pillow не установлены - генерация thumbnails недоступна"
            )
            return None

        try:
            self.logger.debug("Генерация thumbnail для PDF: %s", filename)

            # Конвертируем первую страницу PDF в изображение
            images = convert_from_bytes(
                file_content, first_page=1, last_page=1, dpi=150
            )
            if not images:
                self.logger.warning("Не удалось извлечь страницы из PDF")
                return None

            first_page = images[0]

            # Изменяем размер до 400x566 (примерно A4 пропорции)
            thumbnail_size = (400, 566)
            first_page.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

            # Конвертируем в JPEG для меньшего размера
            thumbnail_io = io.BytesIO()
            first_page.save(thumbnail_io, format="JPEG", quality=85, optimize=True)
            thumbnail_bytes = thumbnail_io.getvalue()

            # Загружаем thumbnail в S3
            thumbnail_filename = f"{filename}_thumbnail.jpg"
            if workspace_id:
                thumbnail_key = f"{self.thumbnails_folder}/{workspace_id}/{thumbnail_filename}"
            else:
                thumbnail_key = f"{self.thumbnails_folder}/public/{thumbnail_filename}"

            # Создаем UploadFile-подобный объект для thumbnail
            class ThumbnailFile:
                def __init__(self, content: bytes, name: str):
                    self.content = content
                    self.filename = name
                    self.content_type = "image/jpeg"

                async def read(self) -> bytes:
                    return self.content

            thumbnail_file = ThumbnailFile(thumbnail_bytes, thumbnail_filename)

            # Загружаем используя базовый метод
            if bucket_name is None:
                bucket_name = self.bucket_name

            response = await self._client.put_object(
                Bucket=bucket_name,
                Key=thumbnail_key,
                Body=thumbnail_bytes,
                ContentType="image/jpeg",
                CacheControl="max-age=31536000",
            )

            thumbnail_url = await self.get_file_url(thumbnail_key, bucket_name)

            self.logger.info(
                "Thumbnail создан: %s (размер: %d bytes)",
                thumbnail_url,
                len(thumbnail_bytes),
            )

            return thumbnail_url

        except Exception as e:
            self.logger.error("Ошибка генерации thumbnail для %s: %s", filename, e)
            return None

    async def generate_qr_code(
        self,
        data: str,
        filename: str,
        workspace_id: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> str:
        """
        Генерирует QR-код и загружает в S3.

        Args:
            data: Данные для QR-кода (обычно URL документа)
            filename: Имя файла QR-кода
            workspace_id: ID workspace (для организации)
            bucket_name: Название бакета (опционально)

        Returns:
            str: URL QR-кода изображения

        Raises:
            RuntimeError: При ошибке генерации или загрузки QR-кода
        """
        try:
            self.logger.debug("Генерация QR-кода для: %s", data)

            # Создаем QR-код
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            # Генерируем изображение
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Конвертируем в байты
            qr_io = io.BytesIO()
            qr_image.save(qr_io, format="PNG")
            qr_bytes = qr_io.getvalue()

            # Загружаем QR-код в S3
            qr_filename = f"{filename}_qr.png"
            if workspace_id:
                qr_key = f"{self.qrcodes_folder}/{workspace_id}/{qr_filename}"
            else:
                qr_key = f"{self.qrcodes_folder}/public/{qr_filename}"

            if bucket_name is None:
                bucket_name = self.bucket_name

            response = await self._client.put_object(
                Bucket=bucket_name,
                Key=qr_key,
                Body=qr_bytes,
                ContentType="image/png",
                CacheControl="max-age=31536000",
            )

            qr_url = await self.get_file_url(qr_key, bucket_name)

            self.logger.info(
                "QR-код создан: %s (размер: %d bytes)", qr_url, len(qr_bytes)
            )

            return qr_url

        except Exception as e:
            self.logger.error("Ошибка генерации QR-кода для %s: %s", filename, e)
            raise RuntimeError(f"Не удалось создать QR-код: {e}") from e

    async def delete_document_files(
        self,
        document_key: str,
        thumbnail_key: Optional[str] = None,
        qr_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> dict[str, bool]:
        """
        Удаляет документ и связанные файлы (thumbnail, QR-код).

        Args:
            document_key: Ключ основного документа
            thumbnail_key: Ключ thumbnail (опционально)
            qr_key: Ключ QR-кода (опционально)
            bucket_name: Название бакета (опционально)

        Returns:
            dict[str, bool]: Статус удаления для каждого файла
                             {"document": True, "thumbnail": False, "qr": True}
        """
        results = {}

        # Удаляем основной документ
        results["document"] = await self.delete_file(document_key, bucket_name)

        # Удаляем thumbnail если указан
        if thumbnail_key:
            results["thumbnail"] = await self.delete_file(thumbnail_key, bucket_name)

        # Удаляем QR-код если указан
        if qr_key:
            results["qr"] = await self.delete_file(qr_key, bucket_name)

        self.logger.info("Удаление документа и связанных файлов: %s", results)

        return results
