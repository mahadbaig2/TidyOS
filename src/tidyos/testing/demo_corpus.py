"""Demo corpus fixture generator for safe, isolated testing and demonstration."""

from __future__ import annotations

from pathlib import Path
from typing import Dict


# Minimal valid 1x1 transparent PNG bytes
TINY_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Minimal valid PDF bytes
DUMMY_PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n162\n%%EOF\n"
)


def create_demo_corpus(base_dir: Path | str) -> Dict[str, Path]:
    """Create an isolated, realistic directory structure for testing and demonstration.

    Returns a dictionary mapping section names to their created Path objects.
    """
    root = Path(base_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # 1. Downloads folder with messy typical user files
    downloads = root / "Downloads"
    downloads.mkdir(exist_ok=True)

    # Identical invoice in Downloads (Safe to organize)
    (downloads / "invoice.pdf").write_bytes(DUMMY_PDF_BYTES)
    (downloads / "document (17).pdf").write_bytes(DUMMY_PDF_BYTES)
    (downloads / "Screenshot_2026.png").write_bytes(TINY_PNG_BYTES)
    (downloads / "random_notes.txt").write_text(
        "Quarterly budget estimates and contractor planning notes.",
        encoding="utf-8",
    )

    # 2. Documents folder with typical categories
    documents = root / "Documents"
    documents.mkdir(exist_ok=True)
    (documents / "Finance").mkdir(exist_ok=True)
    (documents / "Work").mkdir(exist_ok=True)

    # 3. Structured project: Next.js + Git repository
    projects = root / "Projects"
    next_demo = projects / "next-demo"
    next_demo.mkdir(parents=True, exist_ok=True)

    (next_demo / ".git").mkdir(exist_ok=True)
    (next_demo / "package.json").write_text(
        '{\n  "name": "next-demo",\n  "version": "0.1.0",\n  "dependencies": {\n    "next": "^14.2.0"\n  }\n}\n',
        encoding="utf-8",
    )
    (next_demo / "next.config.ts").write_text(
        'import type { NextConfig } from "next";\nconst nextConfig: NextConfig = {};\nexport default nextConfig;\n',
        encoding="utf-8",
    )
    (next_demo / "app").mkdir(exist_ok=True)
    next_public = next_demo / "public"
    next_public.mkdir(exist_ok=True)
    # Identical invoice inside public/ of Next.js project (Protected from mutation)
    (next_public / "invoice.pdf").write_bytes(DUMMY_PDF_BYTES)

    # 4. Structured project: Python codebase
    python_demo = projects / "python-demo"
    python_demo.mkdir(parents=True, exist_ok=True)
    (python_demo / "pyproject.toml").write_text(
        '[project]\nname = "fastapi-service"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (python_demo / "requirements.txt").write_text(
        "fastapi>=0.110.0\nuvicorn>=0.28.0\n",
        encoding="utf-8",
    )
    (python_demo / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n",
        encoding="utf-8",
    )

    return {
        "root": root,
        "downloads": downloads,
        "documents": documents,
        "projects": projects,
        "next_demo": next_demo,
        "python_demo": python_demo,
    }

