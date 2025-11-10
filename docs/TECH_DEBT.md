# Technical Debt / Технический долг

Список известных проблем и улучшений для будущей реализации.

## Критичные

### 1. Динамические категории (ALLOWED_CATEGORIES)

**Проблема**: Категории хардкодятся в 3 местах:
- `src/services/v1/issues.py` → `IssueService.ALLOWED_CATEGORIES`
- `src/services/v1/templates.py` → `ALLOWED_CATEGORIES` (module-level)
- `src/schemas/v1/templates/base.py` → `TemplateBaseSchema.validate_category()`

**Текущее состояние**:
```python
ALLOWED_CATEGORIES = ["hardware", "software", "process"]
```

**Проблемы**:
- ❌ Дублирование кода (нарушение DRY)
- ❌ Невозможно добавить категорию без изменения кода
- ❌ Нет API для управления категориями
- ❌ При изменении нужно обновлять 3 файла

**Решение** (планируется в будущем спринте):

**Вариант 1**: Конфигурационный файл
```python
# src/core/config/categories.py
CATEGORIES = {
    "hardware": {"label": "Аппаратное обеспечение", "color": "#FF5733"},
    "software": {"label": "Программное обеспечение", "color": "#33C1FF"},
    "process": {"label": "Процессы", "color": "#75FF33"},
}
```

**Вариант 2**: База данных (более гибкий)
```python
# src/models/v1/categories.py
class CategoryModel(BaseModel):
    """Модель категории проблем/шаблонов."""

    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String(7), default="#000000")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
```

**Admin API**:
```
POST   /api/v1/admin/categories      - Создать категорию
GET    /api/v1/admin/categories      - Список категорий
PATCH  /api/v1/admin/categories/{id} - Обновить
DELETE /api/v1/admin/categories/{id} - Удалить (soft delete)
```

**Миграция**:
1. Создать `CategoryModel` и миграцию
2. Заполнить начальными данными (hardware, software, process)
3. Создать `CategoryRepository` с кешированием
4. Обновить сервисы для чтения из БД/кеша
5. Удалить хардкод из 3 файлов
6. Создать admin API endpoints

**Приоритет**: Medium (не блокирует MVP, но желательно до продакшена)

---

## Некритичные

### 2. Роль Admin в проверке прав

**Проблема**: В `IssueService._check_permission()` есть TODO:
```python
# TODO: Добавить проверку роли admin когда будет доступ к UserModel
if issue.author_id != user_id:
    raise IssuePermissionDeniedError(issue.id, user_id, action)
```

**Решение**: Добавить проверку `user.role == "admin"` после реализации UserService.

**Приоритет**: Low (работает без этого, просто ограничивает admin)

---

## Будущие улучшения

### 3. Кеширование категорий

Когда категории будут в БД - добавить Redis кеш:
- TTL: 1 час
- Invalidation при изменении через admin API
- Warm-up при старте приложения

### 4. i18n для категорий

Добавить мультиязычность:
```python
{
    "name": "hardware",
    "label": {
        "ru": "Аппаратное обеспечение",
        "en": "Hardware"
    }
}
```

---

## История изменений

- **2025-11-10**: Добавлен техдолг про ALLOWED_CATEGORIES (обнаружен при рефакторинге)
