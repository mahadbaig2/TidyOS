"""Base definitions and normalization utilities for content extraction."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


def normalize_extracted_text(raw_text: str) -> str:
    """Clean and normalize extracted raw text.

    - Removes null bytes
    - Normalizes line breaks
    - Collapses excessive blank lines and repeated whitespace
    - Strips leading and trailing whitespace
    """
    if not raw_text:
        return ""

    # Remove null characters and non-printable control characters (except newline/tab)
    cleaned = raw_text.replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)

    # Standardize line breaks
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse multiple consecutive horizontal spaces/tabs to a single space
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    # Collapse more than 2 consecutive newlines into 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip()


class ExtractedContent(BaseModel):
    """Structured container for content extracted from a file."""

    file_path: str
    text: str = ""
    char_count: int = 0
    is_truncated: bool = False
    is_valid: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class BaseExtractor:
    """Abstract interface for file content extractors."""

    def extract(self, file_path: Path, max_chars: int = 12000) -> ExtractedContent:
        """Extract bounded representative content from target file."""
        raise NotImplementedError
