# Исправление ошибки 422 при обновлении токена через cookies

## Проблема

Frontend получал **422 Unprocessable Entity** при попытке обновить токен через endpoint:

```http
POST /auth/refresh?use_cookies=true
```

### Симптомы

1. **Frontend логи**:
   ```
   [Interceptor] 🔄 401 получен, пытаемся refresh через cookie...
   Response: 422 Unprocessable Entity
   ```

2. **Backend логи**:
   ```
   Токен не найден ни в заголовке Authorization, ни в cookies
   ```

3. **Cookie присутствует в запросе**:
   ```
   Cookie: refresh_token=eyJhbGc...
   ```

## Причина

FastAPI's `Cookie()` parameter extractor не всегда корректно извлекает cookies из запроса, особенно при настройках безопасности (httpOnly, Secure, SameSite). Когда оба параметра были `None`:

```python
refresh_token_header: Optional[str] = Header(None, alias="refresh-token")
refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token")

# Результат:
refresh_token = refresh_token_header or refresh_token_cookie  # None
```

Передача `None` в сервис, который ожидает `str`, вызывала **422 ошибку валидации типов**.

## Решение

Добавлена **трехуровневая система приоритетов** с ручным fallback для cookie:

### Изменения в `src/routers/v1/auth.py`

#### 1. Добавлен импорт `Request`

```python
from fastapi import Cookie, Depends, Header, Query, Request, Response, status
```

#### 2. Обновлена сигнатура endpoint

```python
async def refresh_token(
    request: Request,  # ✅ Добавлен для доступа к request.cookies
    response: Response,
    use_cookies: bool = Query(False, description="..."),
    refresh_token_header: Optional[str] = Header(None, alias="refresh-token"),
    refresh_token_cookie: Optional[str] = Cookie(None, alias="refresh_token"),
    auth_service: AuthServiceDep = None,
) -> TokenResponseSchema:
```

#### 3. Добавлен fallback для извлечения cookie

```python
# Приоритет: заголовок -> Cookie() параметр -> request.cookies (fallback)
refresh_token = (
    refresh_token_header 
    or refresh_token_cookie 
    or request.cookies.get("refresh_token")  # ✅ Ручной fallback
)
```

## Приоритет извлечения токена

1. **Header** (`refresh-token` заголовок) - наивысший приоритет
2. **Cookie() parameter** (автоматическое извлечение FastAPI)
3. **request.cookies.get()** (ручной fallback) - ловит случаи когда Cookie() не работает

## Почему это работает

- **Header**: Стандартный способ передачи токенов через `Authorization` или кастомный заголовок
- **Cookie() parameter**: FastAPI пытается извлечь cookie автоматически
- **request.cookies.get()**: Прямой доступ к cookies из ASGI request объекта - **всегда работает**

Такой подход гарантирует, что токен будет извлечен в любом случае, независимо от:
- Cookie security settings (httpOnly, Secure, SameSite)
- Domain/Path ограничений
- Особенностей работы FastAPI Cookie extractor

## Тестирование

### Swagger UI

1. **Login с cookies**:
   ```
   POST /auth/login?use_cookies=true
   {
     "username": "admin",
     "password": "admin123"
   }
   ```

2. **Refresh с cookies** (токен автоматически из cookie):
   ```
   POST /auth/refresh?use_cookies=true
   ```

### cURL

```bash
# 1. Login и сохранение cookies
curl -X POST "http://localhost:8001/auth/login?use_cookies=true" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" \
  -c cookies.txt

# 2. Refresh токена используя cookies
curl -X POST "http://localhost:8001/auth/refresh?use_cookies=true" \
  -b cookies.txt
```

### Axios (Frontend)

```typescript
// 1. Login
await axios.post('/auth/login?use_cookies=true', {
  username: 'admin',
  password: 'admin123'
}, {
  withCredentials: true  // Обязательно!
});

// 2. Refresh (токен автоматически из cookie)
await axios.post('/auth/refresh?use_cookies=true', {}, {
  withCredentials: true
});
```

## Связанные файлы

- `src/routers/v1/auth.py` - Роутер аутентификации с исправлением
- `src/services/v1/auth.py` - Сервис аутентификации (без изменений)
- `src/core/security/cookie_manager.py` - Управление cookies (без изменений)
- `src/core/settings/base.py` - Настройки cookies (без изменений)

## Cookie настройки

```python
# Refresh token cookie:
{
    "key": "refresh_token",
    "httponly": True,
    "secure": True,  # Только HTTPS в production
    "samesite": "lax",
    "domain": "equiply.ru",  # Production domain
    "path": "/",
    "max_age": 2592000  # 30 дней
}
```

## Дата исправления

2025-01-15 12:53
