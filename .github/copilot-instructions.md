# NoRake Backend - AI Agent Instructions

## Project Overview

NoRake Backend is a FastAPI-based collective memory system for tracking and resolving problems. Built with strict 4-layer architecture (Router → Service → Repository → Model) using PostgreSQL, Redis, and JWT authentication. Russian codebase with comprehensive dependency injection.

**Current Status**: Core authentication system implemented, ready for feature expansion

## Project Management with Plane

**CRITICAL**: All development tasks are managed in Plane (MCP integration available).

### Before Starting Work

1. **Check Plane for current tasks**: Use MCP Plane tools to list project issues
2. **Pick next task**: Start with the lowest unassigned NORAK-* number
3. **Update task status**: Mark issue as "in progress" before coding
4. **Read task description**: All requirements are in the issue description

### During Development

1. **Follow task requirements**: Implementation details are in Plane issue descriptions
2. **Check acceptance criteria**: Each task has specific success criteria
3. **Reference related tasks**: Issues reference each other (e.g., "depends on NORAK-1")
4. **Add comments**: Use Plane comments to document blockers or decisions

### After Completing Work

1. **Update issue status**: Mark as "completed" when all acceptance criteria met
2. **Add completion comment**: Brief summary of what was implemented
3. **Link related commits**: Reference NORAK-* in commit messages
4. **Move to next task**: Check Plane for dependent or next priority task

### Plane MCP Commands (Available)

```python
# List all project issues
mcp_plane_list_project_issues(project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58")

# Get specific issue details
mcp_plane_get_issue_using_readable_identifier(
    project_identifier="NORAK",
    issue_identifier="1"  # For NORAK-1
)

# Update issue status (mark as completed)
mcp_plane_update_issue(
    project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58",
    issue_id="<uuid>",
    issue_data={"state": "<completed_state_id>"}
)

# Add comment to issue
mcp_plane_add_issue_comment(
    project_id="c4ea1c3f-97d2-4f56-8aaa-5cce4b185f58",
    issue_id="<uuid>",
    comment_html="<p>Task completed. Implemented XYZ.</p>"
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