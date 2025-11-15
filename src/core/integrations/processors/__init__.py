"""
Модуль processors содержит обработчики документов.

Экспортируемые классы:
    - PDFProcessor: Обработка PDF файлов (извлечение текста, метаданных).
"""

from .pdf_processor import PDFProcessor

__all__ = ["PDFProcessor"]
