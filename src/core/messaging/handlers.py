
"""
Обработчики событий системы сообщений с использованием FastStream и RabbitMQ.

Модуль содержит все обработчики событий RabbitMQ для приложения:
    1. Обработка обратной связи (feedback)
    2. Отправка email-уведомлений
    3. Логирование и мониторинг событий

FastStream используется для автоматической обработки очередей внутри основного приложения FastAPI.
"""

import logging
from typing import Dict, Any
import time
from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue, RabbitExchange
from faststream.rabbit.fastapi import RabbitRouter
import aio_pika

from src.core.settings import settings
from src.repository.v1.feedback import FeedbackRepository
from src.services.v1.email import EmailService

logger = logging.getLogger(__name__)

# Создаем брокер с настройками из конфигурации
broker = RabbitBroker(
    settings.rabbitmq_url
)

app = FastStream(broker)

# Cоздаем маршрутизатор для обработки сообщений RabbitMQ
rabbit_router = RabbitRouter(
    settings.rabbitmq_url,
    reconnect_interval=5.0,
)

# Явно определяем exchange и очередь с настройками durable
exchange = RabbitExchange(
    name=settings.RABBITMQ_EXCHANGE,
    type=aio_pika.ExchangeType.DIRECT,
    durable=True
)

feedback_queue = RabbitQueue(
    name="feedback_requests",
    durable=True,
    routing_key="feedback_requests"
)


@rabbit_router.subscriber(feedback_queue, exchange=exchange)
async def process_feedback_request(message: Dict[str, Any]) -> None:
    """
    Обрабатывает новое сообщение об обратной связи из RabbitMQ.

    Args:
        message (Dict[str, Any]): Словарь сообщения, содержащий 'feedback_id' и 'action'.

    Последовательность действий:
        1. Извлечение метаинформации и логирование получения.
        2. Проверка и получение обратной связи из БД.
        3. Пропуск, если обратная связь уже обработана.
        4. Отправка уведомления администратору (если не отправлено).
        5. Отправка подтверждения клиенту (если не отправлено).
        6. Пометка обратной связи как обработанной и логирование времени обработки.

    Raises:
        Exception: Любая ошибка в процессе обработки будет залогирована и вызовет повторную доставку сообщения.
    """
    start = time.time()
    meta, redelivered, message_id = extract_meta(message)
    logger.info("📩 Получено сообщение обратной связи для обработки: %s", message)
    logger.debug("    -> мета=%s, повторная_доставка=%s, id_сообщения=%s", meta, redelivered, message_id)

    try:
        feedback_id = message.get("feedback_id")
        action = message.get("action", "process_feedback")

        if not feedback_id:
            logger.error("❌ Отсутствует feedback_id в сообщении")
            return

        feedback = await get_feedback(feedback_id)
        if not feedback:
            logger.error("❌ Обратная связь с ID %s не найдена", feedback_id)
            return

        if is_feedback_notifications_already_sent(feedback):
            logger.info("ℹ️ Уведомления для обратной связи %s уже отправлены, пропускаем", feedback_id)
            return

        logger.info("🚀 Начинаем процесс уведомлений для обратной связи %s", feedback_id)
        email_service = EmailService(timeout=10)

        logger.info("📧 Шаг 1: Уведомление администратора для обратной связи %s", feedback_id)
        await notify_admin_about_feedback(email_service, feedback, feedback_id)

        logger.info("📧 Шаг 2: Уведомление клиента для обратной связи %s", feedback_id)
        await notify_client_about_feedback(email_service, feedback, feedback_id)

        logger.info("🏁 Шаг 3: Отмечаем время отправки уведомлений для обратной связи %s (статус остается PENDING)", feedback_id)
        await mark_feedback_notifications_sent(feedback_id)

        logger.info("Обратная связь %s обработана за %.2f секунд", feedback_id, time.time() - start)

    except Exception as e:
        logger.error("❌ Ошибка при обработке обратной связи: %s", e, exc_info=True)
        raise

def extract_meta(message: Dict[str, Any]):
    """
    Извлекает метаинформацию из сообщения для логирования и диагностики.

    Args:
        message (Dict[str, Any]): Входящее сообщение RabbitMQ.

    Returns:
        Tuple: (meta, redelivered, message_id)
    """
    try:
        meta = message.get("_meta") or message.get("__meta__") or message.get("headers")
        redelivered = bool(message.get("redelivered") or message.get("redelivery") or message.get("redelivered_flag"))
        message_id = message.get("message_id") or (meta and meta.get("message_id")) or (meta and meta.get("message-id"))
        if not message_id and isinstance(meta, dict):
            message_id = meta.get("message_id") or meta.get("message-id") or (meta.get("headers") and meta.get("headers").get("message_id"))
        return meta, redelivered, message_id
    except Exception:
        return None, False, None


async def get_feedback(feedback_id: str):
    """
    Получает обратную связь из базы данных по её ID.

    Args:
        feedback_id (str): Идентификатор обратной связи.

    Returns:
        FeedbackModel или None: Объект обратной связи или None, если не найдено.
    """
    import uuid
    from sqlalchemy import select
    from src.core.connections.database import get_db_session
    from src.models.v1.feedback import FeedbackModel

    async for db in get_db_session():
        repository = FeedbackRepository(db)
        try:
            feedback_uuid = uuid.UUID(feedback_id)
            statement = select(FeedbackModel).where(FeedbackModel.id == feedback_uuid)
            feedback = await repository.get_one(statement)
            return feedback
        except Exception as e:
            logger.warning("Не удалось получить обратную связь %s: %s", feedback_id, e)
            return None


def is_feedback_notifications_already_sent(feedback) -> bool:
    """
    Проверяет, отправлены ли уже уведомления для обратной связи.
    Проверяет флаги admin_notified и client_notified, а также processed_at.

    Args:
        feedback: Объект обратной связи.

    Returns:
        bool: True, если уведомления уже отправлены, иначе False.
    """
    try:
        admin_notified = bool(getattr(feedback, "admin_notified", False))
        client_notified = bool(getattr(feedback, "client_notified", False))
        processed_at = getattr(feedback, "processed_at", None)

        # Считаем уведомления отправленными, если есть оба флага или есть время обработки
        return (admin_notified and client_notified) or processed_at is not None
    except Exception:
        return False


async def notify_admin_about_feedback(email_service, feedback, feedback_id: str):
    """
    Отправляет уведомление администратору об обратной связи, если оно ещё не было отправлено.

    Args:
        email_service (EmailService): Экземпляр сервиса email.
        feedback: Объект обратной связи.
        feedback_id (str): Идентификатор обратной связи.
    """
    try:
        admin_already = bool(getattr(feedback, "admin_notified", False))
        logger.info("📋 Проверка статуса уведомления администратора: feedback_id=%s, admin_notified=%s", feedback_id, admin_already)
    except Exception as e:
        admin_already = False
        logger.warning("⚠️ Ошибка при проверке статуса admin_notified: %s", e)

    if admin_already:
        logger.info("ℹ️ Администратор уже уведомлен для обратной связи %s, пропускаем", feedback_id)
        return

    logger.info("📧 Отправляем уведомление администратору для обратной связи %s...", feedback_id)
    admin_sent = await email_service.send_admin_notification(feedback)
    if admin_sent:
        logger.info("✅ Уведомление администратору отправлено для обратной связи %s", feedback_id)
        logger.info("🔄 Обновляем флаг admin_notified для обратной связи %s...", feedback_id)
        await update_feedback_flag(feedback_id, "admin_notified")
    else:
        logger.warning("⚠️ Не удалось отправить уведомление администратору для обратной связи %s", feedback_id)


async def notify_client_about_feedback(email_service, feedback, feedback_id: str):
    """
    Отправляет подтверждение клиенту об обратной связи, если оно ещё не было отправлено.

    Args:
        email_service (EmailService): Экземпляр сервиса email.
        feedback: Объект обратной связи.
        feedback_id (str): Идентификатор обратной связи.
    """
    try:
        client_already = bool(getattr(feedback, "client_notified", False))
        logger.info("📋 Проверка статуса уведомления клиента: feedback_id=%s, client_notified=%s", feedback_id, client_already)
    except Exception as e:
        client_already = False
        logger.warning("⚠️ Ошибка при проверке статуса client_notified: %s", e)

    if client_already:
        logger.info("ℹ️ Клиент уже уведомлен для обратной связи %s, пропускаем", feedback_id)
        return

    logger.info("📧 Отправляем подтверждение клиенту для обратной связи %s...", feedback_id)
    client_sent = await email_service.send_client_confirmation(feedback)
    if client_sent:
        logger.info("✅ Подтверждение клиенту отправлено для обратной связи %s", feedback_id)
        logger.info("🔄 Обновляем флаг client_notified для обратной связи %s...", feedback_id)
        await update_feedback_flag(feedback_id, "client_notified")
    else:
        logger.warning("⚠️ Не удалось отправить подтверждение клиенту для обратной связи %s", feedback_id)


async def update_feedback_flag(feedback_id: str, flag: str):
    """
    Обновляет флаг уведомления в базе данных для обратной связи.

    Args:
        feedback_id (str): Идентификатор обратной связи.
        flag (str): Флаг для обновления (например, 'admin_notified', 'client_notified').
    """
    import uuid
    from sqlalchemy import select
    from src.core.connections.database import get_db_session
    from src.models.v1.feedback import FeedbackModel

    logger.info("🔄 Начинаем обновление флага: feedback_id=%s, flag=%s", feedback_id, flag)

    async for db in get_db_session():
        repository = FeedbackRepository(db)
        try:
            feedback_uuid = uuid.UUID(feedback_id)
            logger.debug("🔍 Конвертировано в UUID: %s", feedback_uuid)

            statement = select(FeedbackModel).where(FeedbackModel.id == feedback_uuid)
            feedback = await repository.get_one(statement)

            if feedback:
                logger.info("✅ Обратная связь найдена: %s", feedback_id)
                await repository.update_some(feedback, {flag: True})
                logger.info("✅ Флаг %s успешно установлен в True для обратной связи %s", flag, feedback_id)
            else:
                logger.error("❌ Обратная связь %s не найдена для обновления флага", feedback_id)
        except Exception as e:
            logger.error("❌ Не удалось обновить %s для обратной связи %s: %s", flag, feedback_id, e)
        break

async def mark_feedback_notifications_sent(feedback_id: str):
    """
    Отмечает время обработки уведомлений для обратной связи.
    Статус остается PENDING - изменения статуса (PROCESSING/COMPLETED/DELETED) выполняет только администратор вручную.

    Args:
        feedback_id (str): Идентификатор обратной связи.
    """
    import uuid
    from datetime import datetime, timezone
    from sqlalchemy import select
    from src.core.connections.database import get_db_session
    from src.models.v1.feedback import FeedbackModel

    logger.info("🏁 Начинаем отметку времени отправки уведомлений для обратной связи %s", feedback_id)

    async for db in get_db_session():
        repository = FeedbackRepository(db)
        try:
            feedback_uuid = uuid.UUID(feedback_id)
            statement = select(FeedbackModel).where(FeedbackModel.id == feedback_uuid)
            feedback = await repository.get_one(statement)

            if feedback:
                processed_time = datetime.now(timezone.utc)
                logger.info("✅ Обратная связь найдена, отмечаем время отправки уведомлений: %s", processed_time)

                # Статус остается PENDING, только обновляем время обработки
                await repository.update_some(feedback, {
                    "processed_at": processed_time
                })
                logger.info("✅ Время отправки уведомлений для обратной связи %s обновлено: %s (статус остается PENDING)", feedback_id, processed_time)
            else:
                logger.error("❌ Обратная связь %s не найдена для отметки времени уведомлений", feedback_id)
        except Exception as e:
            logger.error("❌ Не удалось обновить время уведомлений для обратной связи %s: %s", feedback_id, e)
        break

# Хуки жизненного цикла FastStream (опционально)
@app.on_startup
async def setup_logging():
    """
    Инициализация логирования для обработчиков FastStream.

    Returns:
        None
    """
    logger.info("🚀 Обработчики FastStream инициализированы")

@app.on_shutdown
async def cleanup():
    """
    Очистка ресурсов при завершении работы FastStream.

    Returns:
        None
    """
    logger.info("🔄 Обработчики FastStream завершают работу")
