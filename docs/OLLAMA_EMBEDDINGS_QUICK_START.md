# Ollama Embeddings - Quick Start

## Обзор

Интеграция с локальным Ollama Docker контейнером для генерации бесплатных embeddings. Поддерживает две модели с разными размерностями.

## Настройки (.env)

```bash
# Ollama Embeddings (РЕКОМЕНДУЕТСЯ - бесплатно, локально)
OLLAMA_EMBEDDINGS_BASE_URL=http://your-ollama-server.com/ollama
OLLAMA_EMBEDDINGS_API_KEY=your_api_key_here
OLLAMA_EMBEDDING_MODEL=mxbai-embed-large
OLLAMA_EMBEDDING_DIMENSIONS=1024
USE_OLLAMA_EMBEDDINGS=True
```

## Доступные модели

| Модель | Размер | Размерность | Рекомендация |
|--------|--------|-------------|--------------|
| **mxbai-embed-large** | 669 MB | 1024 | ✅ Высокое качество |
| **nomic-embed-text** | 274 MB | 768 | Компактная версия |

## Использование в коде

### Базовое использование

```python
from src.core.integrations.ai.embeddings import OllamaEmbeddings

async with OllamaEmbeddings() as embedder:
    # Один текст
    vector = await embedder.embed_query("поисковый запрос")
    print(f"Размерность: {len(vector)}")  # 1024

    # Несколько текстов
    vectors = await embedder.embed([
        "Первый документ",
        "Второй документ",
    ])
    print(f"Векторов: {len(vectors)}")  # 2
```

### С выбором модели

```python
# Использование компактной модели
async with OllamaEmbeddings(model="nomic-embed-text") as embedder:
    vector = await embedder.embed_query("текст")
    print(f"Размерность: {len(vector)}")  # 768
```

### Проверка доступности

```python
async with OllamaEmbeddings() as embedder:
    if await embedder.check_health():
        print("Ollama доступен")
        vectors = await embedder.embed(["text1", "text2"])
```

## Тестирование

```bash
# Запустить тесты всех функций
uv run python scripts/test_ollama_embeddings.py
```

Тест проверяет:
- ✅ Доступность сервиса
- ✅ Генерацию embedding для одного текста
- ✅ Генерацию embeddings для нескольких текстов
- ✅ Правильность размерности векторов
- ✅ Косинусное сходство (семантическое сравнение)
- ✅ Обе модели (mxbai-embed-large, nomic-embed-text)

## API Reference

### OllamaEmbeddings

#### Методы

**`embed(texts: List[str]) -> List[List[float]]`**
- Генерирует embeddings для списка текстов
- Возвращает список векторов

**`embed_query(text: str) -> List[float]`**
- Генерирует embedding для одного текста
- Оптимизированная версия для единичных запросов

**`embed_documents(documents: List[str]) -> List[List[float]]`**
- Алиас для `embed()` с семантическим названием

**`check_health() -> bool`**
- Проверяет доступность Ollama сервиса
- Возвращает `True` если сервис отвечает

**`get_dimensions() -> int`**
- Возвращает размерность векторов для текущей модели
- 1024 для mxbai-embed-large, 768 для nomic-embed-text

## Архитектура

```
BaseAIClient (src/core/integrations/ai/base.py)
    ↓ наследование
BaseEmbeddings (src/core/integrations/ai/embeddings/base.py)
    ↓ наследование
OllamaEmbeddings (src/core/integrations/ai/embeddings/ollama.py)
```

### Особенности реализации

1. **Кастомные заголовки**: Использует `X-Api-Key` вместо `Authorization Bearer`
2. **Последовательная обработка**: Ollama API не поддерживает batch запросы
3. **Context manager**: Автоматическое управление HTTP клиентом
4. **Retry механизм**: Наследуется от `BaseAIClient`

## Сравнение с OpenAI

| Параметр | Ollama (mxbai-embed-large) | OpenAI (text-embedding-3-small) |
|----------|----------------------------|----------------------------------|
| **Цена** | Бесплатно | $0.02 за 1M токенов |
| **Размерность** | 1024 | 1536 |
| **Локация** | Локальный Docker | Облако |
| **Скорость** | Зависит от железа | Быстро |
| **Качество** | Высокое | Очень высокое |

## Рекомендации

✅ **Используй Ollama если:**
- Нужна бесплатная альтернатива
- Требуется работа без интернета
- Важна конфиденциальность данных
- Есть достаточно ресурсов на сервере (669 MB + RAM)

❌ **Используй OpenAI если:**
- Критична максимальная точность
- Нужна высокая скорость на слабом железе
- Бюджет позволяет ($0.02 за 1M токенов)

## Переключение между провайдерами

В `.env` настрой приоритет:

```bash
# Приоритет 1: Ollama (бесплатно)
USE_OLLAMA_EMBEDDINGS=True

# Приоритет 2: OpenAI (платно)
OPENAI_EMBEDDINGS_API_KEY=sk-xxx

# Приоритет 3: Local sentence-transformers (бесплатно, медленно)
USE_LOCAL_EMBEDDINGS=False
```

## Troubleshooting

### Ошибка подключения

```python
ServiceUnavailableException: Не удалось подключиться к Ollama сервису
```

**Решение:**
1. Проверь доступность: `curl http://ai.equiply.ru/ollama/api/tags`
2. Проверь API ключ в `.env`
3. Убедись что Docker контейнер запущен

### Неправильная размерность

```python
# Ожидалось 1024, получили 768
```

**Решение:** Обнови `OLLAMA_EMBEDDING_DIMENSIONS` в `.env` под текущую модель:
- `mxbai-embed-large` → 1024
- `nomic-embed-text` → 768

### Медленная генерация

**Причины:**
- Модель загружается в память (первый запрос медленный)
- Слабое железо на сервере
- Много текстов обрабатывается последовательно

**Решение:**
- Используй компактную модель `nomic-embed-text`
- Переключись на OpenAI для критичных по скорости запросов
- Кэшируй embeddings для часто используемых текстов

## См. также

- `docs/OPENROUTER_QUICK_TEST.md` - Настройка OpenRouter для чатов
- `docs/OPENROUTER_FREE_MODELS.md` - Список бесплатных моделей
- `src/core/integrations/ai/embeddings/openrouter.py` - OpenRouter embeddings (deprecated)
- `src/core/integrations/ai/embeddings/base.py` - Базовый класс
