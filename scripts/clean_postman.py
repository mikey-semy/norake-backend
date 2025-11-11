#!/usr/bin/env python3
"""Создание Postman-совместимых коллекций без эмодзи."""
import json
import re
from pathlib import Path

def remove_emoji(text):
    """Удаление эмодзи из текста."""
    # Паттерн для большинства эмодзи
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(r'', text).strip()

def clean_collection(data):
    """Рекурсивная очистка коллекции от эмодзи."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key == 'name' and isinstance(value, str):
                data[key] = remove_emoji(value)
            else:
                clean_collection(value)
    elif isinstance(data, list):
        for item in data:
            clean_collection(item)

    return data

def main():
    """Создание чистых коллекций."""
    docs_path = Path(__file__).parent / 'docs'

    collections = [
        'NoRake_Complete_API_Collection.postman_collection.json',
        'NoRake_API_Collection.postman_collection.json'
    ]

    print('🧹 Очистка Postman коллекций от эмодзи...\n')

    for collection_name in collections:
        source_path = docs_path / collection_name

        if not source_path.exists():
            print(f'❌ {collection_name} - файл не найден')
            continue

        # Чтение оригинала
        with open(source_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Очистка
        cleaned_data = clean_collection(data)

        # Сохранение чистой версии (без BOM, с отступами)
        clean_path = docs_path / collection_name.replace('.postman_collection.json', '_clean.postman_collection.json')
        with open(clean_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

        print(f'✅ {collection_name}')
        print(f'   → {clean_path.name}')

    print('\n📌 Попробуйте импортировать файлы с суффиксом _clean')

if __name__ == '__main__':
    main()
