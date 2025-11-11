-- Скрипт для создания шаблона "Запрос помощи: Программирование"
-- Использование: psql -U postgres -d norake_dev -f create_developer_template.sql
-- Или выполните через pgAdmin Query Tool

-- Переменные (замените на актуальные UUID из вашей БД)
-- Получить workspace_id: SELECT id, name FROM workspaces;
-- Получить author_id: SELECT id, username FROM users WHERE role = 'admin';

DO $$
DECLARE
    v_workspace_id UUID := 'YOUR_WORKSPACE_ID_HERE';  -- ЗАМЕНИТЕ!
    v_author_id UUID := 'YOUR_ADMIN_USER_ID_HERE';     -- ЗАМЕНИТЕ!
    v_template_id UUID;
BEGIN
    -- Создание шаблона
    INSERT INTO templates (
        id,
        workspace_id,
        template_name,
        category,
        visibility,
        is_active,
        usage_count,
        author_id,
        fields,
        created_at,
        updated_at
    ) VALUES (
        gen_random_uuid(),
        v_workspace_id,
        'Запрос помощи: Программирование',
        'software',
        'PUBLIC',
        true,
        0,
        v_author_id,
        '[
            {
                "field_name": "goal",
                "field_type": "text",
                "label": "Цель / Что нужно достичь",
                "placeholder": "Опишите конечную цель, а не просто ''не работает''",
                "description": "Четко сформулируйте, что вы хотите реализовать. Цель важнее кода.",
                "validation_rules": {
                    "required": true,
                    "min_length": 20,
                    "max_length": 500
                },
                "display_order": 1,
                "examples": [
                    "Нужно интегрировать OAuth2 авторизацию через Google в FastAPI",
                    "Необходимо оптимизировать SQL-запрос, который выполняется >5 секунд"
                ]
            },
            {
                "field_name": "current_behavior",
                "field_type": "text",
                "label": "Проблема / Что происходит сейчас",
                "placeholder": "Опишите текущее поведение системы",
                "description": "Четкое описание того, что происходит в данный момент.",
                "validation_rules": {
                    "required": true,
                    "min_length": 30,
                    "max_length": 1000
                },
                "display_order": 2
            },
            {
                "field_name": "code_example",
                "field_type": "text",
                "label": "Минимальный воспроизводимый пример (MRE)",
                "placeholder": "Вставьте минимальный код для воспроизведения проблемы",
                "description": "Код должен быть максимально упрощен. 10-50 строк.",
                "validation_rules": {
                    "required": true,
                    "min_length": 50,
                    "max_length": 5000
                },
                "display_order": 3
            },
            {
                "field_name": "error_message",
                "field_type": "text",
                "label": "Полная ошибка / Traceback",
                "placeholder": "Вставьте полный текст ошибки (не скриншот!)",
                "description": "Точный текст ошибки, traceback, логи.",
                "validation_rules": {
                    "required": false,
                    "max_length": 3000
                },
                "display_order": 4
            },
            {
                "field_name": "environment",
                "field_type": "text",
                "label": "Окружение (язык, версии, ОС)",
                "placeholder": "Python 3.11.5, FastAPI 0.104.1, Ubuntu 22.04",
                "description": "Версии языка, фреймворков, библиотек, ОС.",
                "validation_rules": {
                    "required": true,
                    "min_length": 20,
                    "max_length": 1000
                },
                "display_order": 5,
                "hints": [
                    "Python: python --version && pip freeze",
                    "Node.js: node --version && npm list --depth=0"
                ]
            },
            {
                "field_name": "attempts",
                "field_type": "text",
                "label": "Что уже пробовали",
                "placeholder": "Перечислите попытки решения проблемы",
                "description": "Покажите, что вы уже пытались сделать.",
                "validation_rules": {
                    "required": true,
                    "min_length": 30,
                    "max_length": 2000
                },
                "display_order": 6
            },
            {
                "field_name": "expected_behavior",
                "field_type": "text",
                "label": "Ожидаемое поведение",
                "placeholder": "Что должно происходить в идеале?",
                "validation_rules": {
                    "required": false,
                    "max_length": 500
                },
                "display_order": 7
            },
            {
                "field_name": "additional_context",
                "field_type": "text",
                "label": "Дополнительный контекст",
                "placeholder": "Любая другая полезная информация",
                "validation_rules": {
                    "required": false,
                    "max_length": 1000
                },
                "display_order": 8
            },
            {
                "field_name": "checklist",
                "field_type": "multiselect",
                "label": "Чек-лист перед отправкой",
                "description": "Убедитесь, что выполнили все пункты",
                "validation_rules": {
                    "required": true,
                    "min_selected": 5
                },
                "display_order": 9,
                "options": [
                    "Попытался решить сам (документация, Google, Stack Overflow)",
                    "Проблема воспроизводится стабильно",
                    "Код минимизирован (убрал всё лишнее)",
                    "Ошибка полная (весь traceback)",
                    "Окружение указано (язык, версии, ОС)",
                    "Попытки решения описаны",
                    "Формулировка вежливая"
                ]
            }
        ]'::jsonb,
        NOW(),
        NOW()
    )
    RETURNING id INTO v_template_id;

    RAISE NOTICE 'Template created successfully with ID: %', v_template_id;
    RAISE NOTICE 'Template name: Запрос помощи: Программирование';
    RAISE NOTICE 'Category: software';
    RAISE NOTICE 'Visibility: PUBLIC';
    RAISE NOTICE 'Fields: 9 (goal, current_behavior, code_example, error_message, environment, attempts, expected_behavior, additional_context, checklist)';
END $$;

-- Проверка созданного шаблона
SELECT 
    id,
    template_name,
    category,
    visibility,
    is_active,
    usage_count,
    jsonb_array_length(fields) as fields_count,
    created_at
FROM templates
WHERE template_name = 'Запрос помощи: Программирование'
ORDER BY created_at DESC
LIMIT 1;

-- Вывод структуры полей для проверки
SELECT 
    template_name,
    jsonb_pretty(fields) as fields_structure
FROM templates
WHERE template_name = 'Запрос помощи: Программирование'
LIMIT 1;

-- ПРИМЕЧАНИЕ:
-- Перед выполнением скрипта ОБЯЗАТЕЛЬНО замените:
-- 1. YOUR_WORKSPACE_ID_HERE - на реальный UUID workspace из таблицы workspaces
-- 2. YOUR_ADMIN_USER_ID_HERE - на реальный UUID admin пользователя из таблицы users
--
-- Получить ID можно так:
-- SELECT id, name FROM workspaces LIMIT 5;
-- SELECT id, username, role FROM users WHERE role = 'admin' LIMIT 5;
