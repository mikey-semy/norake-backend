"""
Загрузчик фикстур из JSON файлов.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.repository.v1.templates import TemplateRepository
from src.repository.v1.users import UserRepository
from src.models.v1.templates import TemplateModel
from src.models.v1.users import UserModel
from src.models.v1.roles import UserRoleModel, RoleCode

logger = logging.getLogger(__name__)


class JSONFixtureLoader:
    """
    Загрузчик фикстур из JSON файлов.

    Читает данные только из JSON файлов, позволяет легко редактировать шаблоны.
    """

    def __init__(self, session: AsyncSession, fixtures_dir: str = "fixtures_data"):
        """
        Инициализирует загрузчик фикстур.

        Args:
            session: Асинхронная сессия SQLAlchemy
            fixtures_dir: Директория с JSON файлами фикстур
        """
        self.session = session
        self.fixtures_dir = Path(fixtures_dir)
        self.template_repository = TemplateRepository(session)
        self.user_repository = UserRepository(session)

    def _find_fixture_file(self, fixture_type: str) -> Path | None:
        """
        Ищет самый актуальный файл фикстур для заданного типа.

        Приоритет поиска:
        1. {fixture_type}.json (основной файл)
        2. current_{fixture_type}_YYYYMMDD_HHMMSS.json (самый свежий экспорт)
        3. Любой файл с названием, содержащим fixture_type

        Args:
            fixture_type: Тип фикстуры (templates)

        Returns:
            Path к найденному файлу или None
        """
        if not self.fixtures_dir.exists():
            logger.warning("📁 Директория фикстур не найдена: %s", self.fixtures_dir)
            return None

        # 1. Ищем основной файл
        main_file = self.fixtures_dir / f"{fixture_type}.json"
        if main_file.exists():
            logger.debug("✅ Найден основной файл: %s", main_file)
            return main_file

        # 2. Ищем файлы экспорта (current_*) и берем самый свежий
        export_pattern = f"current_{fixture_type}_*.json"
        export_files = list(self.fixtures_dir.glob(export_pattern))

        if export_files:
            # Сортируем по дате в имени файла (самый свежий последний)
            latest_file = sorted(export_files)[-1]
            logger.debug("✅ Найден файл экспорта: %s", latest_file)
            return latest_file

        # 3. Ищем любой файл, содержащий fixture_type
        any_pattern = f"*{fixture_type}*.json"
        any_files = list(self.fixtures_dir.glob(any_pattern))

        if any_files:
            found_file = any_files[0]
            logger.debug("✅ Найден альтернативный файл: %s", found_file)
            return found_file

        logger.warning("❌ Файл фикстур не найден для типа: %s", fixture_type)
        return None

    def _load_json_file(self, fixture_type: str) -> Dict[str, Any] | None:
        """
        Загружает JSON файл для указанного типа фикстур.

        Args:
            fixture_type: Тип фикстуры (templates)

        Returns:
            Данные из JSON файла или None если файл не найден
        """
        file_path = self._find_fixture_file(fixture_type)

        if not file_path:
            logger.warning("⚠️ Пропускаем загрузку %s - файл не найден", fixture_type)
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info("📄 Загружен JSON файл: %s", file_path)
            return data

        except Exception as e:
            logger.error("❌ Ошибка при чтении %s: %s", file_path, e)
            return None

    def _prepare_data_for_import(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Подготавливает данные для импорта, удаляя служебные поля.

        Args:
            data: Данные из JSON файла

        Returns:
            Список очищенных словарей для импорта
        """
        items = data.get("data", [])
        cleaned_items = []

        for item in items:
            # Удаляем поля, которые не должны импортироваться (авто-генерируемые)
            clean_item = {k: v for k, v in item.items()
                         if k not in ["id", "created_at", "updated_at"]}

            cleaned_items.append(clean_item)

        return cleaned_items

    async def load_templates(self, force: bool = False) -> Dict[str, int]:
        """
        Загружает шаблоны из JSON файла.

        Args:
            force: Если True - перезаписывает существующие шаблоны

        Returns:
            Статистика: {created, updated, skipped}
        """
        logger.info("🔄 Загрузка шаблонов из JSON...")

        data = self._load_json_file("templates")
        if not data:
            logger.warning("⚠️ Файл templates не найден, пропускаем")
            return {"created": 0, "updated": 0, "skipped": 0}

        items = self._prepare_data_for_import(data)

        # Находим автора для шаблонов (админа или первого пользователя)
        try:
            author = await self._get_author_for_fixtures()
        except ValueError as e:
            logger.error(str(e))
            return {"created": 0, "updated": 0, "skipped": 0}

        created = 0
        updated = 0
        skipped = 0

        for item_data in items:
            # Удаляем author_id из данных если он там есть (используем найденного автора)
            item_data.pop("author_id", None)

            # Проверяем существование по названию
            stmt = select(TemplateModel).where(TemplateModel.title == item_data["title"])
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                # Создаем новый шаблон с найденным автором
                new_item = TemplateModel(**item_data, author_id=author.id)
                self.session.add(new_item)
                await self.session.commit()
                created += 1
                logger.info("✅ Создан шаблон: %s (автор: %s)", item_data['title'], author.username)
            elif force:
                # Обновляем существующий (не меняем автора!)
                update_data = {k: v for k, v in item_data.items() if k != "title"}
                stmt = update(TemplateModel).where(
                    TemplateModel.title == item_data["title"]
                ).values(**update_data)
                await self.session.execute(stmt)
                await self.session.commit()
                updated += 1
                logger.info("🔄 Обновлен шаблон: %s", item_data['title'])
            else:
                skipped += 1
                logger.debug("⏭️ Шаблон уже существует: %s", item_data['title'])

        logger.info("📊 Шаблоны: создано=%d, обновлено=%d, пропущено=%d", created, updated, skipped)
        return {"created": created, "updated": updated, "skipped": skipped}

    async def _get_author_for_fixtures(self) -> UserModel:
        """
        Находит автора для создания шаблонов из фикстур.

        Логика поиска:
        1. Ищет первого пользователя с ролью 'admin'
        2. Если админа нет - возвращает первого найденного пользователя
        3. Если пользователей вообще нет - выбрасывает исключение

        Returns:
            UserModel: Найденный пользователь для назначения автором

        Raises:
            ValueError: Если в базе нет ни одного пользователя
        """
        # Ищем первого админа через связь с UserRoleModel
        stmt = (
            select(UserModel)
            .join(UserRoleModel, UserModel.id == UserRoleModel.user_id)
            .where(UserRoleModel.role_code == RoleCode.ADMIN)
            .options(selectinload(UserModel.user_roles))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        admin = result.scalar_one_or_none()

        if admin:
            logger.info("✅ Найден админ для фикстур: %s (ID: %s)", admin.username, admin.id)
            return admin

        # Если админа нет - берём первого пользователя
        stmt = select(UserModel).limit(1)
        result = await self.session.execute(stmt)
        first_user = result.scalar_one_or_none()

        if first_user:
            logger.warning(
                "⚠️ Админ не найден, используем первого пользователя: %s (ID: %s)",
                first_user.username,
                first_user.id
            )
            return first_user

        # Если вообще нет пользователей - ошибка
        raise ValueError(
            "❌ В базе данных нет ни одного пользователя! "
            "Создайте хотя бы одного пользователя перед загрузкой фикстур шаблонов."
        )

    async def load_all_fixtures(self, force: bool = False) -> Dict[str, Dict[str, int]]:
        """
        Загружает все фикстуры из JSON файлов.

        Args:
            force: Если True - перезаписывает существующие данные

        Returns:
            Статистика по каждому типу фикстур
        """
        logger.info("🚀 Начало загрузки всех фикстур...")

        results = {}

        # Загружаем шаблоны
        results["templates"] = await self.load_templates(force=force)

        logger.info("✅ Загрузка всех фикстур завершена")
        return results
