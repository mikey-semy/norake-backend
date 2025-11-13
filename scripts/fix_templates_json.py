"""Скрипт для пересоздания templates.json с правильной структурой fields."""

import json
from pathlib import Path

def main():
    """Пересоздаёт templates.json с обёрткой fields."""
    # Загружаем оба шаблона
    dev_template = json.load(
        open('docs/templates/developer-issue-template.json', encoding='utf-8')
    )
    drive_template = json.load(
        open('docs/templates/drive-engineer-template.json', encoding='utf-8')
    )

    # Формируем структуру для фикстур
    fixtures = {
        'metadata': {
            'export_type': 'templates',
            'export_date': '2025-11-13T00:00:00',
            'count': 2,
            'description': 'Базовые шаблоны для NoRake Backend: Developer Help и Drive Engineer Error Tracking'
        },
        'data': [
            {
                'title': dev_template['template_name'],
                'description': 'Шаблон для запросов помощи по программированию с минимальным воспроизводимым примером (MRE)',
                'category': dev_template['category'].lower(),
                'visibility': dev_template['visibility'].lower(),
                'author_id': '00000000-0000-0000-0000-000000000001',
                'usage_count': 0,
                'is_active': True,
                'fields': {'fields': dev_template['fields']}  # ОБЁРТКА!
            },
            {
                'title': drive_template['template_name'],
                'description': 'Шаблон для документирования ошибок преобразователей частоты (ПЧ) с детальной диагностикой и решениями',
                'category': drive_template['category'].lower(),
                'visibility': drive_template['visibility'].lower(),
                'author_id': '00000000-0000-0000-0000-000000000001',
                'usage_count': 0,
                'is_active': True,
                'fields': {'fields': drive_template['fields']}  # ОБЁРТКА!
            }
        ]
    }

    # Сохраняем
    output_path = Path('fixtures_data/templates.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(fixtures, f, indent=2, ensure_ascii=False)

    print(f'✅ Создан {output_path} с правильной структурой fields')
    print(f'📊 Шаблонов: {len(fixtures["data"])}')
    print(f'📁 Размер файла: {output_path.stat().st_size} байт')

if __name__ == '__main__':
    main()
