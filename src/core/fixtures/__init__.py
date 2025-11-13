"""
Модуль для работы с фикстурами.

Предоставляет инструменты для:
- Загрузки фикстур из JSON файлов
- Экспорта данных в JSON
- Управления тестовыми данными
"""

from src.core.fixtures.json_loader import JSONFixtureLoader
from src.core.fixtures.json_handler import FixtureJSONHandler

__all__ = [
    "JSONFixtureLoader",
    "FixtureJSONHandler",
]
