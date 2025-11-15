# Исправление цепочки ошибок в Dependencies

## Проблема

**Симптом**: OpenRouter API error 429 (rate limit) неправильно логируется как "Storage (S3) сервис не доступен"

```
2025-11-15 20:46:11,913 - AIChatService - ERROR  - ❌ Ошибка OpenRouter API [429]: model=qwen/qwen3-coder:free, error=Provider returned error
2025-11-15 20:46:11,913 - src.core.exceptions.base - ERROR  - ❌ OpenRouter API error [429]: Provider returned error
2025-11-15 20:46:11,913 - src.dependencies.storage - ERROR  - ❌ ❌ Ошибка подключения к S3: 503: OpenRouter API error [429]: Provider returned error
2025-11-15 20:46:11,913 - src.core.exceptions.base - ERROR  - ❌ Storage (S3) сервис не доступен
```

## Корневая причина

**Все зависимости ловили `Exception` и подменяли исключение на `ServiceUnavailableException`**, даже если это были **бизнес-исключения** (`BaseAPIException`):

### ❌ До исправления

```python
# src/core/dependencies/storage.py
async def get_s3_client():
    try:
        async with S3ContextManager() as s3:
            yield s3
    except ServiceUnavailableException:
        raise
    except Exception as e:  # ❌ Ловит ВСЕ исключения, включая OpenRouterAPIError!
        logger.error("❌ Ошибка подключения к S3: %s", str(e))
        raise ServiceUnavailableException("Storage (S3)") from e
```

```python
# src/core/dependencies/base.py
class BaseDependency:
    async def handle_exception(self, e: Exception, service_name: str):
        # ❌ Всегда подменяет исключение на ServiceUnavailableException
        self.logger.error("Ошибка получения зависимости %s: %s", service_name, e)
        raise ServiceUnavailableException(service_name=service_name)
```

### ❌ Последовательность ошибки

1. `AIChatService._call_openrouter()` → выбрасывает `OpenRouterAPIError(429)`
2. `get_s3_client()` → перехватывает `Exception`, подменяет на `ServiceUnavailableException("Storage (S3)")`
3. **В логах:** "Storage (S3) сервис не доступен" вместо "OpenRouter API error [429]"

## Решение

### ✅ После исправления

**Правило**: Всегда пробрасывать `BaseAPIException` **ДО** обработки `Exception`.

```python
# src/core/dependencies/storage.py
from src.core.exceptions.base import BaseAPIException

async def get_s3_client():
    try:
        async with S3ContextManager() as s3:
            yield s3
    except ServiceUnavailableException:
        raise
    except BaseAPIException:  # ✅ Пробрасываем бизнес-исключения
        raise
    except Exception as e:
        logger.error("❌ Ошибка подключения к S3: %s", str(e))
        raise ServiceUnavailableException("Storage (S3)") from e
```

```python
# src/core/dependencies/base.py
from src.core.exceptions.base import BaseAPIException

class BaseDependency:
    async def handle_exception(self, e: Exception, service_name: str):
        # ✅ Пробрасываем бизнес-исключения
        if isinstance(e, BaseAPIException):
            raise
        
        self.logger.error("Ошибка получения зависимости %s: %s", service_name, e)
        raise ServiceUnavailableException(service_name=service_name)
```

## Исправленные файлы

1. **`src/core/dependencies/storage.py`**
   - Добавлен `except BaseAPIException: raise` перед `except Exception`
   - Добавлен import `BaseAPIException`

2. **`src/core/dependencies/cache.py`**
   - Добавлен `except BaseAPIException: raise` в `get_redis_dependency()`
   - Добавлен import `BaseAPIException`

3. **`src/core/dependencies/messaging.py`**
   - Добавлен `except BaseAPIException: raise` в `get_rabbitmq_connection()`
   - Добавлен `except BaseAPIException: raise` в `get_rabbitmq_context()`
   - Добавлен import `BaseAPIException`

4. **`src/core/dependencies/base.py`**
   - Добавлена проверка `isinstance(e, BaseAPIException)` в `handle_exception()`
   - Добавлен import `BaseAPIException`

5. **`src/core/dependencies/search.py`**
   - Добавлен `except BaseAPIException: raise` в `get_rag_search_service()`
   - Добавлен `except BaseAPIException: raise` в `get_search_service()`
   - Добавлен import `BaseAPIException`

## Принцип работы

### Иерархия исключений

```
Exception
└── HTTPException (FastAPI)
    └── BaseAPIException (наш базовый класс)
        ├── OpenRouterAPIError (429, 500, 503)
        ├── OpenRouterConfigError (500)
        ├── ChatNotFoundError (404)
        ├── DocumentServiceNotFoundError (404)
        └── ServiceUnavailableException (503)
```

### Правило обработки в dependencies

```python
try:
    # Код dependency
    pass
except ServiceUnavailableException:
    # Пробрасываем инфраструктурные ошибки 503
    raise
except BaseAPIException:
    # ✅ Пробрасываем ВСЕ бизнес-исключения (404, 429, 500 и т.д.)
    raise
except Exception as e:
    # Обрабатываем только настоящие инфраструктурные ошибки (сеть, база данных)
    logger.error("Ошибка подключения к %s: %s", service_name, e)
    raise ServiceUnavailableException(service_name)
```

## Тестирование

После исправления OpenRouter 429 должен логироваться корректно:

```
✅ Правильные логи после фикса:
2025-11-15 20:46:11,913 - AIChatService - ERROR  - ❌ Ошибка OpenRouter API [429]: model=qwen/qwen3-coder:free, error=Provider returned error
2025-11-15 20:46:11,913 - src.core.exceptions.base - ERROR  - ❌ OpenRouter API error [429]: Provider returned error
```

**Без подмены на "Storage (S3) сервис не доступен"!**

## Рекомендации для будущего

### При создании новых dependencies:

1. **ВСЕГДА** добавляй `except BaseAPIException: raise` перед `except Exception`
2. **Импортируй** `from src.core.exceptions.base import BaseAPIException`
3. **Не ловить** `Exception` без проверки типа исключения
4. **Используй** `BaseDependency.handle_exception()` для консистентности

### Паттерн для новых зависимостей:

```python
from src.core.exceptions.base import BaseAPIException
from src.core.exceptions.dependencies import ServiceUnavailableException

async def get_new_service():
    try:
        # Код создания сервиса
        return NewService()
    except ServiceUnavailableException:
        # Пробрасываем 503
        raise
    except BaseAPIException:
        # Пробрасываем бизнес-исключения (404, 429, 500)
        raise
    except Exception as e:
        # Обрабатываем только инфраструктурные ошибки
        logger.error("Ошибка создания NewService: %s", e, exc_info=True)
        raise ServiceUnavailableException("NewService")
```

## Связанные документы

- `docs/EXCEPTION_HANDLING.md` - общая архитектура обработки исключений
- `src/core/exceptions/README.md` - документация по кастомным исключениям
- `.github/copilot-instructions.md` - правила архитектуры для AI агента

## Дата исправления

2025-11-15
