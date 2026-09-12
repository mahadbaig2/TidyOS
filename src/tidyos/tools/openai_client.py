"""OpenAI integration wrapper for document and vision understanding with 100% offline fallback."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from tidyos.config import config

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI LLM and Vision semantic file analysis with deterministic local fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or config.openai_api_key
        self.model = model
        self._client = None

        if self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client: %s", e)
                self._client = None

    def is_available(self) -> bool:
        """Check if an active OpenAI client with API key is available."""
        return self._client is not None and bool(self.api_key and self.api_key.strip())

    def understand_document(
        self,
        extracted_text: str,
        filename: str,
        path_context: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate structured semantic understanding for a document.

        Falls back gracefully to local heuristic analysis if API key is missing
        or an API error occurs.
        """
        metadata = metadata or {}

        if not self.is_available():
            return self._heuristic_document_analysis(extracted_text, filename, path_context, metadata)

        prompt = (
            f"Analyze the following document and return a JSON object summarizing it.\n"
            f"Filename: {filename}\n"
            f"Surrounding Path Context: {path_context}\n"
            f"Known Metadata: {json.dumps(metadata)}\n\n"
            f"Extracted Text Content:\n{extracted_text[:6000]}\n\n"
            f"Respond with a JSON object with keys:\n"
            f"- 'document_type': string (e.g. invoice, report, meeting_notes, source_code, documentation, contract, resume, receipt, data, article, presentation, other)\n"
            f"- 'title': string (concise, professional title)\n"
            f"- 'summary': string (1-2 sentences summarizing document purpose and key info)\n"
            f"- 'entities': list of strings (companies, people, projects, products mentioned)\n"
            f"- 'topics': list of strings (key subject matter topics)\n"
            f"- 'suggested_folder': string (logical destination folder path, e.g. 'Finance/Invoices')\n"
            f"- 'confidence': float (between 0.0 and 1.0)\n"
        )

        try:
            assert self._client is not None
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are the TidyOS Librarian Agent. You analyze file contents to produce structured semantic understanding. Always respond with valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=500,
            )
            raw_content = response.choices[0].message.content or "{}"
            result = json.loads(raw_content)
            result["analysis_source"] = f"openai_{self.model}"

            # Validate and clamp fields
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.85))))
            if not isinstance(result.get("entities"), list):
                result["entities"] = []
            if not isinstance(result.get("topics"), list):
                result["topics"] = []

            return result
        except Exception as e:
            logger.warning("OpenAI document analysis failed (%s); falling back to local heuristics", e)
            return self._heuristic_document_analysis(extracted_text, filename, path_context, metadata)

    def describe_image(
        self,
        base64_image: str,
        filename: str,
        mime_type: str = "image/jpeg",
        path_context: str = "",
        extracted_text: str = "",
    ) -> Dict[str, Any]:
        """Describe and classify an image using OpenAI Vision.

        Falls back gracefully to local heuristic image analysis if API key is missing
        or an API error occurs.
        """
        if not self.is_available() or not base64_image:
            return self._heuristic_image_analysis(filename, path_context, extracted_text)

        prompt = (
            f"Analyze this image file named '{filename}' (path: {path_context}).\n"
            f"Determine what it depicts (e.g. screenshot of code/UI, receipt/invoice, diagram/chart, personal photo, artwork, infographic, error log).\n"
            f"Respond with a JSON object with keys:\n"
            f"- 'document_type': string (e.g. screenshot, receipt, diagram, chart, mockup, photo, artwork)\n"
            f"- 'title': string (descriptive title of what the image shows)\n"
            f"- 'summary': string (1-2 sentences describing image contents, visible text, or purpose)\n"
            f"- 'entities': list of strings (visible brands, products, software, or text items)\n"
            f"- 'topics': list of strings (categories or themes)\n"
            f"- 'suggested_folder': string (e.g. 'Pictures/Screenshots', 'Finance/Receipts', 'Design/Mockups')\n"
            f"- 'confidence': float (between 0.0 and 1.0)\n"
        )

        try:
            assert self._client is not None
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are the TidyOS Librarian Vision Agent. You analyze images to extract visual and semantic metadata. Always respond with valid JSON.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}",
                                    "detail": "low",
                                },
                            },
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=400,
            )
            raw_content = response.choices[0].message.content or "{}"
            result = json.loads(raw_content)
            result["analysis_source"] = f"openai_vision_{self.model}"
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.85))))
            if not isinstance(result.get("entities"), list):
                result["entities"] = []
            if not isinstance(result.get("topics"), list):
                result["topics"] = []
            return result
        except Exception as e:
            logger.warning("OpenAI vision analysis failed (%s); falling back to local heuristics", e)
            return self._heuristic_image_analysis(filename, path_context, extracted_text)

    # --------------------------------------------------------------------------
    # Deterministic Heuristic Fallbacks (100% Offline, Zero Crashes)
    # --------------------------------------------------------------------------

    def _heuristic_document_analysis(
        self,
        text: str,
        filename: str,
        path_context: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Fast, 100% offline local heuristic semantic analysis."""
        stem = Path(filename).stem
        ext = Path(filename).suffix.lower()
        lower_text = text.lower()
        combined_text = f"{stem.lower()} {path_context.lower()} {lower_text[:2000]}"

        # Check metadata title first
        title = metadata.get("title")
        if not title:
            # Look for markdown header # Title
            header_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            if header_match:
                title = header_match.group(1).strip()
            else:
                # Format file stem nicely
                title = re.sub(r"[_\-]+", " ", stem).title()

        # Classify document type and suggested folder
        doc_type = "document"
        suggested_folder = "Documents"
        topics: List[str] = []
        entities: List[str] = []

        if any(k in combined_text for k in ["invoice", "receipt", "bill", "payment due", "amount due", "subtotal"]):
            doc_type = "invoice" if "invoice" in combined_text else "receipt"
            suggested_folder = "Finance/Invoices"
            topics.extend(["finance", "billing"])
        elif any(k in combined_text for k in ["resume", "curriculum vitae", "work experience", "education", "skills"]):
            doc_type = "resume"
            suggested_folder = "Documents/Career"
            topics.extend(["career", "resume"])
        elif any(k in combined_text for k in ["meeting notes", "action items", "agenda", "minutes of meeting"]):
            doc_type = "meeting_notes"
            suggested_folder = "Documents/Notes"
            topics.extend(["notes", "meeting"])
        elif ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".c", ".cpp", ".h", ".html", ".css"]:
            doc_type = "source_code"
            suggested_folder = "Development/Source"
            topics.extend(["code", "software"])
        elif ext in [".csv", ".tsv", ".json"]:
            doc_type = "data"
            suggested_folder = "Documents/Data"
            topics.extend(["data"])
        elif ext in [".md", ".txt", ".markdown"]:
            doc_type = "notes"
            suggested_folder = "Documents/Notes"
            topics.extend(["notes"])

        # Extract entities from metadata or uppercase patterns
        if metadata.get("author"):
            entities.append(str(metadata["author"]))

        found_orgs = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Inc|Corp|LLC|Ltd|Technologies|Company)\b", text[:2000])
        for org in found_orgs[:3]:
            if org not in entities:
                entities.append(org)

        # Summary generation
        summary = ""
        if text.strip():
            # First 1-2 lines or sentences
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            summary_candidate = " ".join(lines[:2])
            if len(summary_candidate) > 200:
                summary_candidate = summary_candidate[:197] + "..."
            summary = summary_candidate
        else:
            summary = f"{doc_type.title()} file: {filename}"

        return {
            "document_type": doc_type,
            "title": title or filename,
            "summary": summary,
            "entities": entities,
            "topics": topics,
            "suggested_folder": suggested_folder,
            "confidence": 0.70,
            "analysis_source": "local_heuristic",
        }

    def _heuristic_image_analysis(
        self,
        filename: str,
        path_context: str,
        extracted_text: str = "",
    ) -> Dict[str, Any]:
        """Offline heuristic analysis for images based on OCR text, filename, and directory context."""
        stem = Path(filename).stem
        lower_name = stem.lower()
        lower_path = path_context.lower()
        lower_text = (extracted_text or "").lower()

        clean_title = re.sub(r"[_\-]+", " ", stem).title()
        summary = ""
        entities: List[str] = []
        topics: List[str] = []

        # 1. OCR-driven classification (highest confidence)
        if extracted_text and len(extracted_text.strip()) > 15:
            # Extract meaningful lines
            lines = [line.strip() for line in extracted_text.split("\n") if len(line.strip()) > 3]

            # Detect academic/project poster
            if any(k in lower_text for k in ["poster", "fyp", "final project", "final year project", "problem statement", "our solution", "ensemble", "deep convolutional", "analyzer", "methodology", "group members"]):
                doc_type = "poster"
                suggested_folder = "Projects/Posters"
                topics = ["poster", "project", "presentation", "fyp"]
                if "fyp" in lower_text or "final year project" in lower_text or "final project" in lower_text:
                    topics.append("fyp")
            elif any(k in lower_text for k in ["screenshot", "error", "exception", "traceback", "status 500", "status 404", "fastapi", "localhost", "http:"]):
                doc_type = "screenshot"
                suggested_folder = "Pictures/Screenshots"
                topics = ["screenshot"]
                if any(e in lower_text for e in ["error", "exception", "fail"]):
                    topics.append("error")
            elif any(k in lower_text for k in ["receipt", "invoice", "subtotal", "amount paid", "total due", "payment receipt", "balance due"]):
                doc_type = "receipt"
                suggested_folder = "Finance/Receipts"
                topics = ["finance", "receipt"]
            elif any(k in lower_text for k in ["diagram", "flowchart", "architecture", "component"]):
                doc_type = "diagram"
                suggested_folder = "Documents/Diagrams"
                topics = ["diagram"]
            else:
                doc_type = "photo"
                suggested_folder = "Pictures"
                topics = ["image"]

            # Derive headline title from first prominent lines
            if lines:
                # Find line that is not purely an address or tiny label
                prominent_lines = [l for l in lines[:4] if len(l) > 8 and not re.match(r"^\d+$", l)]
                if prominent_lines:
                    clean_title = prominent_lines[0]
                    if len(clean_title) > 65:
                        clean_title = clean_title[:62] + "..."

            # Extract recognized entities
            found_caps = re.findall(r"\b[A-Z][a-zA-Z0-9_\-]{2,}\b", extracted_text[:1000])
            for cap in found_caps[:5]:
                if cap.lower() not in {"file", "text", "image", "the", "and"} and cap not in entities:
                    entities.append(cap)

            snippet = " ".join(lines[:2])
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            summary = f"{doc_type.replace('_', ' ').title()} depicting: {snippet}"
            conf = 0.85
        else:
            # 2. Filename/Path-driven heuristic fallback
            if any(k in lower_name for k in ["screenshot", "screen shot", "snip", "captur"]):
                doc_type = "screenshot"
                suggested_folder = "Pictures/Screenshots"
                topics = ["screenshot"]
            elif any(k in lower_name for k in ["receipt", "invoice"]):
                doc_type = "receipt"
                suggested_folder = "Finance/Receipts"
                topics = ["finance", "receipt"]
            elif any(k in lower_name for k in ["diagram", "chart", "flowchart", "arch"]):
                doc_type = "diagram"
                suggested_folder = "Documents/Diagrams"
                topics = ["diagram"]
            elif any(k in lower_path for k in ["public", "assets", "static", "images"]):
                doc_type = "web_asset"
                suggested_folder = "Assets"
                topics = ["web_asset"]
            else:
                doc_type = "photo"
                suggested_folder = "Pictures"
                topics = ["image"]

            summary = f"{doc_type.replace('_', ' ').title()} file: {filename}"
            conf = 0.65

        return {
            "document_type": doc_type,
            "title": clean_title,
            "summary": summary,
            "entities": entities,
            "topics": topics,
            "suggested_folder": suggested_folder,
            "confidence": conf,
            "analysis_source": "local_heuristic" if not extracted_text else "local_ocr_heuristic",
        }
