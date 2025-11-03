"""
Базовый репозиторий для profitool-store.
"""

# pylint: disable=not-callable  # func.count() is callable in SQLAlchemy
import logging
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Executable

from src.models.base import BaseModel

# Generic types
M = TypeVar("M", bound=BaseModel)


class SessionMixin:
    """
    Миксин для предоставления экземпляра сессии базы данных.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализирует миксин с сессией базы данных.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
        """
        self.session = session


class BaseRepository(SessionMixin, Generic[M]):
    """
    Базовый класс для репозиториев с поддержкой обобщенных типов.

    ИСПРАВЛЕНО: убрана зависимость от Pydantic схем - репозиторий работает только с SQLAlchemy моделями.

    Attributes:
        session (AsyncSession): Асинхронная сессия базы данных.
        model (Type[M]): Тип SQLAlchemy модели.
    """

    def __init__(
        self,
        session: AsyncSession,
        model: Type[M],
    ):
        """
        Инициализирует BaseRepository.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных.
            model (Type[M]): Тип SQLAlchemy модели.
        """
        super().__init__(session)
        self.model = model
        self.logger = logging.getLogger(self.__class__.__name__)

    async def create_item(self, data: Dict[str, Any]) -> M:
        """
        Создает новую запись в базе данных.

        Args:
            data (Dict[str, Any]): Данные для создания записи.

        Returns:
            M: Созданная SQLAlchemy модель.

        Raises:
            SQLAlchemyError: Если произошла ошибка при создании.
        """
        try:
            instance = self.model(**data)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)
            self.logger.info(
                "Создана запись %s",
                self.model.__name__,
                extra={
                    "model": self.model.__name__,
                    "id": getattr(instance, "id", None),
                },
            )
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при создании %s: %s", self.model.__name__, e)
            raise

    async def get_item_by_id(self, item_id: UUID) -> Optional[M]:
        """
        Получает запись по ID.

        Args:
            item_id (UUID): ID записи.

        Returns:
            Optional[M]: SQLAlchemy модель или None, если не найдена.
        """
        try:
            statement = select(self.model).where(self.model.id == item_id)
            result = await self.session.execute(statement)
            return result.scalar()
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении %s по ID %s: %s", self.model.__name__, item_id, e
            )
            return None

    async def get_item_by_field(self, field_name: str, field_value: Any) -> Optional[M]:
        """
        Получает запись по указанному полю.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.

        Returns:
            Optional[M]: SQLAlchemy модель или None, если не найдена.
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(
                    f"Поле '{field_name}' не существует в модели {self.model.__name__}"
                )

            field = getattr(self.model, field_name)
            statement = select(self.model).where(field == field_value)
            result = await self.session.execute(statement)
            return result.scalar()
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении %s по полю %s=%s: %s",
                self.model.__name__,
                field_name,
                field_value,
                e,
            )
            return None

    async def get_items(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[M]:
        """
        Получает список всех записей.

        Args:
            limit (Optional[int]): Лимит записей.
            offset (Optional[int]): Смещение.

        Returns:
            List[M]: Список SQLAlchemy моделей.
        """
        try:
            statement = select(self.model)

            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            result = await self.session.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении списка %s: %s", self.model.__name__, e
            )
            return []

    async def get_items_by_field(
        self,
        field_name: str,
        field_value: Any,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[M]:
        """
        Получает список записей по указанному полю.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.
            limit (Optional[int]): Лимит записей.
            offset (Optional[int]): Смещение.

        Returns:
            List[M]: Список SQLAlchemy моделей.
        """
        try:
            if not hasattr(self.model, field_name):
                raise ValueError(
                    f"Поле '{field_name}' не существует в модели {self.model.__name__}"
                )

            field = getattr(self.model, field_name)
            statement = select(self.model).where(field == field_value)

            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            result = await self.session.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при получении списка %s по полю %s=%s: %s",
                self.model.__name__,
                field_name,
                field_value,
                e,
            )
            return []

    async def update_item(self, item_id: UUID, data: Dict[str, Any]) -> Optional[M]:
        """
        Обновляет запись по ID.

        Args:
            item_id (UUID): ID записи.
            data (Dict[str, Any]): Данные для обновления.

        Returns:
            Optional[M]: Обновленная SQLAlchemy модель или None, если не найдена.

        Raises:
            SQLAlchemyError: Если произошла ошибка при обновлении.
        """
        try:
            instance = await self.get_item_by_id(item_id)
            if not instance:
                return None

            for key, value in data.items():
                if hasattr(instance, key) and key != "id":  # Не обновляем ID
                    setattr(instance, key, value)

            await self.session.commit()
            await self.session.refresh(instance)

            self.logger.info(
                "Обновлена запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "id": item_id},
            )
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Ошибка при обновлении %s с ID %s: %s", self.model.__name__, item_id, e
            )
            raise

    async def delete_item(self, item_id: UUID) -> bool:
        """
        Удаляет запись по ID.

        Args:
            item_id (UUID): ID записи.

        Returns:
            bool: True, если запись удалена, False, если не найдена.

        Raises:
            SQLAlchemyError: Если произошла ошибка при удалении.
        """
        try:
            instance = await self.get_item_by_id(item_id)
            if not instance:
                return False

            await self.session.delete(instance)
            await self.session.commit()

            self.logger.info(
                "Удалена запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "id": item_id},
            )
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Ошибка при удалении %s с ID %s: %s", self.model.__name__, item_id, e
            )
            raise

    async def count_items(self, **filters) -> int:
        """
        Подсчитывает количество записей с фильтрами.

        Args:
            **filters: Фильтры для подсчета (поддерживает операторы как в filter_by).

        Returns:
            int: Количество записей.

        Example:
            >>> # Простой подсчет
            >>> count = await repo.count_items(is_active=True)
            >>>
            >>> # С операторами
            >>> count = await repo.count_items(sort_order__gte=10, parent_id__is_null=True)
        """
        try:
            statement = select(func.count()).select_from(self.model)

            # Используем централизованную логику фильтрации
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                statement = statement.where(and_(*conditions))

            result = await self.session.execute(statement)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при подсчете %s: %s", self.model.__name__, e)
            return 0

    async def exists_by_field(self, field_name: str, field_value: Any) -> bool:
        """
        Проверяет существование записи по полю.

        Args:
            field_name (str): Название поля.
            field_value (Any): Значение поля.

        Returns:
            bool: True, если запись существует, False иначе.
        """
        try:
            if not hasattr(self.model, field_name):
                return False

            field = getattr(self.model, field_name)
            statement = (
                select(func.count()).select_from(self.model).where(field == field_value)
            )
            result = await self.session.execute(statement)
            count = result.scalar() or 0
            return count > 0
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при проверке существования %s по полю %s=%s: %s",
                self.model.__name__,
                field_name,
                field_value,
                e,
            )
            return False

    async def bulk_create(self, models: List[M]) -> List[M]:
        """
        Массовое создание записей в базе данных.

        Args:
            models (List[M]): Список моделей SQLAlchemy для добавления.

        Returns:
            List[M]: Список добавленных SQLAlchemy моделей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при массовом добавлении.

        Example:
            >>> categories = [
            ...     CategoryModel(name="Инструменты", code="tools"),
            ...     CategoryModel(name="Электрика", code="electric"),
            ... ]
            >>> created = await repo.bulk_create(categories)
        """
        try:
            self.session.add_all(models)
            await self.session.commit()

            for model in models:
                await self.session.refresh(model)

            self.logger.info(
                "Создано %s записей %s",
                len(models),
                self.model.__name__,
                extra={"model": self.model.__name__, "count": len(models)},
            )
            return models
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Ошибка при массовом создании %s: %s", self.model.__name__, e
            )
            raise

    async def bulk_update(self, models: List[M]) -> List[M]:
        """
        Массовое обновление записей в базе данных.

        Args:
            models (List[M]): Список моделей SQLAlchemy для обновления.

        Returns:
            List[M]: Список обновленных SQLAlchemy моделей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при массовом обновлении.

        Example:
            >>> categories = await repo.get_items_by_field("is_active", False)
            >>> for cat in categories:
            ...     cat.is_active = True
            >>> updated = await repo.bulk_update(categories)
        """
        try:
            await self.session.commit()

            for model in models:
                await self.session.refresh(model)

            self.logger.info(
                "Обновлено %s записей %s",
                len(models),
                self.model.__name__,
                extra={"model": self.model.__name__, "count": len(models)},
            )
            return models
        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Ошибка при массовом обновлении %s: %s", self.model.__name__, e
            )
            raise

    async def get_or_create(
        self, filters: Dict[str, Any], defaults: Optional[Dict[str, Any]] = None
    ) -> Tuple[M, bool]:
        """
        Получает запись по фильтрам или создает новую, если не существует.

        Args:
            filters (Dict[str, Any]): Словарь фильтров для поиска записи (поддерживает операторы).
            defaults (Optional[Dict[str, Any]]): Данные по умолчанию для новой записи.

        Returns:
            Tuple[M, bool]: Кортеж (модель, создана), где created=True если запись создана.

        Raises:
            SQLAlchemyError: Если произошла ошибка при получении или создании.

        Example:
            >>> category, created = await repo.get_or_create(
            ...     {"code": "tools"},
            ...     {"name": "Инструменты", "is_active": True}
            ... )
            >>> if created:
            ...     print("Категория создана")
        """
        try:
            # Строим запрос с использованием централизованной логики фильтрации
            statement = select(self.model)
            conditions = self._build_filter_conditions(**filters)

            if conditions:
                statement = statement.where(and_(*conditions))

            result = await self.session.execute(statement)
            instance = result.scalar()

            if instance:
                return instance, False

            # Создаем новую запись (только простые фильтры без операторов для создания)
            create_data = {}
            for key, value in filters.items():
                # Используем только фильтры без операторов для создания объекта
                if "__" not in key:
                    create_data[key] = value

            create_data.update(defaults or {})
            instance = self.model(**create_data)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)

            self.logger.info(
                "Создана новая запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "filters": filters},
            )
            return instance, True

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error("Ошибка при get_or_create %s: %s", self.model.__name__, e)
            raise

    async def update_or_create(
        self, filters: Dict[str, Any], defaults: Dict[str, Any]
    ) -> Tuple[M, bool]:
        """
        Обновляет запись по фильтрам или создает новую, если не существует.

        Args:
            filters (Dict[str, Any]): Словарь фильтров для поиска записи (поддерживает операторы).
            defaults (Dict[str, Any]): Данные для обновления или создания.

        Returns:
            Tuple[M, bool]: Кортеж (модель, создана), где created=True если запись создана.

        Raises:
            SQLAlchemyError: Если произошла ошибка при обновлении или создании.

        Example:
            >>> category, created = await repo.update_or_create(
            ...     {"code": "tools"},
            ...     {"name": "Инструменты обновленные", "is_active": True}
            ... )
        """
        try:
            # Строим запрос с использованием централизованной логики фильтрации
            statement = select(self.model)
            conditions = self._build_filter_conditions(**filters)

            if conditions:
                statement = statement.where(and_(*conditions))

            result = await self.session.execute(statement)
            instance = result.scalar()

            if instance:
                # Обновляем существующую запись
                for key, value in defaults.items():
                    if hasattr(instance, key) and key != "id":
                        setattr(instance, key, value)

                await self.session.commit()
                await self.session.refresh(instance)

                self.logger.info(
                    "Обновлена запись %s",
                    self.model.__name__,
                    extra={"model": self.model.__name__, "filters": filters},
                )
                return instance, False

            # Создаем новую запись (только простые фильтры без операторов)
            create_data = {}
            for key, value in filters.items():
                # Используем только фильтры без операторов для создания объекта
                if "__" not in key:
                    create_data[key] = value

            create_data.update(defaults)
            instance = self.model(**create_data)
            self.session.add(instance)
            await self.session.commit()
            await self.session.refresh(instance)

            self.logger.info(
                "Создана новая запись %s",
                self.model.__name__,
                extra={"model": self.model.__name__, "filters": filters},
            )
            return instance, True

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Ошибка при update_or_create %s: %s", self.model.__name__, e
            )
            raise

    def _apply_filter_condition(self, field, operator: str, value):
        """
        Применяет условие фильтрации к полю.

        Централизованная логика для применения операторов фильтрации.
        Используется во всех методах фильтрации для соблюдения DRY.

        Args:
            field: SQLAlchemy поле модели
            operator: Оператор фильтрации (eq, ne, gt, lt, gte, lte, in, not_in, like, ilike, is_null)
            value: Значение для фильтрации

        Returns:
            SQLAlchemy условие или None если оператор неизвестен
        """
        if operator == "eq":
            return field == value
        elif operator == "ne":
            return field != value
        elif operator == "gt":
            return field > value
        elif operator == "lt":
            return field < value
        elif operator == "gte":
            return field >= value
        elif operator == "lte":
            return field <= value
        elif operator == "in":
            return field.in_(value)
        elif operator == "not_in":
            return ~field.in_(value)
        elif operator == "like":
            return field.like(value)
        elif operator == "ilike":
            return field.ilike(value)
        elif operator == "is_null":
            if value:
                return field.is_(None)
            else:
                return field.isnot(None)
        else:
            self.logger.warning("Неизвестный оператор '%s'", operator)
            return None

    def _build_filter_conditions(self, **kwargs) -> List:
        """
        Строит список условий фильтрации из kwargs.

        Централизованный парсинг фильтров для переиспользования
        во всех методах фильтрации.

        Args:
            **kwargs: Параметры фильтрации в формате field__operator=value

        Returns:
            List: Список SQLAlchemy условий для WHERE
        """
        conditions = []

        for key, value in kwargs.items():
            # Исключаем служебные параметры
            if key in ("limit", "offset"):
                continue

            if "__" in key:
                field_name, operator = key.rsplit("__", 1)
            else:
                field_name, operator = key, "eq"

            if not hasattr(self.model, field_name):
                self.logger.warning(
                    "Поле '%s' не существует в модели %s",
                    field_name,
                    self.model.__name__,
                )
                continue

            field = getattr(self.model, field_name)
            condition = self._apply_filter_condition(field, operator, value)

            if condition is not None:
                conditions.append(condition)

        return conditions

    async def filter_by(self, **kwargs) -> List[M]:
        """
        Фильтрует записи по указанным параметрам с поддержкой операторов.

        Операторы фильтрации:
        | Оператор  | Описание                    | Пример                         |
        |-----------|-----------------------------|---------------------------------|
        | eq        | Равно (=)                   | field__eq=value                 |
        | ne        | Не равно (!=)               | field__ne=value                 |
        | gt        | Больше (>)                  | field__gt=value                 |
        | lt        | Меньше (<)                  | field__lt=value                 |
        | gte       | Больше или равно (>=)       | field__gte=value                |
        | lte       | Меньше или равно (<=)       | field__lte=value                |
        | in        | В списке                    | field__in=[value1, value2]      |
        | not_in    | Не в списке                 | field__not_in=[value1, value2]  |
        | like      | LIKE (с учетом регистра)    | field__like="%value%"           |
        | ilike     | ILIKE (без учета регистра)  | field__ilike="%value%"          |
        | is_null   | IS NULL / IS NOT NULL       | field__is_null=True             |

        Args:
            **kwargs: Параметры фильтрации в формате field__operator=value.

        Returns:
            List[M]: Список отфильтрованных SQLAlchemy моделей.

        Example:
            >>> # Простая фильтрация
            >>> active_cats = await repo.filter_by(is_active=True)
            >>>
            >>> # С операторами
            >>> categories = await repo.filter_by(
            ...     name__ilike="%инструмент%",
            ...     sort_order__gte=10,
            ...     parent_id__is_null=True
            ... )
        """
        try:
            statement = select(self.model)
            conditions = self._build_filter_conditions(**kwargs)

            if conditions:
                statement = statement.where(and_(*conditions))

            # Пагинация
            limit = kwargs.get("limit")
            offset = kwargs.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return await self.execute_and_return_scalars(statement)

        except (SQLAlchemyError, AttributeError) as e:
            self.logger.error("Ошибка при фильтрации %s: %s", self.model.__name__, e)
            return []

    async def filter_by_ordered(
        self, order_by: str, ascending: bool = True, **kwargs
    ) -> List[M]:
        """
        Фильтрует записи с сортировкой.

        Комбинирует возможности filter_by с ORDER BY для случаев,
        когда нужна и фильтрация, и сортировка результатов.

        Args:
            order_by (str): Поле для сортировки.
            ascending (bool): True для ASC, False для DESC. По умолчанию True.
            **kwargs: Параметры фильтрации (те же, что в filter_by).

        Returns:
            List[M]: Отсортированный список отфильтрованных SQLAlchemy моделей.

        Example:
            >>> # Активные категории, отсортированные по sort_order
            >>> categories = await repo.filter_by_ordered(
            ...     "sort_order",
            ...     is_active=True,
            ...     parent_id__is_null=True
            ... )
            >>>
            >>> # Категории с порядком >= 10, отсортированные по имени (DESC)
            >>> categories = await repo.filter_by_ordered(
            ...     "name",
            ...     ascending=False,
            ...     sort_order__gte=10
            ... )
        """
        try:
            statement = select(self.model)
            conditions = self._build_filter_conditions(**kwargs)

            if conditions:
                statement = statement.where(and_(*conditions))

            # Добавляем сортировку
            if not hasattr(self.model, order_by):
                self.logger.warning(
                    "Поле '%s' для сортировки не существует в модели %s",
                    order_by,
                    self.model.__name__,
                )
            else:
                order_field = getattr(self.model, order_by)
                if ascending:
                    statement = statement.order_by(order_field)
                else:
                    statement = statement.order_by(order_field.desc())

            # Пагинация
            limit = kwargs.get("limit")
            offset = kwargs.get("offset")
            if offset is not None:
                statement = statement.offset(offset)
            if limit is not None:
                statement = statement.limit(limit)

            return await self.execute_and_return_scalars(statement)

        except (SQLAlchemyError, AttributeError) as e:
            self.logger.error(
                "Ошибка при фильтрации с сортировкой %s: %s", self.model.__name__, e
            )
            return []

    async def execute_statement(self, statement: Executable) -> Any:
        """
        Выполняет произвольный SQL-запрос (SELECT).

        Args:
            statement (Executable): SQLAlchemy запрос для выполнения.

        Returns:
            Any: Результат выполнения запроса.

        Example:
            >>> from sqlalchemy import select
            >>> stmt = select(CategoryModel).where(
            ...     CategoryModel.name.ilike("%инструмент%")
            ... ).order_by(CategoryModel.sort_order)
            >>> result = await repo.execute_statement(stmt)
            >>> categories = list(result.scalars().all())
        """
        try:
            result = await self.session.execute(statement)
            return result
        except SQLAlchemyError as e:
            self.logger.error("Ошибка при выполнении запроса: %s", e)
            raise

    async def delete_by_filters(self, **filters) -> int:
        """
        Удаляет записи по фильтрам.

        Args:
            **filters: Фильтры для удаления (поддерживает операторы как в filter_by).

        Returns:
            int: Количество удаленных записей.

        Raises:
            SQLAlchemyError: Если произошла ошибка при удалении.

        Example:
            >>> # Удалить неактивные категории
            >>> deleted_count = await repo.delete_by_filters(is_active=False)
            >>>
            >>> # С операторами
            >>> deleted_count = await repo.delete_by_filters(sort_order__lt=10)
        """
        try:
            statement = delete(self.model)

            # Используем централизованную логику фильтрации
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                # delete() требует where() с условиями через and_
                for condition in conditions:
                    statement = statement.where(condition)

            result = await self.session.execute(statement)
            await self.session.commit()

            deleted_count = result.rowcount
            self.logger.info(
                "Удалено %s записей %s",
                deleted_count,
                self.model.__name__,
                extra={"model": self.model.__name__, "filters": filters},
            )
            return deleted_count

        except SQLAlchemyError as e:
            await self.session.rollback()
            self.logger.error(
                "Ошибка при удалении %s по фильтрам: %s", self.model.__name__, e
            )
            raise

    async def execute_and_return_scalars(self, statement: Executable) -> List[M]:
        """
        Выполняет statement и возвращает список моделей.

        Базовый метод для выполнения SELECT запросов с автоматическим
        логированием и обработкой ошибок.

        Args:
            statement: SQLAlchemy statement для выполнения

        Returns:
            List[M]: Список моделей

        Raises:
            SQLAlchemyError: При ошибке выполнения запроса
        """
        try:
            result = await self.session.execute(statement)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при выполнении запроса %s: %s", self.model.__name__, e
            )
            raise

    async def execute_and_return_scalar(self, statement: Executable) -> Optional[M]:
        """
        Выполняет statement и возвращает одну модель.

        Базовый метод для выполнения SELECT запросов, возвращающих одну запись.

        Args:
            statement: SQLAlchemy statement для выполнения

        Returns:
            Optional[M]: Модель или None

        Raises:
            SQLAlchemyError: При ошибке выполнения запроса
        """
        try:
            result = await self.session.execute(statement)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            self.logger.error(
                "Ошибка при выполнении запроса %s: %s", self.model.__name__, e
            )
            raise

    async def get_items_with_relations(
        self, relation_options: List, **filters
    ) -> List[M]:
        """
        Получает записи с загрузкой связанных объектов.

        Базовый метод для запросов с selectinload/joinedload.

        Args:
            relation_options: Список options для загрузки связей (selectinload, joinedload)
            **filters: Фильтры как в filter_by

        Returns:
            List[M]: Список моделей с загруженными связями

        Example:
            >>> options = [selectinload(ProductModel.categories)]
            >>> products = await repo.get_items_with_relations(options, is_active=True)
        """
        try:
            stmt = select(self.model)

            # Добавляем relation options
            for option in relation_options:
                stmt = stmt.options(option)

            # Применяем фильтры используя централизованную логику
            conditions = self._build_filter_conditions(**filters)
            if conditions:
                stmt = stmt.where(and_(*conditions))

            # Пагинация
            limit = filters.get("limit")
            offset = filters.get("offset")
            if offset is not None:
                stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)

            return await self.execute_and_return_scalars(stmt)

        except (SQLAlchemyError, AttributeError) as e:
            self.logger.error(
                "Ошибка при получении %s с связями: %s", self.model.__name__, e
            )
            return []
