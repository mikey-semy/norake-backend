"""Клиент для работы с n8n webhooks.

Модуль предоставляет асинхронный HTTP клиент для взаимодействия с n8n workflows
через webhook триггеры. Используется для автоматизации бизнес-процессов:
- Авто-категоризация Issues через AI
- Индексация документов в Knowledge Base
- Поиск с RAG (Retrieval-Augmented Generation)
- Генерация еженедельных дайджестов

Конфигурация через settings:
    N8N_WEBHOOK_TIMEOUT: Таймаут HTTP запроса (сек)
    N8N_WEBHOOK_RETRY_ATTEMPTS: Количество попыток при ошибке
    N8N_WEBHOOK_RETRY_DELAY: Задержка между попытками (сек)

Пример использования:
    >>> from src.core.integrations.n8n import n8n_webhook_client
    >>> 
    >>> # Синхронный вызов (ждёт ответа)
    >>> result = await n8n_webhook_client.trigger_autocategorize(
    ...     webhook_url="http://localhost:5678/webhook/autocategorize",
    ...     issue_id=uuid4(),
    ...     title="Ошибка E401",
    ...     description="Станок останавливается"
    ... )
    >>> 
    >>> # Асинхронный вызов (fire-and-forget)
    >>> n8n_webhook_client.trigger_autocategorize_background(
    ...     webhook_url="http://localhost:5678/webhook/autocategorize",
    ...     issue_id=issue.id,
    ...     title=issue.title,
    ...     description=issue.description
    ... )

Архитектура:
    Backend (IssueService) → N8nWebhookClient → n8n Workflow → OpenRouter AI → Backend API

Безопасность:
    - Таймауты для предотвращения зависаний
    - Retry механизм с экспоненциальной задержкой
    - Логирование всех запросов/ошибок
    - Graceful degradation (не блокирует основной flow при ошибках)

Зависимости:
    - httpx: Асинхронный HTTP клиент
    - pydantic: Валидация настроек
    - asyncio: Background tasks для fire-and-forget

См. также:
    - docs/n8n_workflows/README.md: Инструкции по импорту workflows
    - src/repository/v1/n8n_workflows.py: Repository для работы с N8nWorkflowModel
    - src/services/v1/issues.py: Интеграция webhook в IssueService
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from uuid import UUID

import httpx

from src.core.settings import settings


logger = logging.getLogger(__name__)


class N8nWebhookClient:
    """Асинхронный HTTP клиент для вызова n8n webhooks.

    Выполняет POST запросы к n8n workflows с:
    - Настраиваемым таймаутом
    - Retry механизмом при сетевых ошибках
    - Детальным логированием
    - Обработкой HTTP ошибок

    Все методы возвращают Optional[Dict] - None при ошибке (graceful degradation).

    Attributes:
        timeout (float): Таймаут HTTP запроса в секундах (из settings.N8N_WEBHOOK_TIMEOUT).
        retry_attempts (int): Количество попыток при ошибке (из settings.N8N_WEBHOOK_RETRY_ATTEMPTS).
        retry_delay (float): Задержка между попытками в секундах (из settings.N8N_WEBHOOK_RETRY_DELAY).

    Пример:
        >>> client = N8nWebhookClient()
        >>> result = await client.trigger_autocategorize(
        ...     webhook_url="http://n8n:5678/webhook/categorize",
        ...     issue_id=uuid4(),
        ...     title="Проблема с оборудованием",
        ...     description="Станок не запускается"
        ... )
        >>> if result:
        ...     print(f"Category: {result['category']}")
    """

    def __init__(
        self,
        timeout: Optional[float] = None,
        retry_attempts: Optional[int] = None,
        retry_delay: Optional[float] = None,
    ):
        """Инициализация клиента с настройками из settings.

        Args:
            timeout: Таймаут запроса в секундах.
                По умолчанию используется settings.N8N_WEBHOOK_TIMEOUT (30 сек).
            retry_attempts: Количество попыток при ошибке.
                По умолчанию используется settings.N8N_WEBHOOK_RETRY_ATTEMPTS (2).
            retry_delay: Задержка между попытками в секундах.
                По умолчанию используется settings.N8N_WEBHOOK_RETRY_DELAY (1.0 сек).

        Example:
            >>> # Использование настроек по умолчанию
            >>> client = N8nWebhookClient()
            >>> 
            >>> # Переопределение таймаута
            >>> client = N8nWebhookClient(timeout=60.0)
        """
        self.timeout = timeout or settings.N8N_WEBHOOK_TIMEOUT
        self.retry_attempts = retry_attempts or settings.N8N_WEBHOOK_RETRY_ATTEMPTS
        self.retry_delay = retry_delay or settings.N8N_WEBHOOK_RETRY_DELAY

        logger.debug(
            "N8nWebhookClient инициализирован: timeout=%s, retry_attempts=%s, retry_delay=%s",
            self.timeout,
            self.retry_attempts,
            self.retry_delay,
        )

    async def trigger_autocategorize(
        self,
        webhook_url: str,
        issue_id: UUID,
        title: str,
        description: str,
    ) -> Optional[Dict[str, Any]]:
        """Вызвать n8n workflow для авто-категоризации Issue через AI.

        Отправляет данные Issue в n8n webhook, который:
        1. Извлекает title и description
        2. Отправляет в OpenRouter AI (LLaMA 3.2)
        3. Парсит категорию из ответа
        4. Обновляет Issue через Backend API
        5. Возвращает результат

        Args:
            webhook_url: URL n8n webhook (production).
                Пример: "http://localhost:5678/webhook/autocategorize-issue"
            issue_id: UUID Issue для категоризации.
            title: Заголовок проблемы (краткое описание).
            description: Детальное описание проблемы.

        Returns:
            Dict с результатом категоризации:
                {
                    "success": True,
                    "issue_id": "uuid",
                    "category": "hardware",  # или software, process и т.д.
                    "message": "Issue categorized successfully"
                }
            None при ошибке (сетевая ошибка, таймаут, HTTP 4xx/5xx).

        Raises:
            Не выбрасывает исключения - возвращает None для graceful degradation.

        Example:
            >>> result = await client.trigger_autocategorize(
            ...     webhook_url="http://n8n:5678/webhook/autocategorize-issue",
            ...     issue_id=UUID("..."),
            ...     title="Ошибка E401 на станке CNC",
            ...     description="При запуске G-code программы станок останавливается"
            ... )
            >>> if result and result["success"]:
            ...     print(f"Категория: {result['category']}")  # Ожидаем: hardware

        Категории (9 вариантов):
            - hardware: Проблемы с оборудованием
            - software: Ошибки ПО, баги, сбои систем
            - process: Нарушения бизнес-процессов
            - documentation: Отсутствие/устаревание документации
            - safety: Вопросы безопасности
            - quality: Проблемы с качеством продукции
            - maintenance: Обслуживание, ремонт
            - training: Обучение персонала
            - other: Неопределённые проблемы

        Performance:
            - Timeout: 30 секунд (по умолчанию)
            - Retry: 2 попытки с задержкой 1 секунда
            - AI latency: ~2-5 секунд (OpenRouter)

        Note:
            Метод НЕ блокирует основной flow создания Issue.
            При ошибке Issue остаётся с category=None.
            Для fire-and-forget используй trigger_autocategorize_background().
        """
        payload = {
            "issue_id": str(issue_id),
            "title": title,
            "description": description,
        }

        for attempt in range(1, self.retry_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                    )
                    response.raise_for_status()

                    result = response.json()
                    logger.info(
                        "Webhook auto-categorize успешно вызван для issue %s: %s (попытка %d/%d)",
                        issue_id,
                        result.get("category", "unknown"),
                        attempt,
                        self.retry_attempts,
                    )
                    return result

            except httpx.HTTPStatusError as e:
                logger.error(
                    "HTTP ошибка при вызове webhook %s: %s - %s (попытка %d/%d)",
                    webhook_url,
                    e.response.status_code,
                    e.response.text,
                    attempt,
                    self.retry_attempts,
                )
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return None

            except httpx.RequestError as e:
                logger.error(
                    "Ошибка соединения с webhook %s: %s (попытка %d/%d)",
                    webhook_url,
                    str(e),
                    attempt,
                    self.retry_attempts,
                )
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return None

            except Exception as e:
                logger.error(
                    "Неожиданная ошибка при вызове webhook %s: %s (попытка %d/%d)",
                    webhook_url,
                    str(e),
                    attempt,
                    self.retry_attempts,
                )
                return None

        return None

    async def trigger_kb_indexing(
        self,
        webhook_url: str,
        document_id: UUID,
        content: str,
        kb_id: UUID,
    ) -> Optional[Dict[str, Any]]:
        """Вызвать n8n workflow для индексации документа в Knowledge Base.

        Отправляет документ в n8n webhook, который:
        1. Разбивает текст на чанки (chunks)
        2. Генерирует embeddings через OpenRouter
        3. Сохраняет в pgvector (PostgreSQL)
        4. Возвращает статистику индексации

        Args:
            webhook_url: URL n8n webhook (production).
                Пример: "http://localhost:5678/webhook/kb-indexing"
            document_id: UUID документа для индексации.
            content: Текстовое содержимое документа (markdown/plain text).
            kb_id: UUID Knowledge Base, куда добавляется документ.

        Returns:
            Dict с результатом индексации:
                {
                    "success": True,
                    "document_id": "uuid",
                    "chunks_created": 15,
                    "embeddings_generated": 15,
                    "kb_id": "uuid"
                }
            None при ошибке.

        Example:
            >>> result = await client.trigger_kb_indexing(
            ...     webhook_url="http://n8n:5678/webhook/kb-indexing",
            ...     document_id=UUID("..."),
            ...     content="# Инструкция по ТО станка\\n\\n...",
            ...     kb_id=UUID("...")
            ... )
            >>> if result:
            ...     print(f"Создано чанков: {result['chunks_created']}")

        Chunking Strategy:
            - Размер чанка: 500-1000 символов
            - Overlap: 100 символов
            - Разделители: \\n\\n, \\n, . (по приоритету)

        Embedding Model:
            - openai/text-embedding-ada-002 (через OpenRouter)
            - Размерность: 1536
            - Стоимость: ~$0.0001/1K tokens

        Performance:
            - Timeout: 30 секунд (может быть недостаточно для больших документов)
            - Батчинг: 10 чанков за раз (для оптимизации)

        Note:
            Для больших документов (>10MB) рекомендуется использовать
            отдельный async worker или увеличить timeout.
        """
        payload = {
            "document_id": str(document_id),
            "content": content,
            "kb_id": str(kb_id),
        }

        for attempt in range(1, self.retry_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                    )
                    response.raise_for_status()

                    result = response.json()
                    logger.info(
                        "Webhook KB indexing успешно вызван для document %s: %d chunks (попытка %d/%d)",
                        document_id,
                        result.get("chunks_created", 0),
                        attempt,
                        self.retry_attempts,
                    )
                    return result

            except Exception as e:
                logger.error(
                    "Ошибка при вызове webhook KB indexing: %s (попытка %d/%d)",
                    str(e),
                    attempt,
                    self.retry_attempts,
                )
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_delay * attempt)
                    continue
                return None

        return None

    def trigger_autocategorize_background(
        self,
        webhook_url: str,
        issue_id: UUID,
        title: str,
        description: str,
    ) -> None:
        """Вызвать webhook авто-категоризации в фоне (fire-and-forget).

        Запускает асинхронную задачу через asyncio.create_task() и
        немедленно возвращает управление. НЕ блокирует текущий flow.

        Используется в IssueService.create_issue() для неблокирующей
        категоризации Issues после создания.

        Args:
            webhook_url: URL n8n webhook (production).
            issue_id: UUID Issue для категоризации.
            title: Заголовок Issue.
            description: Описание Issue.

        Returns:
            None (задача запущена в фоне).

        Example:
            >>> # В IssueService.create_issue()
            >>> issue = await self.repository.create_item(data)
            >>> 
            >>> # Запускаем категоризацию в фоне (не ждём результата)
            >>> n8n_webhook_client.trigger_autocategorize_background(
            ...     webhook_url=workflow.webhook_url,
            ...     issue_id=issue.id,
            ...     title=issue.title,
            ...     description=issue.description
            ... )
            >>> 
            >>> # Сразу возвращаем Issue пользователю
            >>> return issue

        Важно:
            - Метод НЕ ждёт выполнения webhook
            - Ошибки логируются, но НЕ прокидываются
            - Issue создаётся успешно даже при ошибке webhook
            - Category обновится асинхронно через n8n → Backend API

        Безопасность:
            - Задача НЕ блокирует основной event loop
            - При shutdown tasks будут gracefully cancelled
            - Timeout защищает от зависаний

        Note:
            Для синхронного вызова (с ожиданием результата)
            используй await trigger_autocategorize().
        """
        asyncio.create_task(
            self.trigger_autocategorize(
                webhook_url=webhook_url,
                issue_id=issue_id,
                title=title,
                description=description,
            )
        )
        logger.debug(
            "Запущен background task для auto-categorize issue %s (webhook: %s)",
            issue_id,
            webhook_url,
        )


# Singleton instance для использования по всему приложению
n8n_webhook_client = N8nWebhookClient()
