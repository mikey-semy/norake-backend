# Cookie-Based Auth: Quick Reference

**Статус**: ✅ Active Configuration  
**Backend**: httpOnly Cookies + Optional JWT  
**Дата**: 2025-11-15

---

## 🍪 Текущая Конфигурация

```env
# Production (.env)
COOKIE_SAMESITE=Lax
COOKIE_SECURE=True
COOKIE_HTTPONLY=True
COOKIE_DOMAIN=equiply.ru

# Development (.env.dev)
COOKIE_SAMESITE=None
COOKIE_SECURE=False
COOKIE_HTTPONLY=True
COOKIE_DOMAIN=None
```

---

## ✅ Frontend Checklist

### Axios Config

```typescript
const api = axios.create({
  baseURL: 'https://api.equiply.ru/api/v1',
  withCredentials: true,  // ✅ ОБЯЗАТЕЛЬНО!
});
```

### Login/Logout

```typescript
// Login - НЕ нужен localStorage!
await api.post('/auth/login', credentials, { withCredentials: true });
// Backend установит cookies через Set-Cookie

// Logout - очистить cookies на backend
await api.post('/auth/logout', {}, { withCredentials: true });
```

### Token Refresh

```typescript
// Просто вызвать - refresh_token УЖЕ в cookies
await api.post('/auth/refresh', {}, { withCredentials: true });
// Backend вернёт новый access_token через Set-Cookie
```

### Response Interceptor

```typescript
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        await api.post('/auth/refresh', {}, { withCredentials: true });
        return api(originalRequest);  // Повторить с новым токеном из cookie
      } catch (refreshError) {
        // Для публичных endpoints - повторить без авторизации
        if (isPublicEndpoint(originalRequest.url)) {
          return api(originalRequest);
        }
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

---

## ❌ Что НЕ Делать

- ❌ `localStorage.setItem('access_token', ...)`
- ❌ `localStorage.getItem('access_token')`
- ❌ `api.defaults.headers.common['Authorization']`
- ❌ `document.cookie` (httpOnly cookies недоступны через JS)
- ❌ Ручная установка Authorization header для refresh

---

## 🔍 Backend Flow

### extract_token_from_request()

```python
# src/core/security/auth.py:61
1. Проверяет Authorization header
2. Если пусто → проверяет request.cookies['access_token']
3. Если ничего → raises TokenMissingError
```

### OptionalUserDep

```python
# Для публичных GET endpoints
current_user: OptionalUserDep = None  # Может быть None
user_id = current_user.id if current_user else None
```

---

## 📚 Документация

- **Полная версия**: [FRONTEND_COOKIES_RECOMMENDATIONS.md](./FRONTEND_COOKIES_RECOMMENDATIONS.md)
- **Техническое обоснование**: [PUBLIC_ENDPOINTS_UPDATE.md](./PUBLIC_ENDPOINTS_UPDATE.md)
- **Legacy (localStorage)**: [FRONTEND_RECOMMENDATIONS_PROMPT.md](./FRONTEND_RECOMMENDATIONS_PROMPT.md)

---

## 🔧 Debugging

### Chrome DevTools → Application → Cookies

```
│ Name          │ HttpOnly │ Secure │ SameSite │
├───────────────┼──────────┼────────┼──────────┤
│ access_token  │ ✅       │ ✅     │ Lax      │
│ refresh_token │ ✅       │ ✅     │ Lax      │
```

### Network Tab → Request Headers

```
Cookie: access_token=<jwt>; refresh_token=<jwt>
```

**НЕ ДОЛЖНО БЫТЬ**:
```
Authorization: Bearer <token>  // ❌ Конфликт с cookies!
```

---

## 🆘 Частые Проблемы

### 1. "Cookies не отправляются"

✅ **Решение**: Добавить `withCredentials: true` в каждый запрос или в axios defaults

### 2. "401 на всех запросах после refresh"

✅ **Решение**: Backend вернул новый токен через Set-Cookie, но `withCredentials: false` в interceptor

### 3. "CORS error: credentials mode not allowed"

✅ **Решение**: Backend должен иметь:
```python
allow_credentials=True,
allow_origins=["http://localhost:3000"],  # НЕ "*"!
```

### 4. "Cookies работают локально, но не на production"

✅ **Решение**: Проверить:
- `COOKIE_SECURE=True` (требует HTTPS)
- `COOKIE_SAMESITE=Lax` (или `None` для cross-origin)
- Frontend и Backend на **одном домене** (или CORS правильно настроен)

---

**Главное правило**: Не трогайте токены руками - всё управляется backend через Set-Cookie! 🍪
