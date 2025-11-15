# Бесплатные OpenRouter модели для AI чата с RAG

## Обзор

Equiply Backend интегрирован с 5 бесплатными моделями OpenRouter, специализирующимися на разных задачах. Все модели поддерживают RAG (Retrieval-Augmented Generation) для работы с документами из вашей базы знаний.

## Доступные модели

| Ключ модели | Полное имя | Специализация | Context Window | Temperature | Max Tokens | Рекомендуемые задачи |
|------------|-----------|---------------|----------------|-------------|------------|---------------------|
| `qwen_coder` | Qwen QwQ 32B | Code review, debugging, refactoring | 32,768 | 0.2 | 8,000 | Анализ кода, рефакторинг, генерация тестов, code review |
| `kimi_dev` | Kimi Free 200K | Long documents, general chat | 200,000 | 0.5 | 16,000 | Анализ больших документов (>50 стр.), длинные контракты, книги |
| `deepseek_r1` | Deepseek R1 64K | Complex reasoning, research | 65,536 | 0.5 | 8,000 | Научные исследования, сложный анализ, логические цепочки |
| `tongyi_research` | Qwen Turbo 32K | Scientific writing, technical analysis | 32,768 | 0.3 | 6,000 | Техническая документация, научные статьи, анализ патентов |
| `deepseek_v3` | Deepseek V3 64K | Fast responses, simple queries | 65,536 | 0.7 | 8,000 | Быстрые ответы, простые Q&A, общение |

## Когда использовать какую модель?

### 🖥️ Анализ кода → `qwen_coder`
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "qwen_coder",
    "title": "Code Review: Authentication Module",
    "document_service_ids": ["uuid-of-auth-code-file"]
  }'
```

**Лучше всего подходит для:**
- Code review существующего кода
- Рефакторинг и оптимизация
- Генерация unit тестов
- Поиск багов и уязвимостей
- Объяснение сложных алгоритмов

**Пример workflow:**
1. Загрузите файл с кодом через drag-and-drop
2. Спросите: "Проанализируй этот код и найди потенциальные проблемы"
3. Получите детальный анализ с предложениями улучшений
4. Temperature 0.2 гарантирует точные технические ответы

### 📚 Длинные документы → `kimi_dev`
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "kimi_dev",
    "title": "Contract Analysis: 150-page Agreement",
    "document_service_ids": ["uuid-of-contract-pdf"]
  }'
```

**Лучше всего подходит для:**
- Анализ контрактов (50+ страниц)
- Обработка технических мануалов
- Извлечение данных из больших отчётов
- Суммаризация книг и диссертаций
- Поиск информации в архивах

**Уникальное преимущество:** Context window 200K токенов позволяет обработать ~150,000 слов (300-400 страниц A4) за один запрос.

### 🔬 Научные исследования → `deepseek_r1`
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "deepseek_r1",
    "title": "Research: ML Model Comparison",
    "document_service_ids": ["uuid-of-research-paper"]
  }'
```

**Лучше всего подходит для:**
- Сравнительный анализ исследований
- Построение логических выводов
- Валидация научных гипотез
- Критический анализ методологии
- Поиск противоречий в данных

**Особенность:** Специализируется на chain-of-thought reasoning - покажет ход рассуждений.

### 📄 Техническая документация → `tongyi_research`
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "tongyi_research",
    "title": "Patent Analysis: AI Technology",
    "document_service_ids": ["uuid-of-patent-pdf"]
  }'
```

**Лучше всего подходит для:**
- Анализ патентов и спецификаций
- Генерация технической документации
- Извлечение терминов и определений
- Сравнение версий документов
- Формализация требований

**Низкая temperature (0.3)** гарантирует точность технических терминов.

### ⚡ Быстрые ответы → `deepseek_v3`
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "deepseek_v3",
    "title": "Quick Q&A Session"
  }'
```

**Лучше всего подходит для:**
- Быстрые вопросы без документов
- Общение в стиле ChatGPT
- Брейнсторминг идей
- Неформальные объяснения
- Креативное письмо

**Высокая temperature (0.7)** делает ответы более разнообразными и креативными.

## Полный API Reference

### 1. Получить список моделей
```bash
curl -X GET "http://localhost:8000/api/v1/chat/models" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "message": "Models retrieved successfully",
  "data": [
    {
      "key": "qwen_coder",
      "id": "qwen/qwq-32b-preview:free",
      "name": "Qwen QwQ 32B",
      "description": "Precise code analysis and debugging with low temperature for technical accuracy",
      "specialization": "Code review, debugging, refactoring",
      "context_window": 32768,
      "default_temperature": 0.2,
      "default_max_tokens": 8000
    }
    // ... остальные модели
  ]
}
```

### 2. Создать новый чат
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "qwen_coder",
    "title": "My Code Analysis Chat",
    "workspace_id": "optional-workspace-uuid",
    "document_service_ids": ["doc-uuid-1", "doc-uuid-2"],
    "system_prompt": "You are a senior code reviewer with 10 years of experience."
  }'
```

**Response:** Полный `ChatDetailSchema` с присвоенным `chat_id`.

### 3. Получить список ваших чатов
```bash
curl -X GET "http://localhost:8000/api/v1/chat?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "message": "Chats retrieved successfully",
  "data": [
    {
      "id": "uuid",
      "chat_id": "chat-abc123xyz",
      "title": "Code Review Session",
      "model_key": "qwen_coder",
      "model_name": "Qwen QwQ 32B",  // Computed field!
      "messages_count": 15,
      "workspace_id": null,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T14:45:00Z"
    }
  ]
}
```

### 4. Получить детали чата с историей
```bash
curl -X GET "http://localhost:8000/api/v1/chat/chat-abc123xyz" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:** Полный `ChatDetailSchema` с массивом `messages[]`.

### 5. Отправить сообщение (с загрузкой файла)
```bash
# Текстовое сообщение
curl -X POST "http://localhost:8000/api/v1/chat/chat-abc123xyz/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "content=Analyze this code for potential bugs"

# Сообщение с файлом (drag-and-drop)
curl -X POST "http://localhost:8000/api/v1/chat/chat-abc123xyz/message" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "content=Review this authentication module" \
  -F "file=@/path/to/auth.py"
```

**Response:**
```json
{
  "success": true,
  "message": "Message sent successfully",
  "data": {
    "role": "assistant",
    "content": "I've analyzed the authentication module...",
    "metadata": {
      "tokens_used": 1250,
      "rag_chunks_used": 5,
      "model_key": "qwen_coder"
    },
    "timestamp": "2024-01-15T14:50:30Z"
  }
}
```

**Что происходит при загрузке файла:**
1. **Автоматическая загрузка в S3:** Файл сохраняется в `DocumentService`
2. **RAG активация:** Документ разбивается на чанки (1500 токенов) с перекрытием (200 токенов)
3. **Генерация embeddings:** Создаются векторные представления через OpenAI
4. **Добавление в чат:** `document_service_ids` обновляется автоматически
5. **RAG поиск:** При отправке сообщения ищутся релевантные чанки (top-10)
6. **OpenRouter запрос:** Контекст + сообщение → AI модель → ответ

### 6. Переключить модель в существующем чате
```bash
curl -X PATCH "http://localhost:8000/api/v1/chat/chat-abc123xyz/model" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_key": "deepseek_r1"}'
```

**Use case:** Начали с `deepseek_v3` для быстрых вопросов, затем нужен глубокий анализ → переключаемся на `deepseek_r1`. **История сообщений сохраняется!**

### 7. Добавить документы в чат (drag-and-drop)
```bash
curl -X POST "http://localhost:8000/api/v1/chat/chat-abc123xyz/documents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_service_ids": ["new-doc-uuid-1", "new-doc-uuid-2"]
  }'
```

**Use case:** Середина разговора, нужен дополнительный контекст из других документов.

### 8. Удалить чат (soft delete)
```bash
curl -X DELETE "http://localhost:8000/api/v1/chat/chat-abc123xyz" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "success": true,
  "message": "Chat deleted successfully",
  "data": {
    "chat_id": "chat-abc123xyz",
    "deleted": true
  }
}
```

Чат помечается как `is_active=False`, но остаётся в БД для аудита.

## Рекомендации по переключению моделей

### Стратегия "От быстрого к мощному"
```
1. Создайте чат с deepseek_v3 (быстрый старт)
2. Задайте общие вопросы о документе
3. Если нужен глубокий анализ → switch_model("deepseek_r1")
4. Если документ очень длинный → switch_model("kimi_dev")
```

### Стратегия "По типу задачи"
```
- Код → qwen_coder
- Юридические документы → kimi_dev
- Научная статья → deepseek_r1 или tongyi_research
- Техническая спецификация → tongyi_research
- Q&A без документов → deepseek_v3
```

## Лимиты бесплатного уровня OpenRouter

- **Rate limit:** 10 запросов в минуту (per IP)
- **Quota:** 200 запросов в день (per API key)
- **Max tokens per request:** Зависит от модели (см. таблицу)
- **Max context window:** До 200K токенов для `kimi_dev`

**Мониторинг использования:**
Поле `metadata.estimated_cost` в `ChatDetailSchema` показывает примерную стоимость (в бесплатном tier всегда $0).

## RAG Configuration (для разработчиков)

```env
# .env.example
RAG_CHUNK_SIZE=1500          # Оптимальный размер чанка для embeddings
RAG_CHUNK_OVERLAP=200        # Предотвращает потерю контекста на границах
RAG_SEARCH_LIMIT=10          # Максимум чанков в RAG запросе
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # Модель для векторизации
```

**Как работает RAG:**
1. Документ разбивается на чанки по `RAG_CHUNK_SIZE` токенов
2. Соседние чанки перекрываются на `RAG_CHUNK_OVERLAP` токенов
3. Каждый чанк векторизуется через OpenAI embeddings
4. При запросе ищутся `RAG_SEARCH_LIMIT` самых релевантных чанков
5. Чанки форматируются как контекст для OpenRouter

## Примеры реальных workflow

### Workflow 1: Анализ кода с рефакторингом
```bash
# 1. Создать чат для code review
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_key": "qwen_coder", "title": "Refactor: Auth Module"}'

# Сохраняем chat_id из response
CHAT_ID="chat-abc123"

# 2. Загрузить файл с кодом
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/message" \
  -H "Authorization: Bearer $TOKEN" \
  -F "content=Analyze this authentication module for security issues" \
  -F "file=@src/auth.py"

# 3. Задать уточняющие вопросы
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/message" \
  -H "Authorization: Bearer $TOKEN" \
  -F "content=Suggest refactoring for better testability"

# 4. Запросить unit тесты
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/message" \
  -H "Authorization: Bearer $TOKEN" \
  -F "content=Generate unit tests for the proposed refactoring"
```

### Workflow 2: Исследование длинного документа
```bash
# 1. Создать чат с Kimi (200K context)
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_key": "kimi_dev", "title": "Research: 200-page Contract"}'

CHAT_ID="chat-xyz789"

# 2. Загрузить контракт (автоматический RAG)
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/message" \
  -H "Authorization: Bearer $TOKEN" \
  -F "content=Summarize key obligations and deadlines" \
  -F "file=@contract.pdf"

# 3. Если нужен глубокий анализ → switch to Deepseek R1
curl -X PATCH "http://localhost:8000/api/v1/chat/$CHAT_ID/model" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model_key": "deepseek_r1"}'

# 4. Запросить критический анализ
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/message" \
  -H "Authorization: Bearer $TOKEN" \
  -F "content=Identify potential risks and unfavorable clauses"
```

### Workflow 3: Команда работает с одним чатом (workspace)
```bash
# 1. Создать чат в workspace
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_key": "tongyi_research",
    "title": "Team: Technical Spec Review",
    "workspace_id": "workspace-uuid"
  }'

# 2. Члены команды добавляют документы по мере необходимости
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/documents" \
  -H "Authorization: Bearer $TEAMMATE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_service_ids": ["new-spec-uuid"]}'

# 3. Все видят общую историю и могут задавать вопросы
curl -X POST "http://localhost:8000/api/v1/chat/$CHAT_ID/message" \
  -H "Authorization: Bearer $ANOTHER_TEAMMATE_TOKEN" \
  -F "content=How does the new spec affect our API design?"
```

## Troubleshooting

### Ошибка: "Invalid model key"
```json
{
  "success": false,
  "message": "Invalid model key: unknown_model",
  "data": null
}
```
**Решение:** Используйте только ключи из таблицы (qwen_coder, kimi_dev, deepseek_r1, tongyi_research, deepseek_v3).

### Ошибка: "Document not found or access denied"
```json
{
  "success": false,
  "message": "Document xxx not found or you don't have access",
  "data": null
}
```
**Решение:** Проверьте, что `document_service_id` существует и принадлежит вашему workspace.

### Ошибка: "Chat not found"
```json
{
  "success": false,
  "message": "Chat not found or access denied",
  "data": null
}
```
**Решение:** Вы можете видеть только свои чаты (user_id) или чаты в ваших workspaces.

### Ошибка: "OpenRouter API error"
```json
{
  "success": false,
  "message": "OpenRouter API error: Rate limit exceeded",
  "data": null
}
```
**Решение:** Подождите 1 минуту (rate limit: 10 req/min) или обратитесь к администратору для апгрейда API key.

## Переменные окружения (.env)

```env
# OpenRouter Configuration
OPENROUTER_API_KEY=sk-or-v1-xxx  # Получить на https://openrouter.ai/keys
OPENROUTER_DEFAULT_CHAT_MODEL=qwen_coder  # По умолчанию для новых чатов

# RAG Configuration
RAG_CHUNK_SIZE=1500
RAG_CHUNK_OVERLAP=200
RAG_SEARCH_LIMIT=10

# OpenAI Embeddings (для RAG)
OPENAI_API_KEY=sk-xxx  # Для text-embedding-3-small
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Дополнительные ресурсы

- **OpenRouter Docs:** https://openrouter.ai/docs
- **Frontend Integration Guide:** `FRONTEND_CHAT_INTEGRATION.md`
- **RAG Architecture:** `RAG_SEARCH_IMPLEMENTATION.md`
- **Workspace Management:** `WORKSPACE_MANAGEMENT.md`
