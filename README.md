# NoRake

## Описание проекта

**NoRake** — система коллективной памяти для решения и предотвращения проблем

## Установка

Клонируйте репозиторий в директорию, в которой находитесь:
```bash
git clone https://github.com/mikey-semy/norake-backend.git .
```
Или:
```bash
git clone https://github.com/mikey-semy/norake-backend.git
```
Перейдите в директорию с проектом:
```bash
cd ./norake-backend
```

> [!NOTE]
> Перед тем, как запускать проект, проверьте наличие файла `.env`

## Настройка окружения

Перед запуском проекта необходимо настроить переменные окружения.
В проекте используется файл `.env.dev` для разработки.

Скопируйте пример конфигурации из .env.example в новый файл .env.dev:
```bash
cp .env.example .env.dev
```

Отредактируйте файл .env.dev, заполнив следующие обязательные параметры:

### Основные настройки
- `DOCS_USERNAME` - имя пользователя для доступа к docs (по умолчанию admin)
- `DOCS_PASSWORD` - пароль для доступа к docs (для разработки обычно admin)

### Настройки базы данных PostgreSQL
- `POSTGRES_USER` - имя пользователя PostgreSQL
- `POSTGRES_PASSWORD` - пароль пользователя PostgreSQL
- `POSTGRES_HOST` - хост базы данных (обычно localhost для разработки)
- `POSTGRES_PORT` - порт PostgreSQL (по умолчанию 5432)
- `POSTGRES_DB` - имя базы данных

### Настройки Redis
- `REDIS_HOST` - хост Redis (обычно localhost для разработки)
- `REDIS_PORT` - порт Redis (по умолчанию 6379)
- `REDIS_PASSWORD` - пароль для Redis (обычно default для разработки)

### Настройки CORS
- `ALLOW_ORIGINS` - список разрешенных источников (для разработки обычно ["http://localhost:3000","http://localhost:5173"])

### Пример минимальной конфигурации для локальной разработки
```bash

POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=norake_db

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

ALLOW_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```
> [!IMPORTANT]
> Никогда не коммитьте файлы .env.dev или другие файлы с реальными учетными данными в репозиторий!
>
> Убедитесь, что они добавлены в .gitignore.

## Первый запуск

`PowerShell`
```bash
.\scripts\activate.ps1
```

## Последующий запуск

Для активации виртуального окружения без запуска режима разработки:

`PowerShell`
```bash
.\scripts\setup.ps1
```

Запуск в режиме разработки (с hot-reload)
```bash
uv run dev
```

Или запуск в режиме разработки (с hot-reload)   одной командой:

`PowerShell`
```bash
.\scripts\activate.ps1
```

## Разработка

### Процесс разработки такой:
- Разработка идёт от `dev`
- В dev мерджим фичи
- Тестим на `dev`
- Когда всё ок - мерджим `dev` в main

Если вы хотите внести изменения или улучшения, пожалуйста, следуйте этим шагам:

1. Переключаемся на `dev` и подтягиваем последние изменения с удалённого репозитория:
```bash
git checkout dev
git pull origin dev
```

2. От `dev` создаем свою ветку разработки и сразу на неё переключаемся:
```bash
git checkout -b feature/your-name-of-feature
```

3. Кодим и по итогу добавляем все изменения в индекс:
```bash
git add .
```

4. Создаём коммит с описанием изменений
```bash
git commit -m "feat: your-changes"
```

5. Перед пушем обновляем ветку от `dev`, то есть
 1) Переключаемся обратно на dev
 2) Подтягиваем новые изменения
 3) Возвращаемся на свою ветку
 4) Переносим свои изменения поверх последней версии `dev`

```bash
git checkout dev
git pull origin dev
git checkout feature/your-name-of-feature
git rebase dev
```

6. Отправляем свою ветку в удалённый репозиторий:
```bash
git push origin feature/your-name-of-feature --force-with-lease
```

7. Создаем Pull Request в dev ветку!
> 1) Жмём кнопку "New Pull Request"
> 2) В base выбираем `dev` (КУДА льём)
> 3) В compare выбираем свою ветку feature/your-name-of-feature (ОТКУДА льём)
> 4) Пишешь нормальное описание что сделали
> 5) Добавляем ревьюеров
> 6) Создаёи PR

Либо просто делаем merge в dev ветку из своей feature/your-name-of-feature ветки.
```bash
git checkout dev
git merge feature/your-name-of-feature
```

8. После тестирования на `dev`, создаём PR из `dev` в `main`.
> 1) Создаём новый PR
> 2) В base выбираем main (КУДА льём)
> 3) В compare выбираем dev (ОТКУДА льём)
> 4) Описываем все изменения которые войдут в прод
> 6) Ждём подтверждения от тимлида

Либо просто делаем merge в main ветку из dev ветки.
```bash
git checkout main
git merge dev
```

9. Удаляем свою ветку feature/your-name-of-feature

Локально:

```bash
git branch -d feature/your-name-of-feature
```
Удалённо:
```bash
git push origin --delete feature/your-name-of-feature
```

## Контакты
Если у вас есть вопросы или предложения, вы можете обратиться по адресу telegram: [@mikey_semi](https://t.me/mikey_semi).

Спасибо за интерес к проекту norake!

Мы надеемся, что эта документация поможет вам начать работу и внести свой вклад в развитие платформы.