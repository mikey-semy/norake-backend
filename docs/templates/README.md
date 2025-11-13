# Шаблоны для NoRake

Этот каталог содержит готовые шаблоны для структурированного создания Issues.

## 📚 Навигация по документации

### Документация шаблонов

- **[QUICKSTART.md](QUICKSTART.md)** - Быстрый старт (5 минут)
- **[WORKFLOW.md](WORKFLOW.md)** - Визуальная диаграмма workflow с метриками

### Developer Template (Программисты)

- **[developer-issue-template.md](developer-issue-template.md)** - Полное руководство с примерами
- **[developer-issue-template.json](developer-issue-template.json)** - JSON для API

### Drive Engineer Template (Приводчики)

- **[drive-engineer-template.md](drive-engineer-template.md)** - Руководство для ошибок ПЧ
- **[drive-engineer-template.json](drive-engineer-template.json)** - JSON для API

### Скрипты автоматизации

- **[create_templates.sql](create_templates.sql)** - SQL скрипт для PostgreSQL (оба шаблона)
- **[create_templates.py](create_templates.py)** - Python автоматизация (оба шаблона)
- **[create_developer_template.py](create_developer_template.py)** - Python (только Developer)
- **[create_developer_template.sql](create_developer_template.sql)** - SQL (только Developer)

## 📋 Доступные шаблоны

### 1. Developer Issue Template (Запрос помощи: Программирование) 💻

**Назначение**: Помочь программистам правильно структурировать запрос помощи для получения быстрого и точного ответа.

**Категория**: `software`

**Иконка**: 💻

**Поля**: 9 (goal, current_behavior, code_example, error_message, environment, attempts, expected_behavior, additional_context, solution)

**Принцип**: Статусная система RED/GREEN - проблемы остаются в истории с решениями для всех.

---

### 2. Drive Engineer Template (Ошибка преобразователя частоты) ⚡

**Назначение**: Структурировать информацию об ошибках преобразователей частоты (ПЧ) для быстрой диагностики и решения.

**Категория**: `hardware`

**Иконка**: ⚡

**Поля**: 16 (equipment_name, drive_info, error_code, error_description, occurrence_moment, parameters_at_error, actions_taken, related_parameters, equipment_state, connection_config, operating_conditions, error_history, solution, preventive_measures, criticality, downtime)

**Принцип**: Статусная система RED/YELLOW/GREEN с детальной диагностикой и превентивными мерами.

**Поддержка производителей**: Siemens SINAMICS, ABB ACS, Danfoss VLT, Schneider Altivar

---

## 🚀 Способы создания шаблонов

### ⭐ Способ 1: Через систему фикстур (РЕКОМЕНДУЕТСЯ)

Шаблоны автоматически загружаются из `fixtures_data/templates.json` при инициализации проекта.

**Первичная загрузка** (после `uv run bootstrap`):
```bash
# Загрузка фикстур выполняется автоматически при инициализации
# Или вручную:
uv run load-fixtures
```

**Обновление шаблонов**:
1. Отредактируйте `fixtures_data/templates.json`
2. Загрузите изменения:
   ```bash
   uv run load-fixtures  # Без перезаписи существующих
   # ИЛИ
   uv run load-fixtures --force  # С перезаписью
   ```

**Экспорт текущих шаблонов из БД**:
```bash
uv run export-fixtures
# → Создаст fixtures_export/templates_YYYYMMDD_HHMMSS.json
```

**Подробности**: См. [FIXTURES_GUIDE.md](../FIXTURES_GUIDE.md)

---

### Способ 2: Через Python скрипт (для обоих шаблонов)

```bash
# Установка зависимостей
pip install httpx rich

# Создание обоих шаблонов одной командой
python create_templates.py \
  --workspace-id YOUR_WORKSPACE_UUID \
  --username admin \
  --password your_password

# Для создания только Developer Template
python create_developer_template.py \
  --workspace-id YOUR_WORKSPACE_UUID \
  --username admin \
  --password your_password
```

**Вывод**:
```
🔐 Логин в http://localhost:8000...
✅ Авторизация успешна

📦 Загрузка и создание шаблонов...
📄 Загрузка шаблона из developer-issue-template.json...
   ✓ Запрос помощи: Программирование
   📂 Категория: software
   📊 Полей: 9

🚀 Создание шаблона: Запрос помощи: Программирование
✅ Шаблон создан успешно!
   🆔 ID: abc12345...
   📈 Использований: 0

📄 Загрузка шаблона из drive-engineer-template.json...
   ✓ Ошибка преобразователя частоты
   📂 Категория: hardware
   📊 Полей: 16

🚀 Создание шаблона: Ошибка преобразователя частоты
✅ Шаблон создан успешно!
   🆔 ID: def67890...
   📈 Использований: 0

✨ Созданные шаблоны
┌──────────────────────────────────┬──────────┬───────┬────────────┐
│ Название                         │ Категория│ Полей │ ID         │
├──────────────────────────────────┼──────────┼───────┼────────────┤
│ Запрос помощи: Программирование │ software │   9   │ abc12345...│
│ Ошибка преобразователя частоты  │ hardware │  16   │ def67890...│
└──────────────────────────────────┴──────────┴───────┴────────────┘

🎉 Все шаблоны успешно созданы!
```

---

### Способ 2: Через API напрямую

```bash
# 1. Залогиньтесь и получите токен
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"

# Сохраните access_token из ответа
export TOKEN="your_access_token_here"

# 2. Создайте Developer Template
curl -X POST http://localhost:8000/api/v1/templates/{workspace_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @developer-issue-template.json

# 3. Создайте Drive Engineer Template
curl -X POST http://localhost:8000/api/v1/templates/{workspace_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @drive-engineer-template.json
```

**Ответ**:
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "template_name": "Запрос помощи: Программирование",
    "category": "software",
    "visibility": "PUBLIC",
    "is_active": true,
    "usage_count": 0,
    "fields": [...]
  }
}
```

---

### Способ 2: Через SQL-скрипт

```bash
# 1. Получите workspace_id и author_id
psql -U postgres -d norake_dev -c "SELECT id, name FROM workspaces;"
psql -U postgres -d norake_dev -c "SELECT id, username FROM users WHERE role = 'admin';"

# 2. Отредактируйте create_developer_template.sql
# Замените YOUR_WORKSPACE_ID_HERE и YOUR_ADMIN_USER_ID_HERE

# 3. Выполните скрипт
psql -U postgres -d norake_dev -f create_developer_template.sql
```

**Проверка**:
```sql
SELECT id, template_name, category, usage_count
FROM templates
WHERE template_name = 'Запрос помощи: Программирование';
```

---

### Способ 3: Через Python (для автоматизации)

```python
import httpx
import json

# Логин
response = httpx.post(
    "http://localhost:8000/api/v1/auth/login",
    data={"username": "admin", "password": "your_password"}
)
token = response.json()["access_token"]

# Загрузка шаблона
with open("developer-issue-template.json") as f:
    template_data = json.load(f)

# Создание через API
response = httpx.post(
    f"http://localhost:8000/api/v1/templates/{workspace_id}",
    headers={"Authorization": f"Bearer {token}"},
    json=template_data
)

print(response.json())
```

---

## 📝 Как использовать шаблон

### 1. Создание Issue с шаблоном

```bash
POST /api/v1/issues
Authorization: Bearer YOUR_TOKEN

{
  "workspace_id": "uuid",
  "title": "FastAPI OAuth2: Google authorization возвращает 401",
  "description": "Заполнено по шаблону Developer Issue",
  "category": "software",
  "template_id": "uuid_developer_template",
  "template_data": {
    "goal": "Интегрировать OAuth2 авторизацию через Google",
    "current_behavior": "При попытке логина возвращается HTTP 401",
    "code_example": "```python\nfrom fastapi import FastAPI\n...```",
    "error_message": "Traceback (most recent call last):\n...",
    "environment": "Python 3.11.5, FastAPI 0.104.1, Ubuntu 22.04",
    "attempts": "1. Читал документацию\n2. Пробовал изменить authorizationUrl",
    "expected_behavior": "После авторизации должен вернуться access_token",
    "additional_context": "Проблема появилась после обновления FastAPI",
    "checklist": [
      "Попытался решить сам",
      "Проблема воспроизводится стабильно",
      "Код минимизирован",
      "Ошибка полная",
      "Окружение указано",
      "Попытки решения описаны",
      "Формулировка вежливая"
    ]
  }
}
```

---

### 2. Workflow создания Issue

```
1. Пользователь создаёт Issue (статус RED)
   ↓
2. n8n автоматически категоризирует через AI (qwen/qwen-3-coder-480b)
   ↓
3. Система ищет похожие Issues в базе знаний (RAG)
   ↓
4. Уведомления отправляются команде (опционально)
   ↓
5. Коллеги предлагают решения через комментарии
   ↓
6. Issue закрывается с solution (статус GREEN)
   ↓
7. Issue остаётся в истории для всех (reference)
```

---

## 🎯 Преимущества шаблона

### Для автора Issue:

1. **Структура помогает самому понять проблему** - процесс заполнения заставляет детально разобраться
2. **Меньше уточняющих вопросов** - вся информация сразу на месте
3. **Быстрее получается ответ** - люди охотнее помогают при правильной формулировке
4. **Обучение** - шаблон учит правильно задавать вопросы

### Для команды:

1. **Экономия времени** - не нужно выуживать контекст вопросами
2. **База знаний** - все проблемы и решения структурированы
3. **Поиск аналогичных** - легко найти похожие Issues
4. **Онбординг** - новички учатся на примерах

### Для организации:

1. **История решений** - ничего не теряется
2. **Метрики** - можно анализировать типы проблем
3. **Документация** - Issues превращаются в wiki
4. **Снижение дублирования** - RAG находит существующие решения

---

## 📊 Статистика и метрики

После использования шаблона можно анализировать:

```sql
-- Топ-5 самых используемых шаблонов
SELECT 
    template_name,
    usage_count,
    category
FROM templates
WHERE is_active = true
ORDER BY usage_count DESC
LIMIT 5;

-- Среднее время решения Issue по шаблонам
SELECT 
    t.template_name,
    AVG(EXTRACT(EPOCH FROM (i.resolved_at - i.created_at))/3600) as avg_hours_to_resolve,
    COUNT(i.id) as issues_count
FROM issues i
JOIN templates t ON i.template_id = t.id
WHERE i.status = 'GREEN'
GROUP BY t.template_name
ORDER BY avg_hours_to_resolve ASC;

-- Категории проблем (автоматически категоризированные AI)
SELECT 
    category,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM issues
WHERE template_id = (SELECT id FROM templates WHERE template_name = 'Запрос помощи: Программирование')
GROUP BY category
ORDER BY count DESC;
```

---

## 🔄 Обновление шаблона

### Через API

```bash
PATCH /api/v1/templates/{template_id}
Authorization: Bearer YOUR_TOKEN

{
  "fields": [
    {
      "field_name": "new_field",
      "field_type": "text",
      "label": "Новое поле",
      ...
    }
  ]
}
```

### Через SQL

```sql
UPDATE templates
SET 
    fields = fields || '[{"field_name": "new_field", ...}]'::jsonb,
    updated_at = NOW()
WHERE template_name = 'Запрос помощи: Программирование';
```

---

## 🚫 Частые ошибки

### ❌ Неполное заполнение

**Проблема**: Пропущены обязательные поля (goal, current_behavior, environment)

**Решение**: Включить `validation_rules.required: true` в JSON и проверять на фронтенде

---

### ❌ Слишком много кода

**Проблема**: code_example содержит 1000+ строк вместо минимального примера

**Решение**: Добавить `validation_rules.max_length: 5000` и подсказку "10-50 строк"

---

### ❌ Расплывчатая формулировка

**Проблема**: "Не работает", "Ошибка", "Помогите"

**Решение**: Примеры в `placeholder` и `examples` показывают правильный формат

---

## 📚 Дополнительные ресурсы

- [Stack Overflow: How to Ask](https://stackoverflow.com/help/how-to-ask)
- [GitHub: Minimal Reproducible Example](https://stackoverflow.com/help/minimal-reproducible-example)
- [NoRake API Documentation](../../../README.md)
- [n8n Workflows for Auto-categorization](../n8n_workflows/README.md)

---

## 📝 Changelog

### v1.0.0 (2025-11-11)
- ✅ Initial Developer Issue Template
- ✅ 9 полей (goal, current_behavior, code_example, error_message, environment, attempts, expected_behavior, additional_context, checklist)
- ✅ Validation rules (required, min/max length, min_selected)
- ✅ Examples и hints для каждого поля
- ✅ Markdown documentation (developer-issue-template.md)
- ✅ JSON API payload (developer-issue-template.json)
- ✅ SQL creation script (create_developer_template.sql)

### Planned
- ⏳ Template для hardware-проблем (оборудование, датчики)
- ⏳ Template для process-проблем (бизнес-процессы, документация)
- ⏳ Template для safety-проблем (безопасность, инциденты)
- ⏳ Web UI для визуального создания Templates (drag-and-drop fields)

---

## 💡 Идеи для расширения

1. **AI-генерация полей** - на основе описания проблемы предзаполнять поля шаблона
2. **Автоматические теги** - извлекать технологии из environment (FastAPI, PostgreSQL) и добавлять как labels
3. **Similarity search** - при создании Issue искать похожие через RAG и предлагать существующие решения
4. **Template suggestions** - на основе title/description предлагать подходящий Template
5. **Gamification** - награждать за правильное заполнение шаблонов (badges, points)

---

**Контакты**: Вопросы и предложения - создавайте Issue с этим же шаблоном! 😊
