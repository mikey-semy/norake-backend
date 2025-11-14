# Исправление ошибки SignatureDoesNotMatch с Yandex Cloud Storage

## Проблема

При загрузке файлов в Yandex Cloud Storage возникала ошибка:
```
SignatureDoesNotMatch: The request signature we calculated does not match the signature you provided.
Check your key and signing method.
```

## Причина

Неправильная конфигурация S3 клиента в `src/core/connections/storage.py`:
1. Отсутствовал `signature_version='s3v4'` в BotocoreConfig
2. Использовался `addressing_style="virtual"` вместо `"auto"`

## Решение

### 1. Обновлена конфигурация S3 клиента

**Файл**: `src/core/connections/storage.py`

```python
# Было:
s3_config = BotocoreConfig(s3={"addressing_style": "virtual"})

# Стало:
s3_config = BotocoreConfig(
    signature_version='s3v4',
    s3={"addressing_style": "auto"}
)
```

**Почему это работает**:
- `signature_version='s3v4'` - указывает использовать AWS Signature Version 4 (обязательно для Yandex Cloud)
- `addressing_style="auto"` - автоматически определяет правильный стиль адресации на основе endpoint

### 2. Обновлена документация в .env.example

Добавлен пример конфигурации для Yandex Cloud:

```bash
# Для Yandex Cloud Storage:
AWS_ENDPOINT=https://storage.yandexcloud.net
AWS_REGION=ru-central1
AWS_ACCESS_KEY_ID=YCAJExxxxxxxxxx
AWS_SECRET_ACCESS_KEY=YCxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_BUCKET_NAME=equiply.data
```

### 3. Удалён неиспользуемый параметр

Параметр `AWS_ADDRESSING_STYLE` из settings.py больше не используется, т.к. стиль адресации
определяется автоматически через `signature_version='s3v4'` в клиенте.

## Ссылки на документацию

- [aiobotocore Configuration](https://github.com/aio-libs/aiobotocore)
- [AWS Signature Version 4](https://docs.aws.amazon.com/general/latest/gr/signature-version-4.html)
- [Yandex Cloud S3 API](https://cloud.yandex.ru/docs/storage/s3/)

## Тестирование

После изменений необходимо:
1. Перезапустить backend: `docker compose -f docker-compose.dev.yml restart backend` или `uv run dev`
2. Проверить загрузку документов через API `/api/v1/documents/upload`
3. Убедиться, что файлы загружаются без ошибок подписи

## Дата исправления

14 ноября 2025

## Автор

GitHub Copilot (Claude Sonnet 4.5) + Context7 MCP для документации aiobotocore
