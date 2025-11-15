"""
Сервис для обработки PDF файлов.

Предоставляет методы для извлечения текста, метаданных и изображений из PDF.
Использует pdfplumber для текстовых PDF и опционально OCR для сканов.
"""

import io
import logging
from typing import Dict, List, Optional, Tuple

import pdfplumber
import pymupdf  # PyMuPDF

logger = logging.getLogger(__name__)


class PDFProcessor:
    """
    Сервис для обработки PDF файлов.

    Предоставляет методы для извлечения текста, метаданных, информации о страницах.
    Использует pdfplumber как основной метод, PyMuPDF как альтернативу.

    Example:
        >>> processor = PDFProcessor()
        >>> text, page_count, method = await processor.extract_text(pdf_content)
        >>> print(f"Извлечено {page_count} страниц методом {method}")
    """

    async def extract_text(
        self, file_content: bytes, use_pymupdf: bool = False
    ) -> Tuple[str, int, str]:
        """
        Извлекает текст из PDF файла.

        Args:
            file_content: Содержимое PDF файла в байтах.
            use_pymupdf: Использовать PyMuPDF вместо pdfplumber (по умолчанию False).

        Returns:
            Tuple[str, int, str]: (extracted_text, page_count, extraction_method)

        Raises:
            ValueError: Если не удалось извлечь текст.

        Example:
            >>> text, pages, method = await processor.extract_text(pdf_bytes)
            >>> print(f"Метод: {method}, страниц: {pages}")
        """
        if use_pymupdf:
            return await self._extract_with_pymupdf(file_content)
        return await self._extract_with_pdfplumber(file_content)

    async def _extract_with_pdfplumber(
        self, file_content: bytes
    ) -> Tuple[str, int, str]:
        """
        Извлекает текст через pdfplumber.

        Args:
            file_content: Содержимое PDF файла.

        Returns:
            Tuple[str, int, str]: (extracted_text, page_count, "pdfplumber")

        Raises:
            ValueError: Если не удалось открыть PDF или извлечь текст.
        """
        try:
            file_obj = io.BytesIO(file_content)
            extracted_pages = []

            with pdfplumber.open(file_obj) as pdf:
                page_count = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        extracted_pages.append(f"--- Page {page_num} ---\n{text}")

                full_text = "\n\n".join(extracted_pages)

                if not full_text.strip():
                    raise ValueError(
                        "PDF не содержит извлекаемого текста (возможно, это скан)"
                    )

                logger.info(
                    "✅ Извлечено %d страниц через pdfplumber (текст: %d символов)",
                    page_count,
                    len(full_text),
                )

                return full_text, page_count, "pdfplumber"

        except Exception as e:
            logger.error("❌ Ошибка извлечения текста через pdfplumber: %s", str(e))
            raise ValueError(
                f"Не удалось извлечь текст через pdfplumber: {str(e)}"
            ) from e

    async def _extract_with_pymupdf(
        self, file_content: bytes
    ) -> Tuple[str, int, str]:
        """
        Извлекает текст через PyMuPDF (fitz).

        Args:
            file_content: Содержимое PDF файла.

        Returns:
            Tuple[str, int, str]: (extracted_text, page_count, "pymupdf")

        Raises:
            ValueError: Если не удалось открыть PDF или извлечь текст.
        """
        try:
            doc = pymupdf.open(stream=file_content, filetype="pdf")
            page_count = doc.page_count
            extracted_pages = []

            for page_num in range(page_count):
                page = doc[page_num]
                text = page.get_text("text")
                if text.strip():
                    extracted_pages.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()

            full_text = "\n\n".join(extracted_pages)

            if not full_text.strip():
                raise ValueError(
                    "PDF не содержит извлекаемого текста (возможно, это скан)"
                )

            logger.info(
                "✅ Извлечено %d страниц через PyMuPDF (текст: %d символов)",
                page_count,
                len(full_text),
            )

            return full_text, page_count, "pymupdf"

        except Exception as e:
            logger.error("❌ Ошибка извлечения текста через PyMuPDF: %s", str(e))
            raise ValueError(
                f"Не удалось извлечь текст через PyMuPDF: {str(e)}"
            ) from e

    async def extract_metadata(self, file_content: bytes) -> Dict[str, any]:
        """
        Извлекает метаданные из PDF файла.

        Args:
            file_content: Содержимое PDF файла.

        Returns:
            Dict с метаданными: title, author, subject, creator, producer,
            creation_date, modification_date, page_count.

        Example:
            >>> metadata = await processor.extract_metadata(pdf_bytes)
            >>> print(metadata["title"], metadata["page_count"])
        """
        try:
            doc = pymupdf.open(stream=file_content, filetype="pdf")
            # doc.metadata возвращает dict с метаданными PDF
            pdf_meta = doc.metadata if hasattr(doc, 'metadata') else {}
            metadata = {
                "title": pdf_meta.get("title", ""),
                "author": pdf_meta.get("author", ""),
                "subject": pdf_meta.get("subject", ""),
                "creator": pdf_meta.get("creator", ""),
                "producer": pdf_meta.get("producer", ""),
                "creation_date": pdf_meta.get("creationDate", ""),
                "modification_date": pdf_meta.get("modDate", ""),
                "page_count": doc.page_count,
            }
            doc.close()

            logger.info("✅ Извлечены метаданные PDF: %d страниц", metadata["page_count"])
            return metadata

        except Exception as e:
            logger.error("❌ Ошибка извлечения метаданных PDF: %s", str(e))
            return {"page_count": 0, "error": str(e)}

    async def extract_page_text(
        self, file_content: bytes, page_num: int
    ) -> Optional[str]:
        """
        Извлекает текст с конкретной страницы.

        Args:
            file_content: Содержимое PDF файла.
            page_num: Номер страницы (1-based).

        Returns:
            Текст страницы или None, если страница не найдена.

        Example:
            >>> text = await processor.extract_page_text(pdf_bytes, page_num=5)
            >>> print(f"Страница 5: {text[:100]}")
        """
        try:
            file_obj = io.BytesIO(file_content)

            with pdfplumber.open(file_obj) as pdf:
                if page_num < 1 or page_num > len(pdf.pages):
                    logger.warning(
                        "Страница %d не найдена (всего страниц: %d)",
                        page_num,
                        len(pdf.pages),
                    )
                    return None

                page = pdf.pages[page_num - 1]  # 0-based index
                text = page.extract_text()

                logger.info("✅ Извлечён текст страницы %d", page_num)
                return text

        except Exception as e:
            logger.error("❌ Ошибка извлечения текста страницы %d: %s", page_num, str(e))
            return None

    async def get_page_ranges(
        self, file_content: bytes, chunk_size: int = 10
    ) -> List[Dict[str, any]]:
        """
        Разбивает PDF на диапазоны страниц для поэтапной обработки.

        Args:
            file_content: Содержимое PDF файла.
            chunk_size: Размер диапазона в страницах (по умолчанию 10).

        Returns:
            List[Dict]: Список диапазонов [{"start": 1, "end": 10}, ...].

        Example:
            >>> ranges = await processor.get_page_ranges(pdf_bytes, chunk_size=50)
            >>> for r in ranges:
            ...     print(f"Обработать страницы {r['start']}-{r['end']}")
        """
        try:
            metadata = await self.extract_metadata(file_content)
            total_pages = metadata.get("page_count", 0)

            if total_pages == 0:
                return []

            ranges = []
            for start in range(1, total_pages + 1, chunk_size):
                end = min(start + chunk_size - 1, total_pages)
                ranges.append({"start": start, "end": end, "pages": end - start + 1})

            logger.info(
                "✅ Создано %d диапазонов страниц (chunk_size=%d)", len(ranges), chunk_size
            )
            return ranges

        except Exception as e:
            logger.error("❌ Ошибка создания диапазонов страниц: %s", str(e))
            return []
