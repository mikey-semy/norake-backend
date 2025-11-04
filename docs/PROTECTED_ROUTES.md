# Защита роутеров с помощью аутентификации

Этот документ описывает, как использовать модуль аутентификации для защиты эндпоинтов API.

## Быстрый старт

### 1. Использование в роутерах

```python
from src.core.security import CurrentUserDep
from src.routers.base import BaseRouter

class MyRouter(BaseRouter):
    def configure(self):
        @self.router.get("/protected")
        async def protected_endpoint(
            current_user: CurrentUserDep,  # Автоматическая проверка токена
        ):
            return {
                "message": f"Привет, {current_user.username}!",
                "user_id": str(current_user.id),
                "role": current_user.role
            }
```

### 2. Проверка роли пользователя

```python
from fastapi import HTTPException, status
from src.core.security import CurrentUserDep

@router.get("/admin-only")
async def admin_only(current_user: CurrentUserDep):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуется роль администратора"
        )

    return {"admin_data": "Секретная информация"}
```

### 3. Использование токена из заголовка или cookies

Модуль автоматически поддерживает оба способа передачи токена:

**Через заголовок Authorization:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/v1/protected/test
```

**Через cookies:**
```bash
curl -b "access_token=YOUR_TOKEN" http://localhost:8000/api/v1/protected/test
```

## Тестирование

### 1. Получение токена

```bash
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=your_password
```

Ответ:
```json
{
  "success": true,
  "message": "Аутентификация успешна",
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

### 2. Использование токена

```bash
GET /api/v1/protected/test
Authorization: Bearer eyJhbGc...
```

Ответ:
```json
{
  "success": true,
  "message": "Привет, john_doe! Ты аутентифицирован.",
  "data": {
    "user_id": "uuid-here",
    "username": "john_doe",
    "email": "user@example.com",
    "role": "user"
  }
}
```

## Доступные эндпоинты

### Тестовые защищенные эндпоинты

- `GET /api/v1/protected/test` - Тестовый защищенный эндпоинт
- `GET /api/v1/protected/admin-only` - Только для администраторов

## Обработка ошибок

Модуль автоматически обрабатывает следующие случаи:

- **401 Unauthorized**: Токен отсутствует или недействителен
- **403 Forbidden**: Недостаточно прав (например, требуется роль admin)
- **419 Token Expired**: Токен истек (нужно обновить через `/auth/refresh`)

## Архитектура

```
src/core/security/
├── auth.py              # Модуль аутентификации (get_current_user)
├── token_manager.py     # Работа с JWT токенами
└── cookie_manager.py    # Работа с cookies

src/routers/v1/
└── protected.py         # Пример защищенных роутеров
```

## CurrentUserSchema

Объект `current_user` содержит следующие поля:

```python
class UserCurrentSchema:
    id: UUID              # ID пользователя
    username: str         # Имя пользователя
    email: EmailStr       # Email пользователя
    role: str            # Роль (admin/user)
```

## Примеры использования

### Защита всего роутера

```python
from src.core.security import CurrentUserDep

class ProtectedRouter(BaseRouter):
    def configure(self):
        # Все эндпоинты требуют аутентификации

        @self.router.get("/endpoint1")
        async def endpoint1(current_user: CurrentUserDep):
            pass

        @self.router.post("/endpoint2")
        async def endpoint2(current_user: CurrentUserDep):
            pass
```

### Условная защита

```python
from typing import Optional
from src.schemas.v1.auth.base import UserCurrentSchema
from src.core.security import get_current_user

@router.get("/optional-auth")
async def optional_auth(
    current_user: Optional[UserCurrentSchema] = Depends(get_current_user)
):
    if current_user:
        return {"message": f"Привет, {current_user.username}!"}
    return {"message": "Анонимный пользователь"}
```
