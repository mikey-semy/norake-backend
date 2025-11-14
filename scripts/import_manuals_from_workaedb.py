"""
Импорт инструкций из work-aedb в norake-backend Document Services.

Скрипт читает JSON файлы из work-aedb (categories, groups, manuals),
скачивает PDF с Yandex Cloud и импортирует их в Document Services
с правильным маппингом данных, извлечением тегов и генерацией обложек.

Usage:
    python scripts/import_manuals_from_workaedb.py [--workaedb-path ../work-aedb]

Requirements:
    - work-aedb проект должен быть в соседней директории (или указан путь)
    - JSON файлы: app/data/manuals/{categories,groups,manuals}.json
    - norake-backend должен иметь хотя бы одного пользователя в БД
    - S3 credentials должны быть настроены в .env
    - Poppler установлен для генерации обложек (см. docs/POPPLER_SETUP.md)
      * Windows: choco install poppler
      * Linux: sudo apt-get install poppler-utils
      * macOS: brew install poppler

Features:
    ✅ Автоматическая загрузка PDF из Yandex Cloud
    ✅ Генерация thumbnail (обложек) из первой страницы PDF
    ✅ Извлечение тегов (тип документа, язык, производитель, серия)
    ✅ Создание описаний с версией и датой документа
    ✅ Публичные документы (is_public=True) для общего доступа
"""

import asyncio
import io
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.connections.database import DatabaseClient
from src.core.connections.storage import S3ContextManager
from src.core.integrations.storages.documents import DocumentS3Storage
from src.core.settings.base import settings
from src.models.v1.document_services import CoverType, DocumentFileType
from src.models.v1.users import UserModel
from src.models.v1.workspaces import WorkspaceModel
from src.services.v1.document_services import DocumentServiceService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ManualImporter:
    """
    Импортёр инструкций из work-aedb в Document Services.

    Workflow:
        1. Загружает JSON (categories, groups, manuals) из work-aedb
        2. Скачивает PDF с Yandex Cloud через httpx
        3. Загружает файл в S3 norake-backend (папка documents/)
        4. Генерирует thumbnail из первой страницы PDF (папка thumbnails/)
        5. Извлекает теги из названия (Руководство/Инструкция/Брошура + язык)
        6. Создаёт Document Service через DocumentServiceService

    Cover Generation:
        - Использует pdf2image + poppler для конвертации PDF → JPEG
        - Размер: 400x566px, качество 85%
        - Сохраняется в S3: thumbnails/public/{uuid}_filename_thumbnail.jpg
        - Если poppler не установлен → warning, документ создается без обложки
    """

    # Паттерны для извлечения типов документов и языков из названий
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

    def __init__(self, workaedb_path: str = "../work-aedb"):
        """
        Args:
            workaedb_path: Путь к директории work-aedb проекта.
        """
        self.workaedb_path = Path(workaedb_path)
        self.data_path = self.workaedb_path / "app" / "data" / "manuals"

        self.categories: List[Dict] = []
        self.groups: List[Dict] = []
        self.manuals: List[Dict] = []

        self.category_map: Dict[int, str] = {}  # id → name
        self.group_map: Dict[int, Dict] = {}  # id → {name, category_id}

        self.http_client: Optional[httpx.AsyncClient] = None
        self.s3_context: Optional[S3ContextManager] = None
        self.s3_client: Optional[Any] = None
        self.storage: Optional[DocumentS3Storage] = None
        self.session: Optional[AsyncSession] = None
        self.service: Optional[DocumentServiceService] = None

        self.default_user: Optional[UserModel] = None
        self.default_workspace: Optional[WorkspaceModel] = None

        # Статистика
        self.stats = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "errors": [],
        }

    async def __aenter__(self):
        """Инициализация async ресурсов."""
        self.http_client = httpx.AsyncClient(timeout=300.0)

        # Инициализация S3 через контекстный менеджер (как в проекте)
        self.s3_context = S3ContextManager()
        self.s3_client = await self.s3_context.__aenter__()
        self.storage = DocumentS3Storage(s3_client=self.s3_client)

        # Инициализация БД через DatabaseClient (singleton)
        db_client = await DatabaseClient.get_instance()
        session_factory = await db_client.connect()
        self.session = session_factory()

        # Инициализация сервиса
        self.service = DocumentServiceService(
            session=self.session,
            s3_client=self.s3_client,
            settings=settings,
        )

        # Получаем дефолтного пользователя и workspace
        await self._get_default_user_and_workspace()

        logger.info("ManualImporter инициализирован")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие async ресурсов."""
        if self.http_client:
            await self.http_client.aclose()
        if self.s3_context:
            await self.s3_context.__aexit__(exc_type, exc_val, exc_tb)
        if self.session:
            await self.session.close()
        logger.info("ManualImporter закрыт")

    async def _get_default_user_and_workspace(self):
        """Получает первого пользователя и workspace для author_id."""
        from sqlalchemy import select

        # Получаем первого пользователя
        result = await self.session.execute(select(UserModel).limit(1))
        self.default_user = result.scalar_one_or_none()

        if not self.default_user:
            raise ValueError(
                "В БД нет пользователей! Создайте пользователя через фикстуры или API."
            )

        # Получаем первый workspace (опционально)
        result = await self.session.execute(select(WorkspaceModel).limit(1))
        self.default_workspace = result.scalar_one_or_none()

        logger.info(
            "Дефолтный пользователь: %s (id=%s)",
            self.default_user.username,
            self.default_user.id,
        )
        if self.default_workspace:
            logger.info(
                "Дефолтный workspace: %s (id=%s)",
                self.default_workspace.name,
                self.default_workspace.id,
            )

    def load_json_data(self):
        """Загружает JSON файлы из work-aedb."""
        logger.info("Загрузка JSON файлов из %s", self.data_path)

        categories_file = self.data_path / "categories.json"
        groups_file = self.data_path / "groups.json"
        manuals_file = self.data_path / "manuals.json"

        with open(categories_file, "r", encoding="utf-8") as f:
            self.categories = json.load(f)

        with open(groups_file, "r", encoding="utf-8") as f:
            self.groups = json.load(f)

        with open(manuals_file, "r", encoding="utf-8") as f:
            self.manuals = json.load(f)

        # Создаём маппинг для быстрого доступа
        for idx, category in enumerate(self.categories, start=1):
            self.category_map[idx] = category["name"]

        for idx, group in enumerate(self.groups, start=1):
            self.group_map[idx] = {
                "name": group["name"],
                "category_id": group["category_id"],
            }

        logger.info(
            "Загружено: %d категорий, %d групп, %d инструкций",
            len(self.categories),
            len(self.groups),
            len(self.manuals),
        )

    async def download_file(self, url: str) -> bytes:
        """
        Скачивает файл с Yandex Cloud через HTTP.

        Args:
            url: Yandex Cloud URL (https://storage.yandexcloud.net/...)

        Returns:
            bytes: Содержимое файла.

        Raises:
            httpx.HTTPError: При ошибке загрузки.
        """
        logger.debug("Скачивание файла: %s", url)
        response = await self.http_client.get(url)
        response.raise_for_status()
        return response.content

    def extract_tags(self, manual_name: str, category: str, group: str) -> List[str]:
        """
        Извлекает теги из названия инструкции.

        Теги:
        - Тип документа (руководство/инструкция/брошура/manual/guide)
        - Язык (Ru/En/Cn)
        - Производитель (категория)
        - Серия (группа)

        Args:
            manual_name: Название инструкции из JSON.
            category: Производитель.
            group: Серия.

        Returns:
            List[str]: Список тегов.

        Example:
            >>> extract_tags(
            ...     "ASC800 Руководство по микропрограммному обеспечению 1209 Ru",
            ...     "ABB (Швейцария)",
            ...     "ASC"
            ... )
            ['руководство', 'русский', 'abb', 'asc', 'микропрограммное обеспечение']
        """
        tags = set()
        name_lower = manual_name.lower()

        # Извлекаем тип документа
        for pattern, tag in self.DOCUMENT_TYPES.items():
            if pattern in name_lower:
                tags.add(tag)

        # Извлекаем язык
        for pattern, lang in self.LANGUAGES.items():
            if f" {pattern}" in name_lower or name_lower.endswith(pattern):
                tags.add(lang)

        # Добавляем производителя (без страны)
        category_clean = re.sub(r"\s*\([^)]*\)", "", category).strip().lower()
        tags.add(category_clean)

        # Добавляем серию
        tags.add(group.lower())

        # Дополнительные keywords из названия (опционально)
        if "параметрирование" in name_lower or "parameter" in name_lower:
            tags.add("параметры")
        if "эксплуатация" in name_lower or "operation" in name_lower:
            tags.add("эксплуатация")
        if "quick" in name_lower or "краткое" in name_lower:
            tags.add("quick start")

        return sorted(list(tags))

    def create_description(
        self, manual_name: str, category: str, group: str
    ) -> str:
        """
        Создаёт описание для Document Service.

        Description содержит:
        - Производитель
        - Серия
        - Дата документа (если есть 4 цифры - месяц/год: MMYY или YYMM)
        - Версия (если есть буквенно-цифровые: v1.0, R01, A00, etc.)

        Args:
            manual_name: Название инструкции.
            category: Производитель.
            group: Серия.

        Returns:
            str: Описание документа.

        Example:
            >>> create_description(
            ...     "ASC800 Руководство по микропрограммному обеспечению 1209 Ru",
            ...     "ABB (Швейцария)",
            ...     "ASC"
            ... )
            'Производитель: ABB (Швейцария), Серия: ASC, Дата: 12/2009'

            >>> create_description(
            ...     "19011080_A01 MD880-30 Hardware User Guide 202011 Ru",
            ...     "Inovance (Китай)",
            ...     "MD880-30"
            ... )
            'Производитель: Inovance (Китай), Серия: MD880-30, Версия: A01, Дата: 11/2020'
        """
        parts = [f"Производитель: {category}", f"Серия: {group}"]

        # Извлекаем версию (буквенно-цифровая: A00, B02, v1.0, Rev 06, R01, etc.)
        version_match = re.search(
            r"\b([A-Z]\d{2,}|v\d+\.\d+|Rev\s*\d+|R\d+|SC[Y]?[-_][A-Z]\d+)\b",
            manual_name,
            re.I
        )
        if version_match:
            parts.append(f"Версия: {version_match.group(1)}")

        # Извлекаем дату (4 цифры: MMYY, YYMM или 6 цифр: YYYYMM, YYMMDD)
        date_match = re.search(r"\b(\d{4}|\d{6})\b", manual_name)
        if date_match:
            date_str = date_match.group(1)
            if len(date_str) == 4:
                # Определяем формат (MMYY или YYMM по логике)
                # Если первые 2 цифры > 12, то это год (YYMM)
                first_two = int(date_str[:2])
                if first_two > 12:
                    # YYMM формат
                    year = date_str[:2]
                    month = date_str[2:]
                    parts.append(f"Дата: {month}/20{year}")
                else:
                    # MMYY формат (или YYMM если year < 12)
                    # Проверяем вторые 2 цифры
                    last_two = int(date_str[2:])
                    if last_two > 25:  # Вероятно старый год (19XX)
                        parts.append(f"Дата: {date_str[:2]}/19{date_str[2:]}")
                    else:
                        parts.append(f"Дата: {date_str[:2]}/20{date_str[2:]}")
            elif len(date_str) == 6:
                # YYYYMM или YYMMDD
                if int(date_str[:4]) > 1990:  # YYYYMM формат
                    parts.append(f"Дата: {date_str[4:]}/{date_str[:4]}")
                else:  # YYMMDD формат
                    parts.append(f"Дата: {date_str[2:4]}/20{date_str[:2]}")

        return ", ".join(parts)

    async def import_manuals(self):
        """
        Импортирует все инструкции в Document Services.

        Workflow для каждой инструкции:
        1. Скачивает PDF с Yandex Cloud
        2. Загружает в S3 norake-backend
        3. Извлекает теги и создаёт description
        4. Создаёт Document Service через service.create_document()
        """
        self.stats["total"] = len(self.manuals)
        logger.info("Начало импорта %d инструкций", self.stats["total"])

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

                # Создаём UploadFile из bytes (как если бы с фронта прилетело)
                filename = Path(yandex_url).name
                file_obj = io.BytesIO(file_content)
                upload_file = UploadFile(
                    file=file_obj,
                    filename=filename,
                    size=len(file_content),
                    headers={"content-type": "application/pdf"},
                )

                # Загружаем через DocumentS3Storage (теперь возвращает file_content)
                file_url, unique_filename, file_size, uploaded_content = await self.storage.upload_document(
                    file=upload_file,
                    workspace_id=None,  # Публичные документы
                )

                # Генерируем thumbnail (обложка) из первой страницы PDF
                # Используем uploaded_content вместо file_content для консистентности
                cover_url = await self.storage.generate_pdf_thumbnail(
                    file_content=uploaded_content,
                    filename=unique_filename,
                    workspace_id=None,  # Публичные документы
                )

                if cover_url:
                    logger.info("Сгенерирована обложка: %s", cover_url)
                else:
                    logger.warning("Не удалось сгенерировать обложку для %s", manual_name)

                # Извлекаем теги и создаём description
                tags = self.extract_tags(manual_name, category_name, group_name)
                description = self.create_description(
                    manual_name, category_name, group_name
                )

                # Создаём Document Service напрямую через repository
                document = await self.service.repository.create_item(
                    {
                        "title": manual_name,
                        "description": description,
                        "tags": tags,
                        "file_url": file_url,
                        "file_size": file_size,
                        "file_type": DocumentFileType.PDF.value,  # .value для enum
                        "cover_type": CoverType.GENERATED.value,  # .value для enum
                        "cover_url": cover_url,  # URL сгенерированного thumbnail
                        "cover_icon": None,
                        "available_functions": [
                            {
                                "name": "view_pdf",
                                "enabled": True,
                                "label": "Открыть PDF",
                                "icon": "📄",
                            },
                            {
                                "name": "download",
                                "enabled": True,
                                "label": "Скачать",
                                "icon": "📥",
                            },
                            {
                                "name": "qr_code",
                                "enabled": True,
                                "label": "QR-код",
                                "icon": "📱",
                            },
                        ],
                        "author_id": self.default_user.id,
                        "workspace_id": self.default_workspace.id
                        if self.default_workspace
                        else None,
                        "is_public": True,  # Публичные инструкции
                        "view_count": 0,
                    }
                )

                await self.session.commit()
                logger.info(
                    "✅ Создан Document Service: %s (id=%s)", manual_name, document.id
                )
                self.stats["success"] += 1

                # Коммит каждые 10 документов
                if idx % 10 == 0:
                    logger.info("Промежуточный коммит: %d документов", idx)

            except Exception as error:
                logger.error(
                    "❌ Ошибка при импорте '%s': %s", manual_name, str(error)
                )
                self.stats["errors"].append(
                    {"manual": manual_name, "error": str(error)}
                )
                self.stats["skipped"] += 1
                await self.session.rollback()

        logger.info("Импорт завершён!")
        logger.info("Статистика:")
        logger.info("  Всего: %d", self.stats["total"])
        logger.info("  Успешно: %d", self.stats["success"])
        logger.info("  Пропущено: %d", self.stats["skipped"])
        logger.info("  Ошибок: %d", len(self.stats["errors"]))

        if self.stats["errors"]:
            logger.warning("Детали ошибок:")
            for error_info in self.stats["errors"][:10]:  # Первые 10
                logger.warning(
                    "  - %s: %s", error_info["manual"], error_info["error"]
                )

    async def run_import(self):
        """Главный метод импорта."""
        self.load_json_data()
        await self.import_manuals()


async def main():
    """Точка входа скрипта."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Импорт инструкций из work-aedb в norake-backend Document Services"
    )
    parser.add_argument(
        "--workaedb-path",
        type=str,
        default="../work-aedb",
        help="Путь к директории work-aedb (default: ../work-aedb)",
    )
    args = parser.parse_args()

    async with ManualImporter(workaedb_path=args.workaedb_path) as importer:
        await importer.run_import()


if __name__ == "__main__":
    asyncio.run(main())
