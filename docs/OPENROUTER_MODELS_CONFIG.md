# OpenRouter Models Configuration

## Обновление от 2025-01-15

### ✅ Исправлены критические ошибки в ID моделей

**До исправления (причина 400 Bad Request):**
- ❌ `qwen/qwen3-coder-480b` - модель не существует
- ❌ `moonshot/kimi-dev-72b` - неправильный namespace
- ❌ `deepseek/deepseek-r1-70b` - модель не существует
- ❌ `alibaba/tongyi-deepresearch-30b` - неполный ID
- ❌ `deepseek/deepseek-v3.1` - неполный ID
- ❌ `openai/text-embedding-ada-002` - модель не доступна в OpenRouter

**После исправления:**
Все модели заменены на **бесплатные** версии с проверенными ID.

## Текущая конфигурация (FREE models)

### Text-only модели

#### 1. qwen_coder (код-генерация)
```python
"id": "qwen/qwen3-coder:free"
"context_window": 262144
"supports_vision": False
```

#### 2. kimi_k2 (общего назначения)
```python
"id": "moonshotai/kimi-k2:free"
"context_window": 32768
"supports_vision": False
```

#### 3. deepseek_v3 (рассуждения)
```python
"id": "deepseek/deepseek-chat-v3.1:free"
"context_window": 163840
"supports_vision": False
```

#### 4. tongyi_research (исследования)
```python
"id": "alibaba/tongyi-deepresearch-30b-a3b:free"
"context_window": 131072
"supports_vision": False
```

### Multimodal модели (с поддержкой изображений)

#### 5. qwen_vl (vision + текст)
```python
"id": "qwen/qwen2.5-vl-32b-instruct:free"
"context_window": 16384
"supports_vision": True
```

#### 6. gemini_flash (Google, огромный контекст)
```python
"id": "google/gemini-2.0-flash-exp:free"
"context_window": 1048576  # 1M tokens!
"supports_vision": True
```

#### 7. gemma_27b (Google vision)
```python
"id": "google/gemma-3-27b-it:free"
"context_window": 131072
"supports_vision": True
```

## Embeddings

**ВАЖНО:** OpenRouter не предоставляет бесплатные embedding модели.

`OPENROUTER_EMBEDDING_MODEL = None`

Для RAG используется semantic search по текстовым чанкам без embeddings.

## Источник данных

Полный список моделей сохранён в:
```
fixtures_data/openrouter_models.json
```

Получен через OpenRouter API:
```bash
GET https://openrouter.ai/api/v1/models
```

## Проверка моделей

Все бесплатные модели отфильтрованы по:
```python
pricing.prompt == "0"
```

Vision модели отобраны по:
```python
architecture.input_modalities contains "image"
```

## Настройка API ключа

**Текущий статус:** Placeholder в `.env.dev`

Получить ключ:
1. https://openrouter.ai/settings/keys
2. Заменить в `.env.dev`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-ваш-настоящий-ключ
   ```

## Использование в коде

```python
from src.core.settings.base import settings

# Получить конфигурацию модели
model_config = settings.OPENROUTER_CHAT_MODELS["qwen_coder"]

# Проверить поддержку vision
if model_config["supports_vision"]:
    # Можно отправлять изображения
    pass

# API запрос
payload = {
    "model": model_config["id"],  # "qwen/qwen3-coder:free"
    "messages": messages,
    "temperature": model_config["temperature"],
    "max_tokens": model_config["max_tokens"],
}
```

## Multimodal запросы

Для моделей с `supports_vision: True`:

```python
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Что на этом изображении?"},
            {
                "type": "image_url",
                "image_url": {"url": "data:image/jpeg;base64,<base64>"}
            }
        ]
    }
]
```

## Следующие шаги

1. ✅ ID моделей исправлены
2. ✅ Все модели заменены на бесплатные
3. ✅ Добавлены multimodal модели
4. ⏳ Настроить реальный API ключ в `.env.dev`
5. ⏳ Протестировать отправку сообщений
6. ⏳ Реализовать multimodal support в AIChatService
