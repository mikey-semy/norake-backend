# OpenRouter API - Quick Test Guide

## ✅ Проверка доступных моделей

```bash
# PowerShell
$env:OPENROUTER_API_KEY=(Get-Content .env.dev | Select-String 'OPENROUTER_API_KEY=(.*)' | ForEach-Object { $_.Matches.Groups[1].Value })

Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/models" `
  -Method GET `
  -Headers @{
    "Authorization"="Bearer $env:OPENROUTER_API_KEY"
  }
```

## ✅ Тест text-only модели

```bash
# Qwen Coder (бесплатная)
$body = @{
  model = "qwen/qwen3-coder:free"
  messages = @(@{
    role = "user"
    content = "Напиши функцию на Python для сортировки массива"
  })
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" `
  -Method POST `
  -Headers @{
    "Authorization"="Bearer $env:OPENROUTER_API_KEY"
    "Content-Type"="application/json"
  } `
  -Body $body
```

## ✅ Тест multimodal модели (с изображением)

```bash
# Gemini Flash (бесплатная, огромный контекст)
$base64Image = [Convert]::ToBase64String([IO.File]::ReadAllBytes("path/to/image.jpg"))
$dataUri = "data:image/jpeg;base64,$base64Image"

$body = @{
  model = "google/gemini-2.0-flash-exp:free"
  messages = @(@{
    role = "user"
    content = @(
      @{ type = "text"; text = "Что на этом изображении?" }
      @{ type = "image_url"; image_url = @{ url = $dataUri } }
    )
  })
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://openrouter.ai/api/v1/chat/completions" `
  -Method POST `
  -Headers @{
    "Authorization"="Bearer $env:OPENROUTER_API_KEY"
    "Content-Type"="application/json"
  } `
  -Body $body
```

## 🔴 Коды ошибок

- **401 Unauthorized**: Неверный API ключ или не настроен
- **400 Bad Request**: Неправильный ID модели или формат запроса
- **402 Payment Required**: Недостаточно кредитов (для платных моделей)
- **429 Too Many Requests**: Превышен rate limit
- **502 Bad Gateway**: Модель недоступна

## 📋 Быстрая проверка конфигурации

```bash
# Проверить настроенные модели
uv run python -c "from src.core.settings.base import settings; import json; print(json.dumps(settings.OPENROUTER_CHAT_MODELS, indent=2, ensure_ascii=False))"

# Список моделей с vision
uv run python -c "from src.core.settings.base import settings; [print(f'{k}: {v[\"supports_vision\"]}') for k, v in settings.OPENROUTER_CHAT_MODELS.items()]"
```

## 🧪 Тест через curl (универсально)

```bash
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen/qwen3-coder:free",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

## 📊 Проверка бесплатных моделей в fixtures

```bash
# Все бесплатные text-only модели
Get-Content fixtures_data/openrouter_models.json | ConvertFrom-Json |
  Select-Object -ExpandProperty data |
  Where-Object { $_.pricing.prompt -eq "0" -and $_.architecture.input_modalities -notcontains "image" } |
  Select-Object id, name, context_length |
  Format-Table -AutoSize

# Все бесплатные multimodal модели
Get-Content fixtures_data/openrouter_models.json | ConvertFrom-Json |
  Select-Object -ExpandProperty data |
  Where-Object { $_.pricing.prompt -eq "0" -and $_.architecture.input_modalities -contains "image" } |
  Select-Object id, name, context_length |
  Format-Table -AutoSize
```

## ⚙️ Настройка API ключа

1. Получить ключ: https://openrouter.ai/settings/keys
2. Добавить в `.env.dev`:
   ```
   OPENROUTER_API_KEY=sk-or-v1-ваш-реальный-ключ
   ```
3. Перезапустить сервер:
   ```bash
   uv run dev
   ```

## 🔍 Отладка 400 ошибок

Если получаете 400 Bad Request:

1. **Проверьте model_key в чате** (должен быть один из: qwen_coder, qwen_vl, gemini_flash, kimi_k2, deepseek_v3, tongyi_research, gemma_27b)
   ```bash
   # Проверить доступные модели
   uv run python -c "from src.core.settings.base import settings; print(list(settings.OPENROUTER_CHAT_MODELS.keys()))"
   ```

2. **Проверьте ID модели в fixtures** (должен совпадать с API):
   ```bash
   Get-Content fixtures_data/openrouter_models.json | ConvertFrom-Json |
     Select-Object -ExpandProperty data |
     Where-Object { $_.id -eq "ваш-model-id" }
   ```

3. **Проверьте логи** - теперь OpenRouter ошибки логируются с полным телом ответа:
   ```bash
   Get-Content logs/*.log -Tail 100 | Select-String "OpenRouter API"
   ```

4. **Убедитесь что API ключ валидный**:
   ```bash
   # Должен начинаться с sk-or-v1-
   Get-Content .env.dev | Select-String "OPENROUTER_API_KEY"
   ```

5. **Для vision моделей** проверьте base64 кодировку изображения
