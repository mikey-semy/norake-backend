# OpenRouter - Решение проблем

## ✅ Исправленные проблемы (2025-11-15)

### 1. ❌ 400 Bad Request
**Причина**: Неправильные ID моделей в конфигурации
**Решение**: Все 5 моделей заменены на валидные бесплатные версии

**До**:
```python
"qwen/qwen3-coder-480b"          # ❌ Модель не существует
"moonshot/kimi-dev-72b"           # ❌ Неправильный namespace
"deepseek/deepseek-r1-70b"        # ❌ Модель не существует
```

**После**:
```python
"qwen/qwen3-coder:free"           # ✅ Бесплатная версия
"moonshotai/kimi-k2:free"         # ✅ Правильный namespace + :free
"deepseek/deepseek-chat-v3.1:free" # ✅ Правильный ID
```

### 2. ❌ S3: BaseAPIException.__init__() got unexpected keyword argument 'error_code'
**Причина**: Попытка передать `error_code` в BaseAPIException (такого параметра нет)
**Решение**: Убрано пробрасывание BaseAPIException, используется только ServiceUnavailableException

**До**:
```python
except BaseAPIException:
    raise  # ❌ Неправильная попытка reraise
except Exception as e:
    raise ServiceUnavailableException("Storage (S3)") from e
```

**После**:
```python
except ServiceUnavailableException:
    raise  # ✅ Только 503 пробрасываем
except Exception as e:
    logger.error("❌ Ошибка подключения к S3: %s", str(e))
    raise ServiceUnavailableException("Storage (S3)") from e
```

### 3. ❌ 503 Service Unavailable на фронтенде
**Причина**: Cascade ошибок - S3 exception → OpenRouter 400 → 503 на клиенте
**Решение**: Раздельная обработка ошибок + детальное логирование

## 🔍 Как диагностировать новые проблемы

### Шаг 1: Проверить логи с деталями
```bash
# Последние OpenRouter ошибки
Get-Content logs/*.log -Tail 200 | Select-String "OpenRouter API" -Context 3

# Последние S3 ошибки
Get-Content logs/*.log -Tail 200 | Select-String "S3" -Context 3
```

**Теперь логи содержат**:
- Код статуса HTTP
- model_id
- Полное тело ошибки от API
- Контекст запроса

### Шаг 2: Проверить конфигурацию
```bash
# Список доступных моделей
uv run python -c "from src.core.settings.base import settings; print(list(settings.OPENROUTER_CHAT_MODELS.keys()))"

# Проверить ID конкретной модели
uv run python -c "from src.core.settings.base import settings; print(settings.OPENROUTER_CHAT_MODELS['qwen_coder']['id'])"
```

**Ожидаемый вывод**:
```python
# Доступные model_key:
['qwen_coder', 'qwen_vl', 'gemini_flash', 'kimi_k2', 'deepseek_v3', 'tongyi_research', 'gemma_27b']

# ID модели (должен заканчиваться на :free):
'qwen/qwen3-coder:free'
```

### Шаг 3: Проверить API ключ
```bash
# Должен начинаться с sk-or-v1-
Get-Content .env.dev | Select-String "OPENROUTER_API_KEY"

# Тест подключения
curl -X GET "https://openrouter.ai/api/v1/models" `
  -H "Authorization: Bearer $env:OPENROUTER_API_KEY"
```

### Шаг 4: Тест конкретной модели
```bash
# Проверить что модель существует в API
Get-Content fixtures_data/openrouter_models.json | ConvertFrom-Json |
  Select-Object -ExpandProperty data |
  Where-Object { $_.id -eq "qwen/qwen3-coder:free" } |
  Select-Object id, pricing, context_length
```

**Ожидаемый вывод**:
```
id                      pricing                     context_length
--                      -------                     --------------
qwen/qwen3-coder:free   @{prompt=0; completion=0}   262144
```

## 🐛 Типичные ошибки и решения

### 400 Bad Request: Invalid model
**Симптомы**:
```
OpenRouter API error [400]: Invalid model ID: qwen/qwen3-coder-480b
```

**Решение**:
1. Проверить что model_id заканчивается на `:free`
2. Убедиться что model_key в чате соответствует настройкам
3. Проверить что модель есть в `fixtures_data/openrouter_models.json`

### 401 Unauthorized
**Симптомы**:
```
OpenRouter API error [401]: Invalid API key
```

**Решение**:
1. Проверить что API ключ начинается с `sk-or-v1-`
2. Убедиться что ключ валидный (не истёк, не отозван)
3. Проверить что ключ правильно экспортирован в `.env.dev`

### 503 Service Unavailable
**Симптомы**:
```
Storage (S3) сервис не доступен
```

**Решение**:
1. Проверить S3 credentials в `.env.dev`
2. Убедиться что bucket существует
3. Проверить сетевое подключение к S3

### Model не поддерживает vision
**Симптомы**:
```
OpenRouter API error [400]: Model does not support images
```

**Решение**:
1. Использовать модели с `supports_vision: True`:
   - `qwen_vl`
   - `gemini_flash`
   - `gemma_27b`
2. Проверить формат запроса (должен быть multimodal)

## 📊 Мониторинг

### Проверка здоровья системы
```bash
# Проверить последние ошибки (любые)
Get-Content logs/*.log -Tail 100 | Select-String "ERROR"

# Проверить успешные запросы к OpenRouter
Get-Content logs/*.log -Tail 100 | Select-String "Отправка запроса к OpenRouter"

# Статистика по моделям (если есть)
Get-Content logs/*.log | Select-String "model=" |
  ForEach-Object { $_ -replace '.*model=([^\s,]+).*', '$1' } |
  Group-Object | Sort-Object Count -Descending
```

### Проверка токенов
```python
# В Python коде добавить логирование
self.logger.info(
    "Использовано токенов: %d (модель: %s)",
    tokens_used,
    model_id,
)
```

## 🔧 Дополнительные утилиты

### Скрипт проверки всех моделей
```python
# scripts/test_openrouter_models.py
import asyncio
import httpx
from src.core.settings.base import settings

async def test_model(model_key: str):
    model_config = settings.OPENROUTER_CHAT_MODELS[model_key]
    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": model_config["id"],
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 10,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 200:
            print(f"✅ {model_key}: OK")
        else:
            print(f"❌ {model_key}: {response.status_code} {response.text}")

async def main():
    for model_key in settings.OPENROUTER_CHAT_MODELS.keys():
        await test_model(model_key)

if __name__ == "__main__":
    asyncio.run(main())
```

**Запуск**:
```bash
uv run python scripts/test_openrouter_models.py
```

## 📚 Полезные ссылки

- [OpenRouter API Documentation](https://openrouter.ai/docs)
- [OpenRouter Models List](https://openrouter.ai/models)
- [OpenRouter Discord](https://discord.gg/openrouter)
- `fixtures_data/openrouter_models.json` - локальная копия всех моделей
- `docs/OPENROUTER_MODELS_CONFIG.md` - описание конфигурации моделей
- `docs/OPENROUTER_QUICK_TEST.md` - быстрые тесты API
