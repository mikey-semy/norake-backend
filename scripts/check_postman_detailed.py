#!/usr/bin/env python3
"""Детальная проверка Postman коллекций на проблемы импорта."""
import json
from pathlib import Path

def check_postman_issues(file_path: Path):
    """Проверка потенциальных проблем для Postman импорта."""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    issues = []
    
    # 1. Проверка _postman_id
    postman_id = data.get('info', {}).get('_postman_id')
    if not postman_id or not isinstance(postman_id, str):
        issues.append('⚠️ Отсутствует или невалидный _postman_id')
    
    # 2. Проверка schema version
    schema = data.get('info', {}).get('schema')
    if not schema:
        issues.append('⚠️ Отсутствует schema в info')
    
    # 3. Проверка структуры items
    items = data.get('item', [])
    if not items:
        issues.append('⚠️ Нет items в коллекции')
    
    # 4. Проверка каждого request на обязательные поля
    def check_item(item, path="root"):
        if 'request' in item:
            req = item['request']
            if not isinstance(req, dict):
                issues.append(f'❌ {path}/{item.get("name")}: request не является объектом')
            else:
                if 'method' not in req:
                    issues.append(f'❌ {path}/{item.get("name")}: отсутствует method')
                if 'url' not in req:
                    issues.append(f'❌ {path}/{item.get("name")}: отсутствует url')
        
        # Рекурсивная проверка подпапок
        if 'item' in item:
            for sub_item in item['item']:
                check_item(sub_item, f"{path}/{item.get('name', 'unknown')}")
    
    for item in items:
        check_item(item)
    
    return issues

def main():
    """Проверка коллекций на проблемы."""
    docs_path = Path(__file__).parent / 'docs'
    
    collections = [
        docs_path / 'NoRake_Complete_API_Collection.postman_collection.json',
        docs_path / 'NoRake_API_Collection.postman_collection.json'
    ]
    
    print('🔍 Детальная проверка Postman коллекций...\n')
    
    for collection_path in collections:
        print(f'📄 {collection_path.name}')
        
        if not collection_path.exists():
            print(f'   ❌ Файл не найден\n')
            continue
        
        issues = check_postman_issues(collection_path)
        
        if not issues:
            print('   ✅ Проблем не обнаружено')
        else:
            print(f'   ⚠️ Найдено проблем: {len(issues)}')
            for issue in issues:
                print(f'      {issue}')
        
        print()

if __name__ == '__main__':
    main()
