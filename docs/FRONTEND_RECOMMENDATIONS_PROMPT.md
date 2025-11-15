# Frontend Recommendations: Handling Public Endpoints & Expired JWT

## ⚠️ ВАЖНО: Backend Использует httpOnly Cookies!

**🍪 См. актуальную версию**: [FRONTEND_COOKIES_RECOMMENDATIONS.md](./FRONTEND_COOKIES_RECOMMENDATIONS.md)

Этот документ содержит **legacy рекомендации для localStorage/Authorization header**.
Если ваш frontend использует **httpOnly cookies** (текущая настройка backend), используйте **FRONTEND_COOKIES_RECOMMENDATIONS.md**.

---

## 🎯 Быстрые Рекомендации (TL;DR)

**Проблема**: Frontend получает 401 на публичные endpoints после истечения JWT токена.

**Backend Статус**: ✅ **ИСПРАВЛЕНО** - публичные GET endpoints теперь работают без JWT:
- `GET /api/v1/document-services` - список документов (опциональный JWT)
- `GET /api/v1/document-services/{id}` - детали документа (опциональный JWT)
- `GET /api/v1/document-services/most-viewed` - топ документов (без JWT)

**Frontend Actions Required**:

1. **Graceful Degradation** - НЕ блокировать публичный контент при истечении токена
2. **Automatic Token Refresh** - обновлять токен перед истечением или после 401
3. **Retry without Auth** - для публичных GET endpoints повторить запрос без Authorization
4. **UX Indicators** - показывать "Публичный режим" / "Войдите для полного доступа"

---

## 🚀 Prompt для Frontend Developer

```markdown
# Task: Handle Optional JWT Authentication for Public Endpoints

## Context
Backend endpoints теперь поддерживают **опциональную авторизацию**:
- GET endpoints для документов работают БЕЗ JWT (возвращают только публичные)
- С JWT токеном возвращают публичные + ваши приватные документы
- POST/PUT/DELETE всё ещё требуют JWT и вернут 401 без токена

## Problem
Текущее поведение frontend:
1. При истечении JWT токена → AuthProvider блокирует ВСЕ запросы
2. Пользователь видит ошибки 401 даже для публичных данных
3. Приходится заново логиниться для просмотра публичного контента

## API Reference: Document Services

### Что Изменилось

**До**: Все endpoints требовали JWT токен → 401 при истечении
**Сейчас**: GET endpoints работают **БЕЗ токена** → возвращают публичные данные

### Endpoints с Опциональной Авторизацией

#### 1. `GET /api/v1/document-services` - Список документов

**Без токена** (публичный режим):
```http
GET /api/v1/document-services
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Список сервисов документов успешно получен",
  "data": [
    {
      "id": "uuid",
      "title": "Публичный документ",
      "is_public": true,
      "author": { "id": "uuid", "username": "author" },
      "created_at": "2025-11-15T10:00:00Z"
    }
    // Только публичные документы (is_public: true)
  ]
}
```

**С токеном** (авторизованный режим):
```http
GET /api/v1/document-services
Cookie: access_token=<jwt>
# ИЛИ
Authorization: Bearer <jwt>
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Список сервисов документов успешно получен",
  "data": [
    {
      "id": "uuid",
      "title": "Публичный документ",
      "is_public": true,
      ...
    },
    {
      "id": "uuid",
      "title": "Мой приватный документ",
      "is_public": false,
      ...
    }
    // Публичные + ваши приватные
  ]
}
```

**Query Parameters** (опциональные):
- `search` - поиск по title/description
- `category` - фильтр по категории
- `tags` - фильтр по тегам
- `page`, `size` - пагинация

---

#### 2. `GET /api/v1/document-services/{id}` - Детали документа

**Публичный документ БЕЗ токена**:
```http
GET /api/v1/document-services/550e8400-e29b-41d4-a716-446655440000
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Инструкция по использованию",
    "description": "Публичная инструкция",
    "is_public": true,
    "author": {
      "id": "uuid",
      "username": "admin",
      "email": "admin@example.com"
    },
    "files": [
      {
        "id": "uuid",
        "filename": "instruction.pdf",
        "file_size": 1024000,
        "mime_type": "application/pdf",
        "s3_url": "https://s3.amazonaws.com/..."
      }
    ],
    "view_count": 42,
    "created_at": "2025-11-15T10:00:00Z"
  }
}
```

**Приватный документ БЕЗ токена** → 403 Forbidden:
```json
{
  "success": false,
  "message": "Доступ к документу запрещён. Документ приватный.",
  "error_code": "DOCUMENT_ACCESS_DENIED",
  "details": {
    "service_id": "uuid"
  }
}
```

**Query Parameters**:
- `increment_views` (bool, default: true) - увеличить счётчик просмотров

---

#### 3. `GET /api/v1/document-services/most-viewed` - Популярные документы

**БЕЗ токена** (токен НЕ требуется):
```http
GET /api/v1/document-services/most-viewed?limit=10
```

**Response** (200 OK):
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "title": "Самый популярный документ",
      "is_public": true,
      "view_count": 1500,
      ...
    }
    // Топ публичных документов по просмотрам
  ]
}
```

**Query Parameters**:
- `limit` (int, default: 10) - количество документов

---

### Endpoints с Обязательной Авторизацией

#### 4. `POST /api/v1/document-services` - Создать документ

**Требуется JWT**:
```http
POST /api/v1/document-services
Cookie: access_token=<jwt>
Content-Type: multipart/form-data

file=<binary>
title=Мой документ
description=Описание
is_public=false
category=programming
tags=["python", "fastapi"]
```

**Response** (201 Created):
```json
{
  "success": true,
  "message": "Сервис документа успешно создан",
  "data": {
    "id": "uuid",
    "title": "Мой документ",
    "is_public": false,
    "author": { ... },
    "files": [{ ... }],
    "created_at": "2025-11-15T12:00:00Z"
  }
}
```

**БЕЗ токена** → 401 Unauthorized:
```json
{
  "success": false,
  "message": "Токен доступа отсутствует",
  "error_code": "TOKEN_MISSING"
}
```

---

#### 5. `PUT /api/v1/document-services/{id}` - Обновить документ

**Требуется JWT** (только автор):
```http
PUT /api/v1/document-services/{id}
Cookie: access_token=<jwt>
Content-Type: multipart/form-data

title=Обновлённое название
is_public=true
```

**Response** (200 OK) - аналогично POST

**Если НЕ автор** → 403 Forbidden:
```json
{
  "success": false,
  "message": "Доступ к документу запрещён. Только автор может изменять.",
  "error_code": "DOCUMENT_ACCESS_DENIED"
}
```

---

#### 6. `DELETE /api/v1/document-services/{id}` - Удалить документ

**Требуется JWT** (только автор):
```http
DELETE /api/v1/document-services/{id}
Cookie: access_token=<jwt>
```

**Response** (204 No Content) - пустой ответ

---

### Примеры Использования

#### Пример 1: Публичная страница документов

```typescript
// БЕЗ проверки авторизации
async function loadDocuments() {
  const response = await fetch('http://localhost:8000/api/v1/document-services', {
    credentials: 'include'  // Для cookies
  });

  const json = await response.json();

  if (json.success) {
    // Покажет публичные ИЛИ (публичные + приватные) если cookies валидны
    displayDocuments(json.data);
  }
}
```

#### Пример 2: Создание документа

```typescript
async function createDocument(formData: FormData) {
  const response = await fetch('http://localhost:8000/api/v1/document-services', {
    method: 'POST',
    credentials: 'include',  // Автоматически отправит access_token cookie
    body: formData
  });

  if (response.status === 401) {
    // Токен истёк - попробовать refresh
    await refreshToken();
    // Повторить запрос
    return createDocument(formData);
  }

  if (response.status === 403) {
    alert('Доступ запрещён');
  }

  return response.json();
}
```

#### Пример 3: Graceful Degradation

```typescript
async function fetchDocuments() {
  try {
    // Попытка с cookies (если есть токен)
    const response = await fetch('/api/v1/document-services', {
      credentials: 'include'
    });

    if (response.ok) {
      const json = await response.json();
      return json.data;  // Публичные + приватные (если авторизован)
    }

    // Если 401 - cookies истекли, но endpoint работает без них
    if (response.status === 401) {
      // Просто показать данные (backend вернёт публичные)
      const json = await response.json();
      return json.data;  // Только публичные
    }

  } catch (error) {
    console.error('Ошибка загрузки:', error);
    return [];
  }
}
```

---

### Поля Response Schema

#### DocumentServiceDetailSchema

```typescript
interface DocumentService {
  id: string;                    // UUID документа
  title: string;                 // Название
  description: string | null;    // Описание
  is_public: boolean;            // Публичный/приватный
  category: string | null;       // Категория

  author: {                      // Автор документа
    id: string;
    username: string;
    email: string;
  };

  files: Array<{                 // Прикреплённые файлы
    id: string;
    filename: string;
    file_size: number;           // Байты
    mime_type: string;           // "application/pdf", "image/png", etc.
    s3_url: string;              // Прямая ссылка на файл
  }>;

  tags: string[];                // Теги документа
  view_count: number;            // Количество просмотров

  created_at: string;            // ISO 8601 timestamp
  updated_at: string;            // ISO 8601 timestamp
}
```

#### Paginated Response

```typescript
interface PaginatedResponse<T> {
  success: true;
  message: string;
  data: T[];
  pagination: {
    total: number;       // Всего записей
    page: number;        // Текущая страница
    size: number;        // Размер страницы
    pages: number;       // Всего страниц
  };
}
```

---

### HTTP Status Codes

| Код | Значение | Когда происходит |
|-----|----------|------------------|
| 200 | OK | Успешный GET/PUT |
| 201 | Created | Успешный POST |
| 204 | No Content | Успешный DELETE |
| 400 | Bad Request | Невалидные данные |
| 401 | Unauthorized | Токен отсутствует/невалиден (POST/PUT/DELETE) |
| 403 | Forbidden | Нет прав на ресурс (чужой приватный документ) |
| 404 | Not Found | Документ не существует |
| 422 | Unprocessable Entity | Ошибка валидации Pydantic |

**Важно**: GET endpoints БЕЗ токена → **200 OK** (не 401!), просто вернут только публичные данные

---

### Матрица Поведения Endpoints

| Endpoint | Method | БЕЗ токена | С валидным токеном | С истёкшим токеном |
|----------|--------|------------|--------------------|--------------------|
| `/document-services` | GET | ✅ 200 (публичные) | ✅ 200 (публ + приват) | ⚠️ Попробовать refresh |
| `/document-services/most-viewed` | GET | ✅ 200 (топ публичных) | ✅ 200 (топ публичных) | ✅ 200 (топ публичных) |
| `/document-services/{id}` (публичный) | GET | ✅ 200 OK | ✅ 200 OK | ✅ 200 OK |
| `/document-services/{id}` (приватный) | GET | ❌ 403 Forbidden | ✅ 200 (если автор) | ⚠️ Попробовать refresh |
| `/document-services` | POST | ❌ 401 Unauthorized | ✅ 201 Created | ⚠️ Попробовать refresh → 201 |
| `/document-services/{id}` | PUT | ❌ 401 Unauthorized | ✅ 200 (если автор) | ⚠️ Попробовать refresh → 200 |
| `/document-services/{id}` | DELETE | ❌ 401 Unauthorized | ✅ 204 (если автор) | ⚠️ Попробовать refresh → 204 |

**Легенда**:
- ✅ - Успешный ответ
- ❌ - Ошибка
- ⚠️ - Требуется refresh токена → повторить запрос

---

### Аутентификация через Cookies (Текущая Реализация)

Backend **автоматически** читает токен из cookies:

```http
GET /api/v1/document-services
Cookie: access_token=<jwt>; refresh_token=<jwt>
```

**Что это значит для frontend**:
1. ✅ Токены **автоматически** отправляются браузером при каждом запросе
2. ✅ НЕ нужно вручную добавлять `Authorization` header (но можно)
3. ✅ При логине backend установит cookies через `Set-Cookie`
4. ✅ При refresh токена - новый `access_token` придёт автоматически

**Настройка fetch/axios**:
```typescript
// Fetch API
fetch('http://localhost:8000/api/v1/document-services', {
  credentials: 'include'  // ✅ Отправлять cookies
});

// Axios
axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  withCredentials: true  // ✅ Отправлять cookies
});
```

**См. полное руководство**: [FRONTEND_COOKIES_RECOMMENDATIONS.md](./FRONTEND_COOKIES_RECOMMENDATIONS.md)

---

### Token Refresh Endpoint

#### `POST /api/v1/auth/refresh` - Обновить access токен

**С cookies** (рекомендуется):
```http
POST /api/v1/auth/refresh
Cookie: refresh_token=<jwt>
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Токен успешно обновлён",
  "data": {
    "access_token": "eyJ...",  // Новый access токен
    "token_type": "bearer",
    "user": {
      "id": "uuid",
      "username": "user",
      "email": "user@example.com"
    }
  }
}
```

**Set-Cookie Header в ответе**:
```http
Set-Cookie: access_token=<new_jwt>; HttpOnly; Secure; SameSite=Lax
```

**Если refresh токен истёк** → 401:
```json
{
  "success": false,
  "message": "Токен невалиден или истёк",
  "error_code": "TOKEN_INVALID"
}
```

---

## Testing Checklist

### Базовые Сценарии

**1. Публичные документы (БЕЗ токена)**:
```bash
curl http://localhost:8000/api/v1/document-services
# Ожидаем: 200 OK, только документы с is_public=true
```

**2. Приватные + публичные (С токеном)**:
```bash
curl http://localhost:8000/api/v1/document-services \
  -H "Cookie: access_token=<jwt>"
# Ожидаем: 200 OK, публичные + свои приватные
```

**3. Топ просмотров (всегда без авторизации)**:
```bash
curl http://localhost:8000/api/v1/document-services/most-viewed
# Ожидаем: 200 OK, топ 10 публичных документов
```

**4. Доступ к приватному документу БЕЗ токена**:
```bash
curl http://localhost:8000/api/v1/document-services/{private_id}
# Ожидаем: 403 Forbidden
```

**5. Создание документа БЕЗ токена**:
```bash
curl -X POST http://localhost:8000/api/v1/document-services \
  -F "title=Test"
# Ожидаем: 401 Unauthorized
```

**6. Создание документа С токеном**:
```bash
curl -X POST http://localhost:8000/api/v1/document-services \
  -H "Cookie: access_token=<jwt>" \
  -F "title=Test" -F "is_public=false"
# Ожидаем: 201 Created
```

### Edge Cases

**7. Истёкший access токен + валидный refresh**:
```bash
# Шаг 1: Запрос с истёкшим токеном
curl http://localhost:8000/api/v1/document-services \
  -H "Cookie: access_token=<expired_jwt>; refresh_token=<valid_refresh>"
# Ожидаем: 401 Unauthorized, error_code: "TOKEN_EXPIRED"

# Шаг 2: Вызвать /auth/refresh
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Cookie: refresh_token=<valid_refresh>"
# Ожидаем: 200 OK, новый access_token в response + Set-Cookie header

# Шаг 3: Повторить оригинальный запрос с новым токеном
curl http://localhost:8000/api/v1/document-services \
  -H "Cookie: access_token=<new_jwt>"
# Ожидаем: 200 OK
```

**8. Оба токена истекли**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Cookie: refresh_token=<expired_refresh>"
# Ожидаем: 401 Unauthorized
# Действие: Редирект на /login
```

**9. Попытка редактировать чужой документ**:
```bash
curl -X PUT http://localhost:8000/api/v1/document-services/{other_user_id} \
  -H "Cookie: access_token=<jwt_user_A>" \
  -F "title=Hacked"
# Ожидаем: 403 Forbidden
```

**10. Логаут + попытка создать документ**:
```bash
# Шаг 1: Логаут
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Cookie: access_token=<jwt>"
# Ожидаем: 200 OK, cookies удалены (Max-Age=0)

# Шаг 2: Попытка создать документ
curl -X POST http://localhost:8000/api/v1/document-services \
  -F "title=Test"
# Ожидаем: 401 Unauthorized (токен в blacklist)
```

---

## Frontend Integration Guide

### 1. Обновить Axios/Fetch Конфиг

**Использование cookies** (рекомендуется):
```typescript
// Axios
axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  withCredentials: true  // ✅ Браузер сам добавит cookies
});

// Fetch API
fetch('http://localhost:8000/api/v1/document-services', {
  credentials: 'include'  // ✅ Отправлять cookies
});
```

**См. полное руководство**: [FRONTEND_COOKIES_RECOMMENDATIONS.md](./FRONTEND_COOKIES_RECOMMENDATIONS.md)

### 2. Обработка Публичных Endpoints

```typescript
// ✅ ПРАВИЛЬНО - работает с/без токена
const response = await axios.get('/document-services', {
  withCredentials: true
});

// Топ просмотров (не требует токен вообще)
const topDocs = await axios.get('/document-services/most-viewed');
```

### 3. Обработка 401/403 Ошибок

```typescript
axios.interceptors.response.use(
  response => response,
  async error => {
    const { status, data } = error.response;

    if (status === 401 && data.error_code === 'TOKEN_EXPIRED') {
      // Попытка refresh
      try {
        await axios.post('/auth/refresh', {}, { withCredentials: true });
        return axios.request(error.config); // Повторить запрос
      } catch {
        window.location.href = '/login'; // Refresh не удался
      }
    }

    if (status === 403) {
      console.error('Нет доступа к этому ресурсу');
    }

    throw error;
  }
);
```

### 4. Условный Рендеринг UI

```typescript
const [isAuthenticated, setIsAuthenticated] = useState(false);

useEffect(() => {
  axios.get('/auth/me', { withCredentials: true })
    .then(() => setIsAuthenticated(true))
    .catch(() => setIsAuthenticated(false));
}, []);

// В JSX
{isAuthenticated && <button onClick={createDocument}>Создать</button>}
```

---

## Ожидаемое Поведение После Реализации

| Сценарий | Было | Стало |
|----------|------|-------|
| Неавторизованный открывает `/documents` | ❌ Редирект на /login | ✅ Показывает публичные документы |
| JWT истёк, открывает `/documents` | ❌ 401, белый экран | ✅ Auto-refresh → показывает все |
| Refresh истёк, открывает `/documents` | ❌ 401, белый экран | ✅ Показывает публичные + промт "Войти" |
| Создаёт документ без JWT | ❌ 401, непонятная ошибка | ✅ Редирект на /login с сообщением |
| Просматривает чужой приватный документ | ❌ 401 | ✅ 403 Forbidden с сообщением |

---

## Справочник Endpoints

### Публичные (БЕЗ JWT)
- `GET /api/v1/document-services` - список документов (фильтры работают)
- `GET /api/v1/document-services/most-viewed` - топ 10 документов
- `GET /api/v1/document-services/{id}` - детали публичного документа

### Защищённые (Требуют JWT)
- `POST /api/v1/document-services` - создать документ
- `PUT /api/v1/document-services/{id}` - обновить (только автор)
- `DELETE /api/v1/document-services/{id}` - удалить (только автор)
- `GET /api/v1/document-services/{id}` (приватный) - детали (только автор)

### Аутентификация
- `POST /api/v1/auth/login` - логин (устанавливает cookies)
- `POST /api/v1/auth/refresh` - обновить access токен
- `POST /api/v1/auth/logout` - выход (удаляет cookies)
- `GET /api/v1/auth/me` - текущий пользователь

---

## Вопросы?

**Q**: Что если refresh токен тоже истёк?
**A**: Frontend получит 401 на `/auth/refresh` → редирект на `/login`.

**Q**: Нужно ли хранить токены в localStorage?
**A**: НЕТ. Backend использует httpOnly cookies - JavaScript не может читать/записывать токены. Это безопаснее.

**Q**: Как понять, что пользователь авторизован?
**A**: Вызвать `GET /auth/me` с `withCredentials: true`. Если 200 OK → авторизован, если 401 → нет.

**Q**: Workspaces тоже поддерживают публичный доступ?
**A**: ⏳ TODO на backend. Пока все workspaces требуют JWT. Будет реализовано аналогично документам.

---

## Быстрая Справка

**Полная документация**:
- [FRONTEND_COOKIES_RECOMMENDATIONS.md](./FRONTEND_COOKIES_RECOMMENDATIONS.md) - Подробное руководство по cookie-based аутентификации
- [COOKIE_AUTH_QUICK_REFERENCE.md](./COOKIE_AUTH_QUICK_REFERENCE.md) - Чит-шит с примерами кода
- [PUBLIC_ENDPOINTS_UPDATE.md](./PUBLIC_ENDPOINTS_UPDATE.md) - Технические детали реализации на backend


```
