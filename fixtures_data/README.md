# Система фикстур для NoRake Backend

## Быстрый старт

### Автоматическая загрузка при инициализации

```bash
uv run bootstrap  # Шаблоны загрузятся автоматически из fixtures_data/templates.json
```

### Ручная загрузка/обновление

```bash
# Загрузить фикстуры (без перезаписи существующих)
uv run load-fixtures

# Загрузить с перезаписью (для обновления шаблонов)
uv run load-fixtures --force

# Экспортировать текущие данные из БД
uv run export-fixtures
```

## Структура файлов

```
fixtures_data/
  └── templates.json          # Источник истины - редактируемые шаблоны

fixtures_export/
  └── templates_*.json        # Экспорты из БД (для бэкапов)
```

## Редактирование шаблонов

1. **Экспортировать текущие** (опционально):
   ```bash
   uv run export-fixtures
   ```

2. **Отредактировать** `fixtures_data/templates.json`

3. **Применить изменения**:
   ```bash
   uv run load-fixtures --force
   ```

## Формат fixtures_data/templates.json

```json
{
  "metadata": {
    "export_type": "templates",
    "count": 2
  },
  "data": [
    {
      "title": "Запрос помощи: Программирование",
      "category": "software",
      "visibility": "public",
      "author_id": "00000000-0000-0000-0000-000000000001",
      "fields": [...]
    }
  ]
}
```

**Важно**: Не указывайте `id`, `created_at`, `updated_at` - они генерируются автоматически.

## Автозагрузка при старте (development)

В `.env.dev`:
```bash
LOAD_FIXTURES=true  # Загружать при каждом старте uv run dev
```

По умолчанию:
```bash
LOAD_FIXTURES=false  # Production - ручная загрузка
```

## Production deployment

```bash
# После миграций
uv run migrate

# Загрузить фикстуры
uv run load-fixtures
```

## Включенные шаблоны

1. **Запрос помощи: Программирование** (9 полей)
   - Минимальный воспроизводимый пример (MRE)
   - Окружение, error traceback
   - RED/GREEN статусы

2. **Ошибка преобразователя частоты** (16 полей)
   - Коды ошибок (F/A/E)
   - Диагностика параметров ПЧ
   - Решения и превентивные меры
   - RED/YELLOW/GREEN статусы

## Подробная документация

См. [FIXTURES_GUIDE.md](FIXTURES_GUIDE.md) для:
- Программный API (Python)
- Troubleshooting
- Массовые обновления
- Production workflow
