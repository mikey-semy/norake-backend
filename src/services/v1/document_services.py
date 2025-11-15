"""
Сервис для управления сервисами документов (Document Service).

Содержит бизнес-логику для работы с document services: загрузка файлов в S3,
генерация обложек и QR-кодов, управление функциями документа, контроль доступа.

Classes:
    DocumentServiceService: Сервис с методами create, get, update, delete, upload.
"""

import asyncio
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import UploadFile
from langdetect import detect, LangDetectException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    DocumentAccessDeniedError,
    DocumentFileNotFoundError,
    DocumentServiceNotFoundError,
    DocumentServicePermissionDeniedError,
    DocumentServiceValidationError,
    FileSizeExceededError,
    FileTypeValidationError,
    QRCodeGenerationError,
)
from src.core.integrations.processors import PDFProcessor
from src.core.integrations.storages.documents import DocumentS3Storage
from src.core.settings.base import Settings
from src.models.v1 import ExtractionMethod, ProcessingStatus
from src.models.v1.document_services import (
    CoverType,
    DocumentFileType,
    DocumentServiceModel,
)
from src.repository.v1.document_chunks import DocumentChunkRepository
from src.repository.v1.document_processing import (
    DocumentProcessingRepository,
)
from src.repository.v1.document_services import DocumentServiceRepository
from src.schemas.v1.document_services import (
    DocumentServiceCreateRequestSchema,
    DocumentServiceQueryRequestSchema,
    DocumentServiceUpdateRequestSchema,
    ServiceFunctionSchema,
)

logger = logging.getLogger(__name__)


class DocumentServiceService:
    """
    Сервис для управления сервисами документов.

    Предоставляет методы для загрузки файлов, создания сервисов, управления
    функциями документов, генерации обложек и QR-кодов.

    Attributes:
        repository: Репозиторий для работы с базой данных.
        storage: S3 хранилище для файлов документов.

    Methods:
        create_document_service: Создать сервис с загрузкой файла в S3.
        get_document_service: Получить сервис по ID с инкрементом просмотров.
        update_document_service: Обновить метаданные сервиса.
        delete_document_service: Удалить сервис и файлы из S3.
        list_document_services: Получить список сервисов с фильтрацией.
        add_function: Добавить функцию к сервису.
        remove_function: Удалить функцию из сервиса.
        generate_qr: Генерировать QR-код для документа.
        get_most_viewed: Получить самые просматриваемые сервисы.
    """

    def __init__(
        self,
        session: AsyncSession,
        s3_client: Any,
        settings: Settings,
        embeddings: Any,
        workspace_service: Any = None,
    ):
        """
        Инициализирует сервис документов.

        Args:
            session: Асинхронная сессия SQLAlchemy.
            s3_client: S3 клиент для работы с хранилищем.
            settings: Настройки приложения.
            embeddings: OpenRouterEmbeddings клиент для RAG.
            workspace_service: Сервис для проверки доступа workspace (опционально).
        """
        self.repository = DocumentServiceRepository(session)
        self.processing_repository = DocumentProcessingRepository(session)
        self.storage = DocumentS3Storage(s3_client)
        self.pdf_processor = PDFProcessor()
        self.settings = settings
        self.embeddings = embeddings
        self.workspace_service = workspace_service
        self.logger = logging.getLogger(__name__)

    async def create_document_service(
        self,
        file: UploadFile,
        metadata: DocumentServiceCreateRequestSchema,
        author_id: UUID,
    ) -> DocumentServiceModel:
        """
        Создать новый сервис документа с загрузкой файла.

        Загружает файл в S3, генерирует thumbnail для PDF, создаёт QR-код,
        сохраняет метаданные в БД.

        Args:
            file: Загружаемый файл (FastAPI UploadFile).
            metadata: Метаданные документа (title, description, tags и т.д.).
            author_id: UUID пользователя-создателя.

        Returns:
            Созданный DocumentServiceModel.

        Raises:
            ValidationError: При невалидном файле или метаданных.

        Example:
            >>> service = await service.create_document_service(
            ...     file=upload_file,
            ...     metadata=create_request,
            ...     author_id=user_id
            ... )
        """
        # Валидация размера файла
        content = await file.read()
        file_size = len(content)  # Сохраняем размер сразу после чтения

        if file_size > self.settings.DOCUMENT_MAX_FILE_SIZE:
            raise FileSizeExceededError(
                file_size=file_size,
                max_size=self.settings.DOCUMENT_MAX_FILE_SIZE,
            )

        # Валидация MIME типа
        self._validate_file_type(file.content_type, metadata.file_type)

        # Загрузка файла в S3
        await file.seek(0)  # Вернуть указатель в начало
        file_url, _, file_size_from_storage, file_content_from_storage = await self.storage.upload_document(
            file=file,
            workspace_id=str(metadata.workspace_id) if metadata.workspace_id else None,
        )

        # Используем размер из storage (более надёжно)
        file_size = file_size_from_storage

        # Генерация thumbnail для PDF
        cover_url = None
        cover_type = metadata.cover_type or "icon"
        if metadata.file_type == "pdf" and cover_type == "generated":
            try:
                cover_url = await self.storage.generate_pdf_thumbnail(
                    file_content=file_content_from_storage,
                    filename=file.filename or "document",
                    workspace_id=str(metadata.workspace_id) if metadata.workspace_id else None,
                )
            except (OSError, RuntimeError) as e:
                # Thumbnail необязателен, логируем warning
                self.logger.warning("Не удалось создать thumbnail для PDF: %s", e)

        # Подготовка данных для создания
        create_data = {
            "title": metadata.title,
            "description": metadata.description,
            "tags": metadata.tags or [],
            "file_url": file_url,
            "file_size": file_size,
            "file_type": metadata.file_type,  # Уже lowercase строка из валидатора
            "cover_type": cover_type,  # Уже lowercase строка из валидатора
            "cover_url": cover_url,
            "cover_icon": metadata.cover_icon,
            "available_functions": [func.model_dump() for func in metadata.available_functions],
            "author_id": author_id,
            "workspace_id": metadata.workspace_id,
            "is_public": metadata.is_public,
            "view_count": 0,
        }

        # Создание записи в БД
        document_service = await self.repository.create_item(create_data)

        # Перезагрузить с relationships для сериализации
        await self.repository.session.refresh(
            document_service,
            attribute_names=["author", "workspace"]
        )

        self.logger.info(
            "✅ Создан document service %s для пользователя %s (file_size=%d bytes)",
            document_service.id,
            author_id,
            file_size,
        )

        # Создать запись обработки и запустить обработку для PDF
        if metadata.file_type == "pdf":
            await self.processing_repository.create_processing_record(
                document_service_id=document_service.id,
                status=ProcessingStatus.PENDING,
            )
            self.logger.info(
                "📝 Создана запись обработки для PDF документа %s",
                document_service.id,
            )

            # Запустить фоновую обработку PDF
            asyncio.create_task(
                self._process_pdf_background(
                    document_service.id,
                    file_content_from_storage,
                )
            )
            self.logger.info(
                "🚀 Запущена фоновая обработка PDF документа %s",
                document_service.id,
            )

        return document_service

    async def get_document_service(
        self,
        service_id: UUID,
        user_id: Optional[UUID] = None,
        increment_views: bool = True,
    ) -> DocumentServiceModel:
        """
        Получить сервис документа по ID.

        Проверяет права доступа (публичные доступны всем, приватные только автору).
        Опционально инкрементирует счётчик просмотров.

        Args:
            service_id: UUID сервиса документа.
            user_id: UUID текущего пользователя (для проверки прав).
            increment_views: Увеличивать ли счётчик просмотров (по умолчанию True).

        Returns:
            DocumentServiceModel.

        Raises:
            NotFoundError: Если сервис не найден.
            PermissionDeniedError: Если нет прав на просмотр приватного сервиса.

        Example:
            >>> service = await service.get_document_service(service_id, user_id)
        """
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        # Загрузить relationships для сериализации
        await self.repository.session.refresh(
            service,
            attribute_names=["author", "workspace"]
        )

        # Проверка прав на просмотр приватных сервисов
        if not service.is_public:
            # Проверка 1: Автор имеет доступ
            if user_id and service.author_id == user_id:
                pass  # Автор имеет полный доступ
            # Проверка 2: Член workspace имеет доступ
            elif service.workspace_id and user_id and self.workspace_service:
                is_member = await self.workspace_service.member_repo.is_member(
                    workspace_id=service.workspace_id,
                    user_id=user_id,
                )
                if not is_member:
                    self.logger.warning(
                        "Попытка доступа к приватному документу %s пользователем %s без членства в workspace",
                        service_id,
                        user_id,
                    )
                    raise DocumentAccessDeniedError(service_id=service_id)
            else:
                # Нет user_id или не автор и не член workspace
                raise DocumentAccessDeniedError(service_id=service_id)

        # Инкремент счётчика просмотров
        if increment_views:
            await self.repository.increment_view_count(service_id)
            await self.repository.session.refresh(service)
            # Перезагрузить relationships после refresh
            await self.repository.session.refresh(
                service,
                attribute_names=["author", "workspace"]
            )

        return service

    async def update_document_service(
        self,
        service_id: UUID,
        update_data: DocumentServiceUpdateRequestSchema,
        user_id: UUID,
    ) -> DocumentServiceModel:
        """
        Обновить метаданные сервиса документа.

        Только владелец (author) может редактировать сервис.
        Не затрагивает файл в S3 (только метаданные).

        Args:
            service_id: UUID сервиса документа.
            update_data: Данные для обновления.
            user_id: UUID текущего пользователя.

        Returns:
            Обновлённый DocumentServiceModel.

        Raises:
            NotFoundError: Если сервис не найден.
            PermissionDeniedError: Если пользователь не владелец.

        Example:
            >>> service = await service.update_document_service(
            ...     service_id, update_request, user_id
            ... )
        """
        # Получить существующий сервис
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        # Проверка прав (только владелец)
        self._check_permission(service, user_id, "update")

        # Подготовка данных для обновления
        update_dict = update_data.model_dump(exclude_unset=True)

        # Конвертация available_functions в JSONB формат
        if "available_functions" in update_dict:
            update_dict["available_functions"] = [
                func.model_dump() for func in update_data.available_functions
            ]

        # Обновление через репозиторий
        updated_service = await self.repository.update_item(service_id, update_dict)

        # Перезагрузить relationships для сериализации
        await self.repository.session.refresh(
            updated_service,
            attribute_names=["author", "workspace"]
        )

        self.logger.info(
            "Обновлён document service %s пользователем %s",
            service_id,
            user_id,
        )
        return updated_service

    async def delete_document_service(
        self,
        service_id: UUID,
        user_id: UUID,
    ) -> bool:
        """
        Удалить сервис документа.

        Удаляет файлы из S3 (document, thumbnail, QR) и запись из БД.
        Только владелец может удалить сервис.

        Args:
            service_id: UUID сервиса документа.
            user_id: UUID текущего пользователя.

        Returns:
            True при успешном удалении.

        Raises:
            NotFoundError: Если сервис не найден.
            PermissionDeniedError: Если пользователь не владелец.

        Example:
            >>> deleted = await service.delete_document_service(service_id, user_id)
        """
        # Получить существующий сервис
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        # Проверка прав (только владелец)
        self._check_permission(service, user_id, "delete")

        # Удаление файлов из S3 (если storage доступен)
        if self.storage:
            try:
                # Извлекаем S3 ключи из URL
                # URL формат: https://storage.yandexcloud.net/bucket/documents/public/uuid_file.pdf
                # Нужен ключ: documents/public/uuid_file.pdf
                if service.file_url:
                    # Получаем путь после bucket_name
                    url_path = service.file_url.split(f"{self.storage.bucket_name}/")[-1]
                    document_key = url_path
                else:
                    document_key = ""

                thumbnail_key = None
                if service.cover_url:
                    url_path = service.cover_url.split(f"{self.storage.bucket_name}/")[-1]
                    thumbnail_key = url_path

                await self.storage.delete_document_files(
                    document_key=document_key,
                    thumbnail_key=thumbnail_key,
                )
            except (OSError, RuntimeError) as e:
                # Ошибка S3 - логируем warning, но продолжаем
                self.logger.warning("Не удалось удалить файлы из S3: %s", e)
        else:
            self.logger.warning("S3 storage недоступен - файлы не удалены")

        # Удаление записи из БД
        deleted = await self.repository.delete_item(service_id)

        self.logger.info(
            "Удалён document service %s пользователем %s",
            service_id,
            user_id,
        )
        return deleted

    async def list_document_services(
        self,
        query: DocumentServiceQueryRequestSchema,
        user_id: Optional[UUID] = None,
    ) -> tuple[List[DocumentServiceModel], int]:
        """
        Получить список сервисов с фильтрацией.

        Поддерживает поиск по тексту, тегам, типу файла, автору, workspace,
        публичности. Возвращает список и общее количество для пагинации.

        Args:
            query: Параметры запроса (search, tags, filters, pagination).
            user_id: UUID текущего пользователя (для доступа к приватным).

        Returns:
            Кортеж (список DocumentServiceModel, общее количество).

        Example:
            >>> services, total = await service.list_document_services(query, user_id)
        """
        services: List[DocumentServiceModel] = []

        # Поиск по тексту
        if query.search:
            services = await self.repository.search_by_text(
                search_text=query.search,
                limit=query.limit,
                offset=query.offset,
            )

        # Поиск по тегам
        elif query.tags:
            services = await self.repository.get_by_tags(
                tags=query.tags,
                match_all=False,  # OR логика
                limit=query.limit,
                offset=query.offset,
            )

        # Фильтр по автору
        elif query.author_id:
            # Если запрашивают свои сервисы - показываем все
            include_public = (user_id != query.author_id)
            services = await self.repository.get_by_author(
                author_id=query.author_id,
                include_public=include_public,
                limit=query.limit,
                offset=query.offset,
            )

        # Фильтр по workspace
        elif query.workspace_id:
            services = await self.repository.get_by_workspace(
                workspace_id=query.workspace_id,
                limit=query.limit,
                offset=query.offset,
            )

        # Фильтр по типу файла
        elif query.file_type:
            services = await self.repository.get_by_file_type(
                file_type=query.file_type,
                is_public=query.is_public,
                limit=query.limit,
                offset=query.offset,
            )

        # Публичные сервисы (по умолчанию)
        else:
            services = await self.repository.get_public_services(
                file_type=query.file_type,
                limit=query.limit,
                offset=query.offset,
            )

        # Подсчёт общего количества (для пагинации)
        total = await self._count_services(query)

        # Загрузить relationships для всех сервисов
        for service in services:
            await self.repository.session.refresh(
                service,
                attribute_names=["author", "workspace"]
            )

        self.logger.info(
            "Получено %d сервисов (всего: %d) по запросу",
            len(services),
            total,
        )
        return services, total

    async def add_function(
        self,
        service_id: UUID,
        function: ServiceFunctionSchema,
        user_id: UUID,
    ) -> DocumentServiceModel:
        """
        Добавить функцию к сервису документа.

        Только владелец может добавлять функции.
        Проверяет уникальность имени функции.

        Args:
            service_id: UUID сервиса документа.
            function: Данные функции для добавления.
            user_id: UUID текущего пользователя.

        Returns:
            Обновлённый DocumentServiceModel.

        Raises:
            NotFoundError: Если сервис не найден.
            PermissionDeniedError: Если пользователь не владелец.
            ValidationError: Если функция уже существует.

        Example:
            >>> service = await service.add_function(
            ...     service_id,
            ...     ServiceFunctionSchema(name="ai_chat", enabled=True, ...),
            ...     user_id
            ... )
        """
        # Получить существующий сервис
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        # Проверка прав (только владелец)
        self._check_permission(service, user_id, "add_function")

        # Проверка существования функции
        if service.has_function(function.name):
            raise DocumentServiceValidationError(
                detail=f"Функция '{function.name}' уже существует в сервисе"
            )

        # Добавление функции в JSONB
        current_functions = service.available_functions or []
        current_functions.append(function.model_dump())

        # Обновление через репозиторий
        updated_service = await self.repository.update_item(
            service_id,
            {"available_functions": current_functions},
        )

        # Перезагрузить relationships для сериализации
        await self.repository.session.refresh(
            updated_service,
            attribute_names=["author", "workspace"]
        )

        self.logger.info(
            "Добавлена функция '%s' к сервису %s пользователем %s",
            function.name,
            service_id,
            user_id,
        )

        # 🔥 АВТОМАТИЧЕСКАЯ RAG ОБРАБОТКА при активации view_pdf
        if function.name == "view_pdf" and function.enabled:
            self.logger.info(
                "Активирована функция view_pdf для %s, запуск RAG обработки...",
                service_id,
            )
            try:
                # Проверить существующую обработку
                processing = await self.processing_repository.get_by_document_id(service_id)

                if not processing:
                    # Создать запись о начале обработки
                    processing = await self.processing_repository.create_processing_record(
                        document_service_id=service_id,
                        status=ProcessingStatus.PENDING,
                    )
                    self.logger.info(
                        "Создана запись обработки для документа %s (status=PENDING)",
                        service_id,
                    )

                # Если обработка уже завершена - не запускать заново
                if processing.status == ProcessingStatus.COMPLETED:
                    self.logger.info(
                        "Документ %s уже обработан (status=COMPLETED), пропускаем",
                        service_id,
                    )
                else:
                    # Запустить обработку асинхронно (не блокируем ответ)
                    asyncio.create_task(
                        self._process_document_for_rag(service_id, processing.id)
                    )
                    self.logger.info(
                        "Запущена фоновая RAG обработка для документа %s",
                        service_id,
                    )
            except Exception as e:
                self.logger.error(
                    "Ошибка при запуске RAG обработки для %s: %s",
                    service_id,
                    str(e),
                    exc_info=True,
                )
                # Не прерываем добавление функции, только логируем ошибку

        return updated_service

    async def remove_function(
        self,
        service_id: UUID,
        function_name: str,
        user_id: UUID,
    ) -> DocumentServiceModel:
        """
        Удалить функцию из сервиса документа.

        Только владелец может удалять функции.

        Args:
            service_id: UUID сервиса документа.
            function_name: Имя функции для удаления (например, "view_pdf").
            user_id: UUID текущего пользователя.

        Returns:
            Обновлённый DocumentServiceModel.

        Raises:
            NotFoundError: Если сервис не найден.
            PermissionDeniedError: Если пользователь не владелец.
            ValidationError: Если функция не найдена.

        Example:
            >>> service = await service.remove_function(
            ...     service_id, "ai_chat", user_id
            ... )
        """
        # Получить существующий сервис
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        # Проверка прав (только владелец)
        self._check_permission(service, user_id, "remove_function")

        # Проверка существования функции
        if not service.has_function(function_name):
            raise DocumentServiceValidationError(
                detail=f"Функция '{function_name}' не найдена в сервисе"
            )

        # Удаление функции из JSONB
        current_functions = service.available_functions or []
        updated_functions = [
            func for func in current_functions
            if func.get("name") != function_name
        ]

        # Обновление через репозиторий
        updated_service = await self.repository.update_item(
            service_id,
            {"available_functions": updated_functions},
        )

        # Перезагрузить relationships для сериализации
        await self.repository.session.refresh(
            updated_service,
            attribute_names=["author", "workspace"]
        )

        self.logger.info(
            "Удалена функция '%s' из сервиса %s пользователем %s",
            function_name,
            service_id,
            user_id,
        )
        return updated_service

    async def update_cover(
        self,
        service_id: UUID,
        user_id: UUID,
        cover_type: str,
        cover_icon: Optional[str] = None,
        cover_image: Optional[UploadFile] = None,
    ) -> DocumentServiceModel:
        """
        Обновить обложку документа.

        Поддерживает три варианта:
        1. GENERATED - регенерация thumbnail из PDF (только для PDF)
        2. ICON - установка эмодзи/иконки
        3. IMAGE - загрузка изображения обложки

        Args:
            service_id: UUID сервиса.
            user_id: UUID пользователя (проверка прав).
            cover_type: Тип обложки (generated/icon/image).
            cover_icon: Эмодзи/иконка (для ICON).
            cover_image: Файл изображения (для IMAGE).

        Returns:
            Обновлённый DocumentServiceModel.

        Raises:
            DocumentServiceNotFoundError: Сервис не найден.
            DocumentServicePermissionDeniedError: Нет прав на изменение.
            DocumentServiceValidationError: Невалидные данные.
            FileTypeValidationError: Некорректный тип изображения.
            FileSizeExceededError: Превышен размер изображения.

        Example:
            >>> # Регенерировать из PDF
            >>> service = await service.update_cover(
            ...     service_id=doc_id,
            ...     user_id=user_id,
            ...     cover_type="generated"
            ... )
            >>>
            >>> # Установить иконку
            >>> service = await service.update_cover(
            ...     service_id=doc_id,
            ...     user_id=user_id,
            ...     cover_type="icon",
            ...     cover_icon="📄"
            ... )
            >>>
            >>> # Загрузить изображение
            >>> service = await service.update_cover(
            ...     service_id=doc_id,
            ...     user_id=user_id,
            ...     cover_type="image",
            ...     cover_image=upload_file
            ... )
        """
        # Получаем сервис и проверяем права
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        if service.author_id != user_id:
            raise DocumentServicePermissionDeniedError(
                service_id=service_id, user_id=user_id, action="update_cover"
            )

        # Нормализация cover_type
        cover_type_lower = cover_type.lower()

        # Обработка разных типов обложек
        new_cover_url = None
        new_cover_icon = None

        if cover_type_lower == "generated":
            # Регенерация thumbnail из PDF
            if service.file_type != DocumentFileType.PDF:
                raise DocumentServiceValidationError(
                    detail="Автоматическая генерация обложки доступна только для PDF документов"
                )

            # Получаем PDF файл из S3
            file_content, _, _ = await self.get_document_file(
                service_id=service_id, user_id=user_id
            )

            # Генерируем новый thumbnail
            try:
                new_cover_url = await self.storage.generate_pdf_thumbnail(
                    file_content=file_content,
                    filename=service.title,
                    workspace_id=str(service.workspace_id) if service.workspace_id else None,
                )
            except (OSError, RuntimeError) as e:
                raise DocumentServiceValidationError(
                    detail=f"Не удалось сгенерировать обложку: {str(e)}"
                ) from e

            self.logger.info(
                "✅ Регенерирована обложка для сервиса %s (cover_url=%s)",
                service_id,
                new_cover_url,
            )

        elif cover_type_lower == "icon":
            # Установка иконки
            if not cover_icon:
                raise DocumentServiceValidationError(
                    detail="Для cover_type=ICON необходимо указать cover_icon"
                )
            new_cover_icon = cover_icon
            self.logger.info(
                "✅ Установлена иконка для сервиса %s (cover_icon=%s)",
                service_id,
                cover_icon,
            )

        elif cover_type_lower == "image":
            # Загрузка изображения обложки
            if not cover_image:
                raise DocumentServiceValidationError(
                    detail="Для cover_type=IMAGE необходимо загрузить изображение"
                )

            # Валидация размера
            content = await cover_image.read()
            if len(content) > 5 * 1024 * 1024:  # Макс 5MB для изображений
                raise FileSizeExceededError(
                    file_size=len(content),
                    max_size=5 * 1024 * 1024,
                )

            # Валидация MIME типа
            allowed_types = ["image/jpeg", "image/png", "image/webp"]
            if cover_image.content_type not in allowed_types:
                raise FileTypeValidationError(
                    content_type=cover_image.content_type or "unknown",
                    expected_types=allowed_types,
                )

            # Загрузка в S3
            await cover_image.seek(0)
            workspace_str = str(service.workspace_id) if service.workspace_id else None
            folder = f"covers/{workspace_str}" if workspace_str else "covers/public"

            new_cover_url, _ = await self.storage.upload_file(
                file=cover_image,
                file_key=f"{folder}/{service_id}-cover",
            )

            self.logger.info(
                "✅ Загружена обложка для сервиса %s (cover_url=%s)",
                service_id,
                new_cover_url,
            )

        else:
            raise DocumentServiceValidationError(
                detail=f"Недопустимый cover_type: {cover_type}. Используйте: generated, icon, image"
            )

        # Обновляем сервис
        update_data = {
            "cover_type": CoverType(cover_type_lower),
            "cover_url": new_cover_url,
            "cover_icon": new_cover_icon,
        }

        updated_service = await self.repository.update_item(
            item_id=service_id, data=update_data
        )

        # Перезагрузить relationships для сериализации
        await self.repository.session.refresh(
            updated_service,
            attribute_names=["author", "workspace"]
        )

        self.logger.info(
            "✅ Обновлена обложка сервиса %s (cover_type=%s)",
            service_id,
            cover_type_lower,
        )

        return updated_service

    async def generate_qr(
        self,
        service_id: UUID,
        user_id: UUID,
        base_url: str,
    ) -> str:
        """
        Сгенерировать QR-код для документа.

        QR-код содержит ссылку на просмотр документа.
        Загружает QR-изображение в S3 и возвращает URL.

        Args:
            service_id: UUID сервиса документа.
            user_id: UUID текущего пользователя.
            base_url: Базовый URL приложения (для формирования ссылки).

        Returns:
            URL QR-кода в S3.

        Raises:
            NotFoundError: Если сервис не найден.
            PermissionDeniedError: Если пользователь не владелец.
            ValidationError: Если не удалось сгенерировать QR.

        Example:
            >>> qr_url = await service.generate_qr(
            ...     service_id, user_id, "https://app.example.com"
            ... )
        """
        # Получить существующий сервис
        service = await self.repository.get_item_by_id(service_id)
        if not service:
            raise DocumentServiceNotFoundError(service_id=service_id)

        # Проверка прав (только владелец)
        self._check_permission(service, user_id, "generate_qr")

        # Формирование URL для QR-кода
        document_url = f"{base_url}/documents/{service_id}"

        # Проверка доступности S3 storage
        if not self.storage:
            self.logger.error("S3 storage недоступен - невозможно сгенерировать QR-код")
            raise ValueError(
                "S3 storage не настроен. Установите AWS_ACCESS_KEY_ID и AWS_SECRET_ACCESS_KEY"
            )

        # Генерация QR-кода
        try:
            qr_url = await self.storage.generate_qr_code(
                data=document_url,
                filename=f"qr_{service.title}",
                workspace_id=service.workspace_id,
            )
        except Exception as e:
            self.logger.error("Ошибка генерации QR-кода: %s", e)
            raise QRCodeGenerationError() from e

        self.logger.info(
            "Сгенерирован QR-код для сервиса %s пользователем %s",
            service_id,
            user_id,
        )
        return qr_url

    async def get_most_viewed(
        self,
        file_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[DocumentServiceModel]:
        """
        Получить самые просматриваемые сервисы.

        Args:
            file_type: Фильтр по типу файла (опционально, lowercase).
            limit: Количество результатов (по умолчанию 10).

        Returns:
            Список самых просматриваемых DocumentServiceModel.

        Example:
            >>> top_services = await service.get_most_viewed(file_type="pdf", limit=5)
        """
        # Нормализация file_type к lowercase и преобразование в enum
        file_type_enum = None
        if file_type:
            try:
                file_type_enum = DocumentFileType(file_type.lower())
            except ValueError:
                self.logger.warning("Некорректный file_type: %s", file_type)
                file_type_enum = None

        services = await self.repository.get_most_viewed(
            file_type=file_type_enum,
            limit=limit,
        )

        # Загрузить relationships для всех сервисов
        for service in services:
            await self.repository.session.refresh(
                service,
                attribute_names=["author", "workspace"]
            )

        return services

    def _validate_file_type(self, content_type: str, expected_type: str) -> None:
        """
        Валидировать MIME тип загружаемого файла.

        Args:
            content_type: MIME тип из UploadFile.content_type.
            expected_type: Ожидаемый тип файла (lowercase строка: "pdf", "text", и т.д.).

        Raises:
            ValidationError: Если MIME тип не соответствует ожидаемому.
        """
        allowed_types = self.settings.DOCUMENT_ALLOWED_MIME_TYPES.get(expected_type, [])
        if content_type not in allowed_types:
            raise FileTypeValidationError(
                content_type=content_type,
                expected_types=allowed_types,
            )

    def _check_permission(
        self,
        service: DocumentServiceModel,
        user_id: UUID,
        action: str,
    ) -> None:
        """
        Проверить права пользователя на действие с сервисом.

        Args:
            service: Модель сервиса документа.
            user_id: UUID текущего пользователя.
            action: Название действия (для сообщения об ошибке).

        Raises:
            PermissionDeniedError: Если пользователь не владелец.
        """
        if service.author_id != user_id:
            raise DocumentServicePermissionDeniedError(
                service_id=service.id,
                user_id=user_id,
                action=action,
            )

    async def _count_services(self, query: DocumentServiceQueryRequestSchema) -> int:
        """
        Подсчитать общее количество сервисов по запросу.

        Используется для пагинации. Учитывает ВСЕ фильтры включая tags и search.

        Args:
            query: Параметры запроса.

        Returns:
            Общее количество сервисов.
        """
        # Если есть search - используем специальный метод поиска
        if query.search:
            services = await self.repository.search_by_text(query.search)
            return len(services)

        # Если есть tags - используем специальный метод с тегами
        if query.tags:
            services = await self.repository.get_by_tags(
                tags=query.tags,
                match_all=False  # OR logic как в list_document_services
            )
            return len(services)

        # Иначе используем count_items с базовыми фильтрами
        filters: Dict[str, Any] = {}

        if query.file_type:
            filters["file_type"] = query.file_type
        if query.is_public is not None:
            filters["is_public"] = query.is_public
        if query.author_id:
            filters["author_id"] = query.author_id
        if query.workspace_id:
            filters["workspace_id"] = query.workspace_id

        count = await self.repository.count_items(**filters)
        return count

    async def get_document_file(
        self, service_id: UUID, user_id: UUID
    ) -> tuple[bytes, str, str]:
        """
        Получить файл документа для стриминга через backend.

        Проверяет права доступа и возвращает файл из S3.

        Args:
            service_id: UUID сервиса документа.
            user_id: UUID текущего пользователя.

        Returns:
            tuple[bytes, str, str]: (file_content, content_type, filename)

        Raises:
            DocumentServiceNotFoundError: Если сервис не найден.
            DocumentAccessDeniedError: Если доступ запрещён.
        """
        self.logger.info(
            "🔍 Получение файла для сервиса %s пользователем %s",
            service_id,
            user_id,
        )

        # Получаем сервис с проверкой доступа
        service = await self.get_document_service(service_id, user_id)

        # Извлекаем ключ файла из URL
        # Формат URL: https://storage.yandexcloud.net/bucket/documents/public/uuid_filename.pdf
        file_url = service.file_url
        file_key = file_url.split(f"{self.settings.AWS_BUCKET_NAME}/", 1)[-1]

        self.logger.info("📂 Получение файла из S3: key=%s", file_key)

        try:
            # Получаем файл из S3
            file_content, content_type = await self.storage.get_file_stream(file_key)

            # Извлекаем оригинальное имя файла из file_url
            filename = file_url.split("/")[-1]

            self.logger.info(
                "✅ Файл успешно получен: %s (размер: %d байт)",
                filename,
                len(file_content),
            )

            return file_content, content_type, filename

        except FileNotFoundError as exc:
            self.logger.error("❌ Файл не найден в S3: %s", file_url)
            raise DocumentFileNotFoundError(
                service_id=service_id,
                file_key=file_key,
                extra={"file_url": file_url},
            ) from exc
        except Exception as e:
            self.logger.error("❌ Ошибка получения файла из S3: %s", str(e))
            raise

    async def _process_pdf_background(
        self,
        document_service_id: UUID,
        file_content: bytes,
    ) -> None:
        """
        Фоновая обработка PDF документа.

        Извлекает текст из PDF, сохраняет результаты в DocumentProcessingModel.
        Запускается асинхронно через asyncio.create_task при создании документа.

        Args:
            document_service_id: UUID документа для обработки.
            file_content: Содержимое PDF файла в байтах.

        Note:
            Метод намеренно не пробрасывает исключения - все ошибки логируются
            и сохраняются в processing.error_message со статусом FAILED.
        """
        start_time = time.time()
        self.logger.info(
            "🔄 Начало обработки PDF документа %s",
            document_service_id,
        )

        try:
            # Обновить статус на PROCESSING
            await self.processing_repository.update_status(
                document_service_id=document_service_id,
                status=ProcessingStatus.PROCESSING,
            )

            # Извлечь текст из PDF
            extracted_text, page_count, method_str = await self.pdf_processor.extract_text(
                file_content=file_content,
                use_pymupdf=False,  # Сначала pdfplumber
            )

            # Конвертировать строку метода в enum
            extraction_method = ExtractionMethod[method_str.upper()]

            # Вычислить время обработки
            processing_time = time.time() - start_time

            # Сохранить результаты
            await self.processing_repository.save_extracted_text(
                document_service_id=document_service_id,
                extracted_text=extracted_text,
                page_count=page_count,
                extraction_method=extraction_method,
                language="ru",
                processing_time_seconds=processing_time,
            )

            self.logger.info(
                "✅ Обработка PDF документа %s завершена: %d страниц, %d символов, %.2f сек",
                document_service_id,
                page_count,
                len(extracted_text),
                processing_time,
            )

        except ValueError as e:
            # PDF не содержит текста (скан без OCR)
            error_msg = f"Документ не содержит извлекаемого текста: {str(e)}"
            self.logger.warning(
                "⚠️ Невозможно обработать PDF %s: %s",
                document_service_id,
                error_msg,
            )
            await self.processing_repository.update_status(
                document_service_id=document_service_id,
                status=ProcessingStatus.FAILED,
                error_message=error_msg,
            )

        except Exception as e:
            # Непредвиденная ошибка обработки
            error_msg = f"Ошибка при обработке PDF: {str(e)}"
            self.logger.error(
                "❌ Ошибка обработки PDF %s: %s",
                document_service_id,
                error_msg,
                exc_info=True,
            )
            await self.processing_repository.update_status(
                document_service_id=document_service_id,
                status=ProcessingStatus.FAILED,
                error_message=error_msg,
            )

    async def get_ai_functions(
        self,
        service_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> List[Dict[str, Any]]:
        """
        Получить статусы AI функций документа.

        Возвращает информацию о доступности умного поиска, RAG, чата и т.д.
        Проверяет обработку PDF и текущие настройки документа.

        Args:
            service_id: UUID сервиса документа.
            user_id: UUID текущего пользователя (для проверки прав).

        Returns:
            Список словарей с информацией о функциях:
            [
                {
                    "name": "smart_search",
                    "enabled": True/False,
                    "status": "ready" | "processing" | "inactive" | "failed",
                    "progress": 0-100 (для processing),
                    "error_message": "..." (для failed)
                }
            ]

        Raises:
            DocumentServiceNotFoundError: Если сервис не найден.
            DocumentAccessDeniedError: Если доступ запрещён.

        Example:
            >>> functions = await service.get_ai_functions(service_id, user_id)
            >>> for func in functions:
            ...     print(f"{func['name']}: {func['status']}")
        """
        # Получить документ с проверкой прав (без инкремента просмотров)
        # Используем для валидации доступа, возвращаемое значение не нужно
        _ = await self.get_document_service(  # noqa: F841
            service_id=service_id,
            user_id=user_id,
            increment_views=False,
        )

        # Получить статус обработки
        processing = await self.processing_repository.get_by_document_id(
            service_id
        )

        # Определить базовый статус для всех функций
        if not processing:
            # Документ не PDF или обработка не запущена
            base_status = "inactive"
            error_msg = "Документ не является PDF или обработка не инициирована"
        elif processing.status == ProcessingStatus.PENDING:
            base_status = "inactive"
            error_msg = "Обработка ожидает запуска"
        elif processing.status == ProcessingStatus.PROCESSING:
            base_status = "processing"
            error_msg = None
        elif processing.status == ProcessingStatus.COMPLETED:
            base_status = "ready"
            error_msg = None
        else:  # FAILED
            base_status = "failed"
            error_msg = processing.error_message or "Ошибка обработки PDF"

        # Список AI функций
        ai_functions = [
            {
                "name": "smart_search",
                "enabled": True,  # Всегда включен если есть текст
                "status": base_status,
                "progress": 100 if base_status == "processing" else None,
                "error_message": error_msg if base_status == "failed" else None,
            },
            {
                "name": "rag_search",
                "enabled": False,  # Пока не реализовано
                "status": "inactive",
                "progress": None,
                "error_message": "Функция RAG поиска не реализована",
            },
            {
                "name": "document_chat",
                "enabled": False,  # Пока не реализовано
                "status": "inactive",
                "progress": None,
                "error_message": "Функция чата с документом не реализована",
            },
            {
                "name": "summary",
                "enabled": False,  # Пока не реализовано
                "status": "inactive",
                "progress": None,
                "error_message": "Функция генерации саммари не реализована",
            },
            {
                "name": "entity_extraction",
                "enabled": False,  # Пока не реализовано
                "status": "inactive",
                "progress": None,
                "error_message": "Функция извлечения сущностей не реализована",
            },
        ]

        self.logger.info(
            "📊 Получены AI функции для документа %s: smart_search=%s",
            service_id,
            base_status,
        )

        return ai_functions

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int,
    ) -> list[str]:
        """
        Разбивает текст на чанки с перекрытием для RAG.

        Использует алгоритм скользящего окна с учетом границ предложений.
        Чанки используются для генерации embeddings и семантического поиска.

        Args:
            text: Исходный текст для разбиения
            chunk_size: Максимальный размер чанка в символах
            chunk_overlap: Размер перекрытия между чанками в символах

        Returns:
            list[str]: Список текстовых чанков (без пустых)

        Example:
            >>> chunks = self._chunk_text(
            ...     "Hello world. Foo bar.",
            ...     chunk_size=10,
            ...     chunk_overlap=5
            ... )
            >>> len(chunks) >= 1
            True

        Note:
            Адаптировано из document_kb_integration.py для переиспользования логики.
            Пытается разбивать по границам предложений (точки, переносы строк).
        """
        if not text or chunk_size <= 0:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Если не последний чанк, пытаемся найти конец предложения
            if end < len(text):
                last_period = chunk.rfind(".")
                last_newline = chunk.rfind("\n")
                boundary = max(last_period, last_newline)

                if boundary > chunk_size // 2:  # Граница не слишком далеко
                    chunk = chunk[: boundary + 1]
                    end = start + boundary + 1

            chunks.append(chunk.strip())

            # Сдвигаем окно с учетом перекрытия
            start = end - chunk_overlap if end < len(text) else end

        return [c for c in chunks if c]  # Убираем пустые чанки

    async def _process_document_for_rag(
        self,
        service_id: UUID,
        processing_id: UUID,
    ) -> None:
        """
        Фоновая обработка документа для RAG (извлечение текста + эмбеддинги).

        Выполняется асинхронно при активации функции view_pdf.
        Не блокирует основной запрос - пользователь получает ответ сразу,
        а обработка идёт в фоне.

        Workflow:
            1. Обновить статус → PROCESSING
            2. Скачать файл из S3
            3. Извлечь текст (PDFProcessor)
            4. Создать эмбеддинги (chunks)
            5. Сохранить в DocumentProcessingModel
            6. Обновить статус → COMPLETED

        Args:
            service_id: UUID документа для обработки.
            processing_id: UUID записи DocumentProcessingModel.

        Raises:
            Не бросает исключения - все ошибки логируются и сохраняются в БД.

        Example:
            >>> asyncio.create_task(
            ...     service._process_document_for_rag(doc_id, proc_id)
            ... )
        """
        start_time = time.time()

        try:
            # 0% - Начало обработки
            await self.processing_repository.update_item(
                processing_id, {"progress_percent": 0}
            )
            await self.processing_repository.update_status(
                processing_id,
                ProcessingStatus.PROCESSING,
            )
            self.logger.info(
                "Начата RAG обработка документа %s (processing_id=%s)",
                service_id,
                processing_id,
            )

            # 2. Получить документ из БД
            service = await self.repository.get_item_by_id(service_id)
            if not service:
                raise DocumentServiceNotFoundError(service_id=service_id)

            # 3. Скачать файл из S3
            file_key = service.file_url.split("/")[-1]
            self.logger.debug("Скачиваем файл из S3: %s", file_key)

            file_content, _ = await self.storage.get_file_stream(file_key)

            # 4. Извлечь текст через PDFProcessor
            self.logger.debug("Извлекаем текст из PDF...")
            pdf_processor = PDFProcessor()

            # Сохранить во временный файл для обработки
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                # 🔹 Извлекаем текст из PDF (получаем text, page_count, method из tuple)
                extracted_text, page_count, extraction_method = await pdf_processor.extract_text(tmp_path)
            finally:
                # Удалить временный файл
                os.unlink(tmp_path)

            # 25% - Текст извлечён
            await self.processing_repository.update_item(
                processing_id, {"progress_percent": 25}
            )

            # 5. Автоопределение языка
            try:
                language = (
                    detect(extracted_text[:1000]) if extracted_text else "unknown"
                )
            except LangDetectException:
                language = "unknown"
                self.logger.warning(
                    "Не удалось определить язык для документа %s, используем 'unknown'",
                    service_id,
                )

            # Сохранить извлечённый текст с определённым языком
                await self.processing_repository.save_extracted_text(
                    document_service_id=processing_id,
                    extracted_text=extracted_text,
                    page_count=page_count,
                    extraction_method=extraction_method,
                    language=language,
                )            # 6. Разбить текст на чанки
            chunks = self._chunk_text(
                text=extracted_text,
                chunk_size=self.settings.RAG_CHUNK_SIZE,
                chunk_overlap=self.settings.RAG_CHUNK_OVERLAP,
            )
            self.logger.info(
                "Документ %s разбит на %d чанков (размер=%d, overlap=%d)",
                service_id,
                len(chunks),
                self.settings.RAG_CHUNK_SIZE,
                self.settings.RAG_CHUNK_OVERLAP,
            )

            # 50% - Чанки созданы
            await self.processing_repository.update_item(
                processing_id, {"progress_percent": 50}
            )

            # 7. Генерация embeddings с батчингом (по 20 chunks за раз)
            # Это предотвращает перегрузку OpenRouter API и 503 ошибки
            batch_size = 20
            embeddings_list = []

            self.logger.debug(
                "Генерируем embeddings для %d чанков (батчами по %d)...",
                len(chunks),
                batch_size
            )

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                batch_embeddings = await self.embeddings.embed(batch)
                embeddings_list.extend(batch_embeddings)

                # Обновляем прогресс (50-75%)
                progress = 50 + int((i / len(chunks)) * 25)
                await self.processing_repository.update_item(
                    processing_id, {"progress_percent": progress}
                )

                self.logger.debug(
                    "Обработано %d/%d чанков (прогресс: %d%%)",
                    min(i + batch_size, len(chunks)),
                    len(chunks),
                    progress
                )

                # Небольшая задержка между батчами для rate limiting
                if i + batch_size < len(chunks):
                    await asyncio.sleep(0.5)

            self.logger.info(
                "Сгенерировано %d embeddings для документа %s",
                len(embeddings_list),
                service_id,
            )

            # 75% - Embeddings сгенерированы
            await self.processing_repository.update_item(
                processing_id, {"progress_percent": 75}
            )

            # 8. Сохранить чанки с embeddings в БД
            chunk_repo = DocumentChunkRepository(self.repository.session)
            chunk_data = [
                {
                    "document_id": service.id,
                    "chunk_index": idx,
                    "content": chunk,
                    "embedding": embedding,
                    "token_count": len(chunk.split()),  # Грубая оценка
                    "chunk_metadata": {
                        "chunk_size": len(chunk),
                        "chunk_overlap": self.settings.RAG_CHUNK_OVERLAP,
                        "language": language,
                        "extraction_method": ExtractionMethod.PDFPLUMBER.value,
                    },
                }
                for idx, (chunk, embedding) in enumerate(
                    zip(chunks, embeddings_list)
                )
            ]
            await chunk_repo.bulk_create(chunk_data)
            self.logger.info(
                "Сохранено %d чанков с embeddings для документа %s",
                len(chunk_data),
                service_id,
            )

            # 100% - Обработка завершена
            processing_time = time.time() - start_time
            await self.processing_repository.update_item(
                processing_id,
                {
                    "status": ProcessingStatus.COMPLETED,
                    "processing_time_seconds": int(processing_time),
                    "progress_percent": 100,
                },
            )

            self.logger.info(
                "RAG обработка документа %s завершена успешно за %.2f сек: %d страниц, %d чанков, %d embeddings",
                service_id,
                processing_time,
                page_count,
                len(chunks),
                len(embeddings_list),
            )

        except Exception as e:
            # Логировать ошибку и обновить статус на FAILED
            self.logger.error(
                "Ошибка при RAG обработке документа %s: %s",
                service_id,
                str(e),
                exc_info=True,
            )

            try:
                await self.processing_repository.update_status(
                    processing_id,
                    ProcessingStatus.FAILED,
                    error_message=str(e)[:500],  # Ограничение по длине
                )
            except Exception as update_error:
                self.logger.error(
                    "Не удалось обновить статус на FAILED для %s: %s",
                    service_id,
                    str(update_error),
                )
