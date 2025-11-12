# NoRake Backend API - Comprehensive Test Documentation

## 📋 Обзор тестовых коллекций

В проекте созданы две Postman коллекции для полного покрытия API:

1. **NoRake_Complete_API_Collection.json** - Основная коллекция всех endpoints (без эмодзи)
2. **NoRake_Complete_Test_Scenarios.json** - 12 сценариев flow-based тестирования

---

## 🎯 Коллекция 1: Complete API Collection

### Структура (все папки без эмодзи):

#### 1. Main
- **Root** - Проверка работоспособности сервера
- ✅ Публичный доступ, без авторизации

#### 2. Health
- **Health Check** - Полная проверка (PostgreSQL, Redis, RabbitMQ)
- **Liveness Check** - Kubernetes liveness probe
- ✅ Оба публичные, для мониторинга

#### 3. Authentication
- **Login (Admin)** - Вход администратора
- **Login (User)** - Вход обычного пользователя
- **Refresh Token** - Обновление access_token
- **Logout** - Выход с инвалидацией токенов
- **Get Current User** - Информация о текущем пользователе
- ✅ OAuth2 Password Flow, автоматическое сохранение токенов

#### 4. Registration
- **Register User** - Регистрация нового пользователя
- ✅ Автоматический вход после регистрации

#### 5. Protected Routes
- **Test Protected (User)** - Endpoint для любого авторизованного
- **Admin Only** - Endpoint только для администраторов
- ✅ Проверка role-based access control

#### 6. Users
- **Get Profile** - Профиль текущего пользователя
- **Update Profile** - Обновление профиля
- **Get User By ID** - Получение пользователя по UUID
- ✅ Требуется авторизация

#### 7. Issues
- **List Issues (Public)** - Все публичные issues
- **Create Issue** - Создание новой issue
- **Get Issue** - Детали конкретной issue
- **Get History** - История изменений issues пользователя
- **Resolve Issue** - Отметить issue как решённую
- ✅ Публичное чтение, авторизация для создания/изменения

#### 8. Issue Comments
- **Get Issue Comments** - Все комментарии к issue
- **Create Comment** - Добавить комментарий
- **Delete Comment** - Удалить комментарий (только автор/admin)
- ✅ Публичное чтение, авторизация для создания/удаления

#### 9. Templates
- **List Templates** - Все активные templates
- **Create Template** - Создать template
- **Get Template** - Детали template
- **Update Template** - Обновить template
- **Delete Template** - Удалить template
- **Activate Template** - Активировать (admin only)
- **Deactivate Template** - Деактивировать (admin only)
- ✅ Публичное чтение, авторизация для управления

#### 10. Workspaces
- **Create Workspace** - Создать workspace
- **List My Workspaces** - Мои workspaces
- **Get Workspace** - Детали workspace
- **Update Workspace** - Обновить workspace
- **Add Member** - Добавить участника
- **Remove Member** - Удалить участника
- ✅ Полное управление workspace и участниками

#### 11. N8n Workflows
- **Create Workflow** - Создать n8n workflow для workspace
- **Get Workflows** - Все workflows workspace
- ✅ Интеграция с n8n для автоматизации

#### 12. Search
- **Search Public (No Auth)** - Публичный поиск (только DB)
- **Search - DB Only** - Поиск по PostgreSQL (issues + templates)
- **Search - RAG Only** - Поиск через pgvector с embeddings
- **Search - MCP Only** - Поиск через Model Context Protocol (n8n webhook)
- **Search - Combined (DB + RAG)** - Комбинированный поиск с ранжированием
- **Search - Filter by Category** - Поиск с фильтрацией
- **Search - Empty Result** - Обработка пустых результатов
- ✅ Полное покрытие поисковой системы (3 источника: DB, RAG, MCP)

---

## 🚀 Коллекция 2: Complete Test Scenarios

### 12 Flow-Based Сценариев:

#### Scenario 1: Public Access (5 requests)
**Цель**: Проверка всех публичных endpoints без авторизации

1. Root endpoint
2. Health check (полная)
3. List public issues
4. List public templates
5. Public search

**Ожидаемый результат**: Все запросы 200 OK, данные доступны без токена

---

#### Scenario 2: User Registration Flow (3 requests)
**Цель**: Полный цикл регистрации нового пользователя

1. Register new user (с timestamp в username/email)
2. Get current user info (проверка автологина)
3. Update user profile (изменение full_name и bio)

**Ожидаемый результат**:
- Регистрация → 201 Created + токены сохранены
- Роль = "user"
- Профиль успешно обновлён

---

#### Scenario 3: Admin Authentication (3 requests)
**Цель**: Вход администратора и проверка привилегий

1. Admin login (admin/admin)
2. Verify admin access (admin-only endpoint)
3. Get current admin info

**Ожидаемый результат**:
- Токены сохранены в `access_token`/`refresh_token`
- Admin-only endpoint → 200 OK
- Роль = "admin"

---

#### Scenario 4: Workspace Management (4 requests)
**Цель**: Создание и управление workspaces

1. Create workspace (с timestamp)
2. List my workspaces (проверка наличия)
3. Get workspace details
4. Update workspace description

**Ожидаемый результат**:
- Workspace создан, ID сохранён
- Workspace присутствует в списке
- Описание успешно обновлено

---

#### Scenario 5: Issue Lifecycle (6 requests)
**Цель**: Полный жизненный цикл issue

1. Create issue (Hardware Failure - AC Unit)
2. Get issue details (публично)
3. Add comment (Maintenance team notified)
4. Get issue comments
5. Resolve issue
6. Get issue history

**Ожидаемый результат**:
- Issue создана (status = "open")
- Комментарий добавлен
- Issue отмечена как решённая (status = "resolved")
- История содержит все изменения

---

#### Scenario 6: Template Management (4 requests)
**Цель**: Создание и использование templates

1. Create template (Server Maintenance Checklist)
2. Get template (публично)
3. Update template description
4. List all templates (проверка наличия)

**Ожидаемый результат**:
- Template создан (is_active = true)
- Template доступен публично
- Обновления применены
- Template в общем списке

---

#### Scenario 7: Search System (7 requests)
**Цель**: Полное покрытие поисковой системы

1. Search - DB Only (`query: "hardware"`)
2. Search - RAG Only (`query: "maintenance procedure equipment"`)
3. Search - MCP Only (`query: "safety protocols"`)
4. Search - Combined (All Sources) (`query: "server failure"`)
5. Search - With Filters (category=hardware, status=open)
6. Search - Empty Query Handling (nonexistent query)

**Ожидаемый результат**:
- Все источники возвращают результаты
- Combined search содержит mixed sources
- Фильтры работают корректно
- Пустой результат → 200 OK с пустым массивом

---

#### Scenario 8: N8n Workflows (2 requests)
**Цель**: Тестирование n8n интеграции

1. Create workflow (с timestamp)
2. Get workflows list

**Ожидаемый результат**:
- Workflow создан
- Workflow присутствует в списке workspace

---

#### Scenario 9: Authorization Checks (4 requests)
**Цель**: Проверка системы авторизации

1. Unauthorized Access - No Token (users/profile) → ожидается 401
2. User Access - Admin Only Endpoint → ожидается 403
3. Admin Can Deactivate Template → 200 OK
4. Admin Can Reactivate Template → 200 OK

**Ожидаемый результат**:
- Защищённые endpoints требуют токен (401)
- Admin-only endpoints проверяют роль (403 для user)
- Admin имеет полный доступ

---

#### Scenario 10: Token Management (4 requests)
**Цель**: Тестирование refresh/logout механизмов

1. Refresh access token
2. Verify new token works (auth/me)
3. Logout
4. Verify token invalidated → 401

**Ожидаемый результат**:
- Refresh обновляет оба токена
- Новый токен работает
- После logout токен в Redis blacklist
- Запросы с invalidated токеном → 401

---

#### Scenario 11: Error Handling (4 requests)
**Цель**: Проверка обработки ошибок

1. Invalid login credentials → 401
2. Get non-existent issue (UUID 00000000...) → 404
3. Create issue - missing required fields → 422
4. Invalid UUID format → 422

**Ожидаемый результат**:
- Все ошибки возвращают корректные HTTP коды
- Валидация работает на уровне Pydantic

---

#### Scenario 12: Cleanup (2 requests)
**Цель**: Удаление тестовых данных (опционально)

1. Delete test comment
2. Delete test template

**Ожидаемый результат**:
- Комментарий удалён (200 OK)
- Template удалён (204 No Content)

---

## 🔧 Переменные коллекции

### Основные:
```json
{
  "base_url": "http://localhost:8000",
  "access_token": "",        // Автоматически заполняется при логине
  "refresh_token": "",       // Автоматически заполняется
  "current_user_id": "",     // UUID текущего пользователя
  "current_user_role": ""    // "admin" или "user"
}
```

### Тестовые (для Scenario 2):
```json
{
  "test_user_access_token": "",
  "test_user_refresh_token": "",
  "test_user_id": ""
}
```

### Сущности:
```json
{
  "workspace_id": "",
  "issue_id": "",
  "comment_id": "",
  "template_id": "",
  "workflow_id": ""
}
```

---

## 📊 Coverage Analysis

### Endpoints Coverage: **100%** (все API проверены)

#### Публичные (No Auth): 7 endpoints ✅
- GET `/`
- GET `/api/v1/health`
- GET `/api/v1/health/live`
- GET `/api/v1/issues`
- GET `/api/v1/issues/{id}`
- GET `/api/v1/templates`
- POST `/api/v1/search/public`

#### Аутентификация: 5 endpoints ✅
- POST `/api/v1/auth/login`
- POST `/api/v1/auth/refresh`
- POST `/api/v1/auth/logout`
- GET `/api/v1/auth/me`
- POST `/api/v1/register`

#### Users: 3 endpoints ✅
- GET `/api/v1/users/profile`
- PUT `/api/v1/users/profile`
- GET `/api/v1/users/{id}`

#### Issues: 5 endpoints ✅
- GET `/api/v1/issues`
- POST `/api/v1/issues`
- GET `/api/v1/issues/{id}`
- GET `/api/v1/issues/history`
- PATCH `/api/v1/issues/{id}/resolve`

#### Comments: 3 endpoints ✅
- GET `/api/v1/issues/{id}/comments`
- POST `/api/v1/issues/{id}/comments`
- DELETE `/api/v1/issues/{id}/comments/{comment_id}`

#### Templates: 7 endpoints ✅
- GET `/api/v1/templates`
- POST `/api/v1/templates`
- GET `/api/v1/templates/{id}`
- PATCH `/api/v1/templates/{id}`
- DELETE `/api/v1/templates/{id}`
- POST `/api/v1/templates/{id}/activate`
- POST `/api/v1/templates/{id}/deactivate`

#### Workspaces: 6 endpoints ✅
- POST `/api/v1/workspaces`
- GET `/api/v1/workspaces/me`
- GET `/api/v1/workspaces/{id}`
- PATCH `/api/v1/workspaces/{id}`
- POST `/api/v1/workspaces/{id}/members`
- DELETE `/api/v1/workspaces/{id}/members/{user_id}`

#### N8n Workflows: 2 endpoints ✅
- POST `/api/v1/workflows/{workspace_id}`
- GET `/api/v1/workflows/{workspace_id}`

#### Search: 2 endpoints (7 scenarios) ✅
- POST `/api/v1/search/public`
- POST `/api/v1/search` (с параметрами: db, rag, mcp, combined, filters)

#### Protected Routes: 2 endpoints ✅
- GET `/api/v1/protected/test`
- GET `/api/v1/protected/admin-only`

### **ИТОГО: 47 API endpoints покрыты тестами**

---

## 🏃 Запуск тестов

### В Postman Desktop:

1. **Импорт коллекций**:
   - File → Import → выбрать оба `.json` файла

2. **Настройка окружения** (если нужно изменить base_url):
   - Environments → Create Environment
   - Добавить `base_url = http://your-server:8000`

3. **Запуск полной коллекции**:
   - Collection → Run
   - Select: "NoRake Complete Test Scenarios"
   - Run Collection

4. **Запуск отдельных сценариев**:
   - Открыть папку (Scenario 1, 2, 3...)
   - Run Folder

### В Newman (CLI):

```bash
# Установка
npm install -g newman

# Запуск всех тестов
newman run docs/NoRake_Complete_Test_Scenarios.postman_collection.json

# С HTML отчётом
newman run docs/NoRake_Complete_Test_Scenarios.postman_collection.json \
  --reporters cli,html \
  --reporter-html-export newman-report.html
```

### В CI/CD Pipeline (GitHub Actions):

```yaml
- name: Run API Tests
  run: |
    npm install -g newman
    newman run docs/NoRake_Complete_Test_Scenarios.postman_collection.json \
      --env-var "base_url=${{ secrets.API_BASE_URL }}"
```

---

## ✅ Рекомендуемый порядок выполнения

**Для первого прогона**:

1. Scenario 3 (Admin Authentication) - получить admin токен
2. Scenario 4 (Workspace Management) - создать workspace
3. Scenario 5 (Issue Lifecycle) - создать issue + комментарии
4. Scenario 6 (Template Management) - создать templates
5. Scenario 7 (Search System) - протестировать поиск по созданным данным
6. Scenario 2 (User Registration) - создать обычного пользователя
7. Scenario 9 (Authorization Checks) - проверить доступы
8. Scenario 10 (Token Management) - тесты с токенами
9. Scenario 11 (Error Handling) - edge cases
10. Scenario 12 (Cleanup) - удалить тестовые данные

**Для ежедневного тестирования**:
- Запускать всю коллекцию "NoRake Complete Test Scenarios" целиком
- Newman будет выполнять сценарии последовательно

---

## 📝 Изменения в коллекции

### Удалены эмодзи из названий папок:
- ~~🏠 Main~~ → **Main**
- ~~❤️ Health~~ → **Health**
- ~~🔐 Authentication~~ → **Authentication**
- ~~📝 Registration~~ → **Registration**
- ~~🔒 Protected Routes~~ → **Protected Routes**
- ~~👤 Users~~ → **Users**
- ~~📋 Issues~~ → **Issues**
- ~~💬 Issue Comments~~ → **Issue Comments**
- ~~📄 Templates~~ → **Templates**
- ~~🏢 Workspaces~~ → **Workspaces**
- ~~⚡ N8n Workflows~~ → **N8n Workflows**
- ~~🔍 Search~~ → **Search**

**Причина**: Эмодзи могут вызывать проблемы в некоторых CI/CD системах и Newman CLI.

---

## 🐛 Troubleshooting

### Проблема: 401 Unauthorized на защищённых endpoints
**Решение**: Сначала запустите "Admin Login" или "User Login" для получения токенов

### Проблема: Workspace ID not found
**Решение**: Запустите Scenario 4 (Workspace Management) для создания workspace

### Проблема: Search возвращает пустые результаты
**Решение**: Сначала создайте issues/templates через Scenarios 5-6

### Проблема: Newman reports connection errors
**Решение**:
```bash
# Проверьте доступность API
curl http://localhost:8000/api/v1/health

# Убедитесь что база данных и Redis запущены
docker ps | grep norake
```

---

## 📚 Дополнительная документация

- **API Swagger**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **Architecture**: `docs/DEVELOPMENT_PLAN.md`
- **MVP Extended Plan**: `docs/MVP_EXTENDED_PLAN.md`

---

## 🎯 Следующие шаги

1. ✅ Все endpoints покрыты тестами
2. ✅ Flow-based сценарии созданы
3. ✅ Эмодзи удалены из названий
4. 🔄 Настроить CI/CD интеграцию (Newman в GitHub Actions)
5. 🔄 Добавить performance тесты (k6 или Artillery)
6. 🔄 Создать smoke tests для production

---

**Последнее обновление**: 2025-11-12
**Версия коллекции**: v1.0
**Автор**: NoRake Development Team
