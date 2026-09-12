"""Librarian Agent: Read-only semantic document and image understanding."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from tidyos.indexing.extractors.composite import ContentExtractor
from tidyos.tools.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class FileUnderstanding(BaseModel):
    """Structured semantic metadata produced by the Librarian Agent."""

    file_path: str
    sha256_hash: str = ""
    document_type: str = "unknown"
    title: str = ""
    summary: str = ""
    entities: List[str] = Field(default_factory=list)
    topics: List[str] = Field(default_factory=list)
    suggested_folder: Optional[str] = None
    confidence: float = 0.0
    extracted_chars: int = 0
    is_truncated: bool = False
    analysis_source: str = "local_heuristic"
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


def compute_file_sha256(file_path: Path | str) -> str:
    """Compute SHA-256 hash of a file in streaming chunks."""
    path = Path(file_path)
    if not path.is_file():
        return ""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class LibrarianAgent:
    """Read-only semantic intelligence agent for analyzing documents and images.

    SAFETY INVARIANT:
    Zero mutation authority. The Librarian inspects and summarizes files, but
    never modifies, moves, renames, or deletes files on the filesystem.
    """

    def __init__(
        self,
        extractor: Optional[ContentExtractor] = None,
        openai_client: Optional[OpenAIClient] = None,
        repository: Optional[Any] = None,
    ):
        self.extractor = extractor or ContentExtractor()
        self.openai_client = openai_client or OpenAIClient()
        self.repository = repository

    def analyze_file(
        self,
        file_path: Path | str,
        path_context: str = "",
        force_refresh: bool = False,
    ) -> FileUnderstanding:
        """Perform semantic understanding on a file with caching and offline fallback."""
        path = Path(file_path).resolve()
        path_str = str(path)

        if not path.exists() or not path.is_file():
            return FileUnderstanding(
                file_path=path_str,
                document_type="missing",
                title=path.name,
                summary=f"File not found: {path_str}",
                confidence=0.0,
                analysis_source="error",
            )

        # 1. Compute SHA-256 hash
        file_hash = compute_file_sha256(path)

        # 2. Check cache in repository if available
        if self.repository and not force_refresh:
            try:
                cached = self.repository.get_file_understanding(path_str, file_hash)
                if cached:
                    logger.debug("Librarian cache hit for %s", path_str)
                    return cached
            except Exception as e:
                logger.debug("Failed to query repository cache: %s", e)

        # 3. Extract content using bounded local extractors
        content = self.extractor.extract(path)
        if not content.is_valid:
            understanding = FileUnderstanding(
                file_path=path_str,
                sha256_hash=file_hash,
                document_type="unsupported",
                title=path.name,
                summary=content.error or "Extraction unsupported or failed",
                confidence=0.0,
                analysis_source="error",
            )
            return understanding

        # 4. Synthesize context
        effective_context = path_context or str(path.parent)

        # 5. Route to Vision or Document understanding
        if "base64" in content.metadata and content.metadata["base64"]:
            # Image analysis
            raw_analysis = self.openai_client.describe_image(
                base64_image=content.metadata["base64"],
                filename=path.name,
                mime_type=content.metadata.get("mime_type", "image/jpeg"),
                path_context=effective_context,
                extracted_text=content.metadata.get("ocr_text", ""),
            )
        else:
            # Document analysis
            raw_analysis = self.openai_client.understand_document(
                extracted_text=content.text,
                filename=path.name,
                path_context=effective_context,
                metadata=content.metadata,
            )

        understanding = FileUnderstanding(
            file_path=path_str,
            sha256_hash=file_hash,
            document_type=raw_analysis.get("document_type", "document"),
            title=raw_analysis.get("title", path.stem),
            summary=raw_analysis.get("summary", ""),
            entities=raw_analysis.get("entities", []),
            topics=raw_analysis.get("topics", []),
            suggested_folder=raw_analysis.get("suggested_folder"),
            confidence=float(raw_analysis.get("confidence", 0.70)),
            extracted_chars=content.char_count,
            is_truncated=content.is_truncated,
            analysis_source=raw_analysis.get("analysis_source", "local_heuristic"),
            analyzed_at=datetime.utcnow(),
        )

        # 6. Save to repository cache if available
        if self.repository:
            try:
                self.repository.save_file_understanding(understanding)
            except Exception as e:
                logger.warning("Failed to save file understanding to repository: %s", e)

        return understanding

    def analyze_batch(
        self,
        file_paths: List[Path | str],
        progress_callback: Optional[Callable[[int, int, FileUnderstanding], None]] = None,
    ) -> List[FileUnderstanding]:
        """Analyze multiple files with progress reporting."""
        results: List[FileUnderstanding] = []
        total = len(file_paths)

        for idx, path in enumerate(file_paths, 1):
            understanding = self.analyze_file(path)
            results.append(understanding)
            if progress_callback:
                try:
                    progress_callback(idx, total, understanding)
                except Exception as e:
                    logger.warning("Progress callback raised exception: %s", e)

        return results
