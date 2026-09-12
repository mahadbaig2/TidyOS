"""OpenAI integration wrapper for document and vision understanding with 100% offline fallback."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dataclasses import dataclass
from pydantic import BaseModel, Field, model_validator

from tidyos.config import config

logger = logging.getLogger(__name__)


class AIProviderConfig(BaseModel):
    """Configuration container for an AI provider (OpenAI or OpenRouter)."""

    provider: str = Field(default="openai")  # "openai" or "openrouter"
    api_key: Optional[str] = None
    model: str = Field(default="gpt-4o-mini")
    base_url: Optional[str] = None

    @model_validator(mode="after")
    def set_openrouter_defaults(self) -> "AIProviderConfig":
        if self.provider and self.provider.lower() == "openrouter" and not self.base_url:
            self.base_url = "https://openrouter.ai/api/v1"
        return self


def get_active_ai_config(repository: Optional[Any] = None) -> AIProviderConfig:
    """Resolve active AI provider configuration from database preferences or environment variables."""
    provider = "openai"
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

    if repository and hasattr(repository, "get_preference"):
        pref_provider = repository.get_preference("ai_provider")
        if pref_provider:
            provider = pref_provider.lower().strip()

        pref_key = repository.get_preference(f"{provider}_api_key") or repository.get_preference("ai_api_key")
        if pref_key:
            api_key = pref_key.strip()

        pref_model = repository.get_preference(f"{provider}_model") or repository.get_preference("ai_model")
        if pref_model:
            model = pref_model.strip()

        pref_url = repository.get_preference(f"{provider}_base_url")
        if pref_url:
            base_url = pref_url.strip()

    # Fallback to environment variables if not set in repository preferences
    if not provider:
        provider = (config.ai_provider or "openai").lower().strip()

    if not api_key:
        if provider == "openrouter":
            api_key = config.openrouter_api_key
            model = model or config.openrouter_model
            base_url = base_url or config.openrouter_base_url
        else:
            api_key = config.openai_api_key
            model = model or config.openai_model

    if provider == "openrouter":
        if not base_url:
            base_url = config.openrouter_base_url or "https://openrouter.ai/api/v1"
        if not model:
            model = config.openrouter_model or "openai/gpt-4o-mini"
    else:
        if not model:
            model = config.openai_model or "gpt-4o-mini"

    return AIProviderConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url if provider == "openrouter" else None,
    )


class OpenAIClient:
    """Unified client for OpenAI and OpenRouter LLM/Vision semantic file analysis with offline fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        config_obj: Optional[AIProviderConfig] = None,
        repository: Optional[Any] = None,
    ):
        if config_obj:
            self.provider = config_obj.provider
            self.api_key = config_obj.api_key
            self.model = config_obj.model
            self.base_url = config_obj.base_url
        elif repository:
            active = get_active_ai_config(repository)
            self.provider = (provider or active.provider).lower()
            self.api_key = api_key if api_key is not None else active.api_key
            self.model = model or active.model
            self.base_url = base_url if base_url is not None else active.base_url
        else:
            self.provider = (provider or config.ai_provider or "openai").lower()
            if self.provider == "openrouter":
                self.api_key = api_key if api_key is not None else config.openrouter_api_key
                self.model = model or config.openrouter_model or "openai/gpt-4o-mini"
                self.base_url = base_url or config.openrouter_base_url or "https://openrouter.ai/api/v1"
            else:
                self.api_key = api_key if api_key is not None else config.openai_api_key
                self.model = model or config.openai_model or "gpt-4o-mini"
                self.base_url = base_url

        self._client = None

        if self.api_key and self.api_key.strip():
            try:
                from openai import OpenAI
                client_kwargs: Dict[str, Any] = {"api_key": self.api_key.strip()}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                self._client = OpenAI(**client_kwargs)
            except Exception as e:
                logger.warning("Failed to initialize %s client: %s", self.provider, e)
                self._client = None

    def is_available(self) -> bool:
        """Check if an active client with API key is available."""
        return self._client is not None and bool(self.api_key and self.api_key.strip())

    def test_connection(self) -> Tuple[bool, str]:
        """Verify provider connectivity, API key acceptance, and model reachability.

        Returns:
            Tuple[bool, str]: (is_success, sanitized_message)
        """
        if not self.api_key or not self.api_key.strip():
            return False, "API key is missing"

        if not self._client:
            return False, f"Could not initialize {self.provider} client"

        try:
            # Probe models or ping lightweight endpoint with timeout
            models_page = self._client.models.list(timeout=6.0)
            if self.model:
                if self.provider == "openai":
                    try:
                        self._client.models.retrieve(self.model, timeout=4.0)
                    except Exception as me:
                        me_str = str(me).lower()
                        if "not found" in me_str or "404" in me_str or "does not exist" in me_str:
                            return False, "Model unavailable"
                elif self.provider == "openrouter":
                    try:
                        data = getattr(models_page, "data", None)
                        if data:
                            known_ids = {getattr(m, "id", "") for m in data}
                            if known_ids and not any(self.model.strip().lower() == kid.strip().lower() for kid in known_ids if kid):
                                return False, "Model unavailable"
                    except Exception:
                        pass
            return True, "Connection successful"
        except Exception as e:
            err = str(e).lower()
            if "auth" in err or "401" in err or "invalid" in err or "key" in err or "unauthorized" in err:
                return False, "Invalid API key"
            elif "not found" in err or "404" in err or "model" in err:
                return False, "Model unavailable"
            elif "timeout" in err or "connect" in err or "connection" in err or "timed out" in err:
                return False, "Provider unreachable"
            elif "rate" in err or "429" in err:
                return False, "Rate limit reached"
            else:
                return False, "Connection failed: check network/credentials"

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
            try:
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
            except Exception as fmt_err:
                # If json_object format is not supported by the model (e.g. some OpenRouter models), retry without it
                if "response_format" in str(fmt_err).lower() or "json" in str(fmt_err).lower():
                    response = self._client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": "You are the TidyOS Librarian Agent. You analyze file contents to produce structured semantic understanding. Always respond with valid JSON.",
                            },
                            {"role": "user", "content": prompt + "\n\nImportant: Output ONLY the raw JSON object and nothing else."},
                        ],
                        temperature=0.1,
                        max_tokens=500,
                    )
                else:
                    raise fmt_err

            raw_content = response.choices[0].message.content or "{}"
            # Extract JSON substring if needed
            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            json_str = match.group(0) if match else raw_content
            result = json.loads(json_str)
            result["analysis_source"] = f"{self.provider}_{self.model}"

            # Validate and clamp fields
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.85))))
            if not isinstance(result.get("entities"), list):
                result["entities"] = []
            if not isinstance(result.get("topics"), list):
                result["topics"] = []

            return result
        except Exception as e:
            logger.warning("%s document analysis failed (%s); falling back to local heuristics", self.provider, e)
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
            try:
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
            except Exception as fmt_err:
                # If json_object format is not supported by the vision model, retry without it
                if "response_format" in str(fmt_err).lower() or "json" in str(fmt_err).lower():
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
                                    {"type": "text", "text": prompt + "\n\nOutput ONLY valid raw JSON."},
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
                        temperature=0.1,
                        max_tokens=400,
                    )
                else:
                    raise fmt_err

            raw_content = response.choices[0].message.content or "{}"
            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            json_str = match.group(0) if match else raw_content
            result = json.loads(json_str)
            result["analysis_source"] = f"{self.provider}_vision_{self.model}"
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.85))))
            if not isinstance(result.get("entities"), list):
                result["entities"] = []
            if not isinstance(result.get("topics"), list):
                result["topics"] = []
            return result
        except Exception as e:
            logger.warning("%s vision analysis failed (%s); falling back to local heuristics", self.provider, e)
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
        suggested_folder = ""   # will be resolved from topics if not set explicitly
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

        # -----------------------------------------------------------------------
        # Topic extraction from filename — runs when AI is unavailable.
        # This is the key fallback for descriptive filenames like
        # "Network_Programming_Comprehensive_Answers.pdf".
        # -----------------------------------------------------------------------
        if not topics:
            topics = self._extract_filename_topics(stem, combined_text)

        # Derive suggested_folder from topics when not already set by keyword rules
        if not suggested_folder and topics:
            suggested_folder = self._suggest_folder_from_topics(topics, ext)

        if not suggested_folder:
            suggested_folder = "Documents/Misc"

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

    # -----------------------------------------------------------------------
    # Filename-based topic extraction helpers
    # -----------------------------------------------------------------------

    # Map keyword → (topic_label, folder_path)
    _TOPIC_MAP: List[tuple] = [
        # Computer Science / Technology
        (["network", "networking", "tcp", "udp", "socket", "ip", "protocol", "http", "dns", "osi"], "Network Programming", "Computer Science/Networking"),
        (["machine learning", "ml ", "neural", "deep learning", "cnn", "rnn", "lstm", "transformer", "nlp", "ai ", "artificial intelligence"], "Machine Learning", "Computer Science/AI & ML"),
        (["algorithm", "data structure", "sorting", "graph", "tree", "complexity", "dynamic programming"], "Algorithms", "Computer Science/Algorithms"),
        (["operating system", "os ", "kernel", "process", "thread", "memory management", "scheduling", "deadlock"], "Operating Systems", "Computer Science/Operating Systems"),
        (["database", "sql", "nosql", "mongodb", "postgres", "mysql", "relational", "schema", "query"], "Databases", "Computer Science/Databases"),
        (["security", "cryptography", "encryption", "cybersecurity", "vulnerability", "firewall", "ssl", "tls"], "Cybersecurity", "Computer Science/Security"),
        (["web development", "frontend", "backend", "api", "rest", "graphql", "microservice"], "Web Development", "Development/Web"),
        (["cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops", "ci/cd"], "Cloud & DevOps", "Development/Cloud"),
        (["software engineering", "design pattern", "architecture", "agile", "scrum", "solid", "oop"], "Software Engineering", "Computer Science/Software Engineering"),
        (["computer vision", "image processing", "opencv", "yolo", "segmentation", "detection"], "Computer Vision", "Computer Science/Computer Vision"),
        # Academic
        (["exam", "quiz", "test", "midterm", "final exam", "assignment", "homework", "lab report"], "Academics", "Education/Exams & Assignments"),
        (["lecture", "slides", "course", "tutorial", "study guide", "notes"], "Study Notes", "Education/Notes"),
        (["research", "paper", "thesis", "dissertation", "abstract", "methodology", "literature review"], "Research", "Documents/Research"),
        # Finance
        (["finance", "accounting", "tax", "financial", "budget", "expense", "profit", "loss"], "Finance", "Finance"),
        # Legal
        (["contract", "agreement", "legal", "law", "court", "clause", "party"], "Legal", "Legal"),
        # Health
        (["medical", "health", "prescription", "diagnosis", "hospital", "patient", "clinical"], "Medical", "Health"),
    ]

    def _extract_filename_topics(self, stem: str, combined_text: str) -> List[str]:
        """Extract semantic topic labels from a filename stem and surrounding text."""
        lower = (stem.lower().replace("_", " ").replace("-", " ") + " " + combined_text[:500])
        for keywords, topic_label, _ in self._TOPIC_MAP:
            for kw in keywords:
                if kw in lower:
                    return [topic_label]
        # Fallback: clean up the stem into a topic phrase
        clean = re.sub(r"[_\-]+", " ", stem).strip()
        # Remove generic suffixes
        clean = re.sub(r"\b(comprehensive|answers?|notes?|final|v\d+|\d+)\b", "", clean, flags=re.IGNORECASE).strip()
        if len(clean) > 4:
            return [clean.title()]
        return []

    def _suggest_folder_from_topics(self, topics: List[str], ext: str) -> str:
        """Map extracted topic labels to a folder path."""
        if not topics:
            return "Documents/Misc"
        topic_lower = topics[0].lower()
        for keywords, topic_label, folder in self._TOPIC_MAP:
            if topic_label.lower() == topic_lower:
                return folder
        # Generic: put under Documents/<Topic>
        safe = re.sub(r"[^a-zA-Z0-9 /]", "", topics[0]).strip().title()
        return f"Documents/{safe}" if safe else "Documents/Misc"



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
