"""
Скрипт для генерации единой фикстуры document_services_manuals.json
"""
import json

# Загрузка исходных данных
cats = json.load(open('../work-aedb/app/data/manuals/categories.json', encoding='utf-8'))
groups = json.load(open('../work-aedb/app/data/manuals/groups.json', encoding='utf-8'))
manuals = json.load(open('../work-aedb/app/data/manuals/manuals.json', encoding='utf-8'))

# Создание маппингов
cat_map = {i+1: c['name'] for i, c in enumerate(cats)}
group_map = {
    i+1: {
        **g,
        'category': cat_map.get(g['category_id'], 'Общее')
    }
    for i, g in enumerate(groups)
}

# Формирование фикстуры
result = {
    'metadata': {
        'export_type': 'document_services',
        'export_date': '2025-11-15T00:00:00',
        'count': len(manuals),
        'description': 'PDF мануалы по оборудованию из work-aedb',
        'source': 'work-aedb/app/data/manuals/'
    },
    'data': []
}

for manual in manuals:
    group_info = group_map.get(manual['group_id'], {})
    category = group_info.get('category', 'Общее')
    group_name = group_info.get('name', 'Документация')

    result['data'].append({
        'title': manual['name'],
        'description': f"{category} - {group_name}",
        'tags': [category, group_name],
        'file_url': manual['file_url'],
        'file_type': 'pdf',
        'cover_type': 'generated',
        'is_public': True
    })

# Сохранение
json.dump(
    result,
    open('fixtures_data/document_services_manuals.json', 'w', encoding='utf-8'),
    ensure_ascii=False,
    indent=2
)

print(f"✅ Создана фикстура: fixtures_data/document_services_manuals.json")
print(f"📦 Документов: {len(result['data'])}")
