# Document Services - Quick Start

## 🚀 Быстрый запуск

### 1. Запуск инфраструктуры (включая MinIO)

```bash
# Запуск всех сервисов (PostgreSQL, Redis, RabbitMQ, MinIO)
docker-compose -f docker-compose.dev.yml up -d

# Или только MinIO для тестов
docker-compose -f docker-compose.dev.yml up -d minio
```

### 2. Инициализация MinIO bucket

```bash
# Автоматическое создание bucket 'equiply-documents'
uv run init-minio
```

**Альтернативно (вручную через Web Console):**
1. Открой http://localhost:9001
2. Логин: `minioadmin`, Пароль: `minioadmin`
3. Создай bucket: `equiply-documents`

### 3. Установка Poppler (для генерации обложек)

**Windows:**
```powershell
# Через Chocolatey
choco install poppler

# Или скачай с GitHub:
# https://github.com/oschwartz10612/poppler-windows/releases/
# Добавь папку bin в PATH
```

**Linux:**
```bash
sudo apt-get install -y poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Docker:** Уже включен в Dockerfile (автоматически)

> 📘 Подробнее: [docs/POPPLER_SETUP.md](./POPPLER_SETUP.md)

### 4. Запуск FastAPI

```bash
# Применить миграции
uv run migrate

# Запустить сервер
uv run dev
```

### 4. Тестирование API

Открой Swagger UI: http://localhost:8000/docs

## 📚 API Endpoints

### Загрузка документа
```http
POST /api/v1/document-services
Content-Type: multipart/form-data

file: manual.pdf (до 10 MB)
title: "Техническая документация"
file_type: "PDF"
description: "Руководство по эксплуатации"
tags: "техника,оборудование,инструкция"
workspace_id: "uuid" (опционально)
is_public: true
```

**Response:**
```json
{
  "success": true,
  "message": "Документ успешно загружен",
  "data": {
    "id": "uuid",
    "title": "Техническая документация",
    "file_type": "PDF",
    "s3_document_key": "documents/uuid/manual.pdf",
    "s3_thumbnail_key": "thumbnails/uuid/thumb.png",
    "file_size": 2048576,
    "view_count": 0,
    "available_functions": [
      {
        "name": "view_pdf",
        "enabled": true,
        "label": "Открыть PDF"
      },
      {
        "name": "download",
        "enabled": true,
        "label": "Скачать"
      }
    ]
  }
}
```

### Список документов с фильтрацией
```http
GET /api/v1/document-services?search=техника&tags=инструкция&file_type=PDF&limit=20
```

### Топ по просмотрам
```http
GET /api/v1/document-services/most-viewed?limit=10
```

### Детали документа
```http
GET /api/v1/document-services/{service_id}?increment_views=true
```

### Обновление метаданных (только владелец)
```http
PUT /api/v1/document-services/{service_id}
{
  "title": "Новое название",
  "description": "Обновлённое описание",
  "tags": ["новый", "тег"],
  "is_public": false
}
```

### Удаление (только владелец)
```http
DELETE /api/v1/document-services/{service_id}
```

### Управление функциями (только владелец)
```http
# Добавить функцию
POST /api/v1/document-services/{service_id}/functions
{
  "name": "qr_code",
  "enabled": true,
  "config": {"size": "medium"}
}

# Удалить функцию
DELETE /api/v1/document-services/{service_id}/functions/qr_code
```

### Генерация QR-кода (только владелец)
```http
GET /api/v1/document-services/{service_id}/qr?base_url=https://equiply.ru
```

**Response:**
```json
{
  "success": true,
  "message": "QR-код сгенерирован",
  "qr_url": "http://localhost:9000/equiply-documents/qr-codes/uuid/qr.png?...",
  "document_url": "https://equiply.ru/documents/uuid"
}
```

## 🔧 Конфигурация

### Development (.env.dev)
```env
# MinIO локально
AWS_ENDPOINT=http://localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
AWS_BUCKET_NAME=equiply-documents
AWS_PRESIGNED_URL_EXPIRATION=3600
```

### Production (.env.prod)
```env
# AWS S3 (или другой S3-совместимый провайдер)
AWS_ENDPOINT=  # пусто = настоящий AWS S3
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=secret...
AWS_REGION=eu-central-1
AWS_BUCKET_NAME=equiply-prod-documents
AWS_PRESIGNED_URL_EXPIRATION=3600
```

## 📁 Структура хранилища S3/MinIO

```
equiply-documents/
├── documents/
│   └── {service_id}/
│       └── document.pdf          # Оригинальный файл
├── thumbnails/
│   └── {service_id}/
│       └── thumbnail.png         # Превью (для PDF)
└── qr-codes/
    └── {service_id}/
        └── qr.png                # QR-код для быстрого доступа
```

## 🎨 Обложки документов (Covers)

Document Services поддерживает 3 типа обложек:

### 1. GENERATED (авто-генерация из PDF)
```json
{
  "cover_type": "generated",
  "cover_url": "https://.../thumbnails/public/uuid_document.pdf_thumbnail.jpg"
}
```
- Автоматически создается thumbnail из **первой страницы PDF**
- Размер: 400x566px (пропорции A4)
- Формат: JPEG, качество 85%
- Хранится в S3: `thumbnails/public/` или `thumbnails/{workspace_id}/`

**Требования:**
- Установленный [poppler-utils](./POPPLER_SETUP.md)
- PDF должен быть валидным (не поврежден)

**Ошибки:**
```
❌ "Unable to get page count. Is poppler installed and in PATH?"
   → Решение: Установите poppler (см. docs/POPPLER_SETUP.md)

❌ "Не удалось извлечь страницы из PDF"
   → Файл поврежден или не является PDF
```

### 2. ICON (эмодзи или SVG)
```json
{
  "cover_type": "icon",
  "cover_icon": "📄"
}
```
- Используется эмодзи или SVG код
- Легковесная альтернатива для быстрых превью
- Подходит для списков документов

### 3. IMAGE (загруженное изображение)
```json
{
  "cover_type": "image",
  "cover_url": "https://.../covers/{workspace_id}/custom_cover.png"
}
```
- Загрузка кастомной обложки через отдельный endpoint
- Поддерживаемые форматы: JPG, PNG, WebP
- Максимальный размер: 5MB

**API для загрузки обложки:**
```http
POST /api/v1/document-services/{service_id}/cover
Content-Type: multipart/form-data

cover_image: image.png
```

### Структура в S3

```
equiply-documents/
├── documents/
│   └── {workspace_id}/
│       └── document.pdf          # Оригинальный файл
├── thumbnails/                    # GENERATED обложки
│   └── {workspace_id}/
│       └── uuid_document.pdf_thumbnail.jpg
├── covers/                        # IMAGE обложки (кастомные)
│   └── {workspace_id}/
│       └── custom_cover.png
└── qrcodes/
    └── {workspace_id}/
        └── qr.png
```

### Как работает генерация thumbnail

1. **При загрузке PDF** с `cover_type="generated"`:
   ```python
   # DocumentS3Storage.upload_document()
   file_url, filename, size, content = await storage.upload_document(file)

   # DocumentS3Storage.generate_pdf_thumbnail()
   cover_url = await storage.generate_pdf_thumbnail(
       file_content=content,
       filename=filename,
       workspace_id=workspace_id
   )
   ```

2. **Процесс конвертации:**
   - `pdf2image.convert_from_bytes()` → конвертирует 1-ю страницу в PIL Image
   - Ресайз до 400x566px через `Image.thumbnail()`
   - Сохранение в JPEG с quality=85%
   - Загрузка в S3 с `ContentType: image/jpeg`

3. **Результат:**
   - `cover_url` записывается в `document_services.cover_url`
   - Фронтенд отображает обложку в карточке документа
   - Кэширование: `CacheControl: max-age=31536000` (1 год)

## 🎯 Доступные функции сервиса

Каждый документ имеет набор функций в `available_functions`:

| Функция | Описание | По умолчанию |
|---------|----------|--------------|
| `view_pdf` | Просмотр PDF в браузере | ✅ Включена |
| `download` | Скачивание файла | ✅ Включена |
| `qr_code` | Генерация QR-кода | ❌ Отключена |
| `share_link` | Публичная ссылка | ❌ Отключена |
| `ai_chat` | AI-чат с документом | ❌ Отключена |

Функции управляются через API: `POST/DELETE /{service_id}/functions`

## 🔐 Права доступа

- **Публичные документы** (`is_public=true`): Просмотр всем авторизованным
- **Приватные документы** (`is_public=false`): Только владелец + участники workspace
- **Изменение/удаление**: Только владелец (`author_id`)
- **Управление функциями**: Только владелец

## 🐛 Troubleshooting

### MinIO не доступен
```bash
# Проверь статус контейнера
docker-compose -f docker-compose.dev.yml ps minio

# Логи MinIO
docker-compose -f docker-compose.dev.yml logs minio

# Перезапуск
docker-compose -f docker-compose.dev.yml restart minio
```

### Bucket не создаётся
```bash
# Вручную через Web Console
1. http://localhost:9001
2. Login: minioadmin / minioadmin
3. Create Bucket: equiply-documents
4. Access Policy: Public (для presigned URLs)
```

### Ошибки загрузки файлов
- **413 Payload Too Large**: Файл > 10 MB (настраивается в `DocumentServiceService.MAX_FILE_SIZE`)
- **400 Invalid file type**: Поддерживаются только PDF (пока)
- **500 Upload failed**: Проверь MinIO доступность и credentials в .env.dev

### Ошибки генерации обложек
- **"Unable to get page count. Is poppler installed and in PATH?"**
  ```bash
  # Windows
  choco install poppler

  # Linux
  sudo apt-get install poppler-utils

  # Проверка
  pdftoppm -v
  ```

- **"Не удалось извлечь страницы из PDF"**
  - PDF файл поврежден → проверь через Adobe Reader
  - Файл защищен паролем → снять защиту
  - Формат не поддерживается → конвертировать в стандартный PDF

- **Обложка не генерируется, но ошибок нет**
  - Thumbnail генерация НЕ блокирует создание документа
  - Проверь логи: `docker-compose -f docker-compose.dev.yml logs backend`
  - Fallback: используй `cover_type="icon"` с эмодзи

## 📊 MinIO Web Console

- URL: http://localhost:9001
- Login: `minioadmin`
- Password: `minioadmin`

Здесь можно:
- Просматривать загруженные файлы
- Скачивать/удалять файлы вручную
- Просматривать статистику storage
- Управлять bucket policies

## 🚀 Production Deployment

На production сервере:
1. **НЕ запускай MinIO** - используй AWS S3 или аналоги
2. Настрой `.env.prod` с AWS credentials
3. Создай production bucket в AWS Console
4. Настрой bucket lifecycle policies для автоудаления старых файлов (опционально)

## 💡 Полезные команды

```bash
# Запуск только MinIO
docker-compose -f docker-compose.dev.yml up -d minio

# Инициализация bucket
uv run init-minio

# Остановка MinIO
docker-compose -f docker-compose.dev.yml stop minio

# Полная очистка (удалить все файлы)
docker-compose -f docker-compose.dev.yml down -v
```
