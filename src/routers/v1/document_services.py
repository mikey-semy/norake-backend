"""
Роутеры для работы с сервисами документов (Document Services).

Модуль предоставляет HTTP API для управления сервисами документов:
- DocumentServiceProtectedRouter (ProtectedRouter) - защищённые CRUD endpoints

Все endpoints требуют JWT авторизации. Роутеры преобразуют domain objects
(DocumentServiceModel) в Pydantic схемы для ответа.

Routes:
    POST   /document-services              - Загрузить документ и создать сервис
    GET    /document-services              - Список сервисов с фильтрацией
    GET    /document-services/most-viewed  - Топ по просмотрам
    GET    /document-services/{id}         - Детали сервиса
    PUT    /document-services/{id}         - Обновить сервис
    DELETE /document-services/{id}         - Удалить сервис
    POST   /document-services/{id}/functions        - Добавить функцию
    DELETE /document-services/{id}/functions/{name} - Удалить функцию
    GET    /document-services/{id}/qr      - Сгенерировать QR-код
"""

from typing import Optional
from uuid import UUID

from fastapi import File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
import io

from src.core.dependencies.document_services import DocumentServiceServiceDep
from src.core.security import CurrentUserDep
from src.core.settings.base import settings
from src.routers.base import ProtectedRouter
from src.schemas.v1.document_services import (
    DocumentServiceCreateRequestSchema,
    DocumentServiceDetailSchema,
    DocumentServiceListItemSchema,
    DocumentServiceListResponseSchema,
    DocumentServiceQueryRequestSchema,
    DocumentServiceResponseSchema,
    DocumentServiceUpdateRequestSchema,
    DocumentFunctionAddRequestSchema,
    ServiceFunctionSchema,
)


class DocumentServiceProtectedRouter(ProtectedRouter):
    """
    Защищённый роутер для управления сервисами документов.

    Предоставляет HTTP API для CRUD операций с сервисами документов.
    Все endpoints требуют JWT авторизации.

    Protected Endpoints (требуется JWT):
        POST   /document-services              - Загрузить документ
        GET    /document-services              - Список с фильтрацией
        GET    /document-services/most-viewed  - Топ по просмотрам
        GET    /document-services/{id}         - Детали сервиса
        PUT    /document-services/{id}         - Обновить сервис
        DELETE /document-services/{id}         - Удалить сервис
        POST   /document-services/{id}/functions        - Добавить функцию
        DELETE /document-services/{id}/functions/{name} - Удалить функцию
        GET    /document-services/{id}/qr      - Сгенерировать QR
        GET    /document-services/{id}/file    - Стриминг файла документа

    Архитектурные особенности:
        - Роутер преобразует DocumentServiceModel → Schema
        - Бизнес-логика и права доступа в DocumentServiceService
        - NO try-catch: глобальный exception handler обрабатывает ошибки
        - Multipart/form-data для загрузки файлов
    """

    def __init__(self):
        """Инициализирует DocumentServiceProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="document-services", tags=["Document Services"])

    def configure(self):
        """Настройка защищённых endpoint'ов роутера."""

        # ==================== CREATE (UPLOAD) ====================

        @self.router.post(
            path="",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_201_CREATED,
            description="""
            ## 📤 Загрузить документ и создать сервис

            Создаёт сервис документа с загрузкой файла в S3:
            - Валидация размера (макс. 50MB)
            - Валидация MIME типа
            - Генерация thumbnail для PDF
            - Генерация QR-кода
            - Сохранение метаданных в БД

            ### 🔒 Требуется JWT токен

            ### Form Data:
            * **file**: Файл документа (PDF/DOC/DOCX/TXT/MD)
            * **title**: Название сервиса (3-200 символов)
            * **description**: Описание (опционально)
            * **tags**: Теги через запятую (опционально)
            * **file_type**: Тип файла (PDF/DOC/DOCX/TXT/MD)
            * **workspace_id**: UUID workspace (опционально)
            * **is_public**: Публичность (true/false)

            ### Returns:
            * **DocumentServiceResponseSchema**: Созданный сервис

            ### Errors:
            * **400**: Невалидные данные, превышен размер, недопустимый тип
            * **500**: Ошибка загрузки в S3
            """,
            responses={
                201: {"description": "Документ загружен, сервис создан"},
                400: {"description": "Ошибка валидации"},
                401: {"description": "Не авторизован"},
                500: {"description": "Ошибка загрузки"},
            },
        )
        async def create_document_service(
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
            file: UploadFile = File(..., description="Файл документа"),
            title: str = Form(..., min_length=3, max_length=200, description="Название"),
            file_type: str = Form(..., description="Тип файла (pdf/doc/docx/txt/md/spreadsheet/text/image)"),
            description: Optional[str] = Form(None, description="Описание"),
            tags: Optional[str] = Form(None, description="Теги через запятую"),
            workspace_id: Optional[UUID] = Form(None, description="UUID workspace"),
            is_public: bool = Form(True, description="Публичность"),
        ) -> DocumentServiceResponseSchema:
            """Загрузить документ и создать сервис."""
            # Парсинг тегов
            tags_list = [tag.strip() for tag in tags.split(",")] if tags else []

            # Подготовка метаданных - file_type автоматически нормализуется через field_validator
            metadata = DocumentServiceCreateRequestSchema(
                title=title,
                description=description,
                tags=tags_list,
                file_type=file_type,  # Валидатор схемы приведёт к lowercase
                workspace_id=workspace_id,
                is_public=is_public,
            )

            # Создание через сервис
            service = await document_service.create_document_service(
                file=file, metadata=metadata, author_id=current_user.id
            )

            # Преобразование в схему
            schema = DocumentServiceDetailSchema.model_validate(service)
            return DocumentServiceResponseSchema(
                success=True,
                message="Документ успешно загружен и сервис создан",
                data=schema,
            )

        # ==================== LIST ====================

        @self.router.get(
            path="",
            response_model=DocumentServiceListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📋 Получить список сервисов с фильтрацией

            Возвращает список сервисов с опциональными фильтрами:
            - Публичные сервисы доступны всем
            - Приватные сервисы видны только владельцу
            - Поддержка полнотекстового поиска
            - Фильтрация по тегам, автору, workspace, типу файла

            ### 🔒 Требуется JWT токен

            ### Query параметры:
            * **search**: Полнотекстовый поиск по title/description
            * **tags**: Фильтр по тегам (через запятую)
            * **author_id**: UUID автора
            * **workspace_id**: UUID workspace
            * **file_type**: Тип файла (PDF/DOC/DOCX/TXT/MD)
            * **is_public**: Публичность (true/false)
            * **limit**: Количество результатов (по умолчанию 20)
            * **offset**: Смещение для пагинации (по умолчанию 0)

            ### Returns:
            * **DocumentServiceListResponseSchema**: Список сервисов + total

            ### Примеры:
            * Все доступные: GET /document-services
            * Поиск: GET /document-services?search=инструкция
            * По тегам: GET /document-services?tags=api,docs
            * По типу: GET /document-services?file_type=PDF
            """,
            responses={
                200: {"description": "Список сервисов успешно получен"},
                401: {"description": "Не авторизован"},
            },
        )
        async def list_document_services(
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
            search: Optional[str] = Query(None, description="Полнотекстовый поиск"),
            tags: Optional[str] = Query(None, description="Теги через запятую"),
            author_id: Optional[UUID] = Query(None, description="UUID автора"),
            workspace_id: Optional[UUID] = Query(None, description="UUID workspace"),
            file_type: Optional[str] = Query(
                None, description="Тип файла (pdf/doc/docx/txt/md/spreadsheet/text/image)"
            ),
            is_public: Optional[bool] = Query(None, description="Публичность"),
            limit: int = Query(20, ge=1, le=100, description="Количество результатов"),
            offset: int = Query(0, ge=0, description="Смещение для пагинации"),
        ) -> DocumentServiceListResponseSchema:
            """Получить список сервисов с фильтрами."""
            # Парсинг тегов
            tags_list = [tag.strip() for tag in tags.split(",")] if tags else None

            # Подготовка query
            query = DocumentServiceQueryRequestSchema(
                search=search,
                tags=tags_list,
                author_id=author_id,
                workspace_id=workspace_id,
                file_type=file_type,
                is_public=is_public,
                limit=limit,
                offset=offset,
            )

            # Получение через сервис
            services, total = await document_service.list_document_services(
                query, current_user.id
            )

            # Преобразование в схемы
            items = [DocumentServiceListItemSchema.model_validate(s) for s in services]
            return DocumentServiceListResponseSchema(
                success=True, data=items, total=total
            )

        # ==================== MOST VIEWED ====================

        @self.router.get(
            path="/most-viewed",
            response_model=DocumentServiceListResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔥 Получить самые просматриваемые сервисы

            Возвращает топ сервисов по количеству просмотров.

            ### 🔒 Требуется JWT токен

            ### Query параметры:
            * **file_type**: Фильтр по типу файла (опционально)
            * **limit**: Количество результатов (по умолчанию 10)

            ### Returns:
            * **DocumentServiceListResponseSchema**: Топ сервисов

            ### Пример:
            * Топ-10: GET /document-services/most-viewed
            * Топ-5 PDF: GET /document-services/most-viewed?file_type=PDF&limit=5
            """,
            responses={
                200: {"description": "Топ сервисов получен"},
                401: {"description": "Не авторизован"},
            },
        )
        async def get_most_viewed(
            document_service: DocumentServiceServiceDep = None,
            file_type: Optional[str] = Query(
                None, description="Тип файла (pdf/doc/docx/txt/md/spreadsheet/text/image)"
            ),
            limit: int = Query(10, ge=1, le=50, description="Количество результатов"),
        ) -> DocumentServiceListResponseSchema:
            """Получить самые просматриваемые сервисы."""
            services = await document_service.get_most_viewed(
                file_type=file_type, limit=limit
            )
            items = [DocumentServiceListItemSchema.model_validate(s) for s in services]
            return DocumentServiceListResponseSchema(
                success=True, data=items, total=len(items)
            )

        # ==================== GET ONE ====================

        @self.router.get(
            path="/{service_id}",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📄 Получить детали сервиса по ID

            Возвращает полную информацию о сервисе документа.
            Приватные сервисы доступны только владельцу.
            Автоматически увеличивает счётчик просмотров.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Query параметры:
            * **increment_views**: Увеличить счётчик просмотров (по умолчанию true)

            ### Returns:
            * **DocumentServiceResponseSchema**: Детали сервиса

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на просмотр приватного сервиса
            """,
            responses={
                200: {"description": "Сервис найден"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                401: {"description": "Не авторизован"},
            },
        )
        async def get_document_service(
            service_id: UUID,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
            increment_views: bool = Query(
                True, description="Увеличить счётчик просмотров"
            ),
        ) -> DocumentServiceResponseSchema:
            """Получить сервис по ID."""
            service = await document_service.get_document_service(
                service_id=service_id,
                user_id=current_user.id,
                increment_views=increment_views,
            )
            schema = DocumentServiceDetailSchema.model_validate(service)
            return DocumentServiceResponseSchema(success=True, data=schema)

        # ==================== UPDATE ====================

        @self.router.put(
            path="/{service_id}",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ✏️ Обновить сервис документа

            Обновляет метаданные сервиса (title, description, tags, публичность).
            Файл документа изменить нельзя - только метаданные.
            Только владелец может обновлять сервис.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Body:
            * **title**: Новое название (опционально)
            * **description**: Новое описание (опционально)
            * **tags**: Новые теги (опционально)
            * **is_public**: Новая публичность (опционально)

            ### Returns:
            * **DocumentServiceResponseSchema**: Обновлённый сервис

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на обновление (не владелец)
            """,
            responses={
                200: {"description": "Сервис обновлён"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                401: {"description": "Не авторизован"},
            },
        )
        async def update_document_service(
            service_id: UUID,
            update_data: DocumentServiceUpdateRequestSchema,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> DocumentServiceResponseSchema:
            """Обновить сервис документа."""
            service = await document_service.update_document_service(
                service_id=service_id,
                update_data=update_data,
                user_id=current_user.id,
            )
            schema = DocumentServiceDetailSchema.model_validate(service)
            return DocumentServiceResponseSchema(
                success=True, message="Сервис успешно обновлён", data=schema
            )

        # ==================== DELETE ====================

        @self.router.delete(
            path="/{service_id}",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🗑️ Удалить сервис документа

            Удаляет сервис и все связанные файлы из S3:
            - Основной документ
            - Thumbnail (если есть)
            - QR-код (если есть)
            - Запись из БД

            Только владелец может удалить сервис.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Returns:
            * **DocumentServiceResponseSchema**: Подтверждение удаления

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на удаление (не владелец)
            """,
            responses={
                200: {"description": "Сервис удалён"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                401: {"description": "Не авторизован"},
            },
        )
        async def delete_document_service(
            service_id: UUID,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> DocumentServiceResponseSchema:
            """Удалить сервис документа."""
            await document_service.delete_document_service(
                service_id=service_id, user_id=current_user.id
            )
            return DocumentServiceResponseSchema(
                success=True,
                message="Сервис и связанные файлы успешно удалены",
                data=None,
            )

        # ==================== ADD FUNCTION ====================

        @self.router.post(
            path="/{service_id}/functions",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ➕ Добавить функцию к сервису

            Добавляет новую функцию в available_functions JSONB поле.
            Только владелец может добавлять функции.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Body:
            * **name**: Имя функции (view_pdf, download, qr, share, ai_chat)
            * **enabled**: Включена ли функция (true/false)
            * **config**: Конфигурация функции (опционально)

            ### Returns:
            * **DocumentServiceResponseSchema**: Обновлённый сервис

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на добавление (не владелец)
            * **400**: Функция уже существует
            """,
            responses={
                200: {"description": "Функция добавлена"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                400: {"description": "Функция уже существует"},
                401: {"description": "Не авторизован"},
            },
        )
        async def add_function(
            service_id: UUID,
            function_data: DocumentFunctionAddRequestSchema,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> DocumentServiceResponseSchema:
            """Добавить функцию к сервису."""
            # Преобразование в ServiceFunctionSchema
            function = ServiceFunctionSchema(
                name=function_data.name,
                enabled=function_data.enabled,
                config=function_data.config,
            )

            service = await document_service.add_function(
                service_id=service_id, function=function, user_id=current_user.id
            )
            schema = DocumentServiceDetailSchema.model_validate(service)
            return DocumentServiceResponseSchema(
                success=True, message="Функция успешно добавлена", data=schema
            )

        # ==================== REMOVE FUNCTION ====================

        @self.router.delete(
            path="/{service_id}/functions/{function_name}",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## ➖ Удалить функцию из сервиса

            Удаляет функцию из available_functions JSONB поля.
            Только владелец может удалять функции.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса
            * **function_name**: Имя функции для удаления

            ### Returns:
            * **DocumentServiceResponseSchema**: Обновлённый сервис

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на удаление (не владелец)
            * **400**: Функция не найдена
            """,
            responses={
                200: {"description": "Функция удалена"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                400: {"description": "Функция не найдена"},
                401: {"description": "Не авторизован"},
            },
        )
        async def remove_function(
            service_id: UUID,
            function_name: str,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> DocumentServiceResponseSchema:
            """Удалить функцию из сервиса."""
            service = await document_service.remove_function(
                service_id=service_id,
                function_name=function_name,
                user_id=current_user.id,
            )
            schema = DocumentServiceDetailSchema.model_validate(service)
            return DocumentServiceResponseSchema(
                success=True, message="Функция успешно удалена", data=schema
            )

        # ==================== GET AI FUNCTIONS ====================

        @self.router.get(
            path="/{service_id}/functions",
            response_model=dict,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🤖 Получить статусы AI функций документа

            Возвращает информацию о доступности AI функций:
            - **smart_search**: Умный поиск по тексту документа
            - **rag_search**: RAG поиск с семантическими векторами
            - **document_chat**: Чат с документом (GPT-4)
            - **summary**: Генерация краткого содержания
            - **entity_extraction**: Извлечение сущностей (модели, артикулы)

            Статусы:
            - **ready**: Функция готова к использованию
            - **processing**: Обработка документа в процессе
            - **inactive**: Функция не активирована или не применима
            - **failed**: Ошибка при обработке документа

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса документа

            ### Returns:
            * Список функций с их статусами:
            ```json
            {
                "success": true,
                "message": "AI функции документа получены",
                "data": [
                    {
                        "name": "smart_search",
                        "enabled": true,
                        "status": "ready"
                    },
                    {
                        "name": "rag_search",
                        "enabled": false,
                        "status": "processing",
                        "progress": 65
                    }
                ]
            }
            ```

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав доступа (для приватных документов)
            * **401**: Не авторизован
            """,
            responses={
                200: {"description": "AI функции получены"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                401: {"description": "Не авторизован"},
            },
        )
        async def get_ai_functions(
            service_id: UUID,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> dict:
            """Получить статусы AI функций документа."""
            functions = await document_service.get_ai_functions(
                service_id=service_id,
                user_id=current_user.id,
            )
            return {
                "success": True,
                "message": "AI функции документа получены",
                "data": functions,
            }

        # ==================== GENERATE QR ====================

        @self.router.get(
            path="/{service_id}/qr",
            response_model=dict,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🔲 Сгенерировать QR-код для документа

            Генерирует QR-код со ссылкой на документ и загружает в S3.
            Только владелец может генерировать QR-коды.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Returns:
            * **dict**: {"success": true, "qr_url": "...", "document_url": "..."}

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на генерацию (не владелец)
            * **500**: Ошибка генерации QR
            """,
            responses={
                200: {"description": "QR-код сгенерирован"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                500: {"description": "Ошибка генерации QR"},
                401: {"description": "Не авторизован"},
            },
        )
        async def generate_qr(
            service_id: UUID,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> dict:
            """Сгенерировать QR-код для документа."""
            qr_url = await document_service.generate_qr(
                service_id=service_id, user_id=current_user.id, base_url=settings.DOCUMENT_BASE_URL
            )
            return {
                "success": True,
                "message": "QR-код успешно сгенерирован",
                "qr_url": qr_url,
                "document_url": f"{settings.DOCUMENT_BASE_URL}/documents/{service_id}",
            }

        # ==================== UPDATE COVER ====================

        @self.router.put(
            path="/{service_id}/cover",
            response_model=DocumentServiceResponseSchema,
            status_code=status.HTTP_200_OK,
            description="""
            ## 🎨 Обновить обложку документа

            Поддерживает три варианта обложки:
            1. **GENERATED** - автоматическая генерация из PDF (первая страница)
            2. **ICON** - установка эмодзи/иконки
            3. **IMAGE** - загрузка изображения обложки

            Только владелец может обновлять обложку.

            ### 🔒 Требуется JWT токен

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Form Data:
            * **cover_type**: Тип обложки (generated/icon/image)
            * **cover_icon**: Эмодзи/иконка (если cover_type=ICON)
            * **cover_image**: Файл изображения (если cover_type=IMAGE, макс 5MB)

            ### Returns:
            * **DocumentServiceResponseSchema**: Обновлённый сервис с новой обложкой

            ### Errors:
            * **404**: Сервис не найден
            * **403**: Нет прав на изменение (не владелец)
            * **400**: Невалидные данные, некорректный тип обложки
            * **400**: Для PDF generated доступен только для PDF документов

            ### Примеры:
            * Регенерировать из PDF: `{"cover_type": "generated"}`
            * Установить иконку: `{"cover_type": "icon", "cover_icon": "📄"}`
            * Загрузить изображение: `{"cover_type": "image"}` + файл cover_image
            """,
            responses={
                200: {"description": "Обложка обновлена"},
                404: {"description": "Сервис не найден"},
                403: {"description": "Нет прав доступа"},
                400: {"description": "Невалидные данные"},
                401: {"description": "Не авторизован"},
            },
        )
        async def update_cover(
            service_id: UUID,
            cover_type: str = Form(..., description="Тип обложки (generated/icon/image)"),
            cover_icon: Optional[str] = Form(None, description="Эмодзи/иконка (для ICON)"),
            cover_image: Optional[UploadFile] = File(None, description="Изображение обложки (для IMAGE)"),
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
        ) -> DocumentServiceResponseSchema:
            """Обновить обложку документа."""
            service = await document_service.update_cover(
                service_id=service_id,
                user_id=current_user.id,
                cover_type=cover_type,
                cover_icon=cover_icon,
                cover_image=cover_image,
            )
            schema = DocumentServiceDetailSchema.model_validate(service)
            return DocumentServiceResponseSchema(
                success=True,
                message="Обложка успешно обновлена",
                data=schema,
            )

        # ==================== GET FILE (PROXY) ====================

        @self.router.get(
            path="/{service_id}/file",
            response_class=StreamingResponse,
            status_code=status.HTTP_200_OK,
            description="""
            ## 📥 Получить файл документа

            Проксирует файл из S3 через backend с правильными CORS заголовками.
            Поддерживает просмотр PDF в браузере и скачивание файлов.

            ### 🔒 Требуется JWT токен #TODO: Исправить - для публичных не нужно

            ### Path параметры:
            * **service_id**: UUID сервиса

            ### Returns:
            * **StreamingResponse**: Файл документа с MIME типом

            ### Errors:
            * **404**: Сервис или файл не найден
            * **403**: Нет прав доступа (приватный документ)
            * **401**: Не авторизован

            ### Примеры:
            * Просмотр PDF: GET /document-services/{id}/file
            * Скачивание: GET /document-services/{id}/file?download=true
            """,
            responses={
                200: {"description": "Файл получен", "content": {"application/pdf": {}}},
                404: {"description": "Сервис или файл не найден"},
                403: {"description": "Нет прав доступа"},
                401: {"description": "Не авторизован"},
            },
        )
        async def get_file(
            service_id: UUID,
            current_user: CurrentUserDep = None,
            document_service: DocumentServiceServiceDep = None,
            download: bool = Query(False, description="Скачать файл вместо просмотра"),
        ) -> StreamingResponse:
            """Получить файл документа через backend proxy."""
            # Получаем файл из S3 через сервис
            file_content, content_type, filename = await document_service.get_document_file(
                service_id=service_id, user_id=current_user.id
            )

            # Создаём stream из байтов
            file_stream = io.BytesIO(file_content)

            # Определяем Content-Disposition
            disposition_type = "attachment" if download else "inline"

            # Возвращаем файл с правильными заголовками
            # CORS обрабатывается глобальным CORSMiddleware, не переопределяем вручную
            return StreamingResponse(
                file_stream,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'{disposition_type}; filename="{filename}"',
                    "Cache-Control": "public, max-age=3600",  # Кэширование на 1 час
                },
            )
