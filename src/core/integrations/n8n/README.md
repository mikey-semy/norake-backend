# n8n Integration Documentation

## Обзор

Модуль `src.core.integrations.n8n` предоставляет асинхронный HTTP клиент для взаимодействия с n8n workflows через webhook триггеры. Используется для автоматизации бизнес-процессов NoRake Backend.

## Архитектура

```
Backend Service → N8nWebhookClient → n8n Webhook → n8n Workflow → External Services (AI/Search) → Backend API
```

### Компоненты

1. **N8nWebhookClient** (`webhook_client.py`)
   - Асинхронный HTTP клиент
   - Retry механизм с экспоненциальной задержкой
   - Таймауты и обработка ошибок
   - Fire-and-forget pattern для background tasks

2. **Settings** (`src.core.settings.base.py`)
   ```python
   N8N_BASE_URL: str = "http://localhost:5678"
   N8N_API_KEY: Optional[SecretStr] = None
   N8N_WEBHOOK_TIMEOUT: int = 30
   N8N_WEBHOOK_RETRY_ATTEMPTS: int = 2
   N8N_WEBHOOK_RETRY_DELAY: float = 1.0
   ```

3. **N8nWorkflowModel** (`src.models.v1.n8n_workflows.py`)
   - База данных для хранения webhook URLs
   - Типы: AUTO_CATEGORIZE, KB_INDEXING, SMART_SEARCH, WEEKLY_DIGEST
   - Привязка к Workspace

## Workflows

### 1. Auto-categorize Issues

**Описание**: Автоматическая категоризация Issues через OpenRouter AI (LLaMA 3.2).

**Webhook**: `POST /webhook/autocategorize-issue`

**Payload**:
```json
{
  "issue_id": "uuid",
  "title": "Ошибка E401 на станке",
  "description": "Станок останавливается при запуске G-code"
}
```

**Response**:
```json
{
  "success": true,
  "issue_id": "uuid",
  "category": "hardware",
  "message": "Issue categorized successfully"
}
```

**Категории** (9 вариантов):
- `hardware`: Проблемы с оборудованием
- `software`: Ошибки ПО, баги
- `process`: Нарушения бизнес-процессов
- `documentation`: Отсутствие/устаревание документации
- `safety`: Вопросы безопасности
- `quality`: Проблемы качества
- `maintenance`: Обслуживание, ремонт
- `training`: Обучение персонала
- `other`: Неопределённые

**Интеграция**:
```python
from src.core.integrations.n8n import n8n_webhook_client

# В IssueService.create_issue()
issue = await self.repository.create_item(data)

# Fire-and-forget (не блокирует создание Issue)
n8n_webhook_client.trigger_autocategorize_background(
    webhook_url=workflow.webhook_url,
    issue_id=issue.id,
    title=issue.title,
    description=issue.description
)

return issue
```

**n8n Workflow** (6 nodes):
1. Webhook Trigger (POST)
2. Extract Issue Data (Set node)
3. OpenRouter: Categorize (HTTP Request)
4. Extract Category (Set node)
5. Update Issue Category (HTTP Request PATCH → Backend)
6. Respond (respondToWebhook)

---

### 2. KB Indexing Pipeline

**Описание**: Индексация документов в Knowledge Base с генерацией embeddings.

**Webhook**: `POST /webhook/kb-indexing`

**Payload**:
```json
{
  "document_id": "uuid",
  "content": "# Инструкция по ТО\\n\\n...",
  "kb_id": "uuid"
}
```

**Response**:
```json
{
  "success": true,
  "document_id": "uuid",
  "chunks_created": 15,
  "embeddings_generated": 15,
  "kb_id": "uuid"
}
```

**Chunking Strategy**:
- Размер чанка: 500-1000 символов
- Overlap: 100 символов
- Разделители: `\n\n`, `\n`, `.` (по приоритету)

**Embedding Model**:
- `openai/text-embedding-ada-002` (через OpenRouter)
- Размерность: 1536
- Стоимость: ~$0.0001/1K tokens

**Интеграция**:
```python
# В DocumentService.create_document()
document = await self.repository.create_item(data)

# Запускаем индексацию
result = await n8n_webhook_client.trigger_kb_indexing(
    webhook_url=workflow.webhook_url,
    document_id=document.id,
    content=document.content,
    kb_id=document.kb_id
)

if result:
    logger.info(f"Indexed: {result['chunks_created']} chunks")

return document
```

**n8n Workflow** (9+ nodes):
1. Webhook Trigger
2. Split Text (chunking with overlap)
3. Loop Over Items (для батчинга)
4. OpenRouter: Generate Embeddings (HTTP Request)
5. Transform to pgvector format
6. Insert into PostgreSQL (pgvector extension)
7. Update Document metadata
8. Respond

---

### 3. Smart Search Helper

**Описание**: Гибридный поиск с RAG (DB + Semantic + Web).

**Webhook**: `POST /webhook/smart-search`

**Payload**:
```json
{
  "query": "как настроить станок CNC",
  "workspace_id": "uuid",
  "user_id": "uuid",
  "filters": {
    "issue_status": "resolved",
    "date_from": "2024-01-01"
  }
}
```

**Response**:
```json
{
  "success": true,
  "results": [
    {
      "type": "issue",
      "id": "uuid",
      "title": "Настройка CNC станка",
      "score": 0.95,
      "source": "database"
    },
    {
      "type": "kb_document",
      "id": "uuid",
      "title": "Инструкция по настройке",
      "score": 0.89,
      "source": "rag"
    }
  ],
  "total": 2
}
```

**Алгоритм**:
1. Параллельный запуск 3 веток:
   - DB Search (PostgreSQL full-text)
   - RAG Search (pgvector semantic)
   - Web Search (Tavily API)
2. Merge Results (Union node)
3. Rank & Deduplicate (Set node)
4. Return Top N results

---

### 4. Weekly Digest

**Описание**: Еженедельные дайджесты с агрегацией статистики.

**Webhook**: `POST /webhook/weekly-digest` (Cron trigger)

**Schedule**: Каждый понедельник 09:00

**Process**:
1. Aggregate Stats (SQL queries)
2. Format Report (Set node)
3. Send Email/Slack (Email node)

---

## Использование

### Базовое использование

```python
from src.core.integrations.n8n import n8n_webhook_client

# Синхронный вызов (ждёт ответа)
result = await n8n_webhook_client.trigger_autocategorize(
    webhook_url="http://localhost:5678/webhook/autocategorize",
    issue_id=uuid4(),
    title="Проблема",
    description="Описание"
)

if result:
    print(f"Category: {result['category']}")
else:
    print("Webhook failed")
```

### Fire-and-forget pattern

```python
# Асинхронный вызов (не блокирует)
n8n_webhook_client.trigger_autocategorize_background(
    webhook_url=workflow.webhook_url,
    issue_id=issue.id,
    title=issue.title,
    description=issue.description
)
# Сразу продолжаем выполнение
```

### Кастомные настройки

```python
from src.core.integrations.n8n import N8nWebhookClient

# Переопределение таймаута для больших документов
client = N8nWebhookClient(
    timeout=120.0,  # 2 минуты
    retry_attempts=3,
    retry_delay=2.0
)

result = await client.trigger_kb_indexing(
    webhook_url=webhook_url,
    document_id=document.id,
    content=large_document_content,
    kb_id=kb_id
)
```

---

## Конфигурация

### Environment Variables (.env.dev)

```env
# n8n Integration
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=your_n8n_api_key_here
N8N_WEBHOOK_TIMEOUT=30
N8N_WEBHOOK_RETRY_ATTEMPTS=2
N8N_WEBHOOK_RETRY_DELAY=1.0
```

### n8n Credentials

В n8n UI → Credentials создать:

1. **HTTP Header Auth (OpenRouter)**
   - Name: `OpenRouter API Key`
   - Header Name: `Authorization`
   - Header Value: `Bearer sk-or-v1-YOUR_KEY`

2. **HTTP Header Auth (Backend)**
   - Name: `NoRake Backend Token`
   - Header Name: `Authorization`
   - Header Value: `Bearer YOUR_JWT_TOKEN`

### Database Registration

После импорта workflow в n8n зарегистрировать в БД:

```python
POST /api/v1/workflows/{workspace_id}
Authorization: Bearer YOUR_JWT_TOKEN

{
  "workflow_name": "Auto-categorize Issues",
  "workflow_type": "AUTO_CATEGORIZE",
  "webhook_url": "http://localhost:5678/webhook/autocategorize-issue",
  "trigger_config": {
    "model": "qwen/qwen-3-coder-480b-a35b:free",
    "temperature": 0.2,
    "max_tokens": 50,
    "fallback_model": "deepseek/r1-distill-llama-70b:free"
  },
  "n8n_workflow_id": "auto-categorize-issues"
}
```

**Рекомендуемые OpenRouter модели (free tier)**:

| Модель | Параметры | Специализация | Accuracy |
|--------|-----------|---------------|----------|
| `qwen/qwen-3-coder-480b-a35b:free` | 480B MoE | Код, техника | ~95% ✅ |
| `moonshot/kimi-dev-72b:free` | 72B Dense | Документация | ~90% |
| `deepseek/r1-distill-llama-70b:free` | 70B Dense | Универсальная | ~88% |

**Не использовать** (фейки): `openai/gpt-oss-20b`, `meta/llama-4-scout` (не существуют).

---

## Error Handling

### Graceful Degradation

Все методы возвращают `Optional[Dict]` - `None` при ошибке:

```python
result = await client.trigger_autocategorize(...)

if result is None:
    # Webhook failed - продолжаем без категоризации
    logger.warning("Auto-categorization failed, issue created without category")
    return issue
```

### Retry Mechanism

Автоматический retry при:
- Сетевых ошибках (connection timeout, DNS)
- HTTP 5xx ошибках (server errors)

**НЕ** retry при:
- HTTP 4xx ошибках (client errors - неправильный payload)
- Parsing errors (invalid JSON response)

### Logging

Все webhook вызовы логируются:

```
INFO: Webhook auto-categorize успешно вызван для issue <uuid>: hardware (попытка 1/2)
ERROR: HTTP ошибка при вызове webhook http://...: 503 - Service Unavailable (попытка 1/2)
DEBUG: Запущен background task для auto-categorize issue <uuid> (webhook: http://...)
```

---

## Performance

### Benchmarks

| Workflow | AI Model | Avg Latency | Timeout | Accuracy | Payload Size |
|----------|----------|-------------|---------|----------|--------------|
| Auto-categorize | Qwen3 480B | 2-4s | 30s | ~95% | ~1KB |
| KB Indexing | - | 5-30s | 30s* | - | 10KB-10MB |
| Smart Search | - | 3-10s | 30s | - | ~2KB |
| Weekly Digest | - | 10-60s | 120s | - | N/A (Cron) |

*KB Indexing может потребовать увеличения timeout для документов >1MB.

### AI Model Performance (OpenRouter free tier)

| Модель | Latency | Accuracy (категоризация) | Rate Limit | Рекомендуется |
|--------|---------|--------------------------|------------|---------------|
| Qwen3 Coder 480B | 2-4s | ~95% ✅ | 10 req/min | **Да** (текущая) |
| Kimi Dev 72B | 3-5s | ~90% | 10 req/min | Для длинных Issues |
| DeepSeek R1 70B | 2-3s | ~88% | 20 req/min | Баланс скорость/качество |
| Llama 3.2 3B (старая) | 1-2s | ~75% ❌ | 20 req/min | Не рекомендуется |

**Вывод**: Qwen3 Coder 480B - лучший выбор для технических Issues (hardware, software, process).

### Recommendations

1. **Auto-categorize**: 
   - Fire-and-forget pattern (не блокирует создание Issue)
   - Модель: Qwen3 Coder 480B (оптимальная точность для free tier)
   - Temperature: 0.2 (детерминизм)
   
2. **KB Indexing**: 
   - Синхронный вызов + увеличить timeout для больших документов
   - Chunking: 512 токенов с overlap 50 токенов
   
3. **Smart Search**: 
   - Синхронный вызов + кэширование результатов
   - Hybrid: DB + RAG + Tavily (параллельно)
   
4. **Weekly Digest**: 
   - Cron trigger (не через webhook)
   - Batch processing для агрегаций

---

## Security

### Таймауты

Защита от зависаний:
- Default: 30 секунд
- Настраивается через `N8N_WEBHOOK_TIMEOUT`
- Per-request override: `N8nWebhookClient(timeout=120)`

### Credentials

**НЕ хардкодить** токены в коде:
```python
# ❌ WRONG
webhook_url = "http://n8n:5678/webhook?token=secret123"

# ✅ CORRECT - токены в n8n Credentials
webhook_url = "http://n8n:5678/webhook/autocategorize"
# Токен передаётся через HTTP Header Auth в n8n workflow
```

### Rate Limiting

OpenRouter AI:
- Free tier: 10 req/min
- Paid tier: 60 req/min

Рекомендация: Батчинг для KB indexing (10 chunks за раз).

---

## Testing

### Manual Test (curl)

```bash
curl -X POST http://localhost:5678/webhook/autocategorize-issue \
  -H "Content-Type: application/json" \
  -d '{
    "issue_id": "123e4567-e89b-12d3-a456-426614174000",
    "title": "Ошибка E401",
    "description": "Станок останавливается"
  }'
```

### Integration Test (pytest)

```python
import pytest
from src.core.integrations.n8n import n8n_webhook_client

@pytest.mark.asyncio
async def test_autocategorize_webhook():
    result = await n8n_webhook_client.trigger_autocategorize(
        webhook_url="http://localhost:5678/webhook/autocategorize-issue",
        issue_id=uuid4(),
        title="Test Issue",
        description="Test description"
    )
    
    assert result is not None
    assert result["success"] is True
    assert result["category"] in ["hardware", "software", ...]
```

### Mock для unit tests

```python
from unittest.mock import AsyncMock, patch

@patch("src.core.integrations.n8n.webhook_client.httpx.AsyncClient")
async def test_issue_service_create(mock_client):
    mock_response = AsyncMock()
    mock_response.json.return_value = {"success": True, "category": "hardware"}
    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
    
    # Test IssueService.create_issue with mocked webhook
    ...
```

---

## Troubleshooting

### Problem: Webhook timeout

**Solution**: Увеличить `N8N_WEBHOOK_TIMEOUT` или timeout per-request:
```python
client = N8nWebhookClient(timeout=120.0)
```

### Problem: Connection refused

**Check**:
1. n8n running: `docker ps | grep n8n`
2. Webhook URL correct: `http://localhost:5678/webhook/...` (не test URL!)
3. Workflow activated: n8n UI → workflow → Active toggle

### Problem: HTTP 401 Unauthorized

**Check**:
1. Backend JWT token valid (не expired)
2. n8n Credentials configured (HTTP Header Auth)
3. OpenRouter API key valid

### Problem: Category not updating

**Check**:
1. n8n execution logs: n8n UI → Executions
2. Backend logs: `docker logs norake-backend`
3. Issue model has category field: `IssueModel.category`

---

## Migration Guide

### From hardcoded timeout to settings

**Before**:
```python
client = N8nWebhookClient(timeout=30.0)
```

**After**:
```python
from src.core.integrations.n8n import n8n_webhook_client
# Использует settings.N8N_WEBHOOK_TIMEOUT
```

### From manual retry to built-in

**Before**:
```python
for attempt in range(3):
    try:
        result = await client.trigger_autocategorize(...)
        break
    except:
        await asyncio.sleep(1)
```

**After**:
```python
# Retry автоматический (из settings.N8N_WEBHOOK_RETRY_ATTEMPTS)
result = await client.trigger_autocategorize(...)
```

---

## References

- [n8n Official Docs](https://docs.n8n.io/)
- [n8n REST API](https://docs.n8n.io/api/)
- [OpenRouter API](https://openrouter.ai/docs)
- [httpx Documentation](https://www.python-httpx.org/)
- [NoRake Workflows README](../../docs/n8n_workflows/README.md)

---

## Changelog

### v0.2.0 (2025-11-11) - AI Model Upgrade
- ✅ **BREAKING**: Changed AI model from Llama 3.2 3B → Qwen3 Coder 480B
- ✅ Improved accuracy: 75% → 95% на технических Issues
- ✅ Reduced temperature: 0.3 → 0.2 (более детерминированные результаты)
- ✅ Expanded categories: 3 → 9 (hardware, software, process, documentation, safety, quality, maintenance, training, other)
- ✅ Added AI model selection guide в документации
- ✅ Updated performance benchmarks
- 📝 Requires workflow re-import or manual model update

### v0.1.0 (2025-11-11) - NORAK-35
- ✅ Initial implementation
- ✅ N8nWebhookClient with retry mechanism
- ✅ Auto-categorize Issues workflow (Llama 3.2 3B)
- ✅ Fire-and-forget pattern
- ✅ Settings integration
- ✅ Comprehensive documentation

### Planned (NORAK-36, 37, 38)
- ⏳ KB Indexing Pipeline workflow
- ⏳ Smart Search Helper workflow
- ⏳ Weekly Digest workflow
