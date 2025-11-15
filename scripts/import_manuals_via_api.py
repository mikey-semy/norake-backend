"""
Импорт инструкций из work-aedb через HTTP API endpoints.

Скрипт делает реальные HTTP запросы к API (как с фронта):
1. Логинится и получает JWT токен
2. Для каждой инструкции делает POST /api/v1/document-services
3. Загружает PDF как multipart/form-data

Usage:
    python scripts/import_manuals_via_api.py --api-url http://localhost:8000 --email admin@example.com --password admin

Requirements:
    - norake-backend должен быть запущен (uv run dev)
    - work-aedb проект должен быть в соседней директории
    - У пользователя должны быть права на создание документов
"""

import argparse
import asyncio
import io
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class APIManualImporter:
    """
    Импортёр инструкций через HTTP API endpoints.

    Делает реальные HTTP запросы к API, полностью эмулируя работу фронтенда.
    """

    # Паттерны для извлечения типов документов и языков
    DOCUMENT_TYPES = {
        "руководство": "руководство",
        "инструкция": "инструкция",
        "брошура": "брошура",
        "каталог": "каталог",
        "параметрирование": "параметры",
        "manual": "manual",
        "guide": "guide",
        "datasheet": "datasheet",
        "user guide": "user guide",
        "quick": "quick start",
        "краткое": "краткое руководство",
    }

    LANGUAGES = {
        "ru": "русский",
        "en": "english",
        "cn": "chinese",
        "ch": "chinese",
    }

    def __init__(
        self,
        api_url: str,
        email: str,
        password: str,
        workaedb_path: str = "../work-aedb",
    ):
        """
        Args:
            api_url: URL API (например http://localhost:8000)
            email: Email пользователя для логина
            password: Пароль пользователя
            workaedb_path: Путь к директории work-aedb проекта
        """
        self.api_url = api_url.rstrip("/")
        self.email = email
        self.password = password
        self.workaedb_path = Path(workaedb_path)
        self.data_path = self.workaedb_path / "app" / "data" / "manuals"

        self.categories: List[Dict] = []
        self.groups: List[Dict] = []
        self.manuals: List[Dict] = []

        self.category_map: Dict[int, str] = {}
        self.group_map: Dict[int, Dict] = {}

        self.http_client: Optional[httpx.AsyncClient] = None
        self.access_token: Optional[str] = None

        # Статистика
        self.stats = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "errors": [],
        }

    async def __aenter__(self):
        """Инициализация async клиента."""
        self.http_client = httpx.AsyncClient(timeout=300.0)
        logger.info("HTTP клиент инициализирован для %s", self.api_url)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие async клиента."""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("HTTP клиент закрыт")

    async def login(self):
        """
        Логин через API и получение JWT токена.

        POST /api/v1/auth/login
        """
        logger.info("Логин как %s...", self.email)

        response = await self.http_client.post(
            f"{self.api_url}/api/v1/auth/login",
            data={
                "username": self.email,  # OAuth2PasswordRequestForm использует username
                "password": self.password,
            },
        )

        if response.status_code != 200:
            logger.error("Ошибка логина: %s", response.text)
            raise Exception(f"Не удалось залогиниться: {response.status_code}")

        data = response.json()
        self.access_token = data["access_token"]
        logger.info("✅ Успешный логин, токен получен")

    def load_json_data(self):
        """Загружает JSON файлы из work-aedb."""
        logger.info("Загрузка JSON файлов из %s", self.data_path)

        # Загрузка categories
        categories_file = self.data_path / "categories.json"
        with open(categories_file, "r", encoding="utf-8") as f:
            self.categories = json.load(f)

        # Загрузка groups
        groups_file = self.data_path / "groups.json"
        with open(groups_file, "r", encoding="utf-8") as f:
            self.groups = json.load(f)

        # Загрузка manuals
        manuals_file = self.data_path / "manuals.json"
        with open(manuals_file, "r", encoding="utf-8") as f:
            self.manuals = json.load(f)

        # Создание маппингов
        self.category_map = {
            idx + 1: cat["name"] for idx, cat in enumerate(self.categories)
        }
        self.group_map = {
            idx + 1: {"name": grp["name"], "category_id": grp["category_id"]}
            for idx, grp in enumerate(self.groups)
        }

        logger.info(
            "Загружено: %d категорий, %d групп, %d инструкций",
            len(self.categories),
            len(self.groups),
            len(self.manuals),
        )

    async def download_file(self, url: str) -> bytes:
        """Скачивает файл с Yandex Cloud."""
        response = await self.http_client.get(url)
        if response.status_code != 200:
            raise Exception(f"Не удалось скачать файл: {response.status_code}")
        return response.content

    def extract_tags(self, manual_name: str, category: str, group: str) -> List[str]:
        """
        Извлекает теги из названия инструкции.

        Tags: тип документа, язык, производитель, серия оборудования
        """
        tags = []
        name_lower = manual_name.lower()

        # Тип документа
        for key, tag in self.DOCUMENT_TYPES.items():
            if key in name_lower:
                tags.append(tag)
                break

        # Язык
        for key, tag in self.LANGUAGES.items():
            if key in name_lower:
                tags.append(tag)
                break

        # Производитель (из категории)
        manufacturer = category.split("(")[0].strip()
        if manufacturer and manufacturer != "Общее":
            tags.append(manufacturer.lower())

        # Серия оборудования (из группы)
        if group and group != "Общее":
            tags.append(group.lower())

        return tags

    def create_description(
        self, manual_name: str, category: str, group: str
    ) -> str:
        """
        Создаёт описание документа.

        Формат: "Документация для {category} > {group}. {version_info}"
        """
        desc_parts = []

        # Основная часть
        if category != "Общее":
            desc_parts.append(f"Документация для {category}")
            if group and group != "Общее":
                desc_parts[0] += f" > {group}"

        # Извлекаем версию/дату из названия
        version_info = []
        name_parts = manual_name.split()

        for part in name_parts:
            # Версия (V1.0, v2.1, Rev 06, etc.)
            if any(prefix in part.lower() for prefix in ["v", "rev", "ver"]):
                version_info.append(part)
            # Дата (1209, 2019, etc.)
            elif part.isdigit() and len(part) == 4:
                version_info.append(f"от {part}")

        if version_info:
            desc_parts.append(" ".join(version_info))

        return ". ".join(desc_parts) if desc_parts else manual_name

    async def upload_document(
        self,
        filename: str,
        file_content: bytes,
        title: str,
        description: str,
        tags: List[str],
    ) -> Dict:
        """
        Загружает документ через API endpoint.

        POST /api/v1/document-services
        Content-Type: multipart/form-data
        """
        # Подготовка multipart/form-data
        files = {"file": (filename, io.BytesIO(file_content), "application/pdf")}

        data = {
            "title": title,
            "description": description,
            "tags": ",".join(tags) if tags else "",
            "file_type": "pdf",
            "is_public": "true",  # Все публичные
        }

        headers = {"Authorization": f"Bearer {self.access_token}"}

        response = await self.http_client.post(
            f"{self.api_url}/api/v1/document-services",
            files=files,
            data=data,
            headers=headers,
        )

        if response.status_code not in [200, 201]:
            logger.error("Ошибка загрузки: %s", response.text)
            raise Exception(f"API вернул {response.status_code}: {response.text}")

        return response.json()

    async def import_manuals(self):
        """
        Импортирует все инструкции через API.

        Workflow:
        1. Скачивает PDF с Yandex Cloud
        2. Делает POST /api/v1/document-services с multipart/form-data
        3. Сервер сам загружает в S3, генерирует обложку, создаёт запись в БД
        """
        self.stats["total"] = len(self.manuals)
        logger.info("Начало импорта %d инструкций через API", self.stats["total"])

        for idx, manual_data in enumerate(self.manuals, start=1):
            manual_name = manual_data["name"]
            yandex_url = manual_data["file_url"]
            group_id = manual_data["group_id"]

            logger.info("[%d/%d] Импорт: %s", idx, self.stats["total"], manual_name)

            try:
                # Получаем категорию и группу
                group_info = self.group_map.get(group_id)
                if not group_info:
                    logger.warning("Группа group_id=%d не найдена, пропуск", group_id)
                    self.stats["skipped"] += 1
                    continue

                group_name = group_info["name"]
                category_id = group_info["category_id"]
                category_name = self.category_map.get(category_id, "Неизвестно")

                # Скачиваем файл
                file_content = await self.download_file(yandex_url)
                filename = Path(yandex_url).name

                # Извлекаем теги и создаём description
                tags = self.extract_tags(manual_name, category_name, group_name)
                description = self.create_description(
                    manual_name, category_name, group_name
                )

                # Загружаем через API
                result = await self.upload_document(
                    filename=filename,
                    file_content=file_content,
                    title=manual_name,
                    description=description,
                    tags=tags,
                )

                document_id = result.get("data", {}).get("id")
                logger.info(
                    "✅ Создан документ: %s (id=%s)", manual_name, document_id
                )
                self.stats["success"] += 1

                # Прогресс каждые 10 документов
                if idx % 10 == 0:
                    logger.info("Прогресс: %d/%d документов", idx, self.stats["total"])

                # Небольшая пауза чтобы не перегрузить API
                await asyncio.sleep(0.5)

            except Exception as error:
                logger.error(
                    "❌ Ошибка при импорте '%s': %s", manual_name, str(error)
                )
                self.stats["errors"].append(
                    {"manual": manual_name, "error": str(error)}
                )
                self.stats["skipped"] += 1

        logger.info("Импорт завершён!")
        logger.info("Статистика:")
        logger.info("  Всего: %d", self.stats["total"])
        logger.info("  Успешно: %d", self.stats["success"])
        logger.info("  Пропущено: %d", self.stats["skipped"])
        logger.info("  Ошибок: %d", len(self.stats["errors"]))

        if self.stats["errors"]:
            logger.warning("Детали ошибок:")
            for error_info in self.stats["errors"][:10]:
                logger.warning(
                    "  - %s: %s", error_info["manual"], error_info["error"]
                )

    async def run_import(self):
        """Главный метод импорта."""
        await self.login()
        self.load_json_data()
        await self.import_manuals()


async def main():
    """Точка входа скрипта."""
    parser = argparse.ArgumentParser(
        description="Импорт инструкций через HTTP API endpoints"
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="URL API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="Email пользователя для логина",
    )
    parser.add_argument(
        "--password",
        type=str,
        required=True,
        help="Пароль пользователя",
    )
    parser.add_argument(
        "--workaedb-path",
        type=str,
        default="../work-aedb",
        help="Путь к директории work-aedb (default: ../work-aedb)",
    )
    args = parser.parse_args()

    async with APIManualImporter(
        api_url=args.api_url,
        email=args.email,
        password=args.password,
        workaedb_path=args.workaedb_path,
    ) as importer:
        await importer.run_import()


if __name__ == "__main__":
    asyncio.run(main())
