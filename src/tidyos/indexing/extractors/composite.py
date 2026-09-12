"""Composite content extractor routing file formats to specialized extractors."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Set

from tidyos.indexing.extractors.base import BaseExtractor, ExtractedContent
from tidyos.indexing.extractors.docx_extractor import (
    DocxExtractor,
    SUPPORTED_DOCX_EXTENSIONS,
)
from tidyos.indexing.extractors.image_extractor import (
    ImageExtractor,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from tidyos.indexing.extractors.pdf_extractor import (
    PdfExtractor,
    SUPPORTED_PDF_EXTENSIONS,
)
from tidyos.indexing.extractors.text_extractor import (
    TextExtractor,
    SUPPORTED_TEXT_EXTENSIONS,
)

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Unified composite content extractor that routes files by format."""

    def __init__(
        self,
        text_extractor: Optional[BaseExtractor] = None,
        pdf_extractor: Optional[BaseExtractor] = None,
        docx_extractor: Optional[BaseExtractor] = None,
        image_extractor: Optional[BaseExtractor] = None,
    ):
        self.text_extractor = text_extractor or TextExtractor()
        self.pdf_extractor = pdf_extractor or PdfExtractor()
        self.docx_extractor = docx_extractor or DocxExtractor()
        self.image_extractor = image_extractor or ImageExtractor()

        # Build extension routing table
        self._router: Dict[str, BaseExtractor] = {}
        for ext in SUPPORTED_TEXT_EXTENSIONS:
            self._router[ext] = self.text_extractor
        for ext in SUPPORTED_PDF_EXTENSIONS:
            self._router[ext] = self.pdf_extractor
        for ext in SUPPORTED_DOCX_EXTENSIONS:
            self._router[ext] = self.docx_extractor
        for ext in SUPPORTED_IMAGE_EXTENSIONS:
            self._router[ext] = self.image_extractor

    @property
    def supported_extensions(self) -> Set[str]:
        """Set of all registered file extensions (lowercase, with dot)."""
        return set(self._router.keys())

    def can_extract(self, file_path: Path | str) -> bool:
        """Check whether the file extension has a registered extractor."""
        path = Path(file_path)
        return path.suffix.lower() in self._router

    def extract(self, file_path: Path | str, max_chars: int = 12000) -> ExtractedContent:
        """Route file to appropriate extractor and return extracted content."""
        path = Path(file_path)

        if not path.exists():
            return ExtractedContent(
                file_path=str(path),
                is_valid=False,
                error=f"File not found: {path}",
            )

        if not path.is_file():
            return ExtractedContent(
                file_path=str(path),
                is_valid=False,
                error=f"Path is not a regular file: {path}",
            )

        ext = path.suffix.lower()
        extractor = self._router.get(ext)

        if not extractor:
            return ExtractedContent(
                file_path=str(path),
                is_valid=False,
                error=f"Unsupported file format: {ext or '[no extension]'}",
            )

        try:
            return extractor.extract(path, max_chars=max_chars)
        except Exception as e:
            logger.error("Extraction error for %s: %s", path, e, exc_info=True)
            return ExtractedContent(
                file_path=str(path),
                is_valid=False,
                error=f"Unhandled extraction error: {e}",
            )
