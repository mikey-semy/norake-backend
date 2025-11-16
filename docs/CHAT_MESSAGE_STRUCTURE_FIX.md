# Исправление структуры сообщений в AI чатах

## Проблема

Frontend получал `Invalid Date` при парсинге timestamp из сообщений чата.

**Причина**: Несоответствие структуры данных между backend и frontend:
- Backend сохранял timestamp внутри `metadata`
- Frontend ожидал timestamp как отдельное поле верхнего уровня
- Schema `ChatMessageSchema` определяла правильную структуру, но service её не следовал

## Решение

### 1. Исправлена структура сообщений (BREAKING CHANGE)

**Было** (неправильно):
```json
{
  "role": "assistant",
  "content": "Текст ответа",
  "metadata": {
    "timestamp": "2025-11-16T06:00:00Z",
    "model": "qwen_coder",
    "tokens_used": 150,
    "rag_chunks_used": 3
  }
}
```

**Стало** (правильно):
```json
{
  "role": "assistant",
  "content": "Текст ответа",
  "message_metadata": {
    "model": "qwen_coder",
    "tokens_used": 150,
    "rag_chunks_used": 3
  },
  "timestamp": "2025-11-16T06:00:00Z"
}
```

### 2. Изменённые файлы

**src/services/v1/ai_chat.py** (строки 321-336):
- `user_message`: timestamp вынесен из metadata на верхний уровень
- `assistant_message`: timestamp вынесен из metadata, metadata → message_metadata

**src/routers/v1/chat.py** (строки 470-486):
- `MessageResponseSchema`: использует timestamp из `ai_response["timestamp"]`
- Исправлен доступ к tokens_used через `message_metadata`

**src/models/v1/ai_chats.py** (строка 118):
- Обновлён комментарий: `'metadata'` → `'message_metadata'`

### 3. Миграция базы данных

**Файл**: `src/core/migrations/versions/adc2a64b76cb_update_ai_chats_messages_comment.py`

```sql
COMMENT ON COLUMN ai_chats.messages IS
'История сообщений в формате [{"role": str, "content": str, "message_metadata": dict, "timestamp": str}]'
```

**Применение**:
```bash
uv run migrate
```

### 4. Скрипт миграции данных

**Файл**: `scripts/migrate_chat_messages_structure.py`

Преобразует существующие сообщения из старого формата в новый:
- Извлекает `timestamp` из `metadata`
- Переименовывает `metadata` → `message_metadata`
- Обрабатывает edge cases (отсутствующие поля)

**Запуск**:
```bash
uv run python scripts/migrate_chat_messages_structure.py
```

## Затронутые API endpoints

- **POST /api/v1/chat/{chat_id}/message** - возвращает новую структуру
- **GET /api/v1/chat/{chat_id}** - возвращает messages с новой структурой

## Frontend изменения

Frontend уже ожидал правильную структуру (`timestamp` на верхнем уровне), поэтому изменения не требуются.

**Проверка**:
```typescript
// chatStore.ts правильно мапит:
...msg  // Spread оператор копирует все поля включая timestamp

// MessageList.tsx правильно использует:
{new Date(message.timestamp).toLocaleString('ru-RU')}
```

## Обратная совместимость

⚠️ **BREAKING CHANGE** для клиентов использующих старую структуру.

**Если у вас есть старые сообщения в БД**:
1. Запустите `uv run python scripts/migrate_chat_messages_structure.py`
2. Обновите клиентский код для использования `message_metadata` вместо `metadata`

## Проверка исправления

1. Запустите backend: `uv run dev`
2. Откройте frontend: `http://localhost:3000`
3. Создайте чат и отправьте сообщение
4. Проверьте console.log в браузере:
   - `📅 Message timestamp:` должен показывать ISO строку
   - Дата должна отображаться корректно (не "Invalid Date")

## Связанные файлы

- **Schemas**: `src/schemas/v1/chat/base.py` (ChatMessageSchema)
- **Service**: `src/services/v1/ai_chat.py` (send_message)
- **Router**: `src/routers/v1/chat.py` (send_message endpoint)
- **Model**: `src/models/v1/ai_chats.py` (AIChatModel)
- **Migration**: `src/core/migrations/versions/adc2a64b76cb_*`
- **Data migration script**: `scripts/migrate_chat_messages_structure.py`

## Дополнительно

- Timestamp использует ISO 8601 формат с 'Z' суффиксом: `datetime.utcnow().isoformat() + "Z"`
- JavaScript правильно парсит: `new Date("2025-11-16T06:00:00Z")`
- Проверено соответствие Pydantic схем и ORM моделей
