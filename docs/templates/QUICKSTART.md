# Developer Issue Template - Quick Start

## 🚀 Быстрый старт (5 минут)

### Шаг 1: Установка зависимостей (для Python-скрипта)

```bash
pip install httpx rich
```

### Шаг 2: Создание шаблона

**Вариант A: Через Python-скрипт (рекомендуется)**

```bash
cd docs/templates

python create_developer_template.py \
  --workspace-id YOUR_WORKSPACE_UUID \
  --username admin \
  --password your_password
```

**Вариант B: Через curl**

```bash
# 1. Получить токен
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password" \
  | jq -r '.access_token')

# 2. Создать шаблон
curl -X POST http://localhost:8000/api/v1/templates/YOUR_WORKSPACE_UUID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @developer-issue-template.json
```

---

## 📝 Использование шаблона

### Создание Issue с шаблоном

```bash
POST /api/v1/issues
Authorization: Bearer YOUR_TOKEN

{
  "workspace_id": "uuid",
  "title": "FastAPI OAuth2: Google authorization возвращает 401",
  "description": "Проблема с авторизацией через Google",
  "category": "software",
  "template_id": "TEMPLATE_UUID_FROM_PREVIOUS_STEP",
  "template_data": {
    "goal": "Интегрировать OAuth2 авторизацию через Google в FastAPI",
    "current_behavior": "При попытке логина через Google возвращается HTTP 401 Unauthorized",
    "code_example": "```python\nfrom fastapi import FastAPI\nfrom fastapi.security import OAuth2AuthorizationCodeBearer\n\napp = FastAPI()\noauth2_scheme = OAuth2AuthorizationCodeBearer(\n    authorizationUrl=\"https://accounts.google.com/o/oauth2/auth\",\n    tokenUrl=\"https://oauth2.googleapis.com/token\"\n)\n\n@app.get(\"/login\")\nasync def login(token: str = Depends(oauth2_scheme)):\n    return {\"token\": token}  # Всегда возвращает 401\n```",
    "error_message": "Traceback (most recent call last):\n  File \"main.py\", line 12, in login\n    return {\"token\": token}\nfastapi.exceptions.HTTPException: 401 Unauthorized\n  Detail: Not authenticated",
    "environment": "Python 3.11.5\nFastAPI 0.104.1\nhttpx 0.25.0\nUbuntu 22.04 LTS",
    "attempts": "1. Читал документацию: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/\n2. Пробовал изменить authorizationUrl на /authorize (не помогло)\n3. Stack Overflow: https://stackoverflow.com/q/75000000 (не подошло)\n4. Добавил debug-логирование: токен приходит пустым",
    "expected_behavior": "После успешной авторизации в Google должен вернуться access_token и пользователь должен быть залогинен",
    "additional_context": "Проблема появилась после обновления FastAPI с 0.100.0 до 0.104.1. На локальной машине работает, на prod-сервере - нет",
    "checklist": [
      "Попытался решить сам (документация, Google, Stack Overflow)",
      "Проблема воспроизводится стабильно (не случайная ошибка)",
      "Код минимизирован (убрал всё лишнее)",
      "Ошибка полная (весь traceback, не обрезанный)",
      "Окружение указано (язык, версии, ОС)",
      "Попытки решения описаны (что пробовал)",
      "Формулировка вежливая (без 'Срочно!' и агрессии)"
    ]
  }
}
```

---

## ✅ Что происходит после создания

1. **Issue создаётся** со статусом **RED** (требуется помощь)
2. **n8n workflow автоматически категоризирует** через AI (Qwen3 Coder 480B)
3. **RAG поиск** находит похожие Issues в базе знаний (опционально)
4. **Уведомления** отправляются команде (опционально)
5. **Коллеги предлагают решения** через комментарии
6. **Issue закрывается** со статусом **GREEN** и полем `solution`
7. **Issue остаётся в истории** для всех (reference)

---

## 📊 Проверка созданного шаблона

```sql
-- Список всех шаблонов
SELECT
    id,
    template_name,
    category,
    visibility,
    usage_count,
    is_active
FROM templates
ORDER BY created_at DESC;

-- Детали конкретного шаблона
SELECT
    template_name,
    jsonb_pretty(fields) as fields_structure
FROM templates
WHERE template_name = 'Запрос помощи: Программирование';
```

---

## 🔗 Дополнительная информация

- **Полная документация**: [README.md](README.md)
- **Примеры использования**: [developer-issue-template.md](developer-issue-template.md)
- **n8n Integration**: [../n8n_workflows/README.md](../n8n_workflows/README.md)
- **Equiply API**: [../../README.md](../../README.md)

---

## 💡 Советы

1. **Минимизируйте код** - 10-50 строк достаточно
2. **Полный traceback** - не обрезайте ошибки
3. **Версии важны** - Python 3.11 ≠ Python 3.9
4. **Что пробовали** - это 50% ответа
5. **Вежливость** - "Пожалуйста" работает лучше "Срочно!"

---

**Готово!** Теперь у вас есть структурированный способ создания Issues для получения быстрой и точной помощи. 🎯
