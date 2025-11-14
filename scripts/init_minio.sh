#!/bin/bash
# Скрипт для инициализации MinIO bucket при первом запуске

set -e

echo "🪣 Ожидание запуска MinIO..."
sleep 5

# Установка MinIO Client (mc) если не установлен
if ! command -v mc &> /dev/null; then
    echo "📦 Установка MinIO Client..."
    wget https://dl.min.io/client/mc/release/linux-amd64/mc -O /usr/local/bin/mc
    chmod +x /usr/local/bin/mc
fi

# Настройка алиаса для локального MinIO
echo "🔧 Настройка MinIO клиента..."
mc alias set local http://localhost:9000 ${MINIO_ROOT_USER:-minioadmin} ${MINIO_ROOT_PASSWORD:-minioadmin}

# Создание bucket если не существует
BUCKET_NAME=${AWS_BUCKET_NAME:-norake-documents}

if mc ls local/$BUCKET_NAME &> /dev/null; then
    echo "✅ Bucket '$BUCKET_NAME' уже существует"
else
    echo "🪣 Создание bucket '$BUCKET_NAME'..."
    mc mb local/$BUCKET_NAME

    # Установка публичной политики для чтения (для presigned URLs)
    echo "🔓 Настройка политики доступа..."
    mc anonymous set download local/$BUCKET_NAME

    echo "✅ Bucket '$BUCKET_NAME' создан и настроен"
fi

echo "🎉 MinIO готов к использованию!"
echo "📊 Web Console: http://localhost:9001"
echo "🔑 Логин: ${MINIO_ROOT_USER:-minioadmin}"
echo "🔑 Пароль: ${MINIO_ROOT_PASSWORD:-minioadmin}"
