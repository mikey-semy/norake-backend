# Импорт инструкций из work-aedb в norake-backend (equiply)

## Описание

Скрипт `import_manuals_from_workaedb.py` импортирует инструкции по эксплуатации из проекта **work-aedb** в систему **Document Services** проекта **norake-backend** (equiply).

**КРИТИЧНО**: Скрипт использует ТУ ЖЕ архитектуру и пути загрузки, что и основной код:
- `DocumentS3Storage.upload_document()` → файлы в `documents/{uuid}.pdf`
- `S3ContextManager` для работы с S3 (как в проекте)
- `DatabaseClient` singleton для БД
- Те же settings из `src.core.settings.base`

## Маппинг данных

### Исходные данные (work-aedb JSON)

| Файл | Поле | Пример |
|------|------|--------|
| `manuals.json` | `name` | "ASC800 Руководство по микропрограммному обеспечению 1209 Ru" |
| `manuals.json` | `file_url` | "https://storage.yandexcloud.net/drivers.data/docs/abb/asc800-m-1209-ru.pdf" |
| `manuals.json` | `group_id` | 1 |
| `groups.json` | `name` | "ASC" |
| `groups.json` | `category_id` | 1 |
| `categories.json` | `name` | "ABB (Швейцария)" |

### Результирующие данные (norake-backend DocumentServiceModel)

| Поле DocumentService | Источник | Пример | Логика формирования |
|---------------------|----------|--------|---------------------|
| **title** | `manuals.name` | "ASC800 Руководство по микропрограммному обеспечению 1209 Ru" | Прямой маппинг |
| **description** | Генерация | "Производитель: ABB (Швейцария), Серия: ASC, Дата: 12/2009" | `{category} + {group} + дата/версия из названия` |
| **tags** | Извлечение из `name` + `category` + `group` | `["руководство", "русский", "abb", "asc", "микропрограммное обеспечение"]` | Парсинг ключевых слов |
| **file_url** | S3 norake-backend | "https://s3.equiply.ru/documents/manuals/abb/asc/asc800-m-1209-ru.pdf" | Скачан с Yandex → загружен в свой S3 |
| **file_size** | Размер скачанного файла | 2548736 (bytes) | Вычисляется при скачивании |
| **file_type** | Константа | "pdf" | Всегда PDF (можно расширить на DOC/DOCX) |
| **cover_type** | Константа | "generated" | Автогенерация thumbnail из PDF |
| **cover_url** | NULL (TODO) | None | Будет генерироваться позже |
| **author_id** | Первый пользователь из БД | UUID первого UserModel | Дефолтный создатель |
| **workspace_id** | Первый workspace из БД (опционально) | UUID первого WorkspaceModel | NULL для публичных |
| **is_public** | Константа | `True` | Публичный доступ к инструкциям |
| **available_functions** | Дефолтные функции | `[{name: "view_pdf", enabled: true}, ...]` | view_pdf, download, qr_code |

## Логика извлечения тегов

Скрипт анализирует **название инструкции** (`manuals.name`) и извлекает:

### 1. Тип документа

| Паттерн в названии | Тег |
|-------------------|-----|
| "руководство" | `руководство` |
| "инструкция" | `инструкция` |
| "брошура" | `брошура` |
| "каталог" | `каталог` |
| "параметрирование" | `параметры` |
| "manual" | `manual` |
| "guide" | `guide` |
| "user guide" | `user guide` |
| "datasheet" | `datasheet` |
| "quick" | `quick start` |
| "краткое" | `краткое руководство` |

### 2. Язык документа

| Суффикс в названии | Тег |
|-------------------|-----|
| "Ru" | `русский` |
| "En" | `english` |
| "Cn" / "Ch" | `chinese` |

### 3. Производитель и серия

- **Производитель**: Извлекается из `categories.name` (без страны в скобках)
  - `"ABB (Швейцария)"` → тег `abb`
  - `"Siemens (Германия)"` → тег `siemens`

- **Серия**: Извлекается из `groups.name`
  - `"ASC"` → тег `asc`
  - `"G120"` → тег `g120`

### 4. Дополнительные ключевые слова

| Слово в названии | Тег |
|------------------|-----|
| "параметрирование", "parameter" | `параметры` |
| "эксплуатация", "operation" | `эксплуатация` |
| "quick", "краткое" | `quick start` |

## Примеры маппинга

### Пример 1: Полное руководство

**Входные данные:**
```json
{
  "name": "ASC800 Руководство по микропрограммному обеспечению 1209 Ru",
  "file_url": "https://storage.yandexcloud.net/drivers.data/docs/abb/asc800-m-1209-ru.pdf",
  "group_id": 1
}

// group_id=1 → groups[0]
{
  "name": "ASC",
  "category_id": 1
}

// category_id=1 → categories[0]
{
  "name": "ABB (Швейцария)"
}
```

**Результирующий Document Service:**
```python
{
  "title": "ASC800 Руководство по микропрограммному обеспечению 1209 Ru",
  "description": "Производитель: ABB (Швейцария), Серия: ASC, Дата: 12/2009",
  "tags": ["abb", "asc", "руководство", "русский", "микропрограммное обеспечение"],
  "file_url": "https://s3.equiply.ru/documents/manuals/abb/asc/asc800-m-1209-ru.pdf",
  "file_type": "pdf",
  "cover_type": "generated",
  "is_public": True
}
```

### Пример 2: Quick Start Guide

**Входные данные:**
```json
{
  "name": "G120 Quick Start Guide 2020 En",
  "file_url": "https://storage.yandexcloud.net/drivers.data/docs/siemens/g120-quick-start.pdf",
  "group_id": 27
}

// group_id=27 → groups[26]
{
  "name": "G120",
  "category_id": 9
}

// category_id=9 → categories[8]
{
  "name": "Siemens (Германия)"
}
```

**Результирующий Document Service:**
```python
{
  "title": "G120 Quick Start Guide 2020 En",
  "description": "Производитель: Siemens (Германия), Серия: G120, Дата: 20/2020",
  "tags": ["english", "g120", "guide", "quick start", "siemens"],
  "file_url": "https://s3.equiply.ru/documents/manuals/siemens/g120/g120-quick-start.pdf",
  "file_type": "pdf",
  "cover_type": "generated",
  "is_public": True
}
```

### Пример 3: Параметрирование

**Входные данные:**
```json
{
  "name": "FC51 Руководство по программированию 1111 Ru",
  "file_url": "https://storage.yandexcloud.net/drivers.data/docs/danfoss/fc51-pm-1111_ru.pdf",
  "group_id": 2
}

// group_id=2 → groups[1]
{
  "name": "DC, FC, MCD",
  "category_id": 2
}

// category_id=2 → categories[1]
{
  "name": "Danfoss (Дания)"
}
```

**Результирующий Document Service:**
```python
{
  "title": "FC51 Руководство по программированию 1111 Ru",
  "description": "Производитель: Danfoss (Дания), Серия: DC, FC, MCD, Дата: 11/2011",
  "tags": ["danfoss", "dc, fc, mcd", "параметры", "руководство", "русский"],
  "file_url": "https://s3.equiply.ru/documents/manuals/danfoss/dc-fc-mcd/fc51-pm-1111_ru.pdf",
  "file_type": "pdf",
  "cover_type": "generated",
  "is_public": True
}
```

## S3 структура файлов

### work-aedb (старая структура)

```
https://storage.yandexcloud.net/drivers.data/docs/
├── abb/
│   ├── asc800-m-1209-ru.pdf
│   └── ...
├── danfoss/
│   ├── fc51-pm-1111_ru.pdf
│   └── ...
└── siemens/
    └── ...
```

### norake-backend (новая структура)

```
https://s3.equiply.ru/documents/manuals/
├── abb/
│   └── asc/
│       ├── asc800-m-1209-ru.pdf
│       └── ...
├── danfoss/
│   └── dc-fc-mcd/
│       ├── fc51-pm-1111_ru.pdf
│       └── ...
└── siemens/
    └── g120/
        └── ...
```

**Формат S3 key:**
```
documents/manuals/{manufacturer_slug}/{series_slug}/{original_filename}
```

- `manufacturer_slug`: Нормализованное название производителя (lowercase, без спецсимволов)
  - `"ABB (Швейцария)"` → `abb`
  - `"Siemens (Германия)"` → `siemens`

- `series_slug`: Нормализованное название серии
  - `"ASC"` → `asc`
  - `"DC, FC, MCD"` → `dc-fc-mcd`

- `original_filename`: Оригинальное имя файла из Yandex URL
  - `asc800-m-1209-ru.pdf` (без изменений)

## Использование

### 1. Убедитесь, что в norake-backend есть пользователь

```bash
cd C:\Users\Mike\Projects\norake-backend

# Загрузить фикстуры (если БД пустая)
uv run load-fixtures

# Или создать пользователя вручную через API
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@equiply.ru",
    "password": "admin123",
    "role": "admin"
  }'
```

### 2. Проверьте настройки S3 в `.env`

```bash
# .env норake-backend
AWS_REGION=us-east-1
AWS_ENDPOINT=https://s3.equiply.ru
AWS_BUCKET_NAME=equiply-documents
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

### 3. Запустите импорт

```bash
# Из директории norake-backend
python scripts/import_manuals_from_workaedb.py

# Или с кастомным путём к work-aedb
python scripts/import_manuals_from_workaedb.py --workaedb-path "C:/Projects/work-aedb"
```

### 4. Проверьте результат

```bash
# Через API
curl http://localhost:8000/api/v1/document-services?is_public=true

# Или в БД
psql -d equiply -c "SELECT id, title, tags FROM document_services LIMIT 10;"
```

## Логирование

Скрипт логирует все операции:

```
2024-11-14 10:00:00 - INFO - ManualImporter инициализирован
2024-11-14 10:00:01 - INFO - Дефолтный пользователь: admin (id=...)
2024-11-14 10:00:02 - INFO - Загружено: 11 категорий, 34 групп, 114 инструкций
2024-11-14 10:00:02 - INFO - Начало импорта 114 инструкций
2024-11-14 10:00:03 - INFO - [1/114] Импорт: ASC800 Руководство...
2024-11-14 10:00:05 - INFO - ✅ Создан Document Service: ASC800... (id=...)
...
2024-11-14 10:10:00 - INFO - Импорт завершён!
2024-11-14 10:10:00 - INFO - Статистика:
2024-11-14 10:10:00 - INFO -   Всего: 114
2024-11-14 10:10:00 - INFO -   Успешно: 110
2024-11-14 10:10:00 - INFO -   Пропущено: 4
2024-11-14 10:10:00 - INFO -   Ошибок: 4
```

## Обработка ошибок

Скрипт пропускает проблемные файлы и продолжает импорт:

- **Ошибка скачивания с Yandex**: Логируется, файл пропускается
- **Ошибка загрузки в S3**: Rollback транзакции, файл пропускается
- **Отсутствие группы/категории**: Логируется, файл пропускается

Все ошибки собираются в `stats["errors"]` и выводятся в конце.

## Возможные проблемы

### 1. "В БД нет пользователей!"

**Решение**: Загрузить фикстуры или создать пользователя через API:
```bash
uv run load-fixtures
```

### 2. Ошибка подключения к S3

**Решение**: Проверить настройки в `.env`:
```bash
# Проверить доступность endpoint
curl https://s3.equiply.ru

# Проверить credentials
aws s3 ls s3://equiply-documents --endpoint-url https://s3.equiply.ru
```

### 3. Дубликаты при повторном запуске

**Решение**: Скрипт НЕ проверяет дубликаты. Перед повторным импортом очистить таблицу:
```sql
DELETE FROM document_services WHERE title LIKE '%ABB%';
-- или полная очистка
TRUNCATE document_services CASCADE;
```

### 4. Медленная загрузка (>30 секунд на файл)

**Решение**: Проблема с сетью до Yandex Cloud или S3. Проверить:
```bash
# Скорость до Yandex
time curl -o /dev/null https://storage.yandexcloud.net/drivers.data/docs/abb/asc800-m-1209-ru.pdf

# Скорость до своего S3
time curl -o /dev/null https://s3.equiply.ru/test-file.pdf
```

## Расширение функциональности

### 1. Добавить генерацию thumbnails

```python
# В методе import_manuals() после создания Document Service
from src.services.v1.images import ImageService

image_service = ImageService(session=self.session, s3_client=self.s3_manager)
thumbnail_url = await image_service.generate_thumbnail_from_pdf(file_url)

# Обновить cover_url
await self.service.repository.update_item(
    document.id,
    {"cover_url": thumbnail_url}
)
```

### 2. Добавить фильтрацию по тегам при импорте

```python
# Импортировать только русские инструкции
if "русский" not in tags:
    logger.info("Пропуск не-русской инструкции: %s", manual_name)
    continue
```

### 3. Добавить версионирование

```python
# Проверить существование документа с таким же title
existing = await self.service.repository.filter_by(title=manual_name)
if existing:
    # Обновить версию вместо создания нового
    await self.service.repository.update_item(
        existing[0].id,
        {"file_url": file_url, "file_size": file_size}
    )
```

## См. также

- **Document Services Quick Start**: `docs/DOCUMENT_SERVICES_QUICK_START.md`
- **API документация**: `http://localhost:8000/docs`
- **Модель DocumentServiceModel**: `src/models/v1/document_services.py`
- **Схемы запросов**: `src/schemas/v1/document_services/requests.py`
