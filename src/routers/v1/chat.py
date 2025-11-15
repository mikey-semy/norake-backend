"""
Router для AI чатов с RAG и OpenRouter интеграцией.

Предоставляет endpoints для работы с AI чатами:
- Список доступных моделей
- Создание и управление чатами
- Отправка сообщений с RAG контекстом
- Drag-and-drop загрузка файлов
- Переключение моделей
- Добавление документов в чат
"""

from datetime import datetime, timezone

from fastapi import File, Form, UploadFile, status

from src.core.dependencies import AIChatServiceDep
from src.core.dependencies.document_kb_integration import \
    DocumentKBIntegrationServiceDep
from src.core.dependencies.document_services import DocumentServiceServiceDep
from src.core.security import CurrentUserDep
from src.routers.base import ProtectedRouter
from src.schemas.v1.chat import (ChatAddDocumentsRequestSchema,
                                  ChatCreateRequestSchema,
                                  ChatCreateResponseSchema,
                                  ChatDeleteResponseSchema,
                                  ChatDetailResponseSchema,
                                  ChatDetailSchema,
                                  ChatListItemSchema,
                                  ChatListResponseSchema,
                                  ChatModelSwitchRequestSchema,
                                  ChatUpdateResponseSchema,
                                  MessageResponseSchema,
                                  MessageSendResponseSchema,
                                  ModelInfoSchema,
                                  ModelsListResponseSchema)


class ChatProtectedRouter(ProtectedRouter):
    """
    Protected router для AI чатов.

    Все endpoints требуют аутентификации. Поддерживает:
    - Создание личных и командных чатов
    - RAG поиск по документам
    - Мультимодельность (5 бесплатных моделей OpenRouter)
    - Drag-and-drop загрузка файлов через FormData
    """

    def __init__(self):
        """Инициализирует ChatProtectedRouter с префиксом и тегами."""
        super().__init__(prefix="chat", tags=["AI Chat"])

    def configure(self) -> None:
        """Конфигурация роутов для AI чатов."""

        @self.router.get(
            "/models",
            response_model=ModelsListResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Список доступных AI моделей",
            description=(
                "Возвращает список всех доступных бесплатных моделей OpenRouter "
                "с описаниями, специализациями и рекомендуемыми настройками. "
                "Используется для отображения в UI селекторе моделей."
            ),
        )
        async def list_models(
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
        ) -> ModelsListResponseSchema:
            """
            Получить список доступных AI моделей.

            Args:
                current_user: Текущий аутентифицированный пользователь
                chat_service: Сервис AI чатов (DI)

            Returns:
                ModelsListResponseSchema: Список моделей с метаданными

            Example:
                ```bash
                curl -X GET "http://localhost:8000/api/v1/models" \\
                     -H "Authorization: Bearer <token>"
                ```
            """
            self.logger.info(
                "Пользователь %s запрашивает список AI моделей",
                current_user.username,
            )

            models = await chat_service.get_available_models()

            # Конвертируем list[dict] в ModelInfoSchema
            models_list = [
                ModelInfoSchema(
                    key=model["key"],
                    id=model["id"],
                    name=model["name"],
                    description=model["description"],
                    specialization=model["specialization"],
                    context_window=model["context_window"],
                    temperature=model["temperature"],
                    max_tokens=model["max_tokens"],
                )
                for model in models
            ]

            self.logger.info("Возвращено %d AI моделей", len(models_list))

            return ModelsListResponseSchema(
                success=True,
                message=f"Доступно {len(models_list)} AI моделей",
                data=models_list,
            )

        @self.router.post(
            "/chat",
            response_model=ChatCreateResponseSchema,
            status_code=status.HTTP_201_CREATED,
            summary="Создать новый AI чат",
            description=(
                "Создаёт новый чат с выбранной AI моделью. Можно указать workspace "
                "для командного доступа и документы для RAG контекста. "
                "Генерирует читаемый chat_id (например: 'chat-abc123')."
            ),
        )
        async def create_chat(
            request: ChatCreateRequestSchema,
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
        ) -> ChatCreateResponseSchema:
            """
            Создать новый AI чат.

            Args:
                request: Данные для создания чата
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)

            Returns:
                ChatCreateResponseSchema: Созданный чат

            Raises:
                InvalidModelKeyError: Если model_key не найден в OPENROUTER_CHAT_MODELS
                DocumentNotFoundError: Если document_service_id не существует
                DocumentAccessDeniedError: Если пользователь не имеет доступа к документу

            Example:
                ```bash
                curl -X POST "http://localhost:8000/api/v1/chat" \\
                     -H "Authorization: Bearer <token>" \\
                     -H "Content-Type: application/json" \\
                     -d '{
                       "model_key": "qwen_coder",
                       "title": "Анализ договора",
                       "workspace_id": null,
                       "document_service_ids": ["550e8400-e29b-41d4-a716-446655440000"]
                     }'
                ```
            """
            self.logger.info(
                "Пользователь %s создаёт чат: model=%s, title=%s",
                current_user.username,
                request.model_key,
                request.title,
            )

            chat = await chat_service.create_chat(
                user_id=current_user.id,
                model_key=request.model_key,
                title=request.title,
                workspace_id=request.workspace_id,
                document_service_ids=request.document_service_ids or [],
                system_prompt=request.system_prompt,
            )

            self.logger.info(
                "Создан чат %s для пользователя %s",
                chat.chat_id,
                current_user.username,
            )

            # Конвертируем в ChatDetailSchema
            chat_schema = ChatDetailSchema.model_validate(chat)

            return ChatCreateResponseSchema(
                success=True,
                message=f"Чат '{chat.title}' создан",
                data=chat_schema,
            )

        @self.router.get(
            "/chat",
            response_model=ChatListResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Список чатов пользователя",
            description=(
                "Возвращает все активные чаты текущего пользователя, "
                "отсортированные по дате обновления (новые первыми). "
                "Максимум 50 чатов."
            ),
        )
        async def get_chats(
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
            limit: int = 50,
        ) -> ChatListResponseSchema:
            """
            Получить список чатов пользователя.

            Args:
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)
                limit: Максимальное количество чатов (по умолчанию 50)

            Returns:
                ChatListResponseSchema: Список чатов

            Example:
                ```bash
                curl -X GET "http://localhost:8000/api/v1/chat?limit=20" \\
                     -H "Authorization: Bearer <token>"
                ```
            """
            self.logger.info(
                "Пользователь %s запрашивает список чатов (limit=%d)",
                current_user.username,
                limit,
            )

            chats = await chat_service.chat_repo.get_user_active_chats(
                user_id=current_user.id, limit=limit
            )

            # Конвертируем в ChatListItemSchema
            chats_list = [
                ChatListItemSchema(
                    id=chat.id,
                    chat_id=chat.chat_id,
                    title=chat.title,
                    model_key=chat.model_key,
                    messages_count=chat.metadata.get("messages_count", 0),
                    workspace_id=chat.workspace_id,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                )
                for chat in chats
            ]

            self.logger.info(
                "Возвращено %d чатов для пользователя %s",
                len(chats_list),
                current_user.username,
            )

            return ChatListResponseSchema(
                success=True,
                message=f"Найдено {len(chats_list)} чатов",
                data=chats_list,
            )

        @self.router.get(
            "/chat/{chat_id}",
            response_model=ChatDetailResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Детальная информация о чате",
            description=(
                "Возвращает полную информацию о чате: сообщения, настройки, "
                "документы, метаданные. Проверяет права доступа пользователя."
            ),
        )
        async def get_chat_detail(
            chat_id: str,
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
        ) -> ChatDetailResponseSchema:
            """
            Получить детальную информацию о чате.

            Args:
                chat_id: Читаемый идентификатор чата
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)

            Returns:
                ChatDetailResponseSchema: Детальная информация о чате

            Raises:
                ChatNotFoundError: Если чат не найден или пользователь не имеет доступа

            Example:
                ```bash
                curl -X GET "http://localhost:8000/api/v1/chat/chat-abc123" \\
                     -H "Authorization: Bearer <token>"
                ```
            """
            self.logger.info(
                "Пользователь %s запрашивает чат %s",
                current_user.username,
                chat_id,
            )

            chat = await chat_service.chat_repo.get_by_chat_id(chat_id)

            if not chat or chat.user_id != current_user.id:
                from src.core.exceptions import ChatNotFoundError

                self.logger.warning(
                    "Чат %s не найден или нет доступа для пользователя %s",
                    chat_id,
                    current_user.username,
                )
                raise ChatNotFoundError(
                    detail=f"Чат '{chat_id}' не найден или нет доступа",
                    extra={"chat_id": chat_id},
                )

            # Конвертируем в ChatDetailSchema
            chat_schema = ChatDetailSchema.model_validate(chat)

            return ChatDetailResponseSchema(
                success=True,
                message=f"Информация о чате '{chat.title}'",
                data=chat_schema,
            )

        @self.router.post(
            "/chat/{chat_id}/message",
            response_model=MessageSendResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Отправить сообщение в чат (с опциональной загрузкой файла)",
            description=(
                "Отправляет сообщение в чат и получает ответ от AI. "
                "Поддерживает drag-and-drop загрузку файла через FormData: "
                "если файл предоставлен, он автоматически загружается в S3, "
                "активируется RAG (chunking + embeddings) и добавляется в чат. "
                "Затем выполняется RAG поиск по всем документам чата, "
                "контекст форматируется и отправляется в OpenRouter API."
            ),
        )
        async def send_message(
            chat_id: str,
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
            doc_service: DocumentServiceServiceDep,
            kb_integration_service: DocumentKBIntegrationServiceDep,
            content: str = Form(..., description="Текст сообщения"),
            file: UploadFile | None = File(None, description="Опциональный файл для загрузки"),
        ) -> MessageSendResponseSchema:
            """
            Отправить сообщение в чат с опциональной загрузкой файла.

            Workflow:
            1. Если файл предоставлен:
               - Загрузить в S3 через DocumentServiceService
               - Активировать RAG через DocumentKBIntegrationService
               - Добавить document в чат через add_documents()
            2. Выполнить RAG search по всем документам чата
            3. Отправить запрос в OpenRouter API с RAG контекстом
            4. Сохранить user + assistant сообщения в БД
            5. Обновить metadata (tokens_used, rag_queries_count)

            Args:
                chat_id: Читаемый идентификатор чата
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)
                doc_service: Сервис документов для загрузки файла (DI)
                kb_integration_service: Сервис активации RAG (DI)
                content: Текст сообщения пользователя (FormData)
                file: Опциональный файл для загрузки (FormData)

            Returns:
                MessageSendResponseSchema: Ответ AI ассистента

            Raises:
                ChatNotFoundError: Если чат не найден или нет доступа
                OpenRouterAPIError: Если OpenRouter API вернул ошибку
                DocumentProcessingError: Если произошла ошибка при обработке файла

            Example (без файла):
                ```bash
                curl -X POST "http://localhost:8000/api/v1/chat/chat-abc123/message" \\
                     -H "Authorization: Bearer <token>" \\
                     -F "content=Проанализируй документ"
                ```

            Example (с файлом):
                ```bash
                curl -X POST "http://localhost:8000/api/v1/chat/chat-abc123/message" \\
                     -H "Authorization: Bearer <token>" \\
                     -F "content=Проанализируй этот новый документ" \\
                     -F "file=@/path/to/document.pdf"
                ```
            """
            self.logger.info(
                "Пользователь %s отправляет сообщение в чат %s (файл: %s)",
                current_user.username,
                chat_id,
                "да" if file else "нет",
            )

            # Получаем чат для проверки доступа
            chat = await chat_service.chat_repo.get_by_chat_id(chat_id)
            if not chat or chat.user_id != current_user.id:
                from src.core.exceptions import ChatNotFoundError

                self.logger.warning(
                    "Чат %s не найден или нет доступа для пользователя %s",
                    chat_id,
                    current_user.username,
                )
                raise ChatNotFoundError(
                    detail=f"Чат '{chat_id}' не найден или нет доступа",
                    extra={"chat_id": chat_id},
                )

            # Если файл предоставлен - загружаем и активируем RAG
            if file:
                self.logger.info(
                    "Загрузка файла %s для чата %s",
                    file.filename,
                    chat_id,
                )

                # 1. Загружаем файл в S3 через DocumentServiceService
                document = await doc_service.create_document_service(
                    user_id=current_user.id,
                    file=file,
                    workspace_id=chat.workspace_id,
                    name=file.filename or "Uploaded Document",
                    description=f"Загружен через чат {chat_id}",
                )

                self.logger.info(
                    "Документ %s создан, активация RAG...",
                    document.id,
                )

                # 2. Активируем RAG (chunking + embeddings + KB)
                await kb_integration_service.activate_rag_for_document_service(
                    document_service_id=document.id,
                    user_id=current_user.id,
                )

                self.logger.info(
                    "RAG активирован для документа %s, добавление в чат...",
                    document.id,
                )

                # 3. Добавляем документ в чат
                await chat_service.add_documents(
                    chat_id=chat_id,
                    document_service_ids=[document.id],
                    user_id=current_user.id,
                )

                self.logger.info(
                    "Документ %s добавлен в чат %s",
                    document.id,
                    chat_id,
                )

            # Отправляем сообщение в OpenRouter с RAG контекстом
            ai_response = await chat_service.send_message(
                chat_id=chat_id,
                content=content,
                user_id=current_user.id,
            )

            self.logger.info(
                "AI ответ получен для чата %s (tokens: %d)",
                chat_id,
                ai_response.get("tokens_used", 0),
            )

            # Конвертируем в MessageResponseSchema
            message_response = MessageResponseSchema(
                role="assistant",
                content=ai_response["content"],
                metadata={
                    "tokens_used": ai_response.get("tokens_used", 0),
                    "rag_chunks_used": ai_response.get("rag_chunks_used", 0),
                    "model_key": chat.model_key,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            return MessageSendResponseSchema(
                success=True,
                message="Ответ получен",
                data=message_response,
            )

        @self.router.patch(
            "/chat/{chat_id}/model",
            response_model=ChatUpdateResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Переключить модель чата",
            description=(
                "Меняет AI модель чата с сохранением истории сообщений. "
                "Полезно для перехода с быстрой модели на более мощную "
                "или специализированную модель."
            ),
        )
        async def switch_model(
            chat_id: str,
            request: ChatModelSwitchRequestSchema,
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
        ) -> ChatUpdateResponseSchema:
            """
            Переключить модель чата.

            Args:
                chat_id: Читаемый идентификатор чата
                request: Новая модель
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)

            Returns:
                ChatUpdateResponseSchema: Обновлённый чат

            Raises:
                ChatNotFoundError: Если чат не найден или нет доступа
                InvalidModelKeyError: Если model_key не найден в OPENROUTER_CHAT_MODELS

            Example:
                ```bash
                curl -X PATCH "http://localhost:8000/api/v1/chat/chat-abc123/model" \\
                     -H "Authorization: Bearer <token>" \\
                     -H "Content-Type: application/json" \\
                     -d '{"model_key": "deepseek_r1"}'
                ```
            """
            self.logger.info(
                "Пользователь %s переключает модель чата %s на %s",
                current_user.username,
                chat_id,
                request.model_key,
            )

            chat = await chat_service.switch_model(
                chat_id=chat_id,
                new_model_key=request.model_key,
                user_id=current_user.id,
            )

            self.logger.info(
                "Модель чата %s переключена на %s",
                chat_id,
                request.model_key,
            )

            # Конвертируем в ChatDetailSchema
            chat_schema = ChatDetailSchema.model_validate(chat)

            return ChatUpdateResponseSchema(
                success=True,
                message=f"Модель изменена на {request.model_key}",
                data=chat_schema,
            )

        @self.router.post(
            "/chat/{chat_id}/documents",
            response_model=ChatUpdateResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Добавить документы в чат",
            description=(
                "Добавляет дополнительные документы в RAG контекст чата. "
                "Поддерживает drag-and-drop сценарий: пользователь перетаскивает "
                "существующие документы в чат для расширения контекста."
            ),
        )
        async def add_documents(
            chat_id: str,
            request: ChatAddDocumentsRequestSchema,
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
        ) -> ChatUpdateResponseSchema:
            """
            Добавить документы в чат.

            Args:
                chat_id: Читаемый идентификатор чата
                request: UUID документов для добавления
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)

            Returns:
                ChatUpdateResponseSchema: Обновлённый чат

            Raises:
                ChatNotFoundError: Если чат не найден или нет доступа
                DocumentNotFoundError: Если document_service_id не существует
                DocumentAccessDeniedError: Если нет доступа к документу

            Example:
                ```bash
                curl -X POST "http://localhost:8000/api/v1/chat/chat-abc123/documents" \\
                     -H "Authorization: Bearer <token>" \\
                     -H "Content-Type: application/json" \\
                     -d '{
                       "document_service_ids": [
                         "550e8400-e29b-41d4-a716-446655440000",
                         "650e8400-e29b-41d4-a716-446655440001"
                       ]
                     }'
                ```
            """
            self.logger.info(
                "Пользователь %s добавляет %d документов в чат %s",
                current_user.username,
                len(request.document_service_ids),
                chat_id,
            )

            chat = await chat_service.add_documents(
                chat_id=chat_id,
                document_service_ids=request.document_service_ids,
                user_id=current_user.id,
            )

            self.logger.info(
                "Документы добавлены в чат %s (всего: %d)",
                chat_id,
                len(chat.document_service_ids),
            )

            # Конвертируем в ChatDetailSchema
            chat_schema = ChatDetailSchema.model_validate(chat)

            return ChatUpdateResponseSchema(
                success=True,
                message=f"Добавлено {len(request.document_service_ids)} документов",
                data=chat_schema,
            )

        @self.router.delete(
            "/chat/{chat_id}",
            response_model=ChatDeleteResponseSchema,
            status_code=status.HTTP_200_OK,
            summary="Удалить чат (мягкое удаление)",
            description=(
                "Мягко удаляет чат (is_active=False). "
                "Чат остаётся в БД для аудита, но не отображается в списках."
            ),
        )
        async def delete_chat(
            chat_id: str,
            current_user: CurrentUserDep,
            chat_service: AIChatServiceDep,
        ) -> ChatDeleteResponseSchema:
            """
            Удалить чат (мягкое удаление).

            Args:
                chat_id: Читаемый идентификатор чата
                current_user: Текущий пользователь
                chat_service: Сервис AI чатов (DI)

            Returns:
                ChatDeleteResponseSchema: Результат удаления

            Raises:
                ChatNotFoundError: Если чат не найден или нет доступа

            Example:
                ```bash
                curl -X DELETE "http://localhost:8000/api/v1/chat/chat-abc123" \\
                     -H "Authorization: Bearer <token>"
                ```
            """
            self.logger.info(
                "Пользователь %s удаляет чат %s",
                current_user.username,
                chat_id,
            )

            # Получаем чат для проверки доступа
            chat = await chat_service.chat_repo.get_by_chat_id(chat_id)
            if not chat or chat.user_id != current_user.id:
                from src.core.exceptions import ChatNotFoundError

                self.logger.warning(
                    "Чат %s не найден или нет доступа для пользователя %s",
                    chat_id,
                    current_user.username,
                )
                raise ChatNotFoundError(
                    detail=f"Чат '{chat_id}' не найден или нет доступа",
                    extra={"chat_id": chat_id},
                )

            # Мягкое удаление (is_active=False)
            await chat_service.chat_repo.update_item(
                item_id=chat.id,
                update_data={"is_active": False},
            )

            self.logger.info(
                "Чат %s удалён для пользователя %s",
                chat_id,
                current_user.username,
            )

            return ChatDeleteResponseSchema(
                success=True,
                message=f"Чат '{chat.title}' удалён",
                data={"chat_id": chat_id, "deleted": True},
            )


# Создаём экземпляр роутера
chat_router = ChatProtectedRouter()
