# Установка Poppler для генерации обложек PDF

## Что такое Poppler?

Poppler - это библиотека для рендеринга PDF, которая используется `pdf2image` для конвертации PDF-страниц в изображения. Она необходима для генерации thumbnails (обложек) из PDF-документов.

## Установка

### Windows

**Вариант 1: Через Chocolatey (рекомендуется)**
```powershell
choco install poppler
```

**Вариант 2: Ручная установка**
1. Скачайте последний релиз poppler для Windows:
   - https://github.com/oschwartz10612/poppler-windows/releases/
   - Скачайте `Release-XX.XX.X-0.zip`

2. Распакуйте архив в `C:\Program Files\poppler` (или любую директорию)

3. Добавьте путь к `bin` в PATH:
   ```powershell
   # Для текущей сессии
   $env:PATH += ";C:\Program Files\poppler\Library\bin"

   # Постоянно (через System Properties → Environment Variables)
   # Добавьте C:\Program Files\poppler\Library\bin в PATH
   ```

4. Проверьте установку:
   ```powershell
   pdftoppm -v
   ```

### Linux (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

### macOS

```bash
brew install poppler
```

## Docker

В Docker контейнере poppler устанавливается автоматически через Dockerfile:

```dockerfile
# Для Alpine Linux (используется в Python slim образах)
RUN apk add --no-cache poppler-utils

# Для Debian/Ubuntu образов
RUN apt-get update && apt-get install -y poppler-utils
```

Проверьте наличие строки в `Dockerfile`:
```dockerfile
# Устанавливаем poppler для pdf2image
RUN apt-get update && \
    apt-get install -y --no-install-recommends poppler-utils && \
    rm -rf /var/lib/apt/lists/*
```

## Проверка работы

После установки poppler, тестируйте генерацию обложек:

```python
from pdf2image import convert_from_bytes

# Тест конвертации
with open("test.pdf", "rb") as f:
    images = convert_from_bytes(f.read(), first_page=1, last_page=1)
    print(f"Успешно! Получено {len(images)} изображений")
```

## Troubleshooting

### Ошибка: "Unable to get page count. Is poppler installed and in PATH?"

**Причины:**
1. Poppler не установлен
2. Poppler установлен, но не в PATH
3. Неправильная версия poppler (слишком старая)

**Решение:**
```powershell
# Проверьте наличие poppler в PATH
where.exe pdftoppm

# Если команда не найдена - добавьте в PATH или переустановите
```

### Ошибка: "Unable to open file"

**Причина:** Некорректный PDF файл или недостаточно прав доступа.

**Решение:**
```python
# Проверьте валидность PDF перед конвертацией
import PyPDF2

with open("document.pdf", "rb") as f:
    reader = PyPDF2.PdfReader(f)
    print(f"PDF содержит {len(reader.pages)} страниц")
```

## Альтернативы (если poppler недоступен)

Если установка poppler невозможна, используйте:

1. **PyMuPDF (fitz)** - чистый Python, без внешних зависимостей:
   ```python
   import fitz  # PyMuPDF

   doc = fitz.open("document.pdf")
   page = doc[0]
   pix = page.get_pixmap(dpi=150)
   pix.save("thumbnail.jpg")
   ```

2. **Сервисы thumbnail generation** - внешние API (например, CloudConvert, PDF.co)

## Ссылки

- Poppler официальный сайт: https://poppler.freedesktop.org/
- pdf2image GitHub: https://github.com/Belval/pdf2image
- Poppler для Windows: https://github.com/oschwartz10612/poppler-windows
