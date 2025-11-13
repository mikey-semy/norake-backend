# Fixtures Management Commands

## Автоматическая загрузка при старте

Фикстуры автоматически загружаются при запуске приложения, если в `.env` установлено:

```bash
LOAD_FIXTURES=true
```

По умолчанию `LOAD_FIXTURES=false` для production.

## Файловая структура

```
fixtures_data/
  └── templates.json          # Шаблоны (Developer, Drive Engineer)

fixtures_export/
  └── templates_YYYYMMDD_HHMMSS.json  # Экспорты из БД
```

## Формат fixtures_data/templates.json

```json
{
  "metadata": {
    "export_type": "templates",
    "export_date": "2025-11-13T00:00:00",
    "count": 2
  },
  "data": [
    {
      "title": "Запрос помощи: Программирование",
      "description": "...",
      "category": "software",
      "visibility": "public",
      "author_id": "00000000-0000-0000-0000-000000000001",
      "usage_count": 0,
      "is_active": true,
      "fields": [...]
    }
  ]
}
```

**Важно**: Поля `id`, `created_at`, `updated_at` НЕ указываются — генерируются автоматически.

## Программный импорт/экспорт

### Python API

```python
from src.core.fixtures.json_loader import JSONFixtureLoader
from src.core.fixtures.json_handler import FixtureJSONHandler

# Загрузка фикстур
async with get_db_session() as session:
    loader = JSONFixtureLoader(session, "fixtures_data")
    
    # Загрузить все фикстуры (без перезаписи)
    results = await loader.load_all_fixtures(force=False)
    
    # Загрузить только шаблоны (с перезаписью)
    results = await loader.load_templates(force=True)

# Экспорт в JSON
async with get_db_session() as session:
    handler = FixtureJSONHandler(session, "fixtures_export")
    
    # Экспорт всех шаблонов
    files = await handler.export_to_json(include_templates=True)
    # -> {"templates": "fixtures_export/templates_20251113_143022.json"}
```

### UV команды (pyproject.toml)

```bash
# Загрузить фикстуры из fixtures_data/
uv run load-fixtures

# Загрузить с перезаписью существующих
uv run load-fixtures --force

# Экспортировать текущие данные в JSON
uv run export-fixtures

# Экспортировать только шаблоны
uv run export-fixtures --templates-only
```

## Обновление шаблонов

### Workflow для редактирования

1. **Экспортировать текущие данные**:
   ```bash
   uv run export-fixtures
   ```
   → Создаст `fixtures_export/templates_20251113_143022.json`

2. **Отредактировать JSON** в любом редакторе:
   - Изменить поля шаблона
   - Добавить/удалить validation_rules
   - Обновить примеры

3. **Скопировать в fixtures_data/**:
   ```bash
   cp fixtures_export/templates_20251113_143022.json fixtures_data/templates.json
   ```

4. **Загрузить обновленные данные**:
   ```bash
   uv run load-fixtures --force
   ```
   → `force=True` перезапишет существующие шаблоны

### Горячая перезагрузка (development)

В `.env.dev`:
```bash
LOAD_FIXTURES=true
```

Тогда при каждом перезапуске `uv run dev` фикстуры автоматически обновятся из `fixtures_data/templates.json`.

## Production Deployment

**Важно**: На production `LOAD_FIXTURES=false` по умолчанию.

### Первичная загрузка

1. После миграций:
   ```bash
   uv run migrate
   ```

2. Загрузить фикстуры вручную:
   ```bash
   LOAD_FIXTURES=true uv run python -c "
   import asyncio
   from src.core.fixtures.json_loader import JSONFixtureLoader
   from src.core.connections.database import get_db_session
   
   async def load():
       async for session in get_db_session():
           loader = JSONFixtureLoader(session)
           await loader.load_all_fixtures(force=False)
           break
   
   asyncio.run(load())
   "
   ```

### Обновление шаблонов на production

1. Подготовить обновленный `fixtures_data/templates.json` локально
2. Задеплоить код с новым JSON файлом
3. Выполнить команду загрузки с `force=True`:
   ```bash
   uv run load-fixtures --force
   ```

## Troubleshooting

### Ошибка "Template already exists"

**Причина**: Шаблон с таким `title` уже в БД, а `force=False`.

**Решение**:
```bash
uv run load-fixtures --force  # Перезапишет существующие
```

### Фикстуры не загружаются при старте

**Проверить**:
1. `.env` содержит `LOAD_FIXTURES=true`
2. Файл `fixtures_data/templates.json` существует
3. Логи содержат `"Начало загрузки фикстур..."` или `"Загрузка фикстур отключена"`

### Несовместимые изменения в структуре полей

**Если изменили структуру `fields`** (добавили required поле, изменили validation_rules):

1. Экспортировать старые данные:
   ```bash
   uv run export-fixtures
   ```

2. Отредактировать JSON вручную под новую структуру

3. Создать backup:
   ```bash
   cp fixtures_data/templates.json fixtures_data/templates_backup.json
   ```

4. Загрузить с force:
   ```bash
   uv run load-fixtures --force
   ```

## Примеры использования

### Добавление нового шаблона

1. Создать JSON в `fixtures_data/templates.json`:
```json
{
  "data": [
    {
      "title": "Новый шаблон: Тестирование",
      "category": "software",
      "fields": [...]
    }
  ]
}
```

2. Загрузить:
```bash
uv run load-fixtures
```

### Массовое обновление author_id

```python
import json

with open("fixtures_data/templates.json") as f:
    data = json.load(f)

for item in data["data"]:
    item["author_id"] = "NEW_UUID_HERE"

with open("fixtures_data/templates.json", "w") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
```

Затем:
```bash
uv run load-fixtures --force
```

## История изменений

- **2025-11-13**: Создана система фикстур с автозагрузкой при старте
- Добавлены шаблоны: Developer Help, Drive Engineer Error Tracking
