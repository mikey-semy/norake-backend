"""
Модуль для экспорта и импорта фикстур в JSON формате.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.repository.v1.templates import TemplateRepository
from src.models.v1.templates import TemplateModel

logger = logging.getLogger(__name__)


class UUIDEncoder(json.JSONEncoder):
    """JSON encoder для обработки UUID объектов."""

    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class FixtureJSONHandler:
    """Класс для работы с фикстурами в JSON формате."""

    def __init__(self, session: AsyncSession, export_dir: str = "fixtures_export"):
        """
        Инициализирует обработчик фикстур.

        Args:
            session: Асинхронная сессия SQLAlchemy
            export_dir: Директория для экспорта JSON файлов
        """
        self.session = session
        self.template_repository = TemplateRepository(session)
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)

    async def export_to_json(self,
                           include_templates: bool = True,
                           filename_prefix: str = None) -> Dict[str, str]:
        """
        Экспортирует фикстуры в JSON файлы.

        Args:
            include_templates: Включить шаблоны в экспорт
            filename_prefix: Префикс для имён файлов

        Returns:
            Словарь с путями к созданным файлам
        """
        logger.info("Начало экспорта фикстур в JSON")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"{filename_prefix}_" if filename_prefix else ""

        exported_files = {}

        if include_templates:
            templates_file = await self._export_templates(f"{prefix}templates_{timestamp}")
            exported_files["templates"] = templates_file

        logger.info("Экспорт фикстур завершён. Файлы: %s", list(exported_files.values()))
        return exported_files

    async def _export_templates(self, filename: str) -> str:
        """
        Экспортирует шаблоны в JSON.

        Args:
            filename: Имя файла без расширения

        Returns:
            Путь к созданному файлу
        """
        logger.info("Экспорт шаблонов...")

        # Получаем все шаблоны из БД
        all_templates = await self.template_repository.filter_by()

        templates_data = []
        for template in all_templates:
            template_dict = {
                "id": template.id,
                "title": template.title,
                "description": template.description,
                "category": template.category,
                "fields": template.fields,
                "visibility": template.visibility,
                "author_id": template.author_id,
                "usage_count": template.usage_count,
                "is_active": template.is_active,
                "created_at": template.created_at,
                "updated_at": template.updated_at,
            }
            templates_data.append(template_dict)

        export_data = {
            "metadata": {
                "export_type": "templates",
                "export_date": datetime.now().isoformat(),
                "count": len(templates_data)
            },
            "data": templates_data
        }

        file_path = self.export_dir / f"{filename}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2, cls=UUIDEncoder)

        logger.info("✅ Экспортировано %d шаблонов в %s", len(templates_data), file_path)
        return str(file_path)

    async def import_from_json(self, filepath: str, force: bool = False) -> Dict[str, int]:
        """
        Импортирует фикстуры из JSON файла.

        Args:
            filepath: Путь к JSON файлу
            force: Перезаписывать существующие записи

        Returns:
            Статистика импорта
        """
        logger.info("Импорт фикстур из %s", filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        export_type = data.get("metadata", {}).get("export_type")

        if export_type == "templates":
            from src.core.fixtures.json_loader import JSONFixtureLoader
            loader = JSONFixtureLoader(self.session)
            return await loader.load_templates(force=force)

        logger.warning("Неизвестный тип экспорта: %s", export_type)
        return {"created": 0, "updated": 0, "skipped": 0}
