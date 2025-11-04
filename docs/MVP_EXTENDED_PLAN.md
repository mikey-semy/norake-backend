# 📋 Расширенный план разработки NoRake MVP

## 🎯 Обновления от 2025-11-04

### Добавлено в MVP:
1. ✅ **Visibility (Видимость)** — PUBLIC/PRIVATE проблемы
2. ✅ **Комментарии** — обсуждение и предложение решений
3. ✅ **Шаблоны** — настраиваемые формы для создания проблем

---

## 📦 Расширенная структура моделей

### 1. IssueModel (обновлённая)

```python
class IssueStatus(str, Enum):
    RED = "red"      # 🔴 Проблема активна
    GREEN = "green"  # 🟢 Проблема решена

class IssueVisibility(str, Enum):
    PUBLIC = "public"    # Видно всем
    PRIVATE = "private"  # Только автор
    TEAM = "team"        # Только команда (v0.2)

class IssueModel(BaseModel):
    __tablename__ = "issues"
    
    # Основная информация
    title: Mapped[str]  # Заголовок
    description: Mapped[str]  # Подробное описание
    category: Mapped[str]  # hardware, software, process
    
    # Статус и видимость
    status: Mapped[IssueStatus] = IssueStatus.RED
    visibility: Mapped[IssueVisibility] = IssueVisibility.PRIVATE
    
    # Решение
    solution: Mapped[Optional[str]]  # Текст решения
    resolved_at: Mapped[Optional[datetime]]  # Когда решена
    
    # Связи
    author_id: Mapped[UUID]  # FK users.id
    template_id: Mapped[Optional[UUID]]  # FK templates.id
    team_id: Mapped[Optional[UUID]]  # FK teams.id (v0.2)
    
    # Relationships
    author: Mapped["UserModel"] = relationship(back_populates="issues")
    template: Mapped[Optional["TemplateModel"]] = relationship()
    comments: Mapped[List["IssueCommentModel"]] = relationship(
        back_populates="issue",
        cascade="all, delete-orphan"
    )
    
    # Properties
    @property
    def is_resolved(self) -> bool:
        return self.status == IssueStatus.GREEN
    
    @property
    def is_public(self) -> bool:
        return self.visibility == IssueVisibility.PUBLIC
    
    @property
    def comments_count(self) -> int:
        return len(self.comments)
```

---

### 2. TemplateModel (новая)

```python
class TemplateVisibility(str, Enum):
    PUBLIC = "public"    # Доступен всем
    PRIVATE = "private"  # Только автор
    TEAM = "team"        # Только команда (v0.2)

class TemplateModel(BaseModel):
    __tablename__ = "templates"
    
    # Основная информация
    title: Mapped[str]  # "Проблема с оборудованием"
    description: Mapped[Optional[str]]  # Описание назначения
    category: Mapped[str]  # hardware, software, process
    
    # Динамические поля (JSONB)
    fields: Mapped[dict]  # JSON-структура полей шаблона
    
    # Видимость и владение
    visibility: Mapped[TemplateVisibility] = TemplateVisibility.PRIVATE
    author_id: Mapped[UUID]  # FK users.id
    team_id: Mapped[Optional[UUID]]  # FK teams.id (v0.2)
    
    # Метрики
    usage_count: Mapped[int] = 0  # Сколько раз использовали
    is_active: Mapped[bool] = True  # Активен ли шаблон
    
    # Relationships
    author: Mapped["UserModel"] = relationship()
    issues: Mapped[List["IssueModel"]] = relationship(back_populates="template")
    user_favorites: Mapped[List["UserTemplateModel"]] = relationship()
```

**Пример структуры fields (JSONB)**:
```json
{
  "fields": [
    {
      "name": "equipment_model",
      "label": "Модель оборудования",
      "type": "text",
      "required": true,
      "placeholder": "Например: KUKA KR 500-3",
      "help_text": "Укажите полное название модели"
    },
    {
      "name": "error_code",
      "label": "Код ошибки",
      "type": "text",
      "required": false,
      "pattern": "^[A-Z]{1,3}\\d{1,4}$"
    },
    {
      "name": "location",
      "label": "Местоположение",
      "type": "select",
      "options": ["Цех 1", "Цех 2", "Цех 3", "Склад"],
      "required": true
    },
    {
      "name": "urgency",
      "label": "Срочность",
      "type": "radio",
      "options": ["Низкая", "Средняя", "Высокая", "Критическая"],
      "default": "Средняя"
    },
    {
      "name": "photos_needed",
      "label": "Нужны фотографии",
      "type": "checkbox",
      "default": false
    }
  ]
}
```

**Поддерживаемые типы полей**:
- `text` — текстовое поле
- `textarea` — многострочный текст
- `number` — числовое поле
- `select` — выпадающий список
- `radio` — радиокнопки
- `checkbox` — чекбокс
- `date` — календарь
- `time` — время

---

### 3. UserTemplateModel (новая)

```python
class UserTemplateModel(BaseModel):
    __tablename__ = "user_templates"
    
    user_id: Mapped[UUID]  # FK users.id
    template_id: Mapped[UUID]  # FK templates.id
    
    is_default: Mapped[bool] = False  # Шаблон по умолчанию
    sort_order: Mapped[int] = 0  # Порядок в списке
    
    # Relationships
    user: Mapped["UserModel"] = relationship()
    template: Mapped["TemplateModel"] = relationship()
    
    __table_args__ = (
        # Только один default на пользователя + категорию
        Index('idx_user_default_template', 
              user_id, template_id, 
              unique=True, 
              postgresql_where=(is_default == True)),
    )
```

**Логика работы**:
1. Пользователь создаёт шаблон или добавляет чужой в избранное
2. Может отметить один шаблон как "по умолчанию"
3. При создании проблемы автоматически предлагается шаблон по умолчанию
4. Может переключиться на другой шаблон из избранных

---

### 4. IssueCommentModel (новая)

```python
class IssueCommentModel(BaseModel):
    __tablename__ = "issue_comments"
    
    # Связи
    issue_id: Mapped[UUID]  # FK issues.id (ON DELETE CASCADE)
    author_id: Mapped[UUID]  # FK users.id
    parent_id: Mapped[Optional[UUID]]  # FK issue_comments.id (для ответов)
    
    # Содержимое
    content: Mapped[str]  # Текст комментария
    is_solution: Mapped[bool] = False  # Отметка "это решение"
    
    # Relationships
    issue: Mapped["IssueModel"] = relationship(back_populates="comments")
    author: Mapped["UserModel"] = relationship()
    parent: Mapped[Optional["IssueCommentModel"]] = relationship(
        remote_side="IssueCommentModel.id",
        back_populates="replies"
    )
    replies: Mapped[List["IssueCommentModel"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    
    # Properties
    @property
    def is_reply(self) -> bool:
        return self.parent_id is not None
    
    @property
    def replies_count(self) -> int:
        return len(self.replies)
```

---

## 🌐 Расширенные API Endpoints

### Issues API (обновлённые)

```python
# Создание проблемы
POST /api/v1/issues
Body: {
  "title": "Станок не включается",
  "description": "Мигает красный индикатор E12",
  "category": "hardware",
  "visibility": "public",  # NEW!
  "template_id": "uuid...",  # NEW! Опционально
  "template_data": {  # NEW! Если используется шаблон
    "equipment_model": "KUKA KR 500-3",
    "error_code": "E12",
    "location": "Цех 3"
  }
}
Response: IssueResponseSchema (201)

# Получение списка (теперь с фильтром visibility)
GET /api/v1/issues?visibility=public&status=red&category=hardware
Response: IssueListResponseSchema (200)

# Публичные проблемы (без авторизации)
GET /api/v1/issues/public
Response: IssueListResponseSchema (200)
```

---

### Templates API (новые endpoints)

```python
# Создать шаблон
POST /api/v1/templates
Body: {
  "title": "Проблема с оборудованием",
  "description": "Для фиксации неисправностей станков",
  "category": "hardware",
  "visibility": "public",
  "fields": [
    {
      "name": "equipment_model",
      "label": "Модель оборудования",
      "type": "text",
      "required": true
    }
  ]
}
Response: TemplateResponseSchema (201)

# Получить доступные шаблоны
GET /api/v1/templates?category=hardware&visibility=public
Response: TemplateListResponseSchema (200)

# Детали шаблона
GET /api/v1/templates/{id}
Response: TemplateResponseSchema (200)

# Обновить шаблон (только автор)
PATCH /api/v1/templates/{id}
Body: { "fields": [...] }
Response: TemplateResponseSchema (200)

# Удалить шаблон (только автор)
DELETE /api/v1/templates/{id}
Response: 204 No Content

# Добавить в избранное
POST /api/v1/templates/{id}/favorite
Body: { "is_default": false }
Response: 200 OK

# Удалить из избранного
DELETE /api/v1/templates/{id}/favorite
Response: 204 No Content

# Мои избранные шаблоны
GET /api/v1/templates/favorites
Response: TemplateListResponseSchema (200)

# Установить шаблон по умолчанию
PATCH /api/v1/templates/{id}/set-default
Response: 200 OK
```

---

### Comments API (новые endpoints)

```python
# Добавить комментарий
POST /api/v1/issues/{issue_id}/comments
Body: {
  "content": "Попробуйте заменить предохранитель F12",
  "is_solution": false,
  "parent_id": null  # Для вложенных комментариев
}
Response: CommentResponseSchema (201)

# Список комментариев
GET /api/v1/issues/{issue_id}/comments
Response: CommentListResponseSchema (200)

# Обновить комментарий (только автор)
PATCH /api/v1/issues/{issue_id}/comments/{comment_id}
Body: { "content": "Обновлённый текст" }
Response: CommentResponseSchema (200)

# Удалить комментарий (только автор)
DELETE /api/v1/issues/{issue_id}/comments/{comment_id}
Response: 204 No Content

# Отметить как решение (только автор проблемы)
PATCH /api/v1/issues/{issue_id}/comments/{comment_id}/mark-solution
Response: CommentResponseSchema (200)
```

---

## 🗄️ Миграции БД

### Порядок создания миграций:

```bash
# 1. Базовые модели Issues (уже есть)
uv run alembic revision --autogenerate -m "add_issues_table"

# 2. Добавить visibility к Issues
uv run alembic revision --autogenerate -m "add_visibility_to_issues"

# 3. Таблица Templates
uv run alembic revision --autogenerate -m "add_templates_table"

# 4. Связь UserTemplate (избранные)
uv run alembic revision --autogenerate -m "add_user_templates_table"

# 5. Таблица Comments
uv run alembic revision --autogenerate -m "add_issue_comments_table"

# 6. Связать Issues с Templates
uv run alembic revision --autogenerate -m "add_template_id_to_issues"

# Применить все
uv run alembic upgrade head
```

---

## 📋 Обновлённый список задач (20+ issues)

### Фаза 1: Базовая система Issues (10 задач)
- NORAK-1 до NORAK-10 (как было)

### Фаза 1.5: Visibility (2 задачи)
- NORAK-11: Добавить enum IssueVisibility и поле visibility
- NORAK-12: Обновить API для фильтрации по visibility

### Фаза 2: Шаблоны (5 задач)
- NORAK-13: Создать модели TemplateModel, UserTemplateModel
- NORAK-14: Создать схемы для Templates
- NORAK-15: Создать TemplateRepository
- NORAK-16: Создать TemplateService
- NORAK-17: Создать TemplateRouter с API

### Фаза 3: Комментарии (5 задач)
- NORAK-18: Создать модель IssueCommentModel
- NORAK-19: Создать схемы для Comments
- NORAK-20: Создать CommentRepository
- NORAK-21: Создать CommentService
- NORAK-22: Добавить Comment endpoints в IssueRouter

### Фаза 4: Интеграция и тесты (3 задачи)
- NORAK-23: Обновить IssueService для работы с шаблонами
- NORAK-24: Миграции для всех новых таблиц
- NORAK-25: Комплексные тесты (Issues + Templates + Comments)

---

## ⏱️ Обновлённая оценка времени

| Фаза | Задачи | Время | Приоритет |
|------|--------|-------|-----------|
| 1. Issues (базовое) | NORAK-1..10 | 2-3 дня | 🔴 Критично |
| 1.5. Visibility | NORAK-11..12 | 2-3 часа | 🟡 Важно |
| 2. Шаблоны | NORAK-13..17 | 1-1.5 дня | 🟠 Высокий |
| 3. Комментарии | NORAK-18..22 | 1-1.5 дня | 🟠 Высокий |
| 4. Интеграция | NORAK-23..25 | 3-4 часа | 🟢 Средний |

**Итого**: 4.5-6 дней (вместо 2-3)

---

## 🎯 Roadmap после MVP

### v0.2 — Команды и файлы (1-2 недели)
- TeamModel, TeamMemberModel
- Загрузка изображений (MinIO)
- Email-уведомления
- Роли в командах

### v0.3 — Продвинутые фичи (2-3 недели)
- MCP-интеграция (LLM-генерация проблем)
- AI-поиск похожих решений
- Аналитика и статистика
- Экспорт в CSV/JSON

### v0.4 — Enterprise (1 месяц)
- SSO (Keycloak, Auth0)
- Audit log
- Интеграция с Jira/GitLab
- Мобильное приложение (PWA)

---

**Версия документа**: 2.0  
**Дата обновления**: 2025-11-04  
**Статус**: Готов к декомпозиции на задачи в Plane
