"""
Скрипт для получения информации о embedding моделях из OpenRouter API.
"""

import asyncio
import json
import os
from typing import Any, Dict, List

import httpx


async def fetch_embedding_models() -> List[Dict[str, Any]]:
    """
    Получает список embedding моделей из OpenRouter API.

    Returns:
        List[Dict]: Список моделей с полной информацией
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY не найден в переменных окружения. "
            "Установите через: $env:OPENROUTER_API_KEY='your-key'"
        )

    url = "https://openrouter.ai/api/v1/models"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            url, headers={"Authorization": f"Bearer {api_key}"}
        )
        response.raise_for_status()
        data = response.json()

    all_models = data.get("data", [])
    print(f"📊 Всего моделей в OpenRouter: {len(all_models)}")

    # Ищем embedding модели по различным признакам
    embedding_keywords = [
        "embed",
        "embedding",
        "ada",
        "text-embedding",
    ]

    embedding_models = []
    for model in all_models:
        model_id = model.get("id", "").lower()
        model_name = model.get("name", "").lower()
        model_desc = model.get("description", "").lower()

        if any(kw in model_id or kw in model_name or kw in model_desc for kw in embedding_keywords):
            embedding_models.append(model)

    print(f"🔍 Найдено embedding моделей: {len(embedding_models)}")

    # Фильтруем по нужным провайдерам
    target_providers = ["qwen", "mistral", "openai"]
    target_models = []

    for model in embedding_models:
        model_id = model.get("id", "").lower()
        if any(provider in model_id for provider in target_providers):
            target_models.append(model)
            print(f"  ✅ {model.get('id')}: {model.get('name')}")

    return target_models


async def main():
    """Основная функция."""
    print("🚀 Получение embedding моделей из OpenRouter API...\n")

    models = await fetch_embedding_models()

    if not models:
        print("\n⚠️  Не найдено ни одной embedding модели!")
        print("Возможные причины:")
        print("1. OpenRouter пока не предоставляет embeddings через API")
        print("2. Модели доступны только через веб-интерфейс")
        print("3. Нужен специальный эндпоинт для embeddings")
        return

    print(f"\n📝 Найдено {len(models)} целевых моделей\n")

    # Группируем по провайдерам
    by_provider = {}
    for model in models:
        provider = model["id"].split("/")[0] if "/" in model["id"] else "unknown"
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)

    # Выводим сгруппированные модели
    for provider, provider_models in sorted(by_provider.items()):
        print(f"\n{'=' * 60}")
        print(f"Провайдер: {provider.upper()}")
        print(f"{'=' * 60}")

        for model in provider_models:
            print(f"\n  ID: {model['id']}")
            print(f"  Name: {model.get('name', 'N/A')}")
            print(f"  Context: {model.get('context_length', 'N/A')}")

            pricing = model.get("pricing", {})
            print(f"  Input: ${pricing.get('prompt', '0')}/M tokens")
            print(f"  Output: ${pricing.get('completion', '0')}/M tokens")

            if model.get("description"):
                desc = model["description"][:200]
                print(f"  Description: {desc}...")

    # Сохраняем в JSON
    output_file = "fixtures_data/openrouter_embedding_models.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(models, f, indent=2, ensure_ascii=False)

    print(f"\n\n💾 Данные сохранены в: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
