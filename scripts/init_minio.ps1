# PowerShell скрипт для инициализации MinIO bucket
# Использование: .\scripts\init_minio.ps1

$ErrorActionPreference = "Stop"

Write-Host "🪣 Инициализация MinIO bucket..." -ForegroundColor Cyan

# Параметры из .env.dev
$MinioEndpoint = "http://localhost:9000"
$MinioUser = "minioadmin"
$MinioPassword = "minioadmin"
$BucketName = "norake-documents"

# Ожидание запуска MinIO
Write-Host "⏳ Ожидание запуска MinIO (5 секунд)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

try {
    # Проверка доступности MinIO
    $HealthCheck = Invoke-RestMethod -Uri "$MinioEndpoint/minio/health/live" -Method Get -ErrorAction SilentlyContinue
    Write-Host "✅ MinIO запущен и доступен" -ForegroundColor Green
} catch {
    Write-Host "❌ MinIO недоступен. Запусти docker-compose up minio" -ForegroundColor Red
    exit 1
}

# Создание bucket через MinIO Admin API
$Headers = @{
    "Host" = "localhost:9000"
}

# Базовая авторизация
$EncodedCredentials = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${MinioUser}:${MinioPassword}"))
$Headers["Authorization"] = "Basic $EncodedCredentials"

try {
    # Проверка существования bucket
    Write-Host "🔍 Проверка bucket '$BucketName'..." -ForegroundColor Yellow

    $CheckUrl = "$MinioEndpoint/$BucketName"
    try {
        Invoke-RestMethod -Uri $CheckUrl -Method Head -Headers $Headers -ErrorAction Stop | Out-Null
        Write-Host "✅ Bucket '$BucketName' уже существует" -ForegroundColor Green
    } catch {
        # Bucket не существует, создаём
        Write-Host "🪣 Создание bucket '$BucketName'..." -ForegroundColor Cyan
        Invoke-RestMethod -Uri $CheckUrl -Method Put -Headers $Headers | Out-Null
        Write-Host "✅ Bucket '$BucketName' создан" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "🎉 MinIO готов к использованию!" -ForegroundColor Green
    Write-Host "📊 Web Console: http://localhost:9001" -ForegroundColor Cyan
    Write-Host "🔑 Логин: $MinioUser" -ForegroundColor Yellow
    Write-Host "🔑 Пароль: $MinioPassword" -ForegroundColor Yellow
    Write-Host "🪣 Bucket: $BucketName" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "💡 Для просмотра файлов открой Web Console в браузере" -ForegroundColor Gray

} catch {
    Write-Host "❌ Ошибка при создании bucket: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
