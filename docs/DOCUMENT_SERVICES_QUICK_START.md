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

### 3. Запуск FastAPI

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
