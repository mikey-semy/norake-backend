# NoRake Backend - AI Agent Instructions

## Project Overview

NoRake Backend is a FastAPI-based collective memory system for tracking and resolving problems. Built with strict 4-layer architecture (Router → Service → Repository → Model) using PostgreSQL, Redis, and JWT authentication. Russian codebase with comprehensive dependency injection.

**Current Status**: Core authentication system implemented, ready for feature expansion

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
- **Russian logging**: `logger.info("Создан пользователь: %s", username)`
- **Type hints mandatory** for all public methods
- **Line length**: 88 characters (Black formatter)

## Authentication & Security

- **JWT tokens** with automatic refresh token rotation
- **Redis blacklist** for logout/token invalidation
- **Role-based access**: `admin` (full access), `buyer` (customer role)
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

1. **Define domain model** in `models/v1/`
2. **Create schemas** (base/requests/responses) in `schemas/v1/`
3. **Build repository** extending `BaseRepository[Model]`
4. **Implement service** with business logic, returning domain objects
5. **Create dependency provider** in `core/dependencies/`
6. **Build router** with schema conversion and typed dependencies
7. **Add custom exceptions** for the domain in `core/exceptions/`