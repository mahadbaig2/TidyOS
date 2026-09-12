"""PDF document extractor using PyMuPDF."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import pymupdf

from tidyos.indexing.extractors.base import (
    BaseExtractor,
    ExtractedContent,
    normalize_extracted_text,
)
from tidyos.logging_config import get_logger

logger = get_logger("indexing.extractors.pdf")

SUPPORTED_PDF_EXTENSIONS = {".pdf"}


class PdfExtractor(BaseExtractor):
    """Fast, bounded local PDF extractor powered by PyMuPDF."""

    def __init__(self, max_pages: int = 10):
        self.max_pages = max_pages

    def extract(self, file_path: Path, max_chars: int = 12000) -> ExtractedContent:
        path_str = str(file_path.resolve())
        if not file_path.exists() or not file_path.is_file():
            return ExtractedContent(
                file_path=path_str,
                is_valid=False,
                error=f"File not found: {path_str}",
            )

        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            logger.warning(f"Could not open PDF file {file_path}: {e}")
            return ExtractedContent(
                file_path=path_str,
                is_valid=False,
                error=f"Corrupt or unreadable PDF: {e}",
            )

        try:
            if doc.is_encrypted:
                return ExtractedContent(
                    file_path=path_str,
                    is_valid=False,
                    error="PDF is encrypted / password protected.",
                )

            metadata: Dict[str, Any] = {
                "page_count": len(doc),
                "title": doc.metadata.get("title") if doc.metadata else None,
                "author": doc.metadata.get("author") if doc.metadata else None,
                "subject": doc.metadata.get("subject") if doc.metadata else None,
            }

            accumulated_text = []
            char_count = 0
            is_truncated = False

            pages_to_read = min(len(doc), self.max_pages)
            for page_idx in range(pages_to_read):
                page = doc[page_idx]
                page_text = page.get_text("text") or ""
                accumulated_text.append(page_text)
                char_count += len(page_text)

                if char_count >= max_chars:
                    is_truncated = True
                    break

            if len(doc) > self.max_pages:
                is_truncated = True

            combined = "".join(accumulated_text)
            if len(combined) > max_chars:
                combined = combined[:max_chars]
                is_truncated = True

            normalized = normalize_extracted_text(combined)

            return ExtractedContent(
                file_path=path_str,
                text=normalized,
                char_count=len(normalized),
                is_truncated=is_truncated,
                is_valid=True,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error parsing PDF content in {file_path}: {e}", exc_info=True)
            return ExtractedContent(
                file_path=path_str,
                is_valid=False,
                error=f"PDF parsing error: {e}",
            )
        finally:
            doc.close()
