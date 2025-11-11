# 📋 5-Day Sprint Plan - NoRake Backend MVP

**Deadline**: 15 ноября 2025 (Пятница EOD)
**Start**: 11 ноября 2025 (Понедельник)
**Project**: NoRake - Collective Memory System с AI + n8n
**Status**: 17/44 задач завершено (38.6%)

---

## 🎯 Цели спринта (ОБНОВЛЕНО)

**Завершено (38.6%)**:
1. ✅ Issues API (NORAK-1 до 10) - **День 1-2 завершён**
2. ✅ Templates API (NORAK-13 до 17) - **День 3 завершён**

**Критично для конкурса (оставшиеся 5 дней)**:
3. ⚠️ **pgvector + AI Infrastructure** (**Понедельник 11.11**)
4. ⚠️ **Workspaces + KB Models** (**Вторник 12.11**)
5. ⚠️ **n8n Workflows (КРИТИЧНО!)** (**Среда-Четверг 13-14.11**)
6. ⚠️ **RAG Search + API** (**Пятница 15.11 утро**)
7. 🎨 **Frontend (минимум)** - **После дедлайна / выходные**

> **⏰ ВНИМАНИЕ**: Осталось **5 рабочих дней** (11-15 ноября)
> **Приоритет**: Backend + n8n workflows для демо конкурса
> **Frontend**: Можно сделать минимальный после 15-го для презентации

> **📝 Заметка про KAG**: Knowledge-augmented Generation (KAG) — это улучшенная версия RAG с графом знаний.
> Планируется как **пост-спринт улучшение** после успешной демо. KAG добавит:
> - Граф связей между проблемами и решениями
> - Контекстное понимание отношений (причина-следствие)
> - Улучшенное ранжирование результатов
>
> **Реализация после конкурса**: Можно использовать Neo4j или PostgreSQL + pg_graph для графовых запросов.

---

## 📅 Распределение по дням (ОБНОВЛЁННЫЙ ПЛАН)

### ✅ **Дни 1-3 (Завершено)** - Issues + Templates MVP

**Завершено 10 ноября 2025**:
- ✅ NORAK-1 до 9: Issues полный CRUD API
- ✅ NORAK-13 до 17: Templates полный CRUD API
- ✅ Архитектура: 4 слоя, DI, exceptions, migrations

**Результат**: 17 задач Done, базовый API готов к расширению

---

### **День 4 (Понедельник 11.11)** - pgvector + AI Infrastructure

**NORAK-27: Настроить pgvector (2 часа)** ⚠️ НАЧАТЬ С ЭТОГО
- Обновить `docker-compose.dev.yml`: image → `pgvector/pgvector:pg16`
- Обновить `docker-compose.test.yml`: image → `pgvector/pgvector:pg16`
- Обновить `docker-compose.yml` (PROD): создать отдельную БД с pgvector
- Создать `scripts/init-pgvector.sql` с `CREATE EXTENSION vector;`
- Тестировать: `SELECT * FROM pg_extension WHERE extname = 'vector';`

**NORAK-30: AI Models (2 часа)**
- `AIModuleModel` (id, name, type, provider, config: JSONB, is_active)
- `WorkspaceModuleModel` (workspace_id, module_id, config: JSONB)
- Миграция Alembic

**NORAK-31: OpenRouter Integration (2 часа)**
- Создать `src/core/integrations/openrouter.py`
- Класс `OpenRouterEmbeddings` с методами:
  - `embed(texts: List[str]) -> List[List[float]]`
  - `embed_query(text: str) -> List[float]`
- Добавить в `.env.dev`: `OPENROUTER_API_KEY=...`
- Unit-тест с mock

**Итого**: **6 часов** (pgvector + AI models + OpenRouter)

---

### **День 5 (Вторник 12.11)** - Workspaces + Knowledge Base

**NORAK-28: Workspace Models (2 часа)**
- `WorkspaceModel` (id, name, slug, visibility, owner_id, settings: JSONB)
- `WorkspaceMemberModel` (workspace_id, user_id, role: Enum)
- Миграция Alembic

**NORAK-29: Workspace API минимум (3 часа)**
- WorkspaceRepository, WorkspaceService, WorkspaceRouter
- POST /workspaces - создать workspace
- GET /workspaces/me - список моих workspaces
- POST /workspaces/{id}/members - добавить участника
- GET /workspaces/{id}/members - список участников

**NORAK-32: Knowledge Base Models (3 часа)**
- `KnowledgeBaseModel` (id, workspace_id, name, description)
- `DocumentModel` (id, kb_id, filename, content_type, size)
- `DocumentChunkModel` (id, doc_id, content: TEXT, embedding: vector(1536), metadata: JSONB)
- Миграция Alembic с pgvector колонкой

**Итого**: **8 часов** (Workspaces + KB ready для загрузки)

---

### **День 6 (Среда 13.11)** - n8n Workflows Setup ⚠️ КРИТИЧНО

**NORAK-34: N8nWorkflow Model (1 час)**
- `N8nWorkflowModel` (id, workspace_id, name, workflow_id: str, webhook_url, is_active)
- API для регистрации workflows
- POST /n8n/workflows, GET /n8n/workflows

**NORAK-33: KB Upload API (2 часа)**
- POST /kb/{kb_id}/upload (multipart/form-data)
- Загрузка файла → сохранение в БД
- Вызов n8n webhook для индексации (background task)

**NORAK-35: n8n Workflow - Auto-categorize (2 часа)**
- Webhook → HTTP Request (OpenRouter) → Categorize → Update Issue
- Тестирование через Postman
- Регистрация в БД через API

**NORAK-36: n8n Workflow - KB Indexing (2 часа)**
- Webhook → Split Text (chunks 1000 chars) → OpenRouter Embeddings → pgvector INSERT
- SQL Node: `INSERT INTO document_chunks (doc_id, content, embedding) VALUES (...)`
- Тестирование с PDF файлом

**Итого**: **7 часов** (n8n infrastructure + 2 critical workflows)

---

### **День 7 (Четверг 14.11)** - RAG + Search

**NORAK-37: n8n Workflow - Smart Search (2 часа)**
- Webhook → Parallel:
  - Branch 1: DB Search (Issues with similar titles)
  - Branch 2: RAG Search (pgvector similarity)
  - Branch 3: Tavily Web Search
- Merge → Rank → Return JSON

**NORAK-39: RAG Service (3 часа)**
- `RAGService` с методами:
  - `similarity_search(query: str, kb_id: UUID, limit: int) -> List[DocumentChunk]`
  - Query: `SELECT * FROM document_chunks WHERE kb_id = $1 ORDER BY embedding <=> $2 LIMIT $3`
- OpenRouter для query embedding
- Redis кеш для embeddings

**NORAK-40: Hybrid SearchService (2 часа)**
- Объединение DB + RAG + n8n webhook call
- Ранжирование результатов (score merging)
- `SearchService.search(query, workspace_id, sources: List[str])`

**Итого**: **7 часов** (RAG + Smart Search working)

---

### **День 8 (Пятница 15.11)** - Search API + Demo Prep

**NORAK-41: Search API (1 час)**
- POST /api/v1/search
- `SearchRequestSchema` (query, workspace_id, sources: List[str], limit)
- `SearchResponseSchema` (results: List[source, title, content, score])

**NORAK-38: Weekly Digest Workflow (1 час)** [OPTIONAL]
- Cron (weekly) → Aggregate Stats → Email/Slack
- Можно пропустить если не успеваем

**Demo Preparation (2 часа)**
- Создать demo workspace "AEP-Production"
- Загрузить 3-5 тестовых PDF через API
- Проиндексировать через n8n
- Создать 5-10 Issues (часть через шаблоны)
- Протестировать Smart Search

**Documentation (2 часа)**
- Обновить README.md с инструкциями запуска
- Добавить примеры API calls
- Описание n8n workflows
- Скриншоты n8n UI

**Итого**: **6 часов** (API + Demo + Docs)

---

## 🎨 Frontend (Next.js 14) - После дедлайна

**NORAK-44** (12-16 часов) - **OPTIONAL / Выходные 16-17 ноября**

**Минимальный UI для презентации:**
- `/login` - вход
- `/workspaces/[id]/issues` - список проблем
- `/issues/[id]` - детали проблемы
- `/search` - умный поиск

---

## 📊 Статус задач в Plane (ОБНОВЛЕНО)

**Всего**: 44 задачи
**✅ Done**: 17 задач (38.6%) - Issues + Templates MVP
**📋 Todo**: 1 задача (NORAK-24 - валидация custom_fields)
**🔴 Backlog**: 26 задач (59%)

**Приоритеты на неделю 11-15 ноября:**
- **🔥 Urgent** (День 6-7): NORAK-34, 35, 36, 37 - n8n workflows
- **⚠️ High** (День 4-5): NORAK-27, 28, 29, 30, 31, 32 - Infrastructure
- **⚠️ High** (День 7-8): NORAK-39, 40, 41 - Search
- **📝 Medium**: NORAK-33, 38 - KB Upload, Digest
- **❌ Out of scope**: NORAK-42 (Comments), 43 (Preferences), 44 (Frontend)

---

## ⚠️ Риски и Митигация (ОБНОВЛЕНО)

## 🎨 Frontend (Next.js 14) - Параллельная разработка

**Задача**: **NORAK-44** (12-16 часов, 2 дня параллельно)

**Стек**:
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui компоненты
- TanStack Query (React Query)

**Страницы (минимум)**:
- `/login` - вход в систему
- `/workspaces` - список групп
- `/workspaces/[id]/issues` - проблемы группы
- `/issues/[id]` - детали проблемы
- `/search` - умный поиск

**Ключевые фичи**:
- Создать issue по шаблону
- Решить issue (статус GREEN)
- Умный поиск с AI результатами из разных источников
- Список workflows workspace

**Распределение**:
- **День 4** (4ч): Setup проекта + Login + API integration
- **День 5** (6ч): Workspaces + Issues list + Create issue
- **День 6** (6ч): Issue details + Search page + Resolve issue

---

## 🎯 Демо Сценарий для Конкурса (5-10 минут)

### 1. **Создание Workspace** (30 сек)
```bash
POST /api/v1/workspaces
{
  "name": "AEP-Production",
  "slug": "aep-ppp",
  "visibility": "private"
}
```

### 2. **Загрузка документации** (30 сек)
```bash
POST /api/v1/kb/{id}/upload
→ Загружаем 3 PDF мануала AEP
→ n8n workflow автоматически индексирует
```

### 3. **Создание Issues по шаблону** (1 мин)
```bash
POST /api/v1/issues (с template_id)
→ n8n workflow авто-категоризирует
→ Создали 3 проблемы (hardware, software, process)
```

### 4. **Smart Search** (2 мин)
```bash
POST /api/v1/search?q="ошибка E401 на оборудовании"
→ Результаты из:
  * БД Issues (похожие проблемы) - 2 результата
  * RAG документация AEP - 5 релевантных кусков
  * Tavily web search - 3 внешних ресурса
→ Показываем агрегированные + ранжированные результаты
```

### 5. **n8n Workflows** (2 мин)
- Показываем n8n UI с 4 активными workflows
- Демонстрируем лог выполнения KB Indexing
- Объясняем как работает Smart Search Helper

### 6. **Weekly Digest** (1 мин)
- Показываем автоматически сгенерированный отчёт
- Статистика: 15 проблем создано, 8 решено за неделю
- Топ категории: hardware (40%), software (35%)

### 7. **Архитектура** (2 мин)
- Показываем диаграмму 4-х слоёв
- Объясняем pluggable AI modules concept
- Подчёркиваем использование n8n как оркестратора

---

## 📊 Статус задач в Plane

**Всего**: 44 задачи
**Todo** (готовы к работе): NORAK-1 до NORAK-7 (Issues MVP)
**Backlog**: NORAK-8 до NORAK-44 (все новые задачи)

**Приоритеты**:
- **Urgent** (n8n workflows): NORAK-34, 35, 36, 37 ⚠️
- **High**: NORAK-1 до 10, 27, 28, 29, 30, 31, 32, 39, 40, 41, 44
- **Medium**: NORAK-33, 38, 42
- **Low**: NORAK-43

---

## ⚠️ Риски и Митигация (ОБНОВЛЕНО)

| Риск | Вероятность | Митигация | Статус |
|------|-------------|-----------|--------|
| pgvector не запустится в prod | Средняя | Отдельная БД с pgvector, тестирование на dev/test | ⏳ |
| OpenRouter rate limits | Низкая | Кеширование embeddings в Redis | ✅ |
| n8n workflows сложные | Высокая | Готовые templates, упростить логику | ⚠️ |
| Не успеем за 5 дней | Высокая | Убрать Comments, Preferences, Frontend из scope | ✅ |
| Баги в поиске | Средняя | День 8 на тестирование и фиксы | ⏳ |
| PROD database отдельная | Высокая | Создать новую БД с pgvector, изменить docker-compose.yml | 🔥 |

---

## ✅ Критерии успеха (Must Have для 15 ноября)

**Backend** (критично):
- ✅ Issues CRUD работает
- ✅ Templates для создания Issues
- ⚠️ Workspaces (группы) - **День 5**
- ⚠️ pgvector + RAG search - **День 4-7**
- 🔥 **3+ n8n workflows работают (КРИТИЧНО)** - **День 6-7**
- ⚠️ Smart Search показывает результаты из разных источников - **День 7-8**

**Frontend** (optional):
- ❌ Login + Issues CRUD UI - **После 15-го**
- ❌ Smart Search page - **После 15-го**

**Demo** (критично):
- ✅ Работающий demo workspace с данными - **День 8**
- ✅ README с инструкциями - **День 8**
- ✅ n8n workflows screenshots - **День 6-7**

---

## 🛠️ Технические решения (ОБНОВЛЕНО)

| Компонент | Решение | Изменения |
|-----------|---------|-----------|
| **Vector Store** | Supabase pgvector (PostgreSQL) | ✅ Все 3 окружения (dev/test/prod) |
| **PROD Database** | Отдельная БД с pgvector | 🔥 Создать новую БД в docker-compose.yml |
| **Embeddings** | OpenRouter API | ✅ Бесплатные модели |
| **n8n** | Self-hosted (Docker) | ✅ Уже есть + MCP подключен |
| **Frontend** | Next.js 14 + shadcn/ui | ❌ После дедлайна |
| **Deployment** | Docker Compose | ✅ 3 окружения готовы |

---

## 🚀 Следующие шаги (СЕЙЧАС - Понедельник 11.11)

**Приоритет 1: NORAK-27 - pgvector setup (2 часа)**
1. ✅ Обновить `docker-compose.dev.yml` → `pgvector/pgvector:pg16`
2. ✅ Обновить `docker-compose.test.yml` → `pgvector/pgvector:pg16`
3. 🔥 **Создать новую БД в `docker-compose.yml` (PROD)** с pgvector
4. ✅ Создать `scripts/init-pgvector.sql` с `CREATE EXTENSION vector;`
5. ✅ Тестировать на всех 3 окружениях

**Приоритет 2: NORAK-30-31 (4 часа)**
6. AI Models (AIModuleModel, WorkspaceModuleModel)
7. OpenRouter Integration (embeddings)

**Цель дня**: **pgvector работает на dev/test/prod + AI infrastructure готова**

---

## 📈 Прогресс Sprint (Daily Updates)

**10.11 (Воскресенье - Prep)**:
- ✅ 17 задач завершено (Issues + Templates MVP)
- ✅ План обновлён под 5 дней (11-15 ноября)
- ⏳ Готовы начать NORAK-27 (pgvector)

**11.11 (Понедельник - День 4)**:
- ⏳ NORAK-27: pgvector setup (dev/test/prod)
- ⏳ NORAK-30: AI Models
- ⏳ NORAK-31: OpenRouter Integration

**12.11 (Вторник - День 5)**:
- ⏳ NORAK-28-29: Workspaces MVP
- ⏳ NORAK-32: KB Models

**13.11 (Среда - День 6)**:
- ⏳ NORAK-34: N8nWorkflow Model
- ⏳ NORAK-33: KB Upload API
- ⏳ NORAK-35-36: 2 critical n8n workflows

**14.11 (Четверг - День 7)**:
- ⏳ NORAK-37: Smart Search Workflow
- ⏳ NORAK-39-40: RAG + Hybrid Search

**15.11 (Пятница - День 8)**:
- ⏳ NORAK-41: Search API
- ⏳ Demo Preparation
- ⏳ Documentation

---

## ✅ Критерии успеха (Must Have)

**Backend**:
- ✅ Issues CRUD работает
- ✅ Templates для создания Issues
- ✅ Workspaces (группы)
- ✅ pgvector + RAG search
- ⚠️ **3+ n8n workflows работают (КРИТИЧНО)**
- ✅ Smart Search показывает результаты из разных источников

**Frontend**:
- ✅ Login + Issues CRUD UI
- ✅ Smart Search page с результатами
- ✅ Workspaces navigation

**Demo**:
- ✅ Видео/скриншоты
- ✅ README с инструкциями
- ✅ Работающий demo workspace с данными

---

## 🛠️ Технические решения (утверждено)

| Компонент | Решение | Обоснование |
|-----------|---------|-------------|
| **Vector Store** | Supabase pgvector (PostgreSQL) | Встроенный, меньше инфраструктуры |
| **Embeddings** | OpenRouter API | Бесплатные модели |
| **n8n** | Self-hosted (Docker) | Уже есть + MCP подключен |
| **Frontend** | Next.js 14 + shadcn/ui | Быстрая разработка, красивый UI |
| **Deployment** | Docker Compose | Всё в одном месте |

---

## 🚀 Следующие шаги

1. **Сейчас**: Начать с NORAK-1 (создание IssueModel)
2. **День 1-2**: Завершить Issues MVP (NORAK-1 до NORAK-10)
3. **День 3**: Workspaces + Templates
4. **День 4-5**: AI + n8n (КРИТИЧНО!)
5. **День 6-7**: Search + Полировка + Demo

**Готов начинать?** 🚀
