#!/usr/bin/env python3
"""Проверка валидности Postman коллекций."""
import json
from pathlib import Path

def check_postman_collection(file_path: Path) -> dict:
    """Проверка Postman коллекции на валидность."""
    result = {
        'valid': False,
        'error': None,
        'stats': {}
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result['valid'] = True
        result['stats'] = {
            'folders': len(data.get('item', [])),
            'variables': len(data.get('variable', [])),
            'schema': data.get('info', {}).get('schema'),
            'name': data.get('info', {}).get('name'),
            'postman_id': data.get('info', {}).get('_postman_id')
        }
        
    except json.JSONDecodeError as e:
        result['error'] = f'JSON decode error: {e}'
    except Exception as e:
        result['error'] = f'Error: {e}'
    
    return result

def main():
    """Проверка всех Postman коллекций."""
    docs_path = Path(__file__).parent / 'docs'
    
    collections = [
        docs_path / 'NoRake_Complete_API_Collection.postman_collection.json',
        docs_path / 'NoRake_API_Collection.postman_collection.json'
    ]
    
    print('🔍 Проверка Postman коллекций...\n')
    
    for collection_path in collections:
        print(f'📄 {collection_path.name}')
        
        if not collection_path.exists():
            print(f'   ❌ Файл не найден\n')
            continue
        
        result = check_postman_collection(collection_path)
        
        if result['valid']:
            print('   ✅ Валидный JSON')
            print(f'   📊 Статистика:')
            for key, value in result['stats'].items():
                print(f'      - {key}: {value}')
        else:
            print(f'   ❌ {result["error"]}')
        
        print()

if __name__ == '__main__':
    main()
