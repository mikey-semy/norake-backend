# ⚠️ ТРЕБУЕТСЯ ПЕРЕЗАПУСК СЕРВЕРА

## Проблема

Изменения в dependencies **не применяются автоматически** через hot reload, потому что:

1. Зависимости FastAPI загружаются **один раз при старте** приложения
2. Изменения в `src/core/dependencies/*.py` требуют **полного перезапуска**
3. Hot reload (uvicorn --reload) работает только для **роутеров и handlers**, но НЕ для dependencies

## Текущая ситуация

Лог показывает, что **старый код** всё ещё выполняется:

```
2025-11-15 20:57:02,967 - src.core.exceptions.base - ERROR  - ❌ OpenRouter API error [429]
2025-11-15 20:57:02,968 - src.dependencies.storage - ERROR  - ❌ ❌ Ошибка подключения к S3: 503: OpenRouter API error [429]
```

Второй лог из `storage.py:35` означает, что `except Exception as e` **всё ещё ловит** `OpenRouterAPIError`, хотя мы добавили `except BaseAPIException: raise` **ПЕРЕД** ним.

## Решение: Перезапустить сервер

### Вариант 1: Development сервер (рекомендуется)

```powershell
# Остановить текущий сервер (Ctrl+C в терминале)
# Затем запустить заново:
uv run dev
```

### Вариант 2: Docker (если используется)

```powershell
# Пересобрать и перезапустить контейнеры
docker-compose down
docker-compose up --build
```

### Вариант 3: Перезапуск через IDE

- **VS Code**: Остановить Debug session (Shift+F5) → Запустить заново (F5)
- **PyCharm**: Stop → Run (Ctrl+F5)

## Проверка после перезапуска

После перезапуска **OpenRouter ошибки НЕ должны подменяться** на "Storage (S3)":

### ❌ БЫЛО (неправильно):

```
2025-11-15 20:57:02,967 - src.core.exceptions.base - ERROR  - ❌ OpenRouter API error [429]
2025-11-15 20:57:02,968 - src.dependencies.storage - ERROR  - ❌ ❌ Ошибка подключения к S3: 503: OpenRouter API error [429]
2025-11-15 20:57:02,968 - src.core.exceptions.base - ERROR  - ❌ Storage (S3) сервис не доступен
```

### ✅ ДОЛЖНО БЫТЬ (правильно):

```
2025-11-15 20:57:02,967 - AIChatService - ERROR  - ❌ Ошибка OpenRouter API [429]: model=qwen/qwen3-coder:free, error=Provider returned error
2025-11-15 20:57:02,967 - src.core.exceptions.base - ERROR  - ❌ OpenRouter API error [429]: Provider returned error
```

**Без второго лога про S3!**

## Причина проблемы

FastAPI загружает dependencies при первом запуске через `Depends()`:

```python
# При старте приложения FastAPI делает:
get_s3_client_func = Depends(get_s3_client)

# И эта функция "заморожена" в памяти
# Изменения в файле НЕ применяются, пока не перезапустить
```

## Изменённые файлы (требуют перезапуска)

1. ✅ `src/core/dependencies/storage.py` - добавлен `except BaseAPIException: raise`
2. ✅ `src/core/dependencies/cache.py` - добавлен `except BaseAPIException: raise`
3. ✅ `src/core/dependencies/messaging.py` - добавлен `except BaseAPIException: raise` (2 места)
4. ✅ `src/core/dependencies/base.py` - добавлена проверка `isinstance(e, BaseAPIException)`
5. ✅ `src/core/dependencies/search.py` - добавлен `except BaseAPIException: raise` (2 места)

## После перезапуска

Проверьте логи при следующей ошибке OpenRouter:

- ✅ Должна быть **одна строка** с `OpenRouterAPIError`
- ❌ **НЕ должно быть** строки про "Storage (S3) сервис не доступен"

Если проблема повторяется - сообщите, приложите **полные логи** с timestamp.

## Дополнительная диагностика

Если после перезапуска проблема остаётся, выполните:

```powershell
# Проверить, что файл действительно изменён
Get-Content src\core\dependencies\storage.py | Select-String "BaseAPIException"

# Должно быть:
# from src.core.exceptions.base import BaseAPIException
# except BaseAPIException:
```

Если строк нет - значит изменения не сохранились. Проверьте Git status:

```powershell
git status src/core/dependencies/
git diff src/core/dependencies/storage.py
```
