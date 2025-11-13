# NoRake Backend - AI Agent Instructions

## Project Overview

NoRake Backend is a FastAPI-based collective memory system for tracking and resolving problems. Built with strict 4-layer architecture (Router → Service → Repository → Model) using PostgreSQL, Redis, and JWT authentication. Russian codebase with comprehensive dependency injection.

**Current Status**: Core authentication system implemented, ready for feature expansion

## Project Management with Plane

**CRITICAL**: All development tasks are managed in Plane (MCP integration available).

### Plane Connection Details

**ВАЖНО**: Убедись что MCP подключён с правильными параметрами:
- **PLANE_API_HOST_URL**: `https://plane.equiply.ru/`
- **PLANE_WORKSPACE_SLUG**: `projects` (НЕ "profitool-store"!)
- **Project ID**: `c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58`
- **Project Identifier**: `NORAK`

**API URL формат**: `https://plane.equiply.ru/api/v1/workspaces/projects/projects/`

### Git Workflow for Tasks

**ОБЯЗАТЕЛЬНО**: Для каждой задачи создавать отдельную ветку от `development`:

1. **Перед началом работы:**
   ```bash
   git checkout development
   git pull origin development
   git checkout -b feature/NORAK-XX-short-description
   ```

2. **Обновить статус в Plane** → "In Progress" (state_id: `6e814f64-8acd-4b61-992d-b89ebf6bf55e`)

3. **Разработка с коммитами:**
   ```bash
   git commit -m "feat(NORAK-XX): краткое описание изменений"
   ```

4. **После завершения:**
   - Обновить статус в Plane → "Done" (state_id: `749a5e1b-a62a-4b50-964b-816ffe1f4dad`)
   - Добавить комментарий в Plane с кратким описанием
   - Создать Pull Request в `development`
   - После мержа удалить feature-ветку

### Before Starting Work

1. **Получить задачу из Plane** по readable ID (NORAK-XX):
   ```python
   issue = await mcp_plane_get_issue_using_readable_identifier(
       project_identifier="NORAK",
       issue_identifier="1"  # Номер задачи
   )
   ```

2. **Создать ветку** от `development` с префиксом `feature/NORAK-XX-description`

3. **Обновить статус** на "In Progress":
   ```python
   await mcp_plane_update_issue(
       project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58",
       issue_id=issue["id"],  # UUID из предыдущего запроса
       state="6e814f64-8acd-4b61-992d-b89ebf6bf55e"  # In Progress
   )
   ```

4. **Прочитать описание задачи** - все требования в `description_html`

### During Development

1. **Следовать требованиям** из описания задачи в Plane
2. **Делать коммиты** с префиксом `feat(NORAK-XX):` или `fix(NORAK-XX):`
3. **Проверять acceptance criteria** перед завершением
4. **Добавлять комментарии в Plane** при блокерах или важных решениях

### After Completing Work

1. **Обновить статус** на "Done":
   ```python
   await mcp_plane_update_issue(
       project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58",
       issue_id=issue["id"],
       state="749a5e1b-a62a-4b50-964b-816ffe1f4dad"  # Done
   )
   ```

2. **Добавить комментарий** с кратким итогом:
   ```python
   await mcp_plane_add_issue_comment(
       project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58",
       issue_id=issue["id"],
       comment_html="<p><strong>Завершено</strong>: Реализовано XYZ. Коммит: abc123</p>"
   )
   ```

3. **Создать PR** в `development` с описанием изменений
4. **После мержа** удалить feature-ветку

### Plane State IDs (NoRake Backend)

```python
STATES = {
    "backlog": "ee55ae62-d94b-4236-8044-bf51830e89be",
    "todo": "a2bf76ee-e462-4e3b-aba8-732b7133e13a",
    "in_progress": "6e814f64-8acd-4b61-992d-b89ebf6bf55e",
    "done": "749a5e1b-a62a-4b50-964b-816ffe1f4dad",
    "cancelled": "a292224e-8a52-4835-81c1-9e7b36743166"
}
```

### Plane MCP Commands Reference

```python
# Получить задачу по readable ID (ВСЕГДА использовать это первым!)
issue = await mcp_plane_get_issue_using_readable_identifier(
    project_identifier="NORAK",
    issue_identifier="1"
)

# Извлечь актуальные ID
issue_id = issue["id"]
project_id = issue["project"]

# Список всех задач проекта
await mcp_plane_list_project_issues(
    project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58"
)

# Обновить статус задачи
await mcp_plane_update_issue(
    project_id=project_id,
    issue_id=issue_id,
    state="6e814f64-8acd-4b61-992d-b89ebf6bf55e"  # In Progress / Done
)

# Добавить комментарий (НЕ больше 2-3KB!)
await mcp_plane_add_issue_comment(
    project_id=project_id,
    issue_id=issue_id,
    comment_html="<p>Краткий комментарий</p>"
)

# Получить все статусы проекта
await mcp_plane_list_states(
    project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58"
)
```

### Development Documentation

All planning and architecture docs are in `docs/`:

- **`docs/DEVELOPMENT_PLAN.md`**: MVP roadmap with all phases and tasks
- **`docs/MVP_EXTENDED_PLAN.md`**: Detailed technical specs (models, API endpoints, JSONB structures)

Refer to these documents when implementing features to ensure alignment with overall architecture.

## Architecture: Strict Layer Separation

**CRITICAL**: Always follow `Router → Service → Repository → Model` flow. Never bypass layers.

```
src/
├── routers/     # HTTP layer - routing, auth checks, schema conversion
├── services/    # Business logic - validation, orchestration, domain operations
├── repository/  # Data access - queries, CRUD, database operations
├── models/      # SQLAlchemy ORM models with Russian docstrings
├── schemas/     # Pydantic validation/serialization (request/response)
└── core/        # Config, security, database, dependencies, exceptions
```

### Dependency Injection Pattern (MANDATORY)

All services use FastAPI's `Depends()` with typed annotations. **Never instantiate services manually**.

```python
# In core/dependencies/{feature}.py - create provider
async def get_auth_service(
    session: AsyncSessionDep,
    redis: RedisDep,
) -> AuthService:
    return AuthService(session=session, redis=redis)

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]

# In routers - inject with = None (REQUIRED)
async def login(
    auth_service: AuthServiceDep = None,  # = None is MANDATORY
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponseSchema:
    return await auth_service.authenticate(form_data)
```

## Service → Domain Object Boundary

**CRITICAL**: Services return SQLAlchemy models, NOT Pydantic schemas. Routers handle schema conversion.

```python
# ✅ CORRECT - Service returns domain object
async def get_user(self, user_id: UUID) -> UserModel:
    return await self.repository.get_item_by_id(user_id)

# ✅ CORRECT - Router converts to schema
user = await service.get_user(user_id)
schema = UserDetailSchema.model_validate(user)
return UserResponseSchema(success=True, data=schema)

# ❌ WRONG - Service returning schema
async def get_user(self, user_id: UUID) -> UserDetailSchema:
    user = await self.repository.get_item_by_id(user_id)
    return UserDetailSchema.model_validate(user)  # Don't do this in service!
```

## Development Workflow & Commands

All commands via UV package manager in `pyproject.toml`:

```bash
# Development setup (first time)
uv run bootstrap        # Initialize environment + dependencies

# Daily development
uv run dev             # Start development server with hot reload
uv run migrate         # Run Alembic migrations
uv run format          # Format code (black, isort)
uv run lint            # Lint code (flake8, mypy)
uv run check           # Check dependencies and configuration

# Infrastructure
uv run infra-test      # Start test infrastructure (Docker)
uv run start           # Start all services (Docker + backend)
```

**Environment Files**: `.env.dev` for development, `.env.test` for testing. Copy from `.env.example`.

## Database & Models Patterns

### BaseRepository Generic CRUD

All repositories inherit `BaseRepository[Model]` with comprehensive CRUD operations:

```python
# Use existing methods before creating custom ones
await self.get_item_by_id(user_id)           # Get by primary key
await self.get_item_by_field("email", email) # Get by any field
await self.filter_by(is_active=True)         # Filter with operators
await self.filter_by_ordered("created_at", is_active=True)  # Filter + sort
await self.create_item({"username": "john"}) # Create from dict
await self.update_item(user_id, {"phone": "+123"})  # Update
```

### ⚠️ КРИТИЧНО: Переиспользование кода в Repository

**ОБЯЗАТЕЛЬНО**: Всегда используй методы BaseRepository вместо дублирования кода!

❌ **НЕПРАВИЛЬНО** - дублирование логики выполнения запросов:
```python
async def get_by_category(self, category: str) -> List[IssueModel]:
    query = select(IssueModel).where(IssueModel.category == category)
    result = await self.session.execute(query)  # ❌ Дублирование!
    issues = result.scalars().all()
    return list(issues)
```

✅ **ПРАВИЛЬНО** - использование filter_by из BaseRepository:
```python
async def get_by_category(self, category: str) -> List[IssueModel]:
    return await self.filter_by(category=category)
```

✅ **ПРАВИЛЬНО** - комбинирование базовых методов:
```python
async def get_active_public(self) -> List[TemplateModel]:
    return await self.filter_by_ordered(
        "usage_count",
        ascending=False,
        is_active=True,
        visibility=TemplateVisibility.PUBLIC
    )
```

✅ **ПРАВИЛЬНО** - расширение базового метода при необходимости:
```python
async def search_by_text(self, text: str) -> List[IssueModel]:
    # Используем execute_and_return_scalars из BaseRepository
    query = select(IssueModel).where(
        or_(
            IssueModel.title.ilike(f"%{text}%"),
            IssueModel.description.ilike(f"%{text}%")
        )
    )
    return await self.execute_and_return_scalars(query)
```

**Правила переиспользования**:
1. **Сначала проверь BaseRepository** - возможно метод уже есть
2. **Используй filter_by/filter_by_ordered** для простой фильтрации
3. **Используй execute_and_return_scalars** для кастомных запросов
4. **НЕ дублируй** `result = await self.session.execute(query)` - это уже в base
5. **Если нужного метода нет** - добавь в BaseRepository для переиспользования

**Доступные методы BaseRepository**:
- `get_item_by_id(id)` - получение по UUID
- `get_item_by_field(field, value)` - получение по любому полю
- `filter_by(**kwargs)` - фильтрация с операторами (__gt, __lt, __in и т.д.)
- `filter_by_ordered(order_by, **kwargs)` - фильтрация + сортировка
- `execute_and_return_scalars(query)` - выполнение + список моделей
- `execute_and_return_scalar(query)` - выполнение + одна модель
- `count_items(**filters)` - подсчёт с фильтрами
- `exists_by_field(field, value)` - проверка существования

### Model Conventions

- **UUID primary keys** on all models via `BaseModel`
- **Russian docstrings** (Google style) for all models and methods
- **Relationships** use `Mapped[]` with proper foreign keys
- **Audit fields** (`created_at`, `updated_at`) from `BaseModel`

## Error Handling Architecture

**NO try-catch in routers!** Use domain exceptions + global handler.

```python
# ✅ Service raises domain exception
from src.core.exceptions import UserNotFoundError

async def get_user(self, user_id: UUID) -> UserModel:
    user = await self.repository.get_item_by_id(user_id)
    if not user:
        raise UserNotFoundError(user_id=user_id)  # Domain exception
    return user

# ✅ Router has clean code - no exception handling
async def get_user(user_id: UUID, service: UserServiceDep = None):
    user = await service.get_user(user_id)  # Let global handler catch exceptions
    schema = UserDetailSchema.model_validate(user)
    return UserResponseSchema(success=True, data=schema)
```

## Code Style Requirements

- **All comments/docstrings in Russian** (Google style)
- **Russian error messages**: `raise ValueError("Пользователь не найден")`
- **Type hints mandatory** for all public methods
- **Line length**: 88 characters (Black formatter)

### Logging Standard (ОБЯЗАТЕЛЬНО)

**КРИТИЧНО**: ВСЕ логи ДОЛЖНЫ использовать %-formatting, НЕ f-strings!

```python
# ✅ ПРАВИЛЬНО - %-formatting с параметрами
logger.info("Создан пользователь: %s", username)
logger.debug("Получено %d комментариев для проблемы %s", count, issue_id)
logger.warning("Пользователь %s не найден в workspace %s", user_id, workspace_id)
logger.error("Ошибка при создании проблемы %s: %s", issue_id, str(error))

# ❌ НЕПРАВИЛЬНО - f-strings НЕ использовать!
logger.info(f"Создан пользователь: {username}")  # НЕТ!
logger.debug(f"Получено {count} комментариев")  # НЕТ!
```

**Причины использования %-formatting**:
1. Отложенное форматирование - строка не форматируется, если уровень лога отключён
2. Производительность - экономия ресурсов на форматировании
3. Лучшая интеграция с системами мониторинга (структурированные логи)
4. Стандарт Python logging module

**Правила**:
- `%s` для строк, UUID, любых объектов с `__str__`
- `%d` для целых чисел (int)
- `%f` для чисел с плавающей точкой (float)
- `%r` для repr() представления (отладка)

### Schema Architecture (КРИТИЧНО)

**ВСЕ схемы ДОЛЖНЫ следовать строгой иерархии наследования:**

```python
# base.py - Доменные модели (БЕЗ системных полей id/timestamps)
class WorkspaceBaseSchema(CommonBaseSchema):
    """Базовая схема workspace БЕЗ системных полей."""
    name: str
    description: str | None = None

# requests.py - Входные данные (БЕЗ системных полей)
class WorkspaceCreateRequestSchema(BaseRequestSchema):
    """Схема для создания workspace (только бизнес-поля)."""
    name: str = Field(..., description="Название")
    description: str | None = Field(None, description="Описание")

# responses.py - Выходные данные
class WorkspaceDetailSchema(BaseSchema):  # С системными полями!
    """Детальная схема workspace (ВСЕ поля включая id/timestamps)."""
    name: str
    description: str | None
    # id, created_at, updated_at приходят из BaseSchema

class UserBriefSchema(CommonBaseSchema):  # БЕЗ системных полей!
    """Краткая информация о пользователе (БЕЗ id/timestamps)."""
    username: str
    email: str
```

**Правила наследования**:
1. `CommonBaseSchema` - базовая схема БЕЗ системных полей (id/timestamps)
2. `BaseRequestSchema` - для входных данных (requests.py), наследует CommonBaseSchema
3. `BaseSchema` - для detail схем (responses.py), С системными полями (id/created_at/updated_at)
4. `BaseResponseSchema` - для обёрток (success/message/data)

**Naming Convention (ОБЯЗАТЕЛЬНО)**:
- Входные данные: `*CreateRequestSchema`, `*UpdateRequestSchema`
- Выходные данные: `*DetailSchema`, `*ListItemSchema`, `*ResponseSchema`
- Обёртки: `*ResponseSchema` с полями `success: bool`, `message: str`, `data: ...`

**Brief vs Detail схемы**:
- **Brief схемы** (UserBriefSchema, TagBriefSchema): Наследуют `CommonBaseSchema`, БЕЗ id/timestamps
- **Detail схемы** (UserDetailSchema, IssueDetailSchema): Наследуют `BaseSchema`, С id/timestamps

**Пример правильной структуры**:
```python
# base.py
class IssueBaseSchema(CommonBaseSchema):  # БЕЗ системных полей
    title: str
    description: str

# requests.py  
class IssueCreateRequestSchema(BaseRequestSchema):  # БЕЗ системных полей
    title: str = Field(..., min_length=1)
    description: str = Field(...)

# responses.py
class UserBriefSchema(CommonBaseSchema):  # БЕЗ id/timestamps (brief!)
    username: str
    email: str

class IssueDetailSchema(BaseSchema):  # С id/timestamps (detail!)
    title: str
    description: str
    author: UserBriefSchema  # Вложенная brief схема
    # id, created_at, updated_at из BaseSchema

class IssueResponseSchema(BaseResponseSchema):  # Обёртка
    success: bool
    message: str
    data: IssueDetailSchema | None
```

**❌ Частые ошибки**:
1. Brief схемы наследуют BaseSchema вместо CommonBaseSchema
2. Request схемы содержат id/created_at/updated_at
3. Названия без *RequestSchema/*ResponseSchema суффиксов
4. Отсутствие Field() с description в request схемах

## Authentication & Security

- **JWT tokens** with automatic refresh token rotation
- **Redis blacklist** for logout/token invalidation
- **Role-based access**: `admin` (full access), `user` (customer role)
- **Argon2 password hashing** via passlib
- **Optional cookie storage** for tokens (supports both headers + cookies)

## Current Implementation Status

**✅ Implemented:**

- Base architecture (Router/Service/Repository/Model layers)
- Authentication system (login, refresh, logout, current user)
- User management with roles
- Exception handling with global handlers
- Database migrations with Alembic
- Development tooling (UV commands, Docker, formatting)

**⏳ Ready for Implementation:**

- Additional business domain models
- CRUD operations for new entities
- Business logic services
- API endpoints for new features

## File Naming Conventions

```
feature/
├── base.py          # Domain models (Pydantic base schemas)
├── requests.py      # Input schemas (Create, Update, Query)
├── responses.py     # Output schemas (Detail, List, Response wrappers)
└── __init__.py      # Exports
```

Follow this structure in `schemas/v1/`, `routers/v1/`, `services/v1/`, `repository/v1/`.

## Critical Development Rules

1. **Layer boundaries**: Router ↔ Schema conversion, Service ↔ Domain objects, Repository ↔ Database
2. **Dependency injection**: Always use typed dependencies, never manual instantiation
3. **Russian documentation**: All docstrings, comments, logging, error messages
4. **Domain exceptions**: Create custom exceptions, use global handler
5. **BaseRepository first**: Use existing CRUD methods before writing custom queries
6. **Environment config**: `.env.dev` for development, proper secret management

## When Adding New Features

**ALWAYS START WITH PLANE**: Check current task in Plane before implementing anything.

1. **Get task from Plane** using `mcp_plane_get_issue_using_readable_identifier`
2. **Read full requirements**: Issue description contains all implementation details
3. **Define domain model** in `models/v1/` (if required by task)
4. **Create schemas** (base/requests/responses) in `schemas/v1/`
5. **Build repository** extending `BaseRepository[Model]`
6. **Implement service** with business logic, returning domain objects
7. **Create dependency provider** in `core/dependencies/`
8. **Build router** with schema conversion and typed dependencies
9. **Add custom exceptions** for the domain in `core/exceptions/`
10. **Run tests** to verify acceptance criteria
11. **Update Plane task status** to "completed" with summary comment

### Task Implementation Checklist

Before marking task as complete in Plane:

- ✅ All acceptance criteria from issue description met
- ✅ Code follows 4-layer architecture (Router → Service → Repository → Model)
- ✅ Russian docstrings and comments added
- ✅ Type hints on all public methods
- ✅ Domain exceptions created and used
- ✅ Dependency injection configured
- ✅ No try-catch in routers (use global handler)
- ✅ Services return domain objects, not schemas
- ✅ Code formatted (black, isort)
- ✅ Tests written (if task requires)
