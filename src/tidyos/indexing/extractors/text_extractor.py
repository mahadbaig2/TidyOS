"""Text and Markdown document extractor."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from tidyos.indexing.extractors.base import (
    BaseExtractor,
    ExtractedContent,
    normalize_extracted_text,
)
from tidyos.logging_config import get_logger

logger = get_logger("indexing.extractors.text")

SUPPORTED_TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".csv",
    ".tsv",
    ".log",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".htm",
    ".css",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".py",
    ".rs",
    ".go",
    ".java",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".sh",
    ".bat",
    ".ps1",
    ".ini",
    ".toml",
    ".env",
    ".rst",
}


class TextExtractor(BaseExtractor):
    """Extractor for plain text, Markdown, JSON, CSV, and code documents."""

    def extract(self, file_path: Path, max_chars: int = 12000) -> ExtractedContent:
        path_str = str(file_path.resolve())
        if not file_path.exists() or not file_path.is_file():
            return ExtractedContent(
                file_path=path_str,
                is_valid=False,
                error=f"File not found: {path_str}",
            )

        raw_text = ""
        # Robust multi-encoding read attempt
        encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        read_success = False

        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc, errors="replace") as f:
                    raw_text = f.read(max_chars + 1024)
                read_success = True
                break
            except Exception as e:
                logger.debug(f"Encoding {enc} failed for {file_path}: {e}")
                continue

        if not read_success:
            return ExtractedContent(
                file_path=path_str,
                is_valid=False,
                error=f"Could not read text file with standard encodings: {path_str}",
            )

        is_truncated = len(raw_text) > max_chars
        truncated_raw = raw_text[:max_chars] if is_truncated else raw_text
        normalized = normalize_extracted_text(truncated_raw)

        meta: Dict[str, Any] = {
            "extension": file_path.suffix.lower(),
            "size_bytes": file_path.stat().st_size,
        }

        return ExtractedContent(
            file_path=path_str,
            text=normalized,
            char_count=len(normalized),
            is_truncated=is_truncated,
            is_valid=True,
            metadata=meta,
        )
