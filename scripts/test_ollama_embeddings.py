"""
Скрипт для тестирования Ollama embeddings клиента.

Проверяет:
1. Доступность Ollama сервиса
2. Генерацию embeddings для одного текста
3. Генерацию embeddings для нескольких текстов
4. Размерность векторов

Usage:
    uv run python scripts/test_ollama_embeddings.py
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.integrations.ai.embeddings.ollama import OllamaEmbeddings


async def test_ollama_embeddings():
    """Тестирует Ollama embeddings клиент."""
    print("🚀 Тестирование Ollama Embeddings\n")

    async with OllamaEmbeddings() as embedder:
        # 1. Проверка доступности сервиса
        print("1️⃣ Проверка доступности Ollama сервиса...")
        is_healthy = await embedder.check_health()
        if not is_healthy:
            print("❌ Ollama сервис недоступен!")
            return False
        print(f"✅ Ollama сервис доступен: {embedder.base_url}\n")

        # 2. Информация о модели
        print("2️⃣ Информация о модели:")
        print(f"   Модель: {embedder.model}")
        print(f"   Размерность: {embedder.get_dimensions()}\n")

        # 3. Тест одного текста
        print("3️⃣ Генерация embedding для одного текста...")
        test_text = "Тестовый текст для проверки работы embeddings"
        vector = await embedder.embed_query(test_text)
        print(f"   Текст: '{test_text}'")
        print(f"   Размерность вектора: {len(vector)}")
        print(f"   Первые 5 значений: {vector[:5]}\n")

        # 4. Тест нескольких текстов
        print("4️⃣ Генерация embeddings для нескольких текстов...")
        test_texts = [
            "Первый тестовый документ о программировании",
            "Второй документ о машинном обучении",
            "Третий текст о векторных базах данных",
        ]
        vectors = await embedder.embed(test_texts)
        print(f"   Количество текстов: {len(test_texts)}")
        print(f"   Количество векторов: {len(vectors)}")
        print(f"   Размерность каждого: {len(vectors[0])}\n")

        # 5. Проверка похожести (косинусное сходство)
        print("5️⃣ Проверка косинусного сходства между текстами...")
        import numpy as np

        def cosine_similarity(v1, v2):
            """Вычисляет косинусное сходство между двумя векторами."""
            v1_norm = np.linalg.norm(v1)
            v2_norm = np.linalg.norm(v2)
            if v1_norm == 0 or v2_norm == 0:
                return 0
            return np.dot(v1, v2) / (v1_norm * v2_norm)

        v1, v2, v3 = np.array(vectors[0]), np.array(vectors[1]), np.array(vectors[2])

        sim_1_2 = cosine_similarity(v1, v2)
        sim_1_3 = cosine_similarity(v1, v3)
        sim_2_3 = cosine_similarity(v2, v3)

        print(f"   Сходство '1-2': {sim_1_2:.4f}")
        print(f"   Сходство '1-3': {sim_1_3:.4f}")
        print(f"   Сходство '2-3': {sim_2_3:.4f}\n")

        print("✅ Все тесты пройдены успешно!")
        return True


async def test_both_models():
    """Тестирует обе доступные модели."""
    print("🔄 Сравнение моделей Ollama\n")

    models = [
        ("mxbai-embed-large", 1024),
        ("nomic-embed-text", 768),
    ]

    test_text = "Тестовый текст для сравнения моделей"

    for model_name, expected_dim in models:
        print(f"📊 Модель: {model_name}")
        print(f"   Ожидаемая размерность: {expected_dim}")

        try:
            async with OllamaEmbeddings(model=model_name) as embedder:
                vector = await embedder.embed_query(test_text)
                actual_dim = len(vector)
                print(f"   Фактическая размерность: {actual_dim}")
                print(
                    f"   Статус: {'✅ OK' if actual_dim == expected_dim else '❌ MISMATCH'}\n"
                )
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)}\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Ollama Embeddings Test Suite")
    print("=" * 60 + "\n")

    try:
        # Основной тест с моделью по умолчанию
        success = asyncio.run(test_ollama_embeddings())

        if success:
            print("\n" + "=" * 60)
            # Сравнение обеих моделей
            asyncio.run(test_both_models())
            print("=" * 60)

    except KeyboardInterrupt:
        print("\n\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {str(e)}")
        import traceback

        traceback.print_exc()
