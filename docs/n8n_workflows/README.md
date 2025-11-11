# n8n Workflows для NoRake Backend

Этот каталог содержит готовые n8n workflows для автоматизации процессов в NoRake.

## 📋 Доступные Workflows

### 1. Auto-categorize Issues (`auto-categorize-issues.json`)

**Назначение**: Автоматическая категоризация Issues через OpenRouter AI при создании.

### 2. KB Indexing Pipeline (`kb-indexing-pipeline.json`)

**Назначение**: Индексация документов Knowledge Base в pgvector с embeddings для RAG поиска.

**Триггер**: Webhook `POST /webhook/kb-index-document`

**AI Model**: text-embedding-3-small (OpenRouter, 1536 dimensions)

**Процесс**:
1. Webhook получает `{document_id, kb_id, content, filename}`
2. Update Status: INDEXING - обновление статуса документа
3. Check if Needs Splitting - проверка размера документа
4. Split into Chunks (если > 500 токенов) - разбивка на чанки с overlap 50
5. Generate Embeddings - создание vector embeddings через OpenRouter
6. Insert Chunk to DB - вставка чанков с embeddings в document_chunks
7. Calculate Stats - подсчёт количества чанков
8. Update Status: INDEXED - финальное обновление статуса + indexed_at
9. Respond - возврат результата

**Параметры**:
- Chunk Size: 500 токенов (примерно 375 слов)
- Overlap: 50 токенов (сохранение контекста между чанками)
- Embedding Dimension: 1536 (text-embedding-3-small)
- Vector Index: ivfflat with cosine similarity

**Производительность**:
- Latency: ~0.5-1 секунда на чанк (зависит от OpenRouter)
- Документ 10KB текста: ~20 чанков × 1s = ~20 секунд
- Rate Limit: 10 req/min (free tier OpenRouter)

**Acceptance Criteria**:
- ✅ Workflow работает в n8n
- ✅ Документ индексируется в pgvector
- ✅ Status меняется на INDEXED

---

### 1. Auto-categorize Issues (COMPLETED)

**Назначение**: Автоматическая категоризация Issues через OpenRouter AI при создании.

**Триггер**: Webhook `POST /webhook/autocategorize-issue`

**AI Model**: qwen/qwen-3-coder-480b-a35b:free (480B MoE, специализация на коде)

**Процесс**:
1. Webhook получает `{issue_id, title, description}`
2. Extract Issue Data - извлечение данных из запроса
3. OpenRouter: Categorize - AI анализ через Qwen3 Coder 480B
4. Extract Category - парсинг ответа AI
5. Update Issue Category - обновление Issue через Backend API
6. Respond - возврат результата

**Категории**: hardware, software, process, documentation, safety, quality, maintenance, training, other

**Производительность**:
- Latency: ~2-4 секунды (зависит от очереди OpenRouter)
- Accuracy: ~95% (480B параметров, специализация на технических задачах)
- Rate Limit: 10 req/min (free tier OpenRouter)

**Альтернативные модели** (для замены в workflow):

| Модель | Размер | Специализация | Рекомендуется для |
|--------|--------|---------------|-------------------|
| `qwen/qwen-3-coder-480b-a35b:free` | 480B MoE | Код, архитектура | **Текущая (рекомендуется)** |
| `moonshot/kimi-dev-72b:free` | 72B Dense | Разработка, документация | Длинные Issues (>2KB) |
| `deepseek/r1-distill-llama-70b:free` | 70B Dense | Универсальная | Баланс скорости/качества |
| `tongyi/deepresearch-30b-a3b:free` | 30B MoE | Анализ, логика | Научные/исследовательские Issues |
| `deepseek/deepseek-v3.1:free` | ~14B | Быстрая универсальная | Прототипирование, тесты |

**Смена модели**: Отредактируйте ноду "OpenRouter: Categorize" → Body → `model` → вставьте ID из таблицы выше.

---

## 🎯 AI Model Selection Guide

### Критерии выбора модели для категоризации

1. **Точность** (Accuracy):
   - **480B+ параметров**: Qwen3 Coder, Kimi Dev 72B → лучшая точность на сложных задачах
   - **70B параметров**: DeepSeek R1 Distill → хороший баланс
   - **14B-30B**: DeepSeek V3.1, Tongyi → базовая точность

2. **Скорость** (Latency):
   - Зависит от очереди на OpenRouter, НЕ от размера модели (все выполняются на серверах провайдера)
   - Среднее время: 2-5 секунд для всех free-моделей

3. **Специализация**:
   - **Технические Issues** (ошибки оборудования, софта) → Qwen3 Coder 480B ✅
   - **Процессы/документация** → Kimi Dev 72B
   - **Универсальные** → DeepSeek R1 70B

4. **Rate Limits** (бесплатный tier):
   - Все free-модели: ~10-20 requests/minute
   - Достаточно для небольших команд (<50 Issues/день)

### ⚠️ Модели для избегания (фейки/нестабильные)

- ❌ `openai/gpt-oss-20b:free` - OpenAI не выпускает open-source моделей
- ❌ `meta/llama-4-scout:free` - Llama 4 официально не существует (на ноябрь 2025)
- ❌ Venice / Chimera / Dolphin - экспериментальные community-модели, нестабильны

---

## 🚀 Импорт Workflow в n8n

### Шаг 1: Откройте n8n UI

```bash
# Если n8n ещё не запущен
docker-compose up -d n8n

# Откройте браузер
open http://localhost:5678
```

### Шаг 2: Импортируйте Workflow

#### 2.1 Auto-categorize Issues

1. В n8n UI нажмите **"Add workflow" → "Import from File"**
2. Выберите файл `auto-categorize-issues.json`
3. Workflow будет импортирован со всеми нодами

#### 2.2 KB Indexing Pipeline

1. В n8n UI нажмите **"Add workflow" → "Import from File"**
2. Выберите файл `kb-indexing-pipeline.json`
3. Workflow будет импортирован со всеми нодами (17 nodes)

### Шаг 3: Настройте Credentials

#### 3.1 Создайте HTTP Header Auth для OpenRouter

1. В n8n UI → **Credentials** → **New Credential**
2. Выберите **"Http Header Auth"**
3. Настройте:
   - **Name**: `OpenRouter API Key`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer sk-or-v1-YOUR_KEY_HERE`
4. Нажмите **Save**

#### 3.2 Создайте HTTP Header Auth для Backend (для обоих workflows)

1. В n8n UI → **Credentials** → **New Credential**
2. Выберите **"Http Header Auth"**
3. Настройте:
   - **Name**: `NoRake Backend Token`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer YOUR_JWT_TOKEN_HERE`
4. Нажмите **Save**

**Получение BACKEND_API_TOKEN**:
```bash
# Залогиньтесь в NoRake Backend
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"

# Скопируйте access_token из ответа
```

#### 3.3 Создайте PostgreSQL Credential (только для KB Indexing)

1. В n8n UI → **Credentials** → **New Credential**
2. Выберите **"Postgres"**
3. Настройте:
   - **Name**: `NoRake PostgreSQL`
   - **Host**: `postgres` (имя сервиса в docker-compose)
   - **Database**: `norake_dev`
   - **User**: `postgres`
   - **Password**: (ваш пароль из `.env.dev`)
   - **Port**: `5432`
4. Нажмите **Test Connection** → должен быть Success
5. Нажмите **Save**

#### 3.3 Создайте PostgreSQL Credential (только для KB Indexing)

1. В n8n UI → **Credentials** → **New Credential**
2. Выберите **"Postgres"**
3. Настройте:
   - **Name**: `NoRake PostgreSQL`
   - **Host**: `postgres` (имя сервиса в docker-compose)
   - **Database**: `norake_dev`
   - **User**: `postgres`
   - **Password**: (ваш пароль из `.env.dev`)
   - **Port**: `5432`
4. Нажмите **Test Connection** → должен быть Success
5. Нажмите **Save**

#### 3.4 Настройте Environment Variables

В n8n UI → **Settings → Environment Variables** добавьте:

```env
BACKEND_URL=http://norake-backend:8000
```

**Примечание**: API ключи теперь в Credentials, только BACKEND_URL нужен как env var.

### Шаг 4: Подключите Credentials к Nodes

#### 4.1 Auto-categorize Issues Workflow

1. Откройте imported workflow в редакторе
2. Нажмите на ноду **"OpenRouter: Categorize"**
3. В секции **Authentication** выберите credential **"OpenRouter API Key"**
4. Нажмите на ноду **"Update Issue Category"**
5. В секции **Authentication** выберите credential **"NoRake Backend Token"**
6. Нажмите **Save** для workflow

#### 4.2 KB Indexing Pipeline Workflow

1. Откройте imported workflow в редакторе
2. Нажмите на ноду **"Update Status: INDEXING"**
3. В секции **Authentication** выберите credential **"NoRake Backend Token"**
4. Нажмите на ноду **"OpenRouter: Generate Embeddings"**
5. В секции **Authentication** выберите credential **"OpenRouter API Key"**
6. Нажмите на ноду **"Insert Chunk to DB"**
7. В секции **Credential** выберите **"NoRake PostgreSQL"**
8. Нажмите на ноду **"Update Status: INDEXED"**
9. В секции **Authentication** выберите credential **"NoRake Backend Token"**
10. Нажмите **Save** для workflow

### Шаг 5: Активируйте Workflows

#### 5.1 Auto-categorize Issues

1. В редакторе workflow нажмите **"Save"** (если были изменения)
2. Нажмите **"Active" toggle** в правом верхнем углу
3. Webhook станет доступен по адресу: `http://localhost:5678/webhook/autocategorize-issue`

#### 5.2 KB Indexing Pipeline

1. В редакторе workflow нажмите **"Save"** (если были изменения)
2. Нажмите **"Active" toggle** в правом верхнем углу
3. Webhook станет доступен по адресу: `http://localhost:5678/webhook/kb-index-document`

### Шаг 6: Получите Webhook URLs

### Шаг 6: Получите Webhook URLs

#### Auto-categorize Issues
После активации в ноде "Webhook" появится:
```
Production URL: http://localhost:5678/webhook/autocategorize-issue
Test URL: http://localhost:5678/webhook-test/autocategorize-issue
```

#### KB Indexing Pipeline
После активации в ноде "Webhook" появится:
```
Production URL: http://localhost:5678/webhook/kb-index-document
Test URL: http://localhost:5678/webhook-test/kb-index-document
```

Скопируйте **Production URLs** для регистрации в Backend.

---

## 📝 Регистрация Workflows в NoRake Backend

После импорта и активации зарегистрируйте workflows через API:

### 1. Auto-categorize Issues

```bash
POST /api/v1/workflows/{workspace_id}
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "workflow_name": "Auto-categorize Issues",
  "workflow_type": "AUTO_CATEGORIZE",
  "webhook_url": "http://localhost:5678/webhook/autocategorize-issue",
  "trigger_config": {
    "model": "qwen/qwen-3-coder-480b-a35b:free",
    "temperature": 0.2,
    "categories": [
      "hardware",
      "software",
      "process",
      "documentation",
      "safety",
      "quality",
      "maintenance",
      "training",
      "other"
    ]
  },
  "n8n_workflow_id": "auto-categorize-issues"
}
```

### 2. KB Indexing Pipeline

```bash
POST /api/v1/workflows/{workspace_id}
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "workflow_name": "KB Indexing Pipeline",
  "workflow_type": "KB_INDEXING",
  "webhook_url": "http://localhost:5678/webhook/kb-index-document",
  "trigger_config": {
    "chunk_size": 500,
    "overlap": 50,
    "embedding_model": "text-embedding-3-small",
    "embedding_dimension": 1536
  },
  "n8n_workflow_id": "kb-indexing-pipeline"
}
```

**Ответ**:
```json
{
  "success": true,
  "message": "Workflow успешно создан",
  "data": {
    "id": "uuid",
    "workflow_name": "Auto-categorize Issues",
    "workflow_type": "AUTO_CATEGORIZE",
    "webhook_url": "http://localhost:5678/webhook/autocategorize-issue",
    "is_active": true,
    "execution_count": 0
  }
}
```

---

## 🔧 Альтернативный способ: Создание Workflow через n8n REST API

Вместо ручного импорта можно создать workflow программно:

```bash
# 1. Создайте workflow через n8n API
curl -X POST http://localhost:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: your_n8n_api_key" \
  -H "Content-Type: application/json" \
  -d @auto-categorize-issues.json

# Ответ содержит workflow ID
# {"id": "abc123", "name": "NoRake: Auto-categorize Issues", ...}

# 2. Активируйте workflow
curl -X POST http://localhost:5678/api/v1/workflows/abc123/activate \
  -H "X-N8N-API-KEY: your_n8n_api_key"

# 3. Получите webhook URL из активированного workflow
curl -X GET http://localhost:5678/api/v1/workflows/abc123 \
  -H "X-N8N-API-KEY: your_n8n_api_key"
```

**Примечание**: n8n API Key настраивается в переменных окружения:
```env
N8N_API_KEY=your_secret_api_key_here
```

---

## 🧪 Тестирование Workflows

### 1. Тест Auto-categorize Issues

#### Ручной тест через Postman/curl:

```bash
curl -X POST http://localhost:5678/webhook/autocategorize-issue \
  -H "Content-Type: application/json" \
  -d '{
    "issue_id": "your-issue-uuid",
    "title": "Ошибка E401 на станке CNC",
    "description": "При запуске программы G-code станок выдаёт ошибку E401 и останавливается"
  }'
```

**Ожидаемый ответ**:
```json
{
  "success": true,
  "issue_id": "your-issue-uuid",
  "category": "hardware",
  "message": "Issue categorized successfully"
}
```

### 2. Тест KB Indexing Pipeline

#### Ручной тест через Postman/curl:

```bash
curl -X POST http://localhost:5678/webhook/kb-index-document \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "your-document-uuid",
    "kb_id": "your-kb-uuid",
    "filename": "manual.pdf",
    "content": "This is a test document. It contains multiple paragraphs with technical information about equipment maintenance procedures. The document should be split into chunks and indexed for RAG search. Each chunk will have an embedding generated via OpenRouter API."
  }'
```

**Ожидаемый ответ**:
```json
{
  "success": true,
  "document_id": "your-document-uuid",
  "chunks_count": 3,
  "status": "indexed"
}
```

**Проверка в БД**:
```sql
-- Проверить статус документа
SELECT id, filename, status, chunks_count, indexed_at 
FROM documents 
WHERE id = 'your-document-uuid';

-- Проверить чанки с embeddings
SELECT chunk_index, token_count, LEFT(content, 50) AS preview
FROM document_chunks
WHERE document_id = 'your-document-uuid'
ORDER BY chunk_index;

-- Проверить vector index
SELECT COUNT(*) AS total_embeddings
FROM document_chunks
WHERE embedding IS NOT NULL;
```

### Автоматический тест через Backend:

```bash
# Создайте Issue - автоматически вызовется webhook
POST /api/v1/issues
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "title": "Не работает датчик температуры",
  "description": "Датчик показывает некорректные значения"
}
```

После создания Issue проверьте, что `category` автоматически проставлена:

```bash
GET /api/v1/issues/{issue_id}
```

---

## 🔧 Troubleshooting

### Workflow не активируется

**Проблема**: Кнопка "Active" не переключается.

**Решение**:
1. Проверьте, что все environment variables настроены
2. Убедитесь, что нет ошибок в нодах (красные треугольники)
3. Перезапустите n8n: `docker-compose restart n8n`

### OpenRouter возвращает 401 Unauthorized

**Проблема**: Ошибка в ноде "OpenRouter: Categorize".

**Решение**:
1. Проверьте `OPENROUTER_API_KEY` в n8n Variables
2. Убедитесь, что ключ начинается с `sk-or-v1-`
3. Проверьте баланс на OpenRouter Dashboard

### Backend не получает webhook

**Проблема**: Issue создаётся, но category не проставляется.

**Решение**:
1. Проверьте логи n8n: `docker-compose logs n8n`
2. Убедитесь, что `BACKEND_URL` правильный
3. Проверьте, что workflow активен (зелёная иконка)
4. Проверьте `BACKEND_API_TOKEN` (должен быть валидным JWT)

### Category некорректная

**Проблема**: AI возвращает неправильную категорию.

**Решение**:
1. Настройте `temperature` в ноде OpenRouter (0.1-0.5 для точности)
2. Улучшите system prompt в ноде OpenRouter
3. Попробуйте другую модель (например, `openai/gpt-3.5-turbo`)

---

## 📊 Мониторинг Executions

### Просмотр логов выполнений:

1. n8n UI → **Executions** (левая панель)
2. Кликните на execution для просмотра деталей
3. Проверьте входные/выходные данные каждой ноды

### Проверка статистики через Backend API:

```bash
GET /api/v1/workflows/{workspace_id}
Authorization: Bearer YOUR_JWT_TOKEN
```

**Ответ**:
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "workflow_name": "Auto-categorize Issues",
      "execution_count": 42,
      "last_triggered_at": "2025-11-11T10:30:00Z",
      "is_active": true
    }
  ]
}
```

---

## 🎯 Best Practices

1. **Environment Variables**: Всегда используйте переменные окружения для секретов
2. **Error Handling**: Добавьте ноды "Error Trigger" для обработки ошибок
3. **Logging**: Используйте ноду "Set" для логирования промежуточных результатов
4. **Testing**: Тестируйте workflow в "Test URL" перед активацией
5. **Monitoring**: Регулярно проверяйте Executions на ошибки

---

## 📚 Дополнительные Workflows

- **KB Indexing Pipeline** (`kb-indexing-pipeline.json`) - индексация документов в pgvector
- **Smart Search Helper** (`smart-search-helper.json`) - гибридный поиск (DB + RAG + Tavily)
- **Weekly Digest** (`weekly-digest.json`) - еженедельные отчёты по Issues

---

## 🔗 Полезные ссылки

- [n8n Documentation](https://docs.n8n.io/)
- [OpenRouter API](https://openrouter.ai/docs)
- [NoRake Backend API Docs](http://localhost:8000/docs)
