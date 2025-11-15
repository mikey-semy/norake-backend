"""
Сервис для работы с AI чатами через OpenRouter.

Модуль предоставляет функциональность AI чатов:
- Создание чатов с выбором модели
- Отправка сообщений с RAG контекстом
- Переключение между моделями
- Управление документами для RAG
- Получение доступных моделей
"""

import httpx
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    ChatNotFoundError,
    DocumentServiceNotFoundError,
    InvalidModelKeyError,
    OpenRouterAPIError,
)
from src.models.v1.ai_chats import AIChatModel
from src.repository.v1.ai_chats import AIChatRepository
from src.repository.v1.document_services import DocumentServiceRepository
from src.services.base import BaseService
from src.services.v1.rag_search import RAGSearchService


class AIChatService(BaseService):
    """
    Сервис для работы с AI чатами.

    Управляет созданием чатов, отправкой сообщений с RAG контекстом,
    переключением моделей и интеграцией с OpenRouter API.

    Attributes:
        session: Сессия SQLAlchemy
        settings: Настройки приложения
        chat_repo: Репозиторий чатов
        doc_service_repo: Репозиторий Document Services
        rag_service: Сервис RAG поиска

    Example:
        >>> service = AIChatService(session, rag_service, settings)
        >>> chat = await service.create_chat(
        ...     user_id=user_id,
        ...     model_key="qwen_coder",
        ...     title="Code Review",
        ...     document_service_ids=[doc_id]
        ... )
    """

    def __init__(
        self,
        session: AsyncSession,
        rag_service: RAGSearchService,
    ):
        """
        Инициализирует сервис AI чатов.

        Args:
            session: Асинхронная сессия SQLAlchemy
            rag_service: Сервис RAG поиска
        """
        super().__init__(session)
        self.rag_service = rag_service
        self.chat_repo = AIChatRepository(session)
        self.doc_service_repo = DocumentServiceRepository(session)

    async def create_chat(
        self,
        user_id: UUID,
        model_key: str,
        title: str,
        workspace_id: UUID | None = None,
        document_service_ids: list[UUID] | None = None,
        system_prompt: str | None = None,
    ) -> AIChatModel:
        """
        Создает новый AI чат.

        Args:
            user_id: UUID пользователя
            model_key: Ключ модели из OPENROUTER_CHAT_MODELS
            title: Название чата
            workspace_id: UUID workspace (опционально)
            document_service_ids: Список UUID документов для RAG
            system_prompt: Кастомный system prompt (опционально)

        Returns:
            AIChatModel: Созданный чат

        Raises:
            InvalidModelKeyError: Неизвестный model_key
            DocumentNotFoundError: Документ из списка не найден

        Example:
            >>> chat = await service.create_chat(
            ...     user_id=user_id,
            ...     model_key="qwen_coder",
            ...     title="Code Review Assistant"
            ... )
        """
        # Валидация model_key
        if model_key not in self.settings.OPENROUTER_CHAT_MODELS:
            raise InvalidModelKeyError(
                detail=f"Неизвестный ключ модели: {model_key}",
                extra={
                    "model_key": model_key,
                    "available": list(self.settings.OPENROUTER_CHAT_MODELS.keys()),
                },
            )

        # Валидация документов (если указаны)
        doc_ids = document_service_ids or []
        if doc_ids:
            for doc_id in doc_ids:
                doc = await self.doc_service_repo.get_item_by_id(doc_id)
                if not doc:
                    raise DocumentServiceNotFoundError(
                        service_id=doc_id,
                    )

        # Генерируем chat_id
        chat_id = self._generate_chat_id()

        # Получаем настройки модели по умолчанию
        model_config = self.settings.OPENROUTER_CHAT_MODELS[model_key]
        model_settings = {
            "temperature": model_config["temperature"],
            "max_tokens": model_config.get("max_tokens", 4000),
        }

        # Добавляем system prompt если указан
        if system_prompt:
            model_settings["system_prompt"] = system_prompt

        # Создаем чат
        chat_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "workspace_id": workspace_id,
            "title": title,
            "model_key": model_key,
            "document_service_ids": doc_ids,
            "messages": [],
            "model_settings": model_settings,
            "metadata": {
                "tokens_used": 0,
                "messages_count": 0,
                "estimated_cost": 0.0,
                "rag_queries_count": 0,
            },
        }

        chat = await self.chat_repo.create_item(chat_data)

        self.logger.info(
            "Создан чат %s для пользователя %s (модель: %s)",
            chat_id,
            user_id,
            model_key,
        )

        return chat

    async def send_message(
        self,
        chat_id: str,
        content: str,
        user_id: UUID,
    ) -> dict[str, Any]:
        """
        Отправляет сообщение в чат и получает ответ от AI.

        Выполняет:
        1. Поиск чата и проверку прав доступа
        2. RAG поиск по документам (если привязаны)
        3. Формирование промпта с контекстом
        4. Запрос к OpenRouter API
        5. Сохранение сообщений в историю

        Args:
            chat_id: Readable идентификатор чата
            content: Текст сообщения пользователя
            user_id: UUID пользователя (для проверки прав)

        Returns:
            dict: Ответ AI с метаданными:
                {
                    "role": "assistant",
                    "content": str,
                    "metadata": {
                        "model": str,
                        "tokens_used": int,
                        "rag_chunks_used": int,
                        "timestamp": str
                    }
                }

        Raises:
            ChatNotFoundError: Чат не найден
            OpenRouterAPIError: Ошибка API OpenRouter

        Example:
            >>> response = await service.send_message(
            ...     chat_id="chat-abc123",
            ...     content="Explain this code",
            ...     user_id=user_id
            ... )
        """
        # Получаем чат
        chat = await self.chat_repo.get_by_chat_id(chat_id)
        if not chat:
            raise ChatNotFoundError(
                detail=f"Чат {chat_id} не найден",
                extra={"chat_id": chat_id},
            )

        # Проверяем права доступа
        if chat.user_id != user_id:
            raise ChatNotFoundError(
                detail="Доступ к чату запрещён",
                extra={"chat_id": chat_id, "user_id": str(user_id)},
            )

        # RAG поиск по документам
        rag_context = ""
        rag_chunks_count = 0

        if chat.document_service_ids:
            rag_results = await self._search_rag_context(
                query=content,
                document_service_ids=chat.document_service_ids,
            )
            rag_context = self._format_rag_context(rag_results)
            rag_chunks_count = len(rag_results)

            self.logger.debug(
                "RAG поиск для чата %s: найдено %d чанков",
                chat_id,
                rag_chunks_count,
            )

        # Формируем messages для OpenRouter
        messages = self._build_messages(
            chat_history=chat.messages,
            user_content=content,
            rag_context=rag_context,
            system_prompt=chat.model_settings.get("system_prompt"),
        )

        # Запрос к OpenRouter
        model_config = self.settings.OPENROUTER_CHAT_MODELS[chat.model_key]
        ai_response = await self._call_openrouter(
            model_id=model_config["id"],
            messages=messages,
            temperature=chat.model_settings.get("temperature", 0.7),
            max_tokens=chat.model_settings.get("max_tokens", 4000),
        )

        # Сохраняем сообщения в историю
        timestamp = datetime.utcnow().isoformat()

        user_message = {
            "role": "user",
            "content": content,
            "metadata": {"timestamp": timestamp},
        }

        assistant_message = {
            "role": "assistant",
            "content": ai_response["content"],
            "metadata": {
                "model": chat.model_key,
                "tokens_used": ai_response.get("tokens_used", 0),
                "rag_chunks_used": rag_chunks_count,
                "timestamp": timestamp,
            },
        }

        new_messages = chat.messages + [user_message, assistant_message]
        await self.chat_repo.update_messages(chat_id, new_messages)

        # Обновляем статистику
        await self._update_chat_stats(
            chat=chat,
            tokens_used=ai_response.get("tokens_used", 0),
            rag_queries_count=1 if rag_chunks_count > 0 else 0,
        )

        self.logger.info(
            "Сообщение отправлено в чат %s (tokens: %d, rag_chunks: %d)",
            chat_id,
            ai_response.get("tokens_used", 0),
            rag_chunks_count,
        )

        return assistant_message

    async def switch_model(
        self,
        chat_id: str,
        new_model_key: str,
        user_id: UUID,
    ) -> AIChatModel:
        """
        Переключает модель чата с сохранением истории.

        Args:
            chat_id: Readable идентификатор чата
            new_model_key: Новый ключ модели
            user_id: UUID пользователя (для проверки прав)

        Returns:
            AIChatModel: Обновленный чат

        Raises:
            ChatNotFoundError: Чат не найден
            InvalidModelKeyError: Неизвестный model_key

        Example:
            >>> chat = await service.switch_model(
            ...     chat_id="chat-abc123",
            ...     new_model_key="deepseek_r1",
            ...     user_id=user_id
            ... )
        """
        # Валидация модели
        if new_model_key not in self.settings.OPENROUTER_CHAT_MODELS:
            raise InvalidModelKeyError(
                detail=f"Неизвестный ключ модели: {new_model_key}",
                extra={"model_key": new_model_key},
            )

        # Получаем чат
        chat = await self.chat_repo.get_by_chat_id(chat_id)
        if not chat or chat.user_id != user_id:
            raise ChatNotFoundError(
                detail=f"Чат {chat_id} не найден",
                extra={"chat_id": chat_id},
            )

        # Обновляем модель и настройки
        model_config = self.settings.OPENROUTER_CHAT_MODELS[new_model_key]
        new_settings = {
            "temperature": model_config["temperature"],
            "max_tokens": model_config.get("max_tokens", 4000),
        }

        # Сохраняем system_prompt если был
        if "system_prompt" in chat.model_settings:
            new_settings["system_prompt"] = chat.model_settings["system_prompt"]

        updated_chat = await self.chat_repo.update_item(
            chat.id,
            {
                "model_key": new_model_key,
                "model_settings": new_settings,
            },
        )

        self.logger.info(
            "Модель чата %s изменена: %s → %s",
            chat_id,
            chat.model_key,
            new_model_key,
        )

        return updated_chat

    async def add_documents(
        self,
        chat_id: str,
        document_service_ids: list[UUID],
        user_id: UUID,
    ) -> AIChatModel:
        """
        Добавляет документы к чату для RAG.

        Args:
            chat_id: Readable идентификатор чата
            document_service_ids: Список UUID документов
            user_id: UUID пользователя (для проверки прав)

        Returns:
            AIChatModel: Обновленный чат

        Raises:
            ChatNotFoundError: Чат не найден
            DocumentNotFoundError: Документ не найден

        Example:
            >>> chat = await service.add_documents(
            ...     chat_id="chat-abc123",
            ...     document_service_ids=[doc1_id, doc2_id],
            ...     user_id=user_id
            ... )
        """
        # Получаем чат
        chat = await self.chat_repo.get_by_chat_id(chat_id)
        if not chat or chat.user_id != user_id:
            raise ChatNotFoundError(
                detail=f"Чат {chat_id} не найден",
                extra={"chat_id": chat_id},
            )

        # Валидация документов
        for doc_id in document_service_ids:
            doc = await self.doc_service_repo.get_item_by_id(doc_id)
            if not doc:
                raise DocumentServiceNotFoundError(
                    service_id=doc_id,
                )

        # Объединяем с существующими (уникальные)
        existing_ids = set(chat.document_service_ids or [])
        new_ids = existing_ids.union(document_service_ids)

        updated_chat = await self.chat_repo.update_item(
            chat.id,
            {"document_service_ids": list(new_ids)},
        )

        self.logger.info(
            "Добавлено %d документов в чат %s (всего: %d)",
            len(document_service_ids),
            chat_id,
            len(new_ids),
        )

        return updated_chat

    async def get_available_models(self) -> list[dict[str, Any]]:
        """
        Возвращает список доступных моделей.

        Returns:
            list[dict]: Список моделей с метаданными

        Example:
            >>> models = await service.get_available_models()
            >>> len(models) == 5
            True
        """
        return [
            {
                "key": key,
                "id": config["id"],
                "name": config["name"],
                "description": config["description"],
                "specialization": config["specialization"],
                "context_window": config["context_window"],
                "temperature": config["temperature"],
                "max_tokens": config.get("max_tokens", 4000),
            }
            for key, config in self.settings.OPENROUTER_CHAT_MODELS.items()
        ]

    def _generate_chat_id(self) -> str:
        """Генерирует уникальный chat_id."""
        return f"chat-{uuid4().hex[:12]}"

    async def _search_rag_context(
        self,
        query: str,
        document_service_ids: list[UUID],
    ) -> list[dict]:
        """
        Выполняет RAG поиск по документам.

        Args:
            query: Поисковый запрос
            document_service_ids: Список UUID документов

        Returns:
            list[dict]: Результаты RAG поиска
        """
        all_results = []

        for doc_id in document_service_ids:
            # Получаем document_service
            doc_service = await self.doc_service_repo.get_item_by_id(doc_id)
            if not doc_service or not doc_service.knowledge_base_id:
                continue

            # Поиск в KB
            results = await self.rag_service.search(
                query=query,
                kb_id=doc_service.knowledge_base_id,
                limit=3,  # 3 чанка на документ
            )

            all_results.extend(results)

        return all_results[:10]  # Максимум 10 чанков

    def _format_rag_context(self, rag_results: list[dict]) -> str:
        """
        Форматирует результаты RAG в текстовый контекст.

        Args:
            rag_results: Результаты RAG поиска

        Returns:
            str: Отформатированный контекст
        """
        if not rag_results:
            return ""

        context_parts = ["### Контекст из документов:\n"]

        for idx, result in enumerate(rag_results, 1):
            content = result.get("content", "")
            score = result.get("score", 0.0)
            context_parts.append(f"\n**Фрагмент {idx}** (релевантность: {score:.2f}):")
            context_parts.append(f"{content}\n")

        return "\n".join(context_parts)

    def _build_messages(
        self,
        chat_history: list[dict],
        user_content: str,
        rag_context: str,
        system_prompt: str | None = None,
    ) -> list[dict]:
        """
        Формирует массив messages для OpenRouter API.

        Args:
            chat_history: История сообщений чата
            user_content: Новое сообщение пользователя
            rag_context: RAG контекст (если есть)
            system_prompt: System prompt (если есть)

        Returns:
            list[dict]: Массив messages для API
        """
        messages = []

        # System prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # История (последние 10 сообщений)
        recent_history = chat_history[-10:]
        for msg in recent_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        # Новое сообщение с RAG контекстом
        user_message = user_content
        if rag_context:
            user_message = f"{rag_context}\n\n---\n\n**Вопрос:** {user_content}"

        messages.append({"role": "user", "content": user_message})

        return messages

    async def _call_openrouter(
        self,
        model_id: str,
        messages: list[dict],
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        """
        Выполняет запрос к OpenRouter API.

        Args:
            model_id: ID модели OpenRouter
            messages: Массив сообщений
            temperature: Температура генерации
            max_tokens: Максимум токенов

        Returns:
            dict: Ответ с content и tokens_used

        Raises:
            OpenRouterAPIError: Ошибка API
        """
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)

                return {"content": content, "tokens_used": tokens_used}

        except httpx.HTTPError as e:
            self.logger.error("Ошибка OpenRouter API: %s", str(e))
            raise OpenRouterAPIError(
                detail=f"Ошибка запроса к OpenRouter: {str(e)}",
                extra={"model": model_id, "error": str(e)},
            ) from e

    async def _update_chat_stats(
        self,
        chat: AIChatModel,
        tokens_used: int,
        rag_queries_count: int,
    ) -> None:
        """
        Обновляет статистику чата.

        Args:
            chat: Модель чата
            tokens_used: Использованные токены
            rag_queries_count: Количество RAG запросов
        """
        metadata = chat.metadata or {}
        metadata["tokens_used"] = metadata.get("tokens_used", 0) + tokens_used
        metadata["rag_queries_count"] = (
            metadata.get("rag_queries_count", 0) + rag_queries_count
        )

        await self.chat_repo.update_item(chat.id, {"metadata": metadata})
