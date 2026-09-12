"""Document and metadata extractors for TidyOS."""

from tidyos.indexing.extractors.base import (
    BaseExtractor,
    ExtractedContent,
    normalize_extracted_text,
)
from tidyos.indexing.extractors.composite import ContentExtractor
from tidyos.indexing.extractors.docx_extractor import DocxExtractor
from tidyos.indexing.extractors.image_extractor import ImageExtractor
from tidyos.indexing.extractors.pdf_extractor import PdfExtractor
from tidyos.indexing.extractors.text_extractor import TextExtractor

__all__ = [
    "BaseExtractor",
    "ExtractedContent",
    "normalize_extracted_text",
    "ContentExtractor",
    "TextExtractor",
    "PdfExtractor",
    "DocxExtractor",
    "ImageExtractor",
]
