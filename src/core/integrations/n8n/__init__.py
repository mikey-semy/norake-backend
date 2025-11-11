"""n8n интеграции для NoRake Backend.

Модуль содержит клиенты и утилиты для работы с n8n workflows:
- Вызов webhooks для автоматизации
- Управление workflow executions
- Интеграция с Backend API
"""

from src.core.integrations.n8n.webhook_client import (
    N8nWebhookClient,
    n8n_webhook_client,
)

__all__ = [
    "N8nWebhookClient",
    "n8n_webhook_client",
]
