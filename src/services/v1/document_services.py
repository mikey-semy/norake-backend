"""
Сервис для управления сервисами документов (Document Service).

Содержит бизнес-логику для работы с document services: загрузка файлов в S3,
генерация обложек и QR-кодов, управление функциями документа, контроль доступа.

Classes:
    DocumentServiceService: Сервис с методами create, get, update, delete, upload.
"""

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    DocumentAccessDeniedError,
    DocumentServiceNotFoundError,
    DocumentServicePermissionDeniedError,
    DocumentServiceValidationError,
    FileSizeExceededError,
    FileTypeValidationError,
    QRCodeGenerationError,
)
from src.core.integrations.storages.documents import DocumentS3Storage
from src.core.settings.base import Settings
from src.models.v1.document_services import (
    CoverType,
    DocumentFileType,
    DocumentServiceModel,
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

    def __init__(self, session: AsyncSession, s3_client: Any, settings: Settings):
        """
        Инициализирует сервис документов.

        Args:
            session: Асинхронная сессия SQLAlchemy.
            s3_client: S3 клиент для работы с хранилищем.
            settings: Настройки приложения.
        """
        self.repository = DocumentServiceRepository(session)
        self.storage = DocumentS3Storage(s3_client)
        self.settings = settings
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
        if len(content) > self.settings.DOCUMENT_MAX_FILE_SIZE:
            raise FileSizeExceededError(
                file_size=len(content),
                max_size=self.settings.DOCUMENT_MAX_FILE_SIZE,
            )

        # Валидация MIME типа
        self._validate_file_type(file.content_type, metadata.file_type)

        # Загрузка файла в S3
        await file.seek(0)  # Вернуть указатель в начало
        file_url, _, file_size = await self.storage.upload_document(
            file=file,
            workspace_id=str(metadata.workspace_id) if metadata.workspace_id else None,
        )

        # Генерация thumbnail для PDF
        cover_url = None
        cover_type = metadata.cover_type or "icon"
        if metadata.file_type == "pdf" and cover_type == "generated":
            try:
                cover_url = await self.storage.generate_pdf_thumbnail(
                    file_content=content,
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
            "Создан document service %s для пользователя %s",
            document_service.id,
            author_id,
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
            if not user_id or service.author_id != user_id:
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
                # Извлекаем ключ из URL для delete_document_files
                document_key = service.file_url.split("/")[-1] if service.file_url else ""
                await self.storage.delete_document_files(
                    document_key=document_key,
                    thumbnail_key=service.cover_url.split("/")[-1] if service.cover_url else None,
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

        Используется для пагинации.

        Args:
            query: Параметры запроса.

        Returns:
            Общее количество сервисов.
        """
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
