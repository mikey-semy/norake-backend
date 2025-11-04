# Защищенные роутеры через классы (Class-based Protected Routers)

## 🎯 Концепция

Вместо ручного добавления `CurrentUserDep` к каждому эндпоинту, используем **наследование классов** для автоматической защиты всех роутов.

## 📋 Архитектура

```
BaseRouter (незащищенный)
    ↓
ProtectedRouter (защищенный)
    ↓
UsersRouter, ProjectsRouter, etc.
```

## 🔓 BaseRouter - Незащищенные роутеры

Базовый класс для всех роутеров. По умолчанию **НЕ требует аутентификации**.

**Файл:** `src/routers/base.py`

```python
class BaseRouter:
    """Базовый незащищенный роутер"""

    def __init__(
        self,
        prefix: str = "",
        tags: Optional[Sequence[str]] = None,
        dependencies: Optional[List[Depends]] = None,
    ):
        self.router = APIRouter(
            prefix=f"/{prefix}" if prefix else "",
            tags=tags or [],
            dependencies=dependencies or [],  # Глобальные зависимости
        )
        self.configure()
```

### Использование BaseRouter

Все **публичные эндпоинты** наследуются от `BaseRouter`:

```python
class AuthRouter(BaseRouter):
    """Публичные эндпоинты: login, register, logout"""

    def __init__(self):
        super().__init__(prefix="auth", tags=["Authentication"])

    def configure(self):
        @self.router.post("/login")
        async def login(form_data: OAuth2PasswordRequestForm):
            # ✅ Доступно БЕЗ токена
            return {"access_token": "..."}
```

**Незащищенные роутеры:**
- `AuthRouter` - `/auth/login`, `/auth/refresh`, `/auth/logout`
- `RegisterRouter` - `/register`
- `HealthRouter` - `/health`

---

## 🔒 ProtectedRouter - Защищенные роутеры

Класс-наследник `BaseRouter` с **автоматической аутентификацией** на уровне всего роутера.

**Файл:** `src/routers/base.py`

```python
class ProtectedRouter(BaseRouter):
    """
    Защищенный роутер с автоматической аутентификацией.

    Все эндпоинты автоматически защищены через CurrentUserDep.
    """

    def __init__(
        self,
        prefix: str = "",
        tags: Optional[Sequence[str]] = None,
        additional_dependencies: Optional[List[Depends]] = None,
    ):
        from src.core.security import get_current_user

        # Добавляем get_current_user как глобальную зависимость
        dependencies = [Depends(get_current_user)]
        if additional_dependencies:
            dependencies.extend(additional_dependencies)

        super().__init__(prefix=prefix, tags=tags, dependencies=dependencies)
```

### ✨ Магия ProtectedRouter

**1. Глобальная зависимость роутера:**

```python
self.router = APIRouter(
    prefix="/users",
    dependencies=[Depends(get_current_user)]  # 🔒 Защита ВСЕХ эндпоинтов
)
```

**2. CurrentUserDep доступен автоматически:**

```python
class UsersRouter(ProtectedRouter):
    def configure(self):
        @self.router.get("/profile")
        async def get_profile(current_user: CurrentUserDep = None):
            # current_user уже валидирован!
            return {"id": current_user.id}
```

---

## 🚀 Примеры использования

### Пример 1: Защищенный роутер пользователей

**Файл:** `src/routers/v1/users.py`

```python
from src.routers.base import ProtectedRouter
from src.core.security import CurrentUserDep

class UsersRouter(ProtectedRouter):
    """Все эндпоинты защищены автоматически"""

    def __init__(self):
        super().__init__(prefix="users", tags=["Users"])

    def configure(self):
        @self.router.get("/profile")
        async def get_profile(current_user: CurrentUserDep = None):
            # ✅ current_user доступен автоматически
            return CurrentUserResponseSchema(
                success=True,
                data=current_user
            )

        @self.router.get("/{user_id}")
        async def get_user_by_id(
            user_id: UUID,
            current_user: CurrentUserDep = None,
        ):
            # ✅ Защита + проверка роли админа
            if current_user.role != "admin":
                raise PermissionDeniedError()

            user = await user_service.get_user_by_id(user_id)
            return {"data": user}

        @self.router.put("/profile")
        async def update_profile(
            current_user: CurrentUserDep = None,
        ):
            # ✅ Только авторизованные пользователи
            await user_service.update_user(current_user.id, data)
            return {"success": True}
```

### Пример 2: Защищенный роутер проектов

```python
class ProjectsRouter(ProtectedRouter):
    """Все операции с проектами требуют аутентификации"""

    def __init__(self):
        super().__init__(prefix="projects", tags=["Projects"])

    def configure(self):
        @self.router.get("/")
        async def list_projects(current_user: CurrentUserDep = None):
            # Получаем только проекты текущего пользователя
            projects = await project_service.get_user_projects(current_user.id)
            return {"projects": projects}

        @self.router.post("/")
        async def create_project(
            data: ProjectCreateSchema,
            current_user: CurrentUserDep = None,
        ):
            # Создаем проект для текущего пользователя
            project = await project_service.create_project(
                owner_id=current_user.id,
                data=data
            )
            return {"project": project}
```

### Пример 3: Смешанный роутер (незащищенный + защищенные методы)

Если нужны **и публичные, и защищенные эндпоинты** в одном роутере:

```python
class BlogRouter(BaseRouter):
    """Смешанный роутер: публичные + защищенные эндпоинты"""

    def __init__(self):
        super().__init__(prefix="blog", tags=["Blog"])

    def configure(self):
        # ✅ Публичный эндпоинт (БЕЗ CurrentUserDep)
        @self.router.get("/posts")
        async def list_posts():
            return {"posts": await blog_service.get_all_posts()}

        # 🔒 Защищенный эндпоинт (С CurrentUserDep)
        @self.router.post("/posts")
        async def create_post(
            data: PostCreateSchema,
            current_user: CurrentUserDep = None,
        ):
            post = await blog_service.create_post(
                author_id=current_user.id,
                data=data
            )
            return {"post": post}

        # 🔒 Защищенный эндпоинт
        @self.router.delete("/posts/{post_id}")
        async def delete_post(
            post_id: UUID,
            current_user: CurrentUserDep = None,
        ):
            await blog_service.delete_post(post_id, current_user.id)
            return {"success": True}
```

---

## 📊 Сравнение подходов

### ❌ Старый подход (ручная защита)

```python
class UsersRouter(BaseRouter):
    @self.router.get("/profile")
    async def get_profile(current_user: CurrentUserDep = None):  # Повторяется везде
        return {"data": current_user}

    @self.router.put("/profile")
    async def update_profile(current_user: CurrentUserDep = None):  # Повторяется везде
        return {"success": True}

    @self.router.get("/{user_id}")
    async def get_user(user_id: UUID, current_user: CurrentUserDep = None):  # Повторяется везде
        return {"data": user}
```

**Проблемы:**
- ❌ Дублирование кода (`current_user: CurrentUserDep = None` в каждом методе)
- ❌ Легко забыть добавить защиту
- ❌ Нет явного указания что роутер защищен

### ✅ Новый подход (class-based защита)

```python
class UsersRouter(ProtectedRouter):  # 🔒 Защита на уровне класса
    @self.router.get("/profile")
    async def get_profile(current_user: CurrentUserDep = None):
        return {"data": current_user}

    @self.router.put("/profile")
    async def update_profile(current_user: CurrentUserDep = None):
        return {"success": True}

    @self.router.get("/{user_id}")
    async def get_user(user_id: UUID, current_user: CurrentUserDep = None):
        return {"data": user}
```

**Преимущества:**
- ✅ Явное указание защиты (`ProtectedRouter`)
- ✅ Автоматическая проверка токена для ВСЕХ эндпоинтов
- ✅ Невозможно забыть добавить защиту
- ✅ Меньше кода, больше читабельности
- ✅ Легко добавить дополнительные глобальные зависимости

---

## 🔧 Дополнительные возможности

### 1. Дополнительные зависимости

```python
class AdminRouter(ProtectedRouter):
    def __init__(self):
        # Добавляем проверку роли администратора
        super().__init__(
            prefix="admin",
            tags=["Admin"],
            additional_dependencies=[Depends(require_admin_role)]
        )
```

### 2. Rate limiting на уровне роутера

```python
class APIKeyRouter(ProtectedRouter):
    def __init__(self):
        super().__init__(
            prefix="api-keys",
            tags=["API Keys"],
            additional_dependencies=[Depends(rate_limiter)]
        )
```

### 3. Проверка подписки на уровне роутера

```python
class PremiumRouter(ProtectedRouter):
    def __init__(self):
        super().__init__(
            prefix="premium",
            tags=["Premium Features"],
            additional_dependencies=[Depends(require_premium_subscription)]
        )
```

---

## 📝 Регистрация роутеров

**Файл:** `src/routers/v1/__init__.py`

```python
from src.routers.base import BaseRouter
from .auth import AuthRouter          # Незащищенный
from .register import RegisterRouter  # Незащищенный
from .users import UsersRouter        # 🔒 Защищенный (ProtectedRouter)
from .projects import ProjectsRouter  # 🔒 Защищенный (ProtectedRouter)

class APIv1(BaseRouter):
    def configure(self):
        self.router.include_router(AuthRouter().get_router())
        self.router.include_router(RegisterRouter().get_router())
        self.router.include_router(UsersRouter().get_router())      # 🔒
        self.router.include_router(ProjectsRouter().get_router())   # 🔒
```

---

## 🎯 Правила использования

### Когда использовать BaseRouter:
- ✅ Публичные эндпоинты (login, register, health)
- ✅ Роутеры со смешанными правами доступа
- ✅ Эндпоинты, не требующие аутентификации

### Когда использовать ProtectedRouter:
- ✅ Все эндпоинты требуют аутентификации
- ✅ Работа с пользовательскими данными
- ✅ CRUD операции с защищенными ресурсами
- ✅ Административные панели

### Когда использовать смешанный подход:
- ✅ Часть эндпоинтов публичная, часть защищенная
- ✅ Используйте `BaseRouter` + ручной `CurrentUserDep` для защищенных методов

---

## 🚀 Итоговая структура

```
src/routers/
├── base.py                     # BaseRouter, ProtectedRouter
├── v1/
│   ├── __init__.py            # APIv1 (регистрация)
│   ├── auth.py                # AuthRouter (BaseRouter)
│   ├── register.py            # RegisterRouter (BaseRouter)
│   ├── health.py              # HealthRouter (BaseRouter)
│   ├── users.py               # UsersRouter (ProtectedRouter) 🔒
│   ├── projects.py            # ProjectsRouter (ProtectedRouter) 🔒
│   └── admin.py               # AdminRouter (ProtectedRouter + admin check) 🔒👑
```

---

## 📚 Резюме

| Аспект | BaseRouter | ProtectedRouter |
|--------|-----------|-----------------|
| **Аутентификация** | Опциональная | Обязательная |
| **CurrentUserDep** | Вручную для каждого метода | Автоматически для всех методов |
| **Использование** | Публичные эндпоинты | Защищенные эндпоинты |
| **Безопасность** | Требует явного указания | Защищено по умолчанию |
| **Примеры** | `/auth/login`, `/register` | `/users/profile`, `/projects` |

**🎉 Итог:** Используйте наследование классов для элегантной и безопасной защиты роутеров!
