# Обновление: Публичные Endpoints с Опциональной Авторизацией

**Дата**: 2025-11-15
**Версия**: v1.0
**Статус**: ✅ Реализовано

---

## 📋 Краткое Описание Проблемы

**Симптом**: Frontend получал 401 Unauthorized на публичных endpoints после истечения JWT токена.

**Root Cause**: Все роутеры наследовали `ProtectedRouter`, который **всегда** требовал JWT токен для доступа к любым endpoints, включая публичные документы и workspaces.

**Service Layer**: Корректно реализована логика проверки `is_public` и `visibility`, но роутер блокировал запросы до обращения к сервису.

---

## ✅ Реализованные Изменения

### 1. Создан Optional Authentication Dependency

**Файл**: `src/core/security/auth.py`

Добавлена новая функция `get_current_user_optional()`:

```python
async def get_current_user_optional(
    request: Request,
    token: str = Depends(oauth2_scheme),
) -> UserCurrentSchema | None:
    """
    Получает данные текущего пользователя БЕЗ обязательной аутентификации.

    - Если токен валиден → возвращает UserCurrentSchema
    - Если токена нет/невалиден → возвращает None (НЕ выбрасывает исключение)
    """
    try:
        return await AuthenticationManager.get_current_user(request, token)
    except (TokenMissingError, TokenInvalidError):
        logger.debug("Опциональная аутентификация: токен отсутствует или невалиден")
        return None
    except Exception as e:
        logger.debug("Опциональная аутентификация: ошибка %s", str(e))
        return None
```

**Type Annotation**:
```python
OptionalUserDep = Annotated[UserCurrentSchema | None, Depends(get_current_user_optional)]
```

### 2. Рефакторинг Document Services Router

**Файл**: `src/routers/v1/document_services.py`

**ДО**:
- Класс: `DocumentServiceProtectedRouter(ProtectedRouter)` → JWT обязателен для ВСЕХ endpoints
- GET endpoints: требовали JWT даже для публичных документов

**ПОСЛЕ**:
- Класс: `DocumentServiceProtectedRouter(BaseRouter)` → selective authentication
- GET endpoints: используют `OptionalUserDep` → JWT опционален

#### Изменённые Endpoints

| Endpoint | Method | JWT | Изменение |
|----------|--------|-----|-----------|
| `/document-services` | GET | 🔓 Опционален | `CurrentUserDep` → `OptionalUserDep` |
| `/document-services/most-viewed` | GET | 🔓 НЕ требуется | Удалён `current_user` параметр |
| `/document-services/{id}` | GET | 🔓 Опционален | `CurrentUserDep` → `OptionalUserDep` |
| `/document-services` | POST | 🔒 Обязателен | Без изменений |
| `/document-services/{id}` | PUT | 🔒 Обязателен | Без изменений |
| `/document-services/{id}` | DELETE | 🔒 Обязателен | Без изменений |

#### Пример Кода (GET /document-services/{id})

**ДО**:
```python
async def get_document_service(
    service_id: UUID,
    current_user: CurrentUserDep = None,  # ❌ ОБЯЗАТЕЛЕН
    ...
):
    service = await document_service.get_document_service(
        service_id=service_id,
        user_id=current_user.id,  # ❌ current_user ВСЕГДА существует
        increment_views=increment_views,
    )
```

**ПОСЛЕ**:
```python
async def get_document_service(
    service_id: UUID,
    current_user: OptionalUserDep = None,  # ✅ ОПЦИОНАЛЕН
    ...
):
    user_id = current_user.id if current_user else None  # ✅ Может быть None
    service = await document_service.get_document_service(
        service_id=service_id,
        user_id=user_id,  # ✅ None для неавторизованных
        increment_views=increment_views,
    )
```

### 3. Service Layer (Без Изменений!)

**Файл**: `src/services/v1/document_services.py`

Service методы **УЖЕ** поддерживали `Optional[UUID]` для `user_id`:

```python
async def get_document_service(
    self,
    service_id: UUID,
    user_id: Optional[UUID] = None,  # ✅ Уже Optional!
    increment_views: bool = True,
) -> DocumentServiceModel:
    # ...
    if not service.is_public:
        if not user_id or service.author_id != user_id:
            raise DocumentAccessDeniedError(service_id=service_id)
    # ...
```

---

## 🔍 Как Это Работает

### Сценарий 1: Неавторизованный Пользователь

**Request**: `GET /api/v1/document-services` (без Authorization header)

1. ✅ `OptionalUserDep` → `current_user = None`
2. ✅ Роутер передаёт `user_id=None` в сервис
3. ✅ Сервис возвращает **только публичные** документы (`is_public=True`)
4. ✅ Response 200 OK с публичными документами

### Сценарий 2: Авторизованный Пользователь

**Request**: `GET /api/v1/document-services` (с Authorization: Bearer <token>)

1. ✅ `OptionalUserDep` → `current_user = UserCurrentSchema(id=...)`
2. ✅ Роутер передаёт `user_id=current_user.id` в сервис
3. ✅ Сервис возвращает **публичные + ваши приватные** документы
4. ✅ Response 200 OK с расширенным списком

### Сценарий 3: Попытка Доступа к Чужому Приватному Документу

**Request**: `GET /api/v1/document-services/{private_doc_id}` (без JWT)

1. ✅ `OptionalUserDep` → `current_user = None`
2. ✅ Роутер передаёт `user_id=None` в сервис
3. ✅ Сервис проверяет: `if not service.is_public and user_id != author_id`
4. ❌ Сервис выбрасывает `DocumentAccessDeniedError`
5. ❌ Response 403 Forbidden

---

## 🔒 Endpoint Security Matrix

| Endpoint | Без JWT | С JWT (свой) | С JWT (чужой) |
|----------|---------|--------------|---------------|
| **GET /document-services** | ✅ Только публичные | ✅ Публичные + свои | ✅ Публичные + свои |
| **GET /document-services/{id}** (публичный) | ✅ 200 OK | ✅ 200 OK | ✅ 200 OK |
| **GET /document-services/{id}** (приватный) | ❌ 403 Forbidden | ✅ 200 OK (если автор) | ❌ 403 Forbidden |
| **POST /document-services** | ❌ 401 Unauthorized | ✅ 201 Created | ✅ 201 Created |
| **PUT /document-services/{id}** | ❌ 401 Unauthorized | ✅ 200 OK (если автор) | ❌ 403 Forbidden |
| **DELETE /document-services/{id}** | ❌ 401 Unauthorized | ✅ 204 No Content (если автор) | ❌ 403 Forbidden |

---

## 📦 Измененные Файлы

```
src/
├── core/
│   └── security/
│       ├── auth.py               # ✅ Добавлен get_current_user_optional + OptionalUserDep
│       └── __init__.py           # ✅ Экспорт OptionalUserDep
└── routers/
    └── v1/
        └── document_services.py  # ✅ BaseRouter + OptionalUserDep для GET endpoints
```

---

## 🧪 Тестирование

### 1. Swagger UI (http://localhost:8000/docs)

#### Тест 1: Публичные документы без JWT

1. Открыть `GET /api/v1/document-services`
2. **НЕ** нажимать "Authorize"
3. Execute
4. ✅ Ожидается 200 OK с публичными документами

#### Тест 2: Приватный документ без JWT

1. Создать приватный документ через POST (с JWT)
2. Открыть `GET /api/v1/document-services/{private_id}`
3. **НЕ** использовать JWT в запросе
4. Execute
5. ❌ Ожидается 403 Forbidden

#### Тест 3: Все документы с JWT

1. Нажать "Authorize" → ввести JWT токен
2. Открыть `GET /api/v1/document-services`
3. Execute
4. ✅ Ожидается 200 OK с публичными + вашими приватными

### 2. cURL / Postman

```bash
# Публичные документы (БЕЗ токена)
curl http://localhost:8000/api/v1/document-services

# С токеном (расширенный список)
curl http://localhost:8000/api/v1/document-services \
  -H "Authorization: Bearer <your_jwt_token>"

# Попытка POST без токена (должна вернуть 401)
curl -X POST http://localhost:8000/api/v1/document-services \
  -F "file=@test.pdf" \
  -F "title=Test"
# ❌ 401 Unauthorized (как и должно быть)
```

---

## 🚀 Рекомендации для Фронтенда

### ⚠️ ВАЖНО: Backend использует httpOnly Cookies!

**См. актуальные рекомендации**: [FRONTEND_COOKIES_RECOMMENDATIONS.md](./FRONTEND_COOKIES_RECOMMENDATIONS.md)

Если ваш frontend использует **localStorage/Authorization header** - см. [FRONTEND_RECOMMENDATIONS_PROMPT.md](./FRONTEND_RECOMMENDATIONS_PROMPT.md) (legacy).

**Краткая сводка для httpOnly cookies**:
- ✅ `withCredentials: true` в Axios config
- ✅ НЕ использовать localStorage для токенов
- ✅ НЕ добавлять Authorization header вручную
- ✅ Backend автоматически читает токены из cookies
- ✅ Refresh: просто вызвать `/auth/refresh` с `withCredentials: true`

### 1. Graceful Degradation для Публичного Контента

**НЕ БЛОКИРУЙТЕ** отображение публичных документов при истечении токена!

#### ❌ НЕПРАВИЛЬНО (Старый Подход)

```typescript
// AuthProvider.tsx
if (!token) {
  // Блокируем доступ ко ВСЕМ страницам
  return <Navigate to="/login" />;
}
```

#### ✅ ПРАВИЛЬНО (Новый Подход)

```typescript
// DocumentListPage.tsx
const fetchDocuments = async () => {
  try {
    // Попытка с токеном (если есть)
    const response = await api.get('/document-services', {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    setDocuments(response.data);
  } catch (error) {
    if (error.response?.status === 401) {
      // Токен истёк - повторить без токена для публичных
      const publicResponse = await api.get('/document-services');
      setDocuments(publicResponse.data);
      setShowLoginPrompt(true); // Предложить войти для полного доступа
    }
  }
};
```

### 2. Реализовать Automatic Token Refresh

```typescript
// api.interceptor.ts
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Попытка обновить токен
        const { accessToken } = await refreshTokens();
        originalRequest.headers.Authorization = `Bearer ${accessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh не удался - переключиться на публичный режим
        if (isPublicEndpoint(originalRequest.url)) {
          delete originalRequest.headers.Authorization;
          return api(originalRequest);
        }
        // Приватный endpoint - редирект на login
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

function isPublicEndpoint(url: string): boolean {
  const publicPatterns = [
    /\/document-services$/,
    /\/document-services\/most-viewed$/,
    /\/document-services\/[a-f0-9-]+$/,
    /\/workspaces\/[a-f0-9-]+$/  // Для публичных workspace (TODO)
  ];
  return publicPatterns.some(pattern => pattern.test(url));
}
```

### 3. UX: Показать Промт для Неавторизованных

```typescript
// DocumentCard.tsx
{document.is_public ? (
  <Badge color="green">Публичный</Badge>
) : (
  !isAuthenticated ? (
    <Tooltip title="Войдите для доступа">
      <Badge color="gray">Требуется вход</Badge>
    </Tooltip>
  ) : (
    <Badge color="orange">Приватный</Badge>
  )
)}
```

### 4. Обработка Ошибок по Статус Кодам

| Статус | Сценарий | Действие Frontend |
|--------|----------|-------------------|
| 200 | Успешный запрос | Отобразить данные |
| 401 | Токен отсутствует/невалиден (POST/PUT/DELETE) | Редирект на /login |
| 403 | Нет прав на приватный ресурс | Показать "Доступ запрещён" |
| 404 | Документ не найден | Показать "Не найдено" |

```typescript
// errorHandler.ts
export function handleApiError(error: AxiosError, navigate: NavigateFunction) {
  const status = error.response?.status;

  switch (status) {
    case 401:
      // Если это GET запрос к публичному endpoint - повторить без токена
      if (isPublicGetRequest(error.config)) {
        return retryWithoutAuth(error.config);
      }
      // Иначе - требуется вход
      toast.error('Необходимо войти в систему');
      navigate('/login');
      break;

    case 403:
      toast.error('У вас нет доступа к этому ресурсу');
      break;

    case 404:
      toast.error('Ресурс не найден');
      break;

    default:
      toast.error('Произошла ошибка при загрузке данных');
  }
}
```

### 5. Indicator для Публичного/Приватного Режима

```typescript
// AppHeader.tsx
{isAuthenticated ? (
  <Badge color="green">
    <UserIcon /> {user.username}
  </Badge>
) : (
  <Badge color="gray">
    <GlobeIcon /> Публичный режим
    <Button size="sm" onClick={() => navigate('/login')}>
      Войти
    </Button>
  </Badge>
)}
```

---

## 🔮 TODO: Workspaces Endpoints (Следующий Шаг)

**Аналогичные изменения** нужно применить к:

- `src/routers/v1/workspaces.py`
  - GET `/workspaces/{id}` → `OptionalUserDep` (для PUBLIC workspaces)
  - GET `/workspaces/me` → `CurrentUserDep` (требует JWT)

**Service Layer** уже поддерживает:
```python
# src/services/v1/workspaces.py, line 727
if workspace.visibility == WorkspaceVisibility.PUBLIC:
    return  # Skip membership check
```

**План**:
1. Изменить `WorkspaceProtectedRouter(ProtectedRouter)` → `BaseRouter`
2. GET `/workspaces/{id}` → использовать `OptionalUserDep`
3. Проверить service метод `get_workspace(workspace_id, user_id)` на поддержку `Optional[UUID]`

---

## 📚 Связанные Документы

- [MCP_PLANE_QUICK_REFERENCE.md](./MCP_PLANE_QUICK_REFERENCE.md) - Интеграция с Plane для задач
- [ASYNC_RELATIONSHIPS_GUIDE.md](./ASYNC_RELATIONSHIPS_GUIDE.md) - Работа с relationships в SQLAlchemy
- [CLASS_BASED_PROTECTED_ROUTERS.md](./CLASS_BASED_PROTECTED_ROUTERS.md) - Архитектура роутеров

---

## ✅ Checklist для Code Review

- [x] ✅ Создан `get_current_user_optional()` в `auth.py`
- [x] ✅ Экспортирован `OptionalUserDep` в `security/__init__.py`
- [x] ✅ Рефакторинг `DocumentServiceProtectedRouter` → `BaseRouter`
- [x] ✅ GET endpoints используют `OptionalUserDep`
- [x] ✅ POST/PUT/DELETE endpoints остались с `CurrentUserDep`
- [x] ✅ Роутер передаёт `user_id=None` для неавторизованных
- [x] ✅ Service layer корректно обрабатывает `None` user_id
- [x] ✅ Обновлена документация OpenAPI (descriptions)
- [x] ✅ Удалены лишние 401 из responses
- [ ] ⏳ TODO: Аналогичные изменения для Workspaces router
- [ ] ⏳ TODO: Интеграционные тесты с/без JWT
- [ ] ⏳ TODO: Frontend updates по рекомендациям

---

**Автор**: AI Agent (GitHub Copilot)
**Дата создания**: 2025-11-15
**Статус**: ✅ Backend Ready for Testing
