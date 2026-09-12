"""Organizer Agent for TidyOS.

PROBABILISTIC INTELLIGENCE. ZERO MUTATION AUTHORITY.
Answers: "Where should this file belong?"
Advisory only. Proposes safe, structured reorganization plans prioritizing existing organization.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from tidyos.storage.models import DirectoryRecord
from tidyos.storage.repository import StorageRepository
from tidyos.agents.librarian import FileUnderstanding
from tidyos.logging_config import get_logger

logger = get_logger("agents.organizer")

# Windows reserved names and forbidden characters
FORBIDDEN_WIN_CHARS = r'<>:"/\\|?*'
RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_windows_filename(name: str, default_ext: str = "") -> str:
    """Sanitize a candidate string into a valid, safe Windows filename."""
    if not name or not name.strip():
        return f"file_{default_ext.lstrip('.')}" if default_ext else "unnamed_file"

    # Separate existing extension if present
    p = Path(name)
    stem = p.stem
    ext = p.suffix if p.suffix else (f".{default_ext.lstrip('.')}" if default_ext else "")

    # Remove traversal sequences and forbidden characters
    clean_stem = re.sub(r"[<>:\"/\\|?*]", "_", stem)
    # Replace multiple underscores or spaces with single underscore
    clean_stem = re.sub(r"[\s_]+", "_", clean_stem).strip("._ ")

    if not clean_stem:
        clean_stem = "organized_file"

    # Check Windows reserved device names
    if clean_stem.upper() in RESERVED_NAMES:
        clean_stem = f"{clean_stem}_file"

    # Ensure length constraint (max 200 chars for stem)
    clean_stem = clean_stem[:200].rstrip(". ")

    clean_ext = re.sub(r"[<>:\"/\\|?*]", "", ext).lower()
    return f"{clean_stem}{clean_ext}"


class OrganizationProposal(BaseModel):
    """Structured organization proposal produced by OrganizerAgent."""

    file_path: str
    current_filename: str
    proposed_filename: str
    proposed_destination: str  # Destination directory path
    reasoning: str
    confidence: float
    organization_needed: bool = True
    requires_folder_creation: bool = False
    signals_used: List[str] = Field(default_factory=list)

    @property
    def proposed_full_path(self) -> str:
        """Complete target path combining destination and proposed filename."""
        return str(Path(self.proposed_destination) / self.proposed_filename)


def _extract_date_snippet(text: str) -> str:
    """Extract a concise date string from text if present (e.g. September_2026, 2026_09)."""
    if not text:
        return ""
    # Month Name + Year (e.g. September 2026, Sep 2026)
    m = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s_\-,]+(\d{4})\b",
        text,
        re.IGNORECASE,
    )
    if m:
        month = m.group(1).capitalize()
        months_map = {
            "Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April",
            "Jun": "June", "Jul": "July", "Aug": "August", "Sep": "September",
            "Oct": "October", "Nov": "November", "Dec": "December",
        }
        month = months_map.get(month, month)
        year = m.group(2)
        return f"{month}_{year}"

    # ISO date YYYY-MM-DD or YYYY-MM
    m = re.search(r"\b(20\d{2})[_\-](\d{2})(?:[_\-](\d{2}))?\b", text)
    if m:
        if m.group(3):
            return f"{m.group(1)}_{m.group(2)}_{m.group(3)}"
        return f"{m.group(1)}_{m.group(2)}"

    # Year only (e.g. 2026)
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return m.group(1)

    return ""


class OrganizerAgent:
    """Organizer Agent advising file destinations based on semantic understanding and existing folder structures.

    CRITICAL INVARIANT:
    The Organizer Agent has ZERO mutation authority. It produces only immutable
    OrganizationProposal objects that must be authorized by SafetyPolicy and
    executed exclusively by MutationService.
    """

    def __init__(self, repository: Optional[StorageRepository] = None):
        self.repository = repository

    def propose(
        self,
        file_path: str,
        understanding: Optional[FileUnderstanding] = None,
        candidate_roots: Optional[List[str]] = None,
    ) -> OrganizationProposal:
        """Evaluate a file and produce an advisory OrganizationProposal."""
        path_obj = Path(file_path)
        current_filename = path_obj.name
        ext = path_obj.suffix.lower()

        signals: List[str] = []

        # 1. Fetch available existing folder paths for context
        existing_folders = self._get_existing_folders(candidate_roots)

        # 2. Extract semantic signals from understanding
        doc_type = understanding.document_type if understanding else "unknown"
        title = understanding.title if understanding else ""
        entities = understanding.entities if understanding else []
        topics = understanding.topics if understanding else []
        summary = understanding.summary if understanding else ""
        suggested_folder = understanding.suggested_folder if understanding else ""
        lib_conf = understanding.confidence if understanding else 0.5

        if doc_type and doc_type != "unknown":
            signals.append(f"doc_type:{doc_type}")
        if entities:
            signals.append(f"entities:{','.join(entities[:3])}")
        if topics:
            signals.append(f"topics:{','.join(topics[:3])}")

        # 3. Formulate Windows-safe proposed filename prioritizing semantic signals
        proposed_filename = self._generate_filename(
            current_filename=current_filename,
            title=title,
            entities=entities,
            doc_type=doc_type,
            ext=ext,
            signals=signals,
            summary=summary,
            topics=topics,
        )

        # 4. Resolve best destination (Existing Organization First)
        best_dest, requires_creation, match_reason = self._resolve_destination(
            path_obj=path_obj,
            existing_folders=existing_folders,
            doc_type=doc_type,
            entities=entities,
            suggested_folder=suggested_folder,
            candidate_roots=candidate_roots,
            signals=signals,
            topics=topics,
        )

        # 5. Check if organization is actually needed
        dest_path_obj = Path(best_dest)
        is_same_dest = dest_path_obj.resolve() == path_obj.parent.resolve() if path_obj.exists() and dest_path_obj.exists() else str(dest_path_obj).lower() == str(path_obj.parent).lower()
        is_same_name = proposed_filename.lower() == current_filename.lower()
        org_needed = not (is_same_dest and is_same_name)

        # 6. Calculate proposal confidence
        proposal_conf = self._calculate_confidence(
            lib_conf=lib_conf,
            requires_creation=requires_creation,
            has_entities=bool(entities),
            has_doc_type=bool(doc_type and doc_type != "unknown"),
        )

        # 7. Compose detailed reasoning
        reasoning = self._compose_reasoning(
            current_filename=current_filename,
            proposed_filename=proposed_filename,
            doc_type=doc_type,
            entities=entities,
            match_reason=match_reason,
            requires_creation=requires_creation,
        )

        return OrganizationProposal(
            file_path=str(path_obj),
            current_filename=current_filename,
            proposed_filename=proposed_filename,
            proposed_destination=str(dest_path_obj),
            reasoning=reasoning,
            confidence=proposal_conf,
            organization_needed=org_needed,
            requires_folder_creation=requires_creation,
            signals_used=signals,
        )

    # -------------------------------------------------------------------------
    # Internal Heuristics & Resolution
    # -------------------------------------------------------------------------

    def _get_existing_folders(self, candidate_roots: Optional[List[str]] = None) -> List[str]:
        """Fetch discovered existing folders from repository or search nearby folders."""
        folders = []
        if self.repository:
            try:
                db_folders = self.repository.list_folders()
                folders = [f.path for f in db_folders if f.is_present]
            except Exception as e:
                logger.warning("Could not list folders from repository: %s", e)

        # Also inspect candidate root filesystem directly if DB has few folders
        if not folders and candidate_roots:
            for r in candidate_roots:
                rp = Path(r)
                if rp.exists() and rp.is_dir():
                    try:
                        for child in rp.glob("**/*"):
                            if child.is_dir() and not child.name.startswith("."):
                                folders.append(str(child))
                    except Exception:
                        pass
        return folders

    def _generate_filename(
        self,
        current_filename: str,
        title: str,
        entities: List[str],
        doc_type: str,
        ext: str,
        signals: List[str],
        summary: str = "",
        topics: Optional[List[str]] = None,
    ) -> str:
        """Synthesize a concise, informative, Windows-safe semantic filename."""
        cur_p = Path(current_filename)
        cur_stem = cur_p.stem

        generic_pattern = r"^(document|file|download|invoice|untitled|screenshot|scan|image|resume|receipt|paper|presentation|notes)[\s_\-\(\)\d_finalcopyv]*$"

        # Detect generic default filenames (e.g. document (17), resume_final_3, invoice (1), download, image_001)
        is_cur_generic = bool(
            re.search(generic_pattern, cur_stem, re.IGNORECASE)
            or cur_stem.isdigit()
            or len(cur_stem) <= 3
        )

        # 1. If user's existing filename is already specific and non-generic, preserve it
        if not is_cur_generic and len(cur_stem) > 5:
            return sanitize_windows_filename(current_filename, ext)

        # Detect generic titles (e.g. "Document (17)", "Resume Final 3", "Untitled")
        is_title_generic = (
            not title
            or bool(re.search(generic_pattern, title.strip(), re.IGNORECASE))
            or title.strip().lower() in {"untitled", "unknown document", "document", "image", "file", "missing", "resume"}
            or len(title.strip()) <= 3
        )

        # 2. If title is strong, informative, and non-generic, use it directly
        if not is_title_generic:
            clean_title = sanitize_windows_filename(title, ext)
            if len(clean_title) > 5 and not bool(re.search(generic_pattern, Path(clean_title).stem, re.IGNORECASE)):
                signals.append("filename_from_semantic_title")
                return clean_title

        # 3. Synthesize semantic name from Entities + Document Type + Date / Topics
        components: List[str] = []

        # Entity component
        if entities:
            clean_entity = re.sub(r"\s+(?:Inc|Corp|LLC|Ltd|Technologies|Company)\.?$", "", entities[0], flags=re.IGNORECASE).strip()
            clean_entity = re.sub(r"[^\w\s\-]", "", clean_entity).strip()
            clean_entity = re.sub(r"[\s\-]+", "_", clean_entity)
            if clean_entity:
                components.append(clean_entity)
        elif topics:
            clean_topic = re.sub(r"[^\w\s\-]", "", topics[0]).strip().replace(" ", "_").title().replace(" ", "_")
            if clean_topic and clean_topic.lower() not in {"data", "other", "general"}:
                components.append(clean_topic)

        # Document type component
        if doc_type and doc_type not in {"unknown", "data", "document", "other", "missing"}:
            formatted_type = doc_type.replace("_", " ").title().replace(" ", "_")
            if not components or formatted_type.lower() not in components[0].lower():
                components.append(formatted_type)

        # Date component
        date_snip = _extract_date_snippet(f"{title} {summary}")
        if date_snip:
            components.append(date_snip)

        if components:
            signals.append("filename_from_semantic_synthesis")
            synthesized = "_".join(components)
            return sanitize_windows_filename(synthesized, ext)

        # 4. Fallback
        fallback_name = f"{doc_type.capitalize()}_{date_snip}" if doc_type != "unknown" and date_snip else current_filename
        return sanitize_windows_filename(fallback_name, ext)

    def _resolve_destination(
        self,
        path_obj: Path,
        existing_folders: List[str],
        doc_type: str,
        entities: List[str],
        suggested_folder: str,
        candidate_roots: Optional[List[str]],
        signals: List[str],
        topics: Optional[List[str]] = None,
    ) -> Tuple[str, bool, str]:
        """Resolve destination directory preferring existing folder hierarchies.

        Priority:
          1. Existing folder that matches entity (strongest signal)
          2. Existing folder that matches topic keywords
          3. Existing folder that matches document type category
          4. Librarian suggested_folder path under the best managed root
          5. Default doc-type category under best managed root
        """
        best_match = None
        best_score = 0
        match_reason = "Matched existing folder structure"

        normalized_entities = [e.lower().replace(" ", "") for e in (entities or [])]
        normalized_topics = [t.lower() for t in (topics or [])]
        norm_type = doc_type.lower()

        for folder_str in existing_folders:
            f_norm = folder_str.lower().replace("\\", "/")
            score = 0

            # Entity match (strongest — e.g. "Vercel" folder for a Vercel invoice)
            for ent in normalized_entities:
                if ent and len(ent) > 3 and ent in f_norm:
                    score += 50
                    signals.append(f"entity_match:{ent}")

            # Topic keyword match — e.g. "networking", "machine learning", "finance"
            for topic in normalized_topics:
                topic_slug = topic.replace(" ", "").lower()
                topic_words = topic.lower().split()
                # Check full phrase or individual words
                if topic_slug in f_norm.replace("/", "").replace("_", "").replace(" ", ""):
                    score += 35
                    signals.append(f"topic_match:{topic}")
                else:
                    for word in topic_words:
                        if len(word) > 4 and word in f_norm:
                            score += 15

            # Document type match
            if norm_type and norm_type in f_norm:
                score += 30
            elif norm_type == "invoice" and ("finance" in f_norm or "billing" in f_norm):
                score += 25
            elif norm_type == "resume" and ("career" in f_norm or "jobs" in f_norm or "hr" in f_norm):
                score += 25
            elif norm_type == "screenshot" and ("picture" in f_norm or "screenshot" in f_norm or "image" in f_norm):
                score += 25
            elif norm_type in ("textbook", "documentation", "academic_paper", "research") and (
                "book" in f_norm or "doc" in f_norm or "education" in f_norm or "study" in f_norm
            ):
                score += 20

            if score > best_score:
                best_score = score
                best_match = folder_str

        # Strong entity match
        if best_match and best_score >= 50:
            signals.append("existing_folder_exact_match")
            return best_match, False, f"Matched existing folder: {Path(best_match).name}"

        # Good topic / type match
        if best_match and best_score >= 25:
            signals.append("existing_folder_topic_match")
            return best_match, False, f"Matched existing category folder: {Path(best_match).name}"

        # -----------------------------------------------------------------------
        # No strong existing folder match — build a structured path
        # -----------------------------------------------------------------------

        # Find the best managed root to anchor under (prefer one that already
        # contains organised content matching this doc type).
        anchor_root = self._pick_anchor_root(
            path_obj=path_obj,
            candidate_roots=candidate_roots,
            existing_folders=existing_folders,
            doc_type=doc_type,
        )

        # 4. Use Librarian's suggested_folder (the richest signal — includes topic hierarchy)
        if suggested_folder:
            clean_rel = suggested_folder.replace("\\", "/").strip("/")
            # Remove the first component if it duplicates the anchor root basename
            # e.g. anchor=.../Documents, suggested=Documents/Computer Science/Networking
            # → target = .../Documents/Computer Science/Networking  ✓
            anchor_name = Path(anchor_root).name.lower()
            parts = clean_rel.split("/")
            if parts and parts[0].lower() == anchor_name:
                clean_rel = "/".join(parts[1:])  # strip duplicate prefix

            if clean_rel:
                target_dest = Path(anchor_root) / clean_rel
            else:
                target_dest = Path(anchor_root)

            requires_creation = not target_dest.exists()
            signals.append("suggested_folder_used")
            return str(target_dest), requires_creation, f"Topic path '{clean_rel}'"

        # 5. Default categorization based on doc_type
        type_defaults = {
            "invoice": "Finance/Invoices",
            "receipt": "Finance/Receipts",
            "contract": "Legal/Contracts",
            "resume": "Career/Resumes",
            "report": "Documents/Reports",
            "screenshot": "Pictures/Screenshots",
            "photo": "Pictures",
            "source_code": "Projects",
            "documentation": "Documents/Documentation",
            "textbook": "Books/Textbooks",
            "academic_paper": "Documents/Research",
            "research": "Documents/Research",
        }
        rel_cat = type_defaults.get(doc_type, "Documents/Misc")
        target_dest = Path(anchor_root) / rel_cat
        requires_creation = not target_dest.exists()
        signals.append("default_type_path_used")
        return str(target_dest), requires_creation, f"Organized into category '{rel_cat}'"

    def _pick_anchor_root(
        self,
        path_obj: Path,
        candidate_roots: Optional[List[str]],
        existing_folders: List[str],
        doc_type: str,
    ) -> str:
        """Choose the best managed root to place this file under.

        Prefers:
          - A managed root that is NOT the file's current parent (avoid staying in Downloads)
          - A root whose name suggests Documents / organised storage
          - Falls back to the first available candidate root
        """
        if not candidate_roots:
            return str(path_obj.parent)

        current_parent = str(path_obj.parent).lower()

        # Prefer roots that look like organised storage (not intake folders)
        doc_hints = {"documents", "docs", "files", "storage", "organised", "organized", "personal"}
        intake_hints = {"downloads", "desktop", "temp", "tmp", "inbox"}

        scored: List[Tuple[int, str]] = []
        for root in candidate_roots:
            root_lower = root.lower().replace("\\", "/")
            score = 0
            basename = Path(root).name.lower()

            if root_lower == current_parent:
                score -= 20  # penalise staying in the same folder
            if basename in intake_hints:
                score -= 10
            if basename in doc_hints:
                score += 20
            if doc_type in ("screenshot", "photo") and "picture" in root_lower:
                score += 15

            scored.append((score, root))

        # Return the highest-scoring root
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]

    def _calculate_confidence(
        self,
        lib_conf: float,
        requires_creation: bool,
        has_entities: bool,
        has_doc_type: bool,
    ) -> float:
        """Calculate overall proposal confidence."""
        base = lib_conf if lib_conf > 0.0 else 0.8
        if has_doc_type:
            base = max(base, 0.85)
        if has_entities:
            base = min(1.0, base + 0.05)
        if requires_creation:
            base = max(0.6, base - 0.1)  # Lower confidence if new folder must be created
        return round(float(base), 2)

    def _compose_reasoning(
        self,
        current_filename: str,
        proposed_filename: str,
        doc_type: str,
        entities: List[str],
        match_reason: str,
        requires_creation: bool,
    ) -> str:
        """Compose human-readable reasoning explaining why the file should be reorganized."""
        parts = []
        if doc_type and doc_type != "unknown":
            ent_str = f" from {entities[0]}" if entities else ""
            parts.append(f"Identified as {doc_type}{ent_str}.")
        parts.append(match_reason + ".")
        if requires_creation:
            parts.append("Requires creating a new destination folder.")
        if proposed_filename != current_filename:
            parts.append(f"Renaming to descriptive title '{proposed_filename}'.")
        return " ".join(parts)
