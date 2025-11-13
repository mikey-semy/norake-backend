-- ============================================================================
-- NoRake Backend: Создание шаблонов для Issues
-- ============================================================================
-- Описание:
--   1. Developer Issue Template (Программирование)
--   2. Drive Engineer Template (Приводчики - ошибки преобразователей частоты)
--
-- Использование:
--   1. Замените YOUR_WORKSPACE_ID_HERE на UUID вашего workspace
--   2. Замените YOUR_ADMIN_USER_ID_HERE на UUID администратора
--   3. Выполните: psql -U postgres -d norake_dev -f create_templates.sql
-- ============================================================================

\set workspace_id 'YOUR_WORKSPACE_ID_HERE'
\set author_id 'YOUR_ADMIN_USER_ID_HERE'

-- ============================================================================
-- 1. DEVELOPER ISSUE TEMPLATE (Программирование)
-- ============================================================================

INSERT INTO templates (
    id,
    workspace_id,
    template_name,
    category,
    description,
    icon,
    visibility,
    is_active,
    usage_count,
    author_id,
    fields,
    custom_metadata,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    :'workspace_id'::uuid,
    'Запрос помощи: Программирование',
    'software',
    'Структурированный запрос помощи для программистов. Система RED/GREEN статусов для сохранения решений.',
    '💻',
    'PUBLIC',
    true,
    0,
    :'author_id'::uuid,
    '[
        {
            "field_name": "goal",
            "field_type": "text",
            "label": "Цель / Что нужно достичь",
            "description": "Опишите конечную цель, а не просто \"не работает\"",
            "is_required": true,
            "order_index": 1,
            "placeholder": "Нужно интегрировать OAuth2 авторизацию через Google в FastAPI",
            "validation_rules": {
                "min_length": 20,
                "max_length": 500
            }
        },
        {
            "field_name": "current_behavior",
            "field_type": "text",
            "label": "Проблема / Что происходит сейчас",
            "description": "Четкое описание текущего поведения системы",
            "is_required": true,
            "order_index": 2,
            "placeholder": "При попытке логина через Google возвращается HTTP 401 Unauthorized",
            "validation_rules": {
                "min_length": 20,
                "max_length": 1000
            }
        },
        {
            "field_name": "code_example",
            "field_type": "text",
            "label": "Минимальный воспроизводимый пример (MRE)",
            "description": "Минимальный код для воспроизведения проблемы без секретов и лишних зависимостей",
            "is_required": true,
            "order_index": 3,
            "placeholder": "from fastapi import FastAPI...",
            "validation_rules": {
                "min_length": 50,
                "max_length": 10000
            }
        },
        {
            "field_name": "error_message",
            "field_type": "text",
            "label": "Полная ошибка / Traceback",
            "description": "Точный текст ошибки, traceback, логи (НЕ скриншот)",
            "is_required": false,
            "order_index": 4,
            "placeholder": "Traceback (most recent call last):...",
            "validation_rules": {
                "max_length": 10000
            }
        },
        {
            "field_name": "environment",
            "field_type": "text",
            "label": "Окружение",
            "description": "Версии языка, библиотек, ОС",
            "is_required": true,
            "order_index": 5,
            "placeholder": "Python 3.11.5, FastAPI 0.104.1, Ubuntu 22.04",
            "validation_rules": {
                "min_length": 10,
                "max_length": 1000
            }
        },
        {
            "field_name": "attempts",
            "field_type": "text",
            "label": "Что уже пробовали",
            "description": "Список предпринятых попыток решения проблемы",
            "is_required": true,
            "order_index": 6,
            "placeholder": "1. Проверил документацию FastAPI\n2. Попробовал изменить...",
            "validation_rules": {
                "min_length": 20,
                "max_length": 5000
            }
        },
        {
            "field_name": "expected_behavior",
            "field_type": "text",
            "label": "Ожидаемое поведение",
            "description": "Что должно произойти в идеале",
            "is_required": true,
            "order_index": 7,
            "placeholder": "После успешного логина должен возвращаться JWT токен",
            "validation_rules": {
                "min_length": 20,
                "max_length": 1000
            }
        },
        {
            "field_name": "additional_context",
            "field_type": "text",
            "label": "Дополнительный контекст",
            "description": "Любая другая информация, которая может помочь",
            "is_required": false,
            "order_index": 8,
            "placeholder": "Проблема воспроизводится только в production окружении",
            "validation_rules": {
                "max_length": 2000
            }
        },
        {
            "field_name": "solution",
            "field_type": "text",
            "label": "Решение (для GREEN статуса)",
            "description": "Финальное решение проблемы для базы знаний",
            "is_required": false,
            "order_index": 9,
            "placeholder": "Проблема решена добавлением...",
            "validation_rules": {
                "min_length": 50,
                "max_length": 10000
            }
        }
    ]'::jsonb,
    '{
        "status_colors": {
            "RED": "Проблема - требуется помощь",
            "GREEN": "Решено - в базе знаний"
        },
        "checklist": [
            "Убрал секреты и пароли из кода",
            "Минимизировал код до MRE",
            "Приложил точный текст ошибки",
            "Указал версии зависимостей",
            "Описал что уже пробовал"
        ]
    }'::jsonb,
    NOW(),
    NOW()
);

-- ============================================================================
-- 2. DRIVE ENGINEER TEMPLATE (Приводчики - ПЧ)
-- ============================================================================

INSERT INTO templates (
    id,
    workspace_id,
    template_name,
    category,
    description,
    icon,
    visibility,
    is_active,
    usage_count,
    author_id,
    fields,
    custom_metadata,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    :'workspace_id'::uuid,
    'Ошибка преобразователя частоты',
    'hardware',
    'Шаблон для документирования ошибок преобразователей частоты (ПЧ) с детальной диагностикой и решениями',
    '⚡',
    'PUBLIC',
    true,
    0,
    :'author_id'::uuid,
    '[
        {
            "field_name": "equipment_name",
            "field_type": "text",
            "label": "Агрегат / Оборудование",
            "description": "Полное наименование агрегата/линии, где произошла ошибка",
            "is_required": true,
            "order_index": 1,
            "placeholder": "Линия розлива №3, конвейер подачи бутылок",
            "validation_rules": {"min_length": 10, "max_length": 200}
        },
        {
            "field_name": "drive_info",
            "field_type": "jsonb",
            "label": "Преобразователь частоты",
            "description": "Информация о ПЧ: производитель, модель, мощность, версия ПО",
            "is_required": true,
            "order_index": 2,
            "default_value": {"manufacturer": "", "model": "", "power": "", "firmware_version": ""},
            "placeholder": "Siemens SINAMICS S120, 15 кВт, FW 4.8.2"
        },
        {
            "field_name": "error_code",
            "field_type": "text",
            "label": "Код ошибки",
            "description": "Точный код ошибки с дисплея ПЧ (Fxxxxx, Axxxxx, Exxxx)",
            "is_required": true,
            "order_index": 3,
            "placeholder": "F07802",
            "validation_rules": {"pattern": "^[FAE]\\\\d{4,5}$", "max_length": 10}
        },
        {
            "field_name": "error_description",
            "field_type": "text",
            "label": "Описание ошибки",
            "description": "Полное текстовое описание ошибки с дисплея ПЧ",
            "is_required": true,
            "order_index": 4,
            "placeholder": "Устройство питания или силовая часть не готова",
            "validation_rules": {"min_length": 10, "max_length": 500}
        },
        {
            "field_name": "occurrence_moment",
            "field_type": "text",
            "label": "Момент возникновения",
            "description": "Когда и при каких условиях возникает ошибка",
            "is_required": true,
            "order_index": 5,
            "placeholder": "При старте двигателя после простоя более 2 часов",
            "validation_rules": {"min_length": 20, "max_length": 500}
        },
        {
            "field_name": "parameters_at_error",
            "field_type": "jsonb",
            "label": "Параметры на момент ошибки",
            "description": "Частота, ток, напряжение, температура и другие параметры",
            "is_required": false,
            "order_index": 6,
            "default_value": {"frequency": "", "current": "", "voltage": "", "dc_bus_voltage": "", "motor_load": "", "temperature": ""}
        },
        {
            "field_name": "actions_taken",
            "field_type": "text",
            "label": "Что было сделано",
            "description": "Подробный список действий по устранению ошибки",
            "is_required": true,
            "order_index": 7,
            "placeholder": "1. Проверил напряжение\\n2. Перезапустил ПЧ\\n3. ...",
            "validation_rules": {"min_length": 50, "max_length": 5000}
        },
        {
            "field_name": "related_parameters",
            "field_type": "jsonb",
            "label": "Связанные параметры ПЧ",
            "description": "Значения параметров конфигурации (p0210, p0857, r0949, etc)",
            "is_required": false,
            "order_index": 8,
            "default_value": {},
            "placeholder": "p0210: 380V, p0857: 5.0 сек"
        },
        {
            "field_name": "equipment_state",
            "field_type": "text",
            "label": "Состояние оборудования",
            "description": "Физическое состояние ПЧ и электродвигателя (чек-лист)",
            "is_required": true,
            "order_index": 9,
            "placeholder": "✅ Визуальный осмотр: чисто\\n⚠️ Вентилятор: шумит",
            "validation_rules": {"min_length": 30, "max_length": 2000}
        },
        {
            "field_name": "connection_config",
            "field_type": "jsonb",
            "label": "Конфигурация подключения",
            "description": "Тип двигателя, мощность, напряжение, длина кабеля",
            "is_required": false,
            "order_index": 10,
            "default_value": {"motor_type": "Асинхронный 3-фазный", "motor_power": "", "motor_voltage": "", "motor_current": "", "motor_speed": "", "cable_length": "", "motor_connection": "Звезда (Y)"}
        },
        {
            "field_name": "operating_conditions",
            "field_type": "jsonb",
            "label": "Условия эксплуатации",
            "description": "Температура, влажность, запылённость, стабильность напряжения",
            "is_required": false,
            "order_index": 11,
            "default_value": {"ambient_temperature": "", "humidity": "", "dust_level": "", "supply_voltage_stability": "", "vibration_level": ""}
        },
        {
            "field_name": "error_history",
            "field_type": "text",
            "label": "История ошибок",
            "description": "Была ли эта ошибка ранее? Что помогло в прошлый раз?",
            "is_required": false,
            "order_index": 12,
            "placeholder": "Первый случай данной ошибки",
            "validation_rules": {"max_length": 2000}
        },
        {
            "field_name": "solution",
            "field_type": "text",
            "label": "Решение (для GREEN статуса)",
            "description": "Детальное описание решения: корневая причина, действия, время, запчасти",
            "is_required": false,
            "order_index": 13,
            "placeholder": "**Корневая причина**: ...\\n**Решение**: ...",
            "validation_rules": {"min_length": 50, "max_length": 5000}
        },
        {
            "field_name": "preventive_measures",
            "field_type": "text",
            "label": "Превентивные меры",
            "description": "Рекомендации для предотвращения повторения ошибки",
            "is_required": false,
            "order_index": 14,
            "placeholder": "1. Ежемесячная проверка...\\n2. Замена вентиляторов",
            "validation_rules": {"max_length": 2000}
        },
        {
            "field_name": "criticality",
            "field_type": "select",
            "label": "Критичность",
            "description": "Влияние на производство",
            "is_required": true,
            "order_index": 15,
            "options": [
                {"value": "low", "label": "LOW - Не влияет на производство"},
                {"value": "medium", "label": "MEDIUM - Локальная остановка участка"},
                {"value": "high", "label": "HIGH - Остановка линии"},
                {"value": "critical", "label": "CRITICAL - Остановка производства"}
            ],
            "default_value": "medium"
        },
        {
            "field_name": "downtime",
            "field_type": "text",
            "label": "Время простоя",
            "description": "Сколько времени оборудование было недоступно",
            "is_required": false,
            "order_index": 16,
            "placeholder": "2 часа 30 минут",
            "validation_rules": {"pattern": "^\\\\d+\\\\s*(ч|час|hour|h|мин|min|m)", "max_length": 50}
        }
    ]'::jsonb,
    '{
        "status_colors": {
            "RED": "Проблема - требуется решение",
            "YELLOW": "В работе - диагностируется",
            "GREEN": "Решено - задокументировано"
        },
        "documentation_links": {
            "siemens": "SINAMICS S120/S150 Справочник по параметрированию",
            "abb": "ABB Drive Composer Pro Manual",
            "danfoss": "VLT Operating Instructions",
            "schneider": "Altivar ATV600 Programming Manual"
        },
        "escalation_levels": [
            "Уровень 1: Локальный приводчик / электрик",
            "Уровень 2: Ведущий инженер КИПиА",
            "Уровень 3: Служба поддержки производителя",
            "Уровень 4: Сервисный инженер (выезд на объект)"
        ]
    }'::jsonb,
    NOW(),
    NOW()
);

-- ============================================================================
-- ПРОВЕРКА СОЗДАННЫХ ШАБЛОНОВ
-- ============================================================================

SELECT 
    id,
    template_name,
    category,
    icon,
    visibility,
    usage_count,
    jsonb_array_length(fields) as fields_count,
    created_at
FROM templates
WHERE workspace_id = :'workspace_id'::uuid
ORDER BY created_at DESC;

\echo ''
\echo '✅ Шаблоны успешно созданы!'
\echo ''
\echo 'Следующие шаги:'
\echo '1. Проверьте созданные шаблоны в таблице выше'
\echo '2. Используйте их при создании Issues через API'
\echo '3. Протестируйте через Postman или UI'
\echo ''
