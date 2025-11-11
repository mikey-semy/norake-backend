# n8n Workflows для NoRake Backend

Этот каталог содержит готовые n8n workflows для автоматизации процессов в NoRake.

## 📋 Доступные Workflows

### 1. Auto-categorize Issues (`auto-categorize-issues.json`)

**Назначение**: Автоматическая категоризация Issues через OpenRouter AI при создании.

**Триггер**: Webhook `POST /webhook/autocategorize-issue`

**Процесс**:
1. Webhook получает `{issue_id, title, description}`
2. Extract Issue Data - извлечение данных из запроса
3. OpenRouter: Categorize - AI анализ через meta-llama/llama-3.2-3b-instruct
4. Extract Category - парсинг ответа AI
5. Update Issue Category - обновление Issue через Backend API
6. Respond - возврат результата

**Категории**: hardware, software, process, documentation, safety, quality, maintenance, training, other

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

1. В n8n UI нажмите **"Add workflow" → "Import from File"**
2. Выберите файл `auto-categorize-issues.json`
3. Workflow будет импортирован со всеми нодами

### Шаг 3: Настройте Credentials

#### 3.1 Создайте HTTP Header Auth для OpenRouter

1. В n8n UI → **Credentials** → **New Credential**
2. Выберите **"Http Header Auth"**
3. Настройте:
   - **Name**: `OpenRouter API Key`
   - **Header Name**: `Authorization`
   - **Header Value**: `Bearer sk-or-v1-YOUR_KEY_HERE`
4. Нажмите **Save**

#### 3.2 Создайте HTTP Header Auth для Backend

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

#### 3.3 Настройте Environment Variables

В n8n UI → **Settings → Environment Variables** добавьте:

```env
BACKEND_URL=http://norake-backend:8000
```

**Примечание**: API ключи теперь в Credentials, только BACKEND_URL нужен как env var.

### Шаг 4: Подключите Credentials к Nodes

1. Откройте imported workflow в редакторе
2. Нажмите на ноду **"OpenRouter: Categorize"**
3. В секции **Authentication** выберите credential **"OpenRouter API Key"**
4. Нажмите на ноду **"Update Issue Category"**
5. В секции **Authentication** выберите credential **"NoRake Backend Token"**
6. Нажмите **Save** для workflow

### Шаг 4: Активируйте Workflow

1. В редакторе workflow нажмите **"Save"** (если были изменения)
2. Нажмите **"Active" toggle** в правом верхнем углу
3. Webhook станет доступен по адресу: `http://localhost:5678/webhook/autocategorize-issue`

### Шаг 5: Получите Webhook URL

После активации в ноде "Webhook" появится:
```
Production URL: http://localhost:5678/webhook/autocategorize-issue
Test URL: http://localhost:5678/webhook-test/autocategorize-issue
```

Скопируйте **Production URL** для регистрации в Backend.

---

## 📝 Регистрация Workflow в NoRake Backend

После импорта и активации зарегистрируйте workflow через API:

```bash
POST /api/v1/workflows/{workspace_id}
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "workflow_name": "Auto-categorize Issues",
  "workflow_type": "AUTO_CATEGORIZE",
  "webhook_url": "http://localhost:5678/webhook/autocategorize-issue",
  "trigger_config": {
    "model": "meta-llama/llama-3.2-3b-instruct:free",
    "temperature": 0.3,
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

## 🧪 Тестирование Workflow

### Ручной тест через Postman/curl:

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
