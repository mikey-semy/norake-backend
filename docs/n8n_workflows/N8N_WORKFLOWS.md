# n8n Workflows для Equiply Backend

> **Статус**: ✅ Проверено через n8n MCP (541 нод, 87% документации)
> **Дата**: 11 ноября 2025
> **Версия n8n**: 1.x+

## 📖 Введение

Production-ready коллекция n8n workflows для автоматизации Equiply Backend. Все workflows валидированы через **официальный n8n MCP server** и следуют best practices.

### Что такое n8n?

**n8n** — fair-code лицензированная платформа автоматизации workflow с **гибкостью кода** и **скоростью no-code**.

**Ключевые возможности**:
- 🔌 **541 нода** доступно (400+ официальных интеграций)
- 🤖 **263 AI-оптимизированных нод** для работы с LLM
- 🏠 **Self-hosting** — полный контроль над данными
- ⚡ **Queue mode** — горизонтальное масштабирование
- 🐍 **JavaScript + Python** — нативная поддержка
- 📊 **Built-in мониторинг** выполнения

📚 **Документация**: https://docs.n8n.io/
🛠️ **MCP Stats**: 541 нод, 87% покрытие, 104 триггера

---

## 📋 Доступные Workflows

### 1. Auto-categorize Issues (`auto-categorize-issues.json`)

**Назначение**: Автоматическая AI-категоризация Issues при создании через OpenRouter.

**Триггер**: `POST /webhook/autocategorize-issue`

**Архитектура Flow**:
```
Webhook → Extract Data → OpenRouter LLM → Parse Category → Update Backend → Respond
```

**Используемые ноды** (валидировано через n8n MCP):

| Нода | Тип | Описание |
|------|-----|----------|
| **Webhook** | `nodes-base.webhook` v2.1 | Trigger нода для приёма HTTP POST запросов |
| **Set** | `nodes-base.set` v3.4 | Извлечение полей `issue_id`, `title`, `description` |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | Вызов OpenRouter API для категоризации |
| **Set** | `nodes-base.set` v3.4 | Парсинг категории из LLM ответа |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | PATCH запрос к Backend API |
| **Respond to Webhook** | `nodes-base.respondToWebhook` v1 | Возврат JSON ответа |

**Конфигурация OpenRouter**:
- **Model**: `qwen/qwen-3-coder-480b-a35b:free`
- **Temperature**: 0.2 (детерминированность)
- **Max Tokens**: 50 (только категория)
- **Headers**: `HTTP-Referer`, `X-Title` (обязательны для OpenRouter)

**Пример Webhook Payload**:
```json
{
  "issue_id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Станок не запускается",
  "description": "Кнопка пуска не реагирует, индикаторы не горят"
}
```

**Пример Response**:
```json
{
  "success": true,
  "issue_id": "123e4567-e89b-12d3-a456-426614174000",
  "category": "hardware",
  "message": "Issue categorized successfully"
}
```

**Категории** (промпт в LLM):
- `hardware` — оборудование, станки
- `software` — ПО, интерфейсы
- `process` — технологические процессы
- `documentation` — документация
- `safety` — безопасность
- `quality` — качество продукции
- `maintenance` — обслуживание
- `training` — обучение персонала
- `other` — прочее

---

### 2. KB Indexing Pipeline (`kb-indexing-pipeline.json`)

**Назначение**: Индексирование документов Knowledge Base в PostgreSQL с pgvector embeddings.

**Триггер**: `POST /webhook/kb-index-document`

**Архитектура Flow**:
```
Webhook → Extract → Update Status (INDEXING) → Set Chunk Config →
Check Size → [Split Chunks | Single Chunk] → Merge →
For Each Chunk:
  - Add Metadata
  - Generate Embedding (OpenRouter)
  - Insert to PostgreSQL
→ Aggregate → Calculate Stats → Update Status (INDEXED) → Respond
```

**Используемые ноды**:

| Нода | Тип | Описание |
|------|-----|----------|
| **Webhook** | `nodes-base.webhook` v2.1 | Приём документа для индексации |
| **Set** | `nodes-base.set` v3.4 | Извлечение `document_id`, `kb_id`, `content` |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | PATCH статуса документа → `indexing` |
| **Set** | `nodes-base.set` v3.4 | Конфиг чанков: `chunk_size=500`, `overlap=50` |
| **If** | `nodes-base.if` v2.2 | Проверка: нужно ли разбивать на чанки |
| **Code** | `nodes-base.code` v2 | JavaScript для умного сплиттинга по границам слов |
| **Merge** | `nodes-base.merge` v2.1 | Объединение веток (split/single) |
| **Split Out** | `nodes-base.splitOut` v1 | Итерация по массиву чанков |
| **Set** | `nodes-base.set` v3.4 | Добавление `chunk_index`, метаданных |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | OpenRouter Embeddings API |
| **Postgres** | `nodes-base.postgres` v2.6 | INSERT в `document_chunks` таблицу |
| **Aggregate** | `nodes-base.aggregate` v1 | Сбор всех чанков для подсчёта |
| **Set** | `nodes-base.set` v3.4 | Подсчёт `chunks_count` |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | PATCH статуса → `indexed` |
| **Respond to Webhook** | `nodes-base.respondToWebhook` v1 | JSON ответ с метриками |

**Конфигурация Chunking**:
```javascript
// Code node: умный сплиттинг по границам слов
chunk_size: 500 tokens (≈2000 символов)
overlap: 50 tokens (≈200 символов)
strategy: разбивка на последнем пробеле в окне 80%-100% chunk_size
```

**Конфигурация Embeddings**:
- **Model**: `openai/text-embedding-3-small`
- **Dimension**: 1536 (по умолчанию)
- **Cost**: ~$0.00002 / 1K tokens

**Пример Webhook Payload**:
```json
{
  "document_id": "doc-uuid-here",
  "kb_id": "kb-uuid-here",
  "content": "Длинный текст документа...",
  "filename": "manual_lathe_operation.pdf"
}
```

**Пример Response**:
```json
{
  "success": true,
  "document_id": "doc-uuid-here",
  "chunks_count": 8,
  "status": "indexed"
}
```

**PostgreSQL Schema** (требуется):
```sql
CREATE TABLE document_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID NOT NULL REFERENCES documents(id),
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(1536), -- pgvector extension
  token_count INTEGER,
  chunk_metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chunks_embedding ON document_chunks
USING ivfflat (embedding vector_cosine_ops);
```

---

### 3. Smart Search Helper (`smart-search-helper.json`)

**Назначение**: Гибридный поисковый помощник с тремя источниками данных.

**Триггер**: `POST /webhook/smart-search`

**Архитектура Flow**:
```
Webhook → Extract Params →
[Параллельно]:
  1. PostgreSQL Full-Text Search (ts_rank)
  2. Generate Embedding → RAG Vector Search (pgvector)
  3. [Опционально] Tavily Web Search
→ Merge All → Rank & Normalize → Respond
```

**Используемые ноды**:

| Нода | Тип | Описание |
|------|-----|----------|
| **Webhook** | `nodes-base.webhook` v2.1 | Приём поискового запроса |
| **Set** | `nodes-base.set` v3.4 | Парсинг `query`, `workspace_id`, `limit`, `search_web` |
| **Postgres** | `nodes-base.postgres` v2.6 | Full-text search через `ts_rank` (русский язык) |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | OpenRouter Embeddings для векторного поиска |
| **Set** | `nodes-base.set` v3.4 | Извлечение embedding вектора |
| **Postgres** | `nodes-base.postgres` v2.6 | Vector similarity search (`<=>` оператор) |
| **If** | `nodes-base.if` v2.2 | Проверка флага `search_web` |
| **HTTP Request** | `nodes-base.httpRequest` v4.3 | Tavily API для web search |
| **Set** | `nodes-base.set` v3.4 | Пустой массив если web search выключен |
| **Merge** | `nodes-base.merge` v2.1 | Объединение 3 источников |
| **Code** | `nodes-base.code` v2 | JavaScript для ранжирования по score |
| **Respond to Webhook** | `nodes-base.respondToWebhook` v1 | Unified JSON response |

**Конфигурация PostgreSQL Full-Text**:
```sql
-- Full-text search с русской морфологией
SELECT
  id, title, description, category, status,
  ts_rank(
    to_tsvector('russian', title || ' ' || description),
    plainto_tsquery('russian', $query)
  ) AS similarity_score
FROM issues
WHERE
  workspace_id = $workspace_id
  AND to_tsvector('russian', title || ' ' || description)
      @@ plainto_tsquery('russian', $query)
ORDER BY similarity_score DESC
LIMIT $limit;
```

**Конфигурация Vector Search**:
```sql
-- Cosine similarity через pgvector
SELECT
  dc.document_id,
  d.filename,
  dc.content,
  dc.chunk_index,
  1 - (dc.embedding <=> $embedding::vector) AS cosine_similarity
FROM document_chunks dc
JOIN documents d ON d.id = dc.document_id
WHERE d.kb_id IN (
  SELECT id FROM knowledge_base WHERE workspace_id = $workspace_id
)
ORDER BY dc.embedding <=> $embedding::vector
LIMIT $limit;
```

**Конфигурация Tavily Web Search**:
```json
{
  "query": "user search query",
  "search_depth": "basic",
  "include_domains": [
    "stackoverflow.com",
    "github.com",
    "docs.python.org",
    "medium.com"
  ],
  "max_results": 5
}
```

**Алгоритм Ранжирования** (Code node):
```javascript
// Весовые коэффициенты
const weights = {
  database: 1.0,    // Точные совпадения в БД
  rag: 0.8,         // Семантическое сходство
  web: 0.6          // Внешние источники
};

// Нормализация score для каждого источника
ranked = allResults.map(result => ({
  ...result,
  normalized_score: result.raw_score * weights[result.source]
}));

// Сортировка по убыванию score
ranked.sort((a, b) => b.normalized_score - a.normalized_score);

return ranked.slice(0, limit);
```

**Пример Webhook Payload**:
```json
{
  "query": "как настроить токарный станок",
  "workspace_id": "ws-uuid-here",
  "limit": 5,
  "search_web": true
}
```

**Пример Response**:
```json
{
  "success": true,
  "query": "как настроить токарный станок",
  "sources": {
    "database": 3,
    "knowledge_base": 2,
    "web": 1
  },
  "results": [
    {
      "source": "database",
      "type": "issue",
      "id": "issue-uuid",
      "title": "Настройка токарного станка CNC",
      "score": 0.95,
      "relevance": 0.95
    },
    {
      "source": "knowledge_base",
      "type": "document",
      "filename": "manual_lathe_setup.pdf",
      "content": "Шаг 1: Калибровка...",
      "score": 0.76,
      "relevance": 0.95
    }
  ],
  "total_found": 6
}
```

---

## 🔧 Установка и Настройка

### Предварительные требования

- ✅ **n8n v1.0+** (рекомендуется актуальная stable)
- ✅ **PostgreSQL 14+** с расширением **pgvector**
- ✅ **OpenRouter API Key** (для LLM и embeddings)
- ✅ **Tavily API Key** (опционально, для web search)

### Шаг 1: Импорт Workflows

```bash
# В n8n UI: Settings → Workflows → Import from File
# Или через CLI:
n8n import:workflow --input=auto-categorize-issues.json
n8n import:workflow --input=kb-indexing-pipeline.json
n8n import:workflow --input=smart-search-helper.json
```

### Шаг 2: Настройка Credentials

**PostgreSQL Credential** (`equiply-postgres`):
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "norake_db",
  "user": "norake_user",
  "password": "***",
  "ssl": false
}
```

**HTTP Header Auth** (OpenRouter):
```json
{
  "name": "Authorization",
  "value": "Bearer sk-or-v1-***"
}
```

**HTTP Header Auth** (Tavily):
```json
{
  "name": "api-key",
  "value": "tvly-***"
}
```

### Шаг 3: Конфигурация Environment Variables

```bash
# В .env или n8n settings
BACKEND_URL=http://localhost:8000
WEBHOOK_URL=https://n8n.yourdomain.com
N8N_EDITOR_BASE_URL=https://n8n.yourdomain.com
```

### Шаг 4: Проверка Webhook URLs

После импорта проверьте webhook endpoints в n8n:

```
https://n8n.yourdomain.com/webhook/autocategorize-issue
https://n8n.yourdomain.com/webhook/kb-index-document
https://n8n.yourdomain.com/webhook/smart-search
```

---

## 🧪 Тестирование Workflows

### Test 1: Auto-categorize Issues

```bash
curl -X POST https://n8n.yourdomain.com/webhook/autocategorize-issue \
  -H "Content-Type: application/json" \
  -d '{
    "issue_id": "test-uuid",
    "title": "Сломался станок",
    "description": "Не включается двигатель"
  }'
```

**Ожидаемый результат**:
```json
{
  "success": true,
  "issue_id": "test-uuid",
  "category": "hardware",
  "message": "Issue categorized successfully"
}
```

### Test 2: KB Indexing Pipeline

```bash
curl -X POST https://n8n.yourdomain.com/webhook/kb-index-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "doc-uuid",
    "kb_id": "kb-uuid",
    "content": "Инструкция по настройке токарного станка...",
    "filename": "lathe_manual.pdf"
  }'
```

### Test 3: Smart Search Helper

```bash
curl -X POST https://n8n.yourdomain.com/webhook/smart-search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "настройка станка",
    "workspace_id": "ws-uuid",
    "limit": 5,
    "search_web": false
  }'
```

---

## 📊 Мониторинг и Метрики

### Встроенный Мониторинг n8n

```javascript
// В n8n UI: Executions → View
- Execution Time
- Node Execution Times
- Error Rate
- Success Rate
```

### Рекомендуемые Метрики

| Метрика | Workflow | Целевое значение |
|---------|----------|------------------|
| Execution Time | Auto-categorize | < 3s |
| Execution Time | KB Indexing | < 10s для 1000 токенов |
| Execution Time | Smart Search | < 2s |
| Error Rate | Все | < 1% |
| OpenRouter API Latency | Все | < 2s |

---

## 🔍 Используемые n8n Ноды (Официальная Документация)

Все ноды валидированы через **n8n MCP server** (541 нода доступно):

### Core Nodes

| Нода | Package | Версия | Описание |
|------|---------|--------|----------|
| **Webhook** | `n8n-nodes-base` | 2.1 | HTTP trigger для входящих запросов |
| **HTTP Request** | `n8n-nodes-base` | 4.3 | Универсальный HTTP клиент с auth |
| **Code** | `n8n-nodes-base` | 2 | JavaScript/Python runtime |
| **Set** | `n8n-nodes-base` | 3.4 | Манипуляция полями данных |
| **If** | `n8n-nodes-base` | 2.2 | Условное ветвление |
| **Merge** | `n8n-nodes-base` | 2.1 | Объединение веток данных |
| **Split Out** | `n8n-nodes-base` | 1 | Итерация по массиву |
| **Aggregate** | `n8n-nodes-base` | 1 | Сбор данных в один item |
| **Postgres** | `n8n-nodes-base` | 2.6 | PostgreSQL клиент |
| **Respond to Webhook** | `n8n-nodes-base` | 1 | HTTP ответ на webhook |

### Webhook Node Details

**Свойства**:
- `httpMethod`: GET, POST, PUT, PATCH, DELETE, HEAD
- `path`: динамический путь с параметрами (`:param`)
- `responseMode`: `onReceived`, `lastNode`, `responseNode`
- `responseData`: `allEntries`, `firstEntryJson`, `firstEntryBinary`, `noData`

**Best Practice**: Всегда используйте `responseMode: lastNode` для контроля над ответом.

### HTTP Request Node Details

**Свойства**:
- `url`: полный URL (с expressions)
- `method`: GET, POST, PUT, PATCH, DELETE
- `authentication`: `none`, `predefinedCredentialType`, `genericCredentialType`
- `sendBody`: true/false
- `contentType`: `json`, `form-urlencoded`, `multipart-form-data`, `raw`

**Best Practice**: Используйте `jsonParameters: true` для динамических body через expressions.

### Code Node Details

**Языки**: JavaScript (default), Python (beta), Python Native (beta)

**Modes**:
- `runOnceForAllItems` — обработка всех items за раз
- `runOnceForEachItem` — цикл по каждому item

**Доступные перемены**:
```javascript
// JavaScript
$input.all()        // все input items
$input.first()      // первый item
$input.last()       // последний item
$json               // текущий item JSON
items               // массив всех items
$itemIndex          // индекс в цикле
```

**Best Practice**: Всегда возвращайте массив объектов с `json` ключом:
```javascript
return [
  { json: { field: value } }
];
```

### Postgres Node Details

**Operations**:
- `executeQuery` — кастомный SQL
- `insert` — INSERT rows
- `update` — UPDATE rows
- `upsert` — INSERT ON CONFLICT UPDATE
- `select` — SELECT rows
- `deleteTable` — DELETE rows

**Best Practice для pgvector**:
```sql
-- Используйте $1, $2, $3 для параметров (защита от SQL injection)
SELECT * FROM table WHERE embedding <=> $1::vector LIMIT $2
```

---

## 🚀 Production Best Practices

### 1. Queue Mode (Горизонтальное масштабирование)

```bash
# n8n с Redis для queue
docker-compose.yml:
  n8n-main:
    environment:
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=redis

  n8n-worker-1:
    environment:
      - EXECUTIONS_MODE=queue
      - N8N_DISABLE_PRODUCTION_MAIN_PROCESS=true
```

### 2. Error Handling

**В Code Node**:
```javascript
try {
  // логика
  return [{ json: result }];
} catch (error) {
  throw new Error(`Processing failed: ${error.message}`);
}
```

**В HTTP Request**: включите `Continue On Fail` для graceful degradation.

### 3. Rate Limiting

**OpenRouter**:
- Free tier: 200 requests/day
- Paid tier: регулируется балансом

**Recommendation**: добавьте `Wait` node с `limit: 10 req/minute`.

### 4. Credential Management

**НЕ храните API keys в workflow JSON!**

```bash
# Используйте n8n Credentials Store
Settings → Credentials → Add Credential
```

### 5. Webhook Security

```javascript
// В Webhook node: Options → Authentication
{
  "headerAuth": {
    "name": "X-API-Key",
    "value": "your-secret-key"
  }
}
```

---

## 🐛 Troubleshooting

### Проблема: Webhook не отвечает

**Решение**:
1. Проверьте `responseMode` в Webhook node
2. Убедитесь что есть `Respond to Webhook` node
3. Проверьте firewall/nginx config для webhook URL

### Проблема: OpenRouter API ошибка 401

**Решение**:
```bash
# Проверьте headers в HTTP Request node
Headers:
  Authorization: Bearer sk-or-v1-***
  HTTP-Referer: https://yourdomain.com
  X-Title: Your App Name
```

### Проблема: PostgreSQL connection timeout

**Решение**:
```bash
# В Postgres credential добавьте
{
  "connectionTimeout": 30000,
  "ssl": {
    "rejectUnauthorized": false
  }
}
```

### Проблема: Code node "items is not defined"

**Решение**:
```javascript
// Убедитесь что mode = "runOnceForAllItems"
// И используйте правильный API
const items = $input.all();
```

---

## 📚 Дополнительные Ресурсы

### Официальная Документация
- 📖 n8n Docs: https://docs.n8n.io/
- 🔌 Node Reference: https://docs.n8n.io/integrations/builtin/
- 💬 Community Forum: https://community.n8n.io/
- 🐙 GitHub: https://github.com/n8n-io/n8n

### Equiply Backend Docs
- 📋 Development Plan: `docs/DEVELOPMENT_PLAN.md`
- 📐 MVP Extended Plan: `docs/MVP_EXTENDED_PLAN.md`
- 🏗️ Architecture: `.github/copilot-instructions.md`

### n8n MCP Server
- 🛠️ **541 нод** доступно
- 🤖 **263 AI tools** (любая нода может быть AI tool!)
- 📊 **87% документации** покрытие
- 🔍 **Semantic search** по workflow шаблонам

---

## 🤝 Контакты

**Equiply Backend Team**

- 📧 Email: team@equiply.equiply.ru
- 🐙 GitHub: https://github.com/mikey-semy/equiply-backend
- 🔗 Plane: https://plane.equiply.ru/projects/projects/NORAK

---

**Дата создания**: 11 ноября 2025
**Последнее обновление**: 11 ноября 2025
**Версия документа**: 1.0.0
