"""Demo corpus fixture generator for safe, isolated testing, retrieval evaluation, and demonstration."""

from __future__ import annotations

from pathlib import Path
from typing import Dict
from PIL import Image
import pymupdf


def _create_pdf(file_path: Path, title: str, content: str) -> None:
    """Helper to create a valid searchable PDF with PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"{title}\n\n{content}", fontsize=11)
    doc.set_metadata({"title": title})
    doc.save(str(file_path))
    doc.close()


def _create_image(file_path: Path, width: int = 300, height: int = 200, color: str = "blue") -> None:
    """Helper to create a valid PNG image file."""
    img = Image.new("RGB", (width, height), color=color)
    img.save(str(file_path), format="PNG")


def create_demo_corpus(base_dir: Path | str, include_benchmarks: bool = False) -> Dict[str, Path]:
    """Create an isolated, realistic directory structure for testing and demonstration."""
    root = Path(base_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)

    # 1. Downloads folder with messy typical user files
    downloads = root / "Downloads"
    downloads.mkdir(exist_ok=True)

    # Baseline 4 files expected by Phase 1/2 tests
    _create_pdf(
        downloads / "invoice.pdf",
        title="Acme Corporation Invoice",
        content="Acme Corporation Invoice #10293. Total Due: $1,250.00. Payment due in 30 days.",
    )
    _create_pdf(
        downloads / "document (17).pdf",
        title="Document 17",
        content="Generic document 17 text content.",
    )
    _create_image(downloads / "Screenshot_2026.png", 100, 100, color="gray")
    (downloads / "random_notes.txt").write_text(
        "Quarterly budget estimates and contractor planning notes.",
        encoding="utf-8",
    )

    if include_benchmarks:
        # Benchmark target 1: Hackathon PDF
        _create_pdf(
            downloads / "document_17.pdf",
            title="Agents Everywhere Hackathon Handbook",
            content="Agents Everywhere AI Hackathon Handbook. September 12, 2026 build session. Submission guidelines for local autonomous agents.",
        )

        # Benchmark target 2: Resume
        _create_pdf(
            downloads / "resume_ai_engineer.pdf",
            title="Mirza Mahad Baig - AI Product Engineer Resume",
            content="Mirza Mahad Baig. Senior AI Product Engineer. Experience building LangGraph multi-agent architectures, local semantic search, and PySide6 desktop systems.",
        )

        # Benchmark target 3: Vercel invoice
        _create_pdf(
            downloads / "billing_03.pdf",
            title="Vercel Invoice September 2026",
            content="Vercel Inc. Monthly Pro Plan hosting invoice for September 2026. Total Amount Due: $20.00.",
        )

        # Benchmark target 4: FastAPI CORS screenshot
        _create_image(downloads / "screenshot_fastapi_cors.png", 400, 250, color="darkred")

        # Benchmark target 5: LangGraph notes
        (downloads / "notes_draft.md").write_text(
            "# LangGraph Multi-Agent Architecture\n"
            "Technical notes about LangGraph agents, StateGraph safety routing, and Librarian semantic indexing.",
            encoding="utf-8",
        )

        # Distractor files
        _create_pdf(
            downloads / "aws_billing_march.pdf",
            title="AWS Invoice March 2025",
            content="Amazon Web Services monthly infrastructure bill for March 2025. S3 storage and EC2 compute.",
        )
        _create_pdf(
            downloads / "resume_sales_associate.pdf",
            title="Sales Associate Resume",
            content="Retail customer service representative resume. Inventory management and point of sale.",
        )
        _create_image(downloads / "screenshot_gameplay.png", 300, 200, color="green")
        (downloads / "dinner_recipe_notes.txt").write_text(
            "Spaghetti Carbonara recipe: fresh eggs, guanciale, pecorino romano, black pepper.",
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
    _create_pdf(
        next_public / "invoice.pdf",
        title="Next.js Storefront Invoice Asset",
        content="Acme Corporation invoice asset deployed inside Next.js public directory.",
    )

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
