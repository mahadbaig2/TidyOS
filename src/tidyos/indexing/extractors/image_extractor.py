"""Image metadata and payload extractor for vision analysis."""

from __future__ import annotations

import base64
import io
import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from tidyos.indexing.extractors.base import BaseExtractor, ExtractedContent

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tiff",
}

MIME_TYPE_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".gif": "image/gif",
    ".tiff": "image/tiff",
}


class ImageExtractor(BaseExtractor):
    """Extracts dimensions, format metadata, and bounded base64 payload from images."""

    def __init__(self, max_dimension: int = 1024):
        self.max_dimension = max_dimension

    def extract(self, file_path: Path, max_chars: int = 12000) -> ExtractedContent:
        path = Path(file_path)
        if not path.exists():
            return ExtractedContent(
                file_path=str(path),
                is_valid=False,
                error="File does not exist",
            )

        ext = path.suffix.lower()
        mime_type = MIME_TYPE_MAP.get(ext, "image/jpeg")

        try:
            with Image.open(path) as img:
                orig_width, orig_height = img.size
                img_format = img.format or ext.lstrip(".").upper()
                img_mode = img.mode

                # Prepare bounded base64 payload for vision
                # If image is larger than max_dimension, downscale for efficient LLM processing
                w, h = orig_width, orig_height
                needs_resize = max(w, h) > self.max_dimension

                processed_img = img
                if needs_resize:
                    scale = self.max_dimension / max(w, h)
                    new_w = max(1, int(w * scale))
                    new_h = max(1, int(h * scale))
                    processed_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

                # Ensure RGB for saving to JPEG/PNG buffer
                if processed_img.mode in ("RGBA", "P") and ext in (".jpg", ".jpeg"):
                    processed_img = processed_img.convert("RGB")

                buffer = io.BytesIO()
                save_fmt = "PNG" if ext == ".png" else "JPEG"
                if processed_img.mode == "RGBA" and save_fmt == "JPEG":
                    save_fmt = "PNG"
                
                processed_img.save(buffer, format=save_fmt)
                b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

                metadata = {
                    "width": orig_width,
                    "height": orig_height,
                    "format": img_format,
                    "mode": img_mode,
                    "mime_type": mime_type,
                    "base64": b64_data,
                    "resized_for_vision": needs_resize,
                }

                summary_text = (
                    f"Image: {path.name} | Dimensions: {orig_width}x{orig_height} | Format: {img_format}"
                )

                return ExtractedContent(
                    file_path=str(path),
                    text=summary_text,
                    char_count=len(summary_text),
                    is_truncated=False,
                    is_valid=True,
                    metadata=metadata,
                )

        except Exception as e:
            logger.warning("Failed to extract image %s: %s", path, e)
            return ExtractedContent(
                file_path=str(path),
                text="",
                char_count=0,
                is_valid=False,
                error=f"Image extraction error: {e}",
            )
