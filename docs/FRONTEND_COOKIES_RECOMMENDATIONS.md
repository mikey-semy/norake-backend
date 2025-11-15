# Frontend Recommendations: httpOnly Cookies + Public Endpoints

**Дата**: 2025-11-15
**Версия**: v2.0 (Cookie-Based Auth)
**Статус**: ✅ Backend Ready

---

## 🎯 КРИТИЧНО: Backend Использует httpOnly Cookies!

### ⚠️ Текущая Конфигурация Backend

```env
# .env (Production)
COOKIE_SAMESITE=Lax
COOKIE_SECURE=True
COOKIE_HTTPONLY=True
COOKIE_DOMAIN=equiply.ru
```

**Что это значит**:
- ✅ **Токены хранятся в httpOnly cookies** - JavaScript НЕ МОЖЕТ прочитать
- ✅ **Backend автоматически читает токены** из cookies (`extract_token_from_request()`)
- ✅ **Cookies автоматически отправляются** браузером с каждым запросом
- ❌ **localStorage.getItem('access_token')** - НЕ РАБОТАЕТ И НЕ НУЖЕН!
- ❌ **Ручная установка Authorization header** - НЕ НУЖНА для основных запросов

---

## 🚀 TL;DR - Что Нужно Сделать на Frontend

### 1. Настроить Axios для Работы с Cookies

```typescript
// api.config.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  withCredentials: true,  // ✅ ОБЯЗАТЕЛЬНО! Включает отправку cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// ⚠️ НЕ добавляйте Authorization header вручную!
// Backend сам читает токен из cookies
```

### 2. Обновить AuthProvider: Удалить localStorage

```typescript
// AuthProvider.tsx - УДАЛИТЬ ВСЕ localStorage операции

// ❌ НЕПРАВИЛЬНО (старый код)
const login = async (credentials) => {
  const response = await api.post('/auth/login', credentials);
  const { access_token, refresh_token } = response.data;
  localStorage.setItem('access_token', access_token);  // ❌ НЕ НУЖНО!
  localStorage.setItem('refresh_token', refresh_token);  // ❌ НЕ НУЖНО!
  setUser(response.data.user);
};

// ✅ ПРАВИЛЬНО (новый код)
const login = async (credentials) => {
  const response = await api.post('/auth/login', credentials, {
    withCredentials: true  // ✅ Backend установит Set-Cookie автоматически
  });
  setUser(response.data.user);  // ✅ Только user state, токены в cookies
};

const logout = async () => {
  await api.post('/auth/logout', {}, { withCredentials: true });  // ✅ Backend очистит cookies
  setUser(null);
};
```

### 3. Automatic Token Refresh (упрощённая версия для cookies)

```typescript
// api.interceptor.ts
import { api } from './api.config';

let isRefreshing = false;
let failedQueue: Array<{ resolve: Function; reject: Function }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Другой запрос уже обновляет токен - ждём
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then(() => {
          return api(originalRequest);
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // ✅ Refresh токен УЖЕ в cookies - просто вызываем endpoint
        await api.post('/auth/refresh', {}, { withCredentials: true });

        // ✅ Новый access_token автоматически установлен в cookie через Set-Cookie
        processQueue(null);
        isRefreshing = false;

        return api(originalRequest);  // Повторить с новым токеном из cookie
      } catch (refreshError) {
        // Refresh не удался - токены истекли окончательно
        processQueue(refreshError);
        isRefreshing = false;

        // Если это публичный endpoint - повторить без авторизации
        if (isPublicEndpoint(originalRequest.url)) {
          return api(originalRequest);  // Cookies невалидны, backend вернёт публичные данные
        }

        // Иначе - редирект на логин
        window.location.href = '/login';
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
    /\/workspaces\/[a-f0-9-]+$/  // Для публичных workspace (когда будет реализовано)
  ];
  return publicPatterns.some(pattern => pattern.test(url));
}
```

### 4. Graceful Degradation для Публичного Контента

```typescript
// DocumentListPage.tsx
const fetchDocuments = async () => {
  try {
    // ✅ Просто вызываем - токен УЖЕ в cookies
    const response = await api.get('/document-services', { withCredentials: true });
    setDocuments(response.data.data);
  } catch (error) {
    // Interceptor уже обработал 401 и повторил без токена
    console.error('Failed to fetch documents:', error);
    setDocuments([]);  // Показать пустой список или retry
  }
};
```

---

## 🔐 Как Работает Cookie-Based Auth

### Login Flow

```
1. Frontend: POST /auth/login { username, password }
               └─ withCredentials: true

2. Backend:  Проверяет credentials
               ├─ Генерирует access_token + refresh_token
               └─ Устанавливает через Set-Cookie:
                    Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax
                    Set-Cookie: refresh_token=<jwt>; HttpOnly; Secure; SameSite=Lax

3. Browser:  Автоматически сохраняет cookies

4. Frontend: Получает response.data.user (БЕЗ токенов)
               └─ setUser(user) → сохранить user state
```

### Authenticated Request Flow

```
1. Frontend: GET /document-services
               └─ withCredentials: true

2. Browser:  Автоматически добавляет в запрос:
               Cookie: access_token=<jwt>; refresh_token=<jwt>

3. Backend:  extract_token_from_request():
               ├─ Проверяет Authorization header (пусто)
               └─ Проверяет request.cookies['access_token'] ✅
               └─ Возвращает пользовательские + публичные документы
```

### Token Refresh Flow

```
1. Frontend: GET /document-services
2. Backend:  Токен истёк → 401 Unauthorized
3. Interceptor: Ловит 401 → POST /auth/refresh { withCredentials: true }
4. Backend:  Читает refresh_token из cookies
               ├─ Генерирует новый access_token
               └─ Set-Cookie: access_token=<new_jwt>
5. Interceptor: Повторяет оригинальный GET /document-services
6. Browser:  Отправляет с НОВЫМ access_token из cookie ✅
```

### Public Endpoint Flow (NO JWT)

```
1. Frontend: GET /document-services (токен истёк/отсутствует)
2. Backend:  request.cookies['access_token'] → None или невалиден
3. Backend:  OptionalUserDep → current_user = None
4. Service:  user_id = None → возвращает ТОЛЬКО публичные документы
5. Frontend: Получает 200 OK с публичными документами ✅
```

---

## ❌ Что НЕ ДЕЛАТЬ

### 1. НЕ Использовать localStorage для Токенов

```typescript
// ❌ НЕПРАВИЛЬНО
localStorage.setItem('access_token', token);
localStorage.setItem('refresh_token', token);
const token = localStorage.getItem('access_token');
api.defaults.headers.common['Authorization'] = `Bearer ${token}`;

// ✅ ПРАВИЛЬНО - токены в httpOnly cookies, управляются backend
api.defaults.withCredentials = true;
```

### 2. НЕ Добавлять Authorization Header Вручную

```typescript
// ❌ НЕПРАВИЛЬНО - переопределяет cookie механизм
api.interceptors.request.use((config) => {
  const token = getCookieByName('access_token');  // НЕ РАБОТАЕТ С httpOnly!
  config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ✅ ПРАВИЛЬНО - браузер автоматически отправляет cookies
api.defaults.withCredentials = true;  // Этого достаточно!
```

### 3. НЕ Блокировать Публичный Контент

```typescript
// ❌ НЕПРАВИЛЬНО
const ProtectedRoute = ({ children }) => {
  if (!isAuthenticated) {
    return <Navigate to="/login" />;  // Блокирует даже публичные страницы!
  }
  return children;
};

// ✅ ПРАВИЛЬНО - разделить публичные и приватные routes
const PublicRoute = ({ children }) => children;  // Всегда доступно
const PrivateRoute = ({ children }) => {
  if (!isAuthenticated) {
    return <Navigate to="/login" />;  // Только для приватных
  }
  return children;
};
```

---

## 🛠️ Migration Checklist

### Шаг 1: Обновить API Config

- [ ] Добавить `withCredentials: true` во все Axios instances
- [ ] Удалить `Authorization` header из `api.defaults.headers.common`
- [ ] Удалить Request Interceptor, который добавляет токен вручную

### Шаг 2: Обновить AuthProvider

- [ ] Удалить все `localStorage.setItem('access_token', ...)`
- [ ] Удалить все `localStorage.getItem('access_token')`
- [ ] Оставить только `user` state, токены управляются backend через cookies
- [ ] Обновить `login()` - только `setUser()`, БЕЗ сохранения токенов
- [ ] Обновить `logout()` - вызвать `/auth/logout` для очистки cookies на backend

### Шаг 3: Обновить Response Interceptor

- [ ] Изменить refresh logic - НЕ передавать токен в теле/headers
- [ ] Просто вызвать `POST /auth/refresh` с `withCredentials: true`
- [ ] Backend автоматически прочитает `refresh_token` из cookies
- [ ] Новый `access_token` автоматически придёт через `Set-Cookie`

### Шаг 4: Graceful Degradation для Public Endpoints

- [ ] Определить функцию `isPublicEndpoint(url)`
- [ ] В catch блоке после failed refresh - повторить публичные GET без токена
- [ ] Добавить UX индикатор "Публичный режим" / "Войдите для полного доступа"

### Шаг 5: Тестирование

- [ ] Логин → проверить Set-Cookie в Network tab
- [ ] Запрос к `/document-services` → проверить Cookie в Request Headers
- [ ] Дождаться истечения токена (15 мин) → убедиться в auto-refresh
- [ ] После истечения refresh token → публичные документы всё ещё доступны
- [ ] Попытка POST без токена → 401 Unauthorized

---

## 🔍 Debugging Tips

### 1. Проверить Cookies в DevTools

```
Chrome DevTools → Application Tab → Cookies → http://localhost:3000
│ Name          │ Value      │ HttpOnly │ Secure │ SameSite │
├───────────────┼────────────┼──────────┼────────┼──────────┤
│ access_token  │ <jwt>      │ ✅       │ ✅     │ Lax      │
│ refresh_token │ <jwt>      │ ✅       │ ✅     │ Lax      │
```

### 2. Проверить Request Headers в Network Tab

```
Request Headers:
Cookie: access_token=eyJ...; refresh_token=eyJ...

⚠️ НЕ ДОЛЖНО БЫТЬ:
Authorization: Bearer <token>  // ❌ Конфликтует с cookies!
```

### 3. Backend Logs для Debugging

```bash
# Запустить backend с DEBUG уровнем логирования
uv run dev

# Смотреть логи extract_token_from_request():
# "Токен найден в cookies"  ✅
# "Токен найден в заголовке Authorization"  ⚠️ Если видишь это - убери Authorization header!
```

### 4. CORS Issues (Cross-Origin)

Если фронт на `localhost:3000`, а API на `api.equiply.ru`:

**Backend Settings**:
```env
COOKIE_SAMESITE=None  # ✅ Разрешить cross-origin cookies
COOKIE_SECURE=True    # ✅ Обязательно для SameSite=None
COOKIE_DOMAIN=None    # ✅ НЕ устанавливать domain для cross-origin
```

**Frontend Axios**:
```typescript
const api = axios.create({
  baseURL: 'https://api.equiply.ru/api/v1',
  withCredentials: true,  // ✅ Отправлять cookies cross-origin
});
```

**Backend CORS Middleware**:
```python
# src/core/middlewares/cors.py - должно быть:
allow_credentials=True,  # ✅ Разрешить cookies с cross-origin
allow_origins=["http://localhost:3000", "https://equiply.ru"],  # ✅ Whitelist origins
```

---

## 📊 Endpoint Security Matrix (Updated)

| Endpoint | Без Cookies | С Валидными Cookies | С Истёкшими Cookies (после refresh) |
|----------|-------------|---------------------|--------------------------------------|
| **GET /document-services** | ✅ Только публичные | ✅ Публичные + свои | ✅ Публичные + свои (auto-refresh) |
| **GET /document-services/{id}** (публичный) | ✅ 200 OK | ✅ 200 OK | ✅ 200 OK |
| **GET /document-services/{id}** (приватный) | ❌ 403 Forbidden | ✅ 200 OK (если автор) | ✅ 200 OK (после refresh) |
| **POST /document-services** | ❌ 401 Unauthorized | ✅ 201 Created | ✅ 201 Created (после refresh) |
| **PUT /document-services/{id}** | ❌ 401 Unauthorized | ✅ 200 OK (если автор) | ✅ 200 OK (после refresh) |
| **DELETE /document-services/{id}** | ❌ 401 Unauthorized | ✅ 204 No Content | ✅ 204 (после refresh) |

---

## 🎨 UX Improvements

### 1. Public Mode Indicator

```typescript
// AppHeader.tsx
{user ? (
  <Badge color="green">
    <UserIcon /> {user.username}
  </Badge>
) : (
  <Badge color="gray">
    <GlobeIcon /> Публичный режим
    <Button size="sm" onClick={() => navigate('/login')}>
      Войти для полного доступа
    </Button>
  </Badge>
)}
```

### 2. Document Card: Show Access Level

```typescript
// DocumentCard.tsx
{document.is_public ? (
  <Badge color="green">
    <UnlockIcon /> Публичный
  </Badge>
) : (
  !user ? (
    <Tooltip title="Войдите для доступа к приватным документам">
      <Badge color="gray">
        <LockIcon /> Требуется вход
      </Badge>
    </Tooltip>
  ) : (
    <Badge color="orange">
      <LockIcon /> Приватный
    </Badge>
  )
)}
```

### 3. Login Prompt for Private Actions

```typescript
// DocumentDetailPage.tsx
const handleDownload = () => {
  if (!user && !document.is_public) {
    toast.info('Войдите для доступа к приватным документам', {
      action: {
        label: 'Войти',
        onClick: () => navigate('/login')
      }
    });
    return;
  }

  // Proceed with download
  downloadDocument(document.id);
};
```

---

## 📚 Related Backend Code

### Backend: Extract Token Logic

```python
# src/core/security/auth.py:61
@staticmethod
def extract_token_from_request(request: Request, header_token: str = None) -> str:
    # 1️⃣ Сначала проверяет Authorization header
    if header_token:
        logger.debug("Токен найден в заголовке Authorization")
        return header_token

    # 2️⃣ Если нет - проверяет cookies
    access_token_cookie = request.cookies.get("access_token")
    if access_token_cookie:
        logger.debug("Токен найден в cookies")
        return access_token_cookie

    # 3️⃣ Если ничего нет - выбрасывает TokenMissingError
    raise TokenMissingError()
```

### Backend: Cookie Settings

```python
# src/core/settings/base.py:632
@property
def access_token_cookie_params(self) -> Dict[str, Any]:
    return {
        "domain": self.COOKIE_DOMAIN,  # None для cross-origin
        "secure": self.COOKIE_SECURE,  # True для HTTPS
        "samesite": self.COOKIE_SAMESITE,  # Lax/None
        "httponly": self.COOKIE_HTTPONLY,  # True - защита от XSS
        "path": self.ACCESS_TOKEN_PATH,  # /
        "max_age": self.ACCESS_TOKEN_MAX_AGE,  # 900 (15 мин)
    }
```

---

## ✅ Summary

1. **Backend УЖЕ использует httpOnly cookies** → НЕ нужен localStorage
2. **Axios нужен только `withCredentials: true`** → браузер сам отправляет cookies
3. **Refresh токен УЖЕ в cookies** → просто вызвать `/auth/refresh`
4. **Public endpoints работают без cookies** → graceful degradation
5. **UX indicators** → показывать "Публичный режим" / "Требуется вход"

**Главное правило**: Не трогайте токены руками - всё управляется backend через Set-Cookie! 🍪
