"""TidyOS Demo Environment Reset System (P0).

Prepares a clean, isolated, repeatable demo sandbox in `TidyOS_Demo/`.
Ensures all four hero demo queries and the environmental safety contrast
are guaranteed to succeed without modifying any user personal files.

FAIL CLOSED: Refuses to operate on any directory not named 'TidyOS_Demo'.
"""

import sys
import os
import shutil
from pathlib import Path
import pymupdf
from PIL import Image, ImageDraw, ImageFont

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from tidyos.config import config
from tidyos.storage.repository import StorageRepository
from tidyos.storage.models import DirectoryRecord
from tidyos.safety.protection_manager import ProtectionManager


def make_pdf(path: Path, title: str, lines: list[str]):
    """Create a formatted PDF document using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # A4

    # Title
    page.insert_text((50, 60), title, fontsize=16, fontname="helv", color=(0.1, 0.1, 0.1))

    # Content lines
    y = 100
    for line in lines:
        page.insert_text((50, y), line, fontsize=11, fontname="helv", color=(0.2, 0.2, 0.2))
        y += 24

    doc.save(str(path))
    doc.close()


def make_cors_screenshot(path: Path):
    """Render a realistic IDE/DevTools screenshot featuring the FastAPI CORS error."""
    img = Image.new("RGB", (900, 450), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)

    # Header bar
    draw.rectangle([(0, 0), (900, 35)], fill=(45, 45, 45))
    draw.ellipse([(12, 12), (24, 24)], fill=(237, 106, 94))
    draw.ellipse([(32, 12), (44, 24)], fill=(245, 190, 60))
    draw.ellipse([(52, 12), (64, 24)], fill=(98, 197, 84))
    draw.text((80, 10), "Developer Console - Network & CORS Inspection", fill=(180, 180, 180))

    # Error box
    draw.rectangle([(20, 60), (880, 220)], fill=(40, 20, 20), outline=(180, 50, 50))
    error_text = (
        "Access to fetch at 'http://localhost:8000/api/v1/organize' from origin 'http://localhost:3000'\n"
        "has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.\n\n"
        "FastAPI CORSMiddleware Exception: 403 Forbidden\n"
        "Origin: http://localhost:3000 is not in allow_origins list."
    )
    draw.text((35, 75), error_text, fill=(255, 110, 110))

    # Code context
    draw.rectangle([(20, 240), (880, 420)], fill=(24, 24, 24))
    code_text = (
        "# backend/main.py\n"
        "from fastapi import FastAPI\n"
        "from fastapi.middleware.cors import CORSMiddleware\n\n"
        "app = FastAPI(title='TidyOS API')\n"
        "# Fix required: Add CORSMiddleware with allow_origins=['http://localhost:3000']"
    )
    draw.text((35, 255), code_text, fill=(160, 210, 240))

    img.save(str(path))


def make_distractor_image(path: Path):
    """Render a neutral distractor image."""
    img = Image.new("RGB", (600, 400), color=(240, 240, 235))
    draw = ImageDraw.Draw(img)
    draw.rectangle([(50, 50), (550, 350)], fill=(200, 220, 200), outline=(150, 180, 150))
    draw.text((180, 180), "Team Lunch at Hackathon Cafe", fill=(50, 80, 50))
    img.save(str(path))


def reset_demo(demo_root: Path = None, reset_db: bool = True) -> Path:
    """Perform fail-closed demo reset."""
    if demo_root is None:
        demo_root = PROJECT_ROOT / "TidyOS_Demo"
    demo_root = demo_root.resolve()

    # STRICT FAIL-CLOSED SECURITY INVARIANT:
    # Refuse to touch any folder whose name is not 'TidyOS_Demo'.
    if demo_root.name.lower() != "tidyos_demo":
        raise ValueError(
            f"FAIL CLOSED: Refusing to reset '{demo_root}'. Target directory MUST be named 'TidyOS_Demo'."
        )

    print(f"[*] Resetting TidyOS Demo sandbox at: {demo_root}")

    # 1. Clean existing demo sandbox
    if demo_root.exists():
        try:
            shutil.rmtree(demo_root, ignore_errors=True)
        except Exception as e:
            print(f"[!] Warning cleaning directory: {e}")

    # 2. Re-create directory structure
    downloads = demo_root / "Downloads"
    documents = demo_root / "Documents"
    projects = demo_root / "Projects"
    vercel_folder = documents / "Finance" / "Invoices" / "Vercel"
    storefront = projects / "storefront"
    storefront_public = storefront / "public"
    storefront_app = storefront / "app"

    downloads.mkdir(parents=True, exist_ok=True)
    vercel_folder.mkdir(parents=True, exist_ok=True)
    storefront_public.mkdir(parents=True, exist_ok=True)
    storefront_app.mkdir(parents=True, exist_ok=True)

    # 3. Create Demo Fixtures
    print(" -> Creating Hero Search Fixture 1: Agent Hackathon Guide (document_42.pdf)")
    make_pdf(
        downloads / "document_42.pdf",
        "Agent Hackathon 2026 - Participant Guide",
        [
            "Schedule & Challenges for the AI Agent Hackathon I am attending today.",
            "Challenge 1: Build local AI agents with deterministic safety boundaries.",
            "Challenge 2: Multi-modal content extraction and local semantic search.",
            "Challenge 3: Background event watching with zero user latency.",
            "Event Timeline: Keynote at 10:00 AM, Hacking starts 10:30 AM, Submissions at 5:00 PM.",
            "Room: Silicon Hall - Team Antigravity.",
        ],
    )

    print(" -> Creating Hero Search Fixture 2: AI Product Engineering Resume (resume_final_3.pdf)")
    make_pdf(
        downloads / "resume_final_3.pdf",
        "Alex Chen - AI Product Engineer",
        [
            "Email: alex.chen@example.com | GitHub: github.com/alexchen-ai | Location: San Francisco, CA",
            "Professional Summary:",
            "AI Product Engineer specializing in autonomous agent workflows, LangGraph orchestration,",
            "PySide6 desktop interfaces, and hybrid semantic retrieval systems (FTS5 + ONNX Runtime).",
            "Experience:",
            "- Senior AI Engineer at Cognitive Labs: Designed deterministic safety layers for file manipulation agents.",
            "- Product Engineer at VectorFlow: Optimized embedded vector database inference for local devices.",
            "Education: B.S. in Computer Science, Stanford University.",
            "Technical Skills: Python, PySide6, LangGraph, ONNX Runtime, SQLite FTS5, FastAPI, TypeScript.",
        ],
    )

    print(" -> Creating Hero Search Fixture 3: FastAPI CORS Screenshot (Screenshot_20260912.png)")
    make_cors_screenshot(downloads / "Screenshot_20260912.png")

    print(" -> Creating Hero Search Fixture 4 & Cleanup Target: Vercel Invoice (document (17).pdf)")
    make_pdf(
        downloads / "document (17).pdf",
        "Vercel Inc. Hosting Invoice",
        [
            "Invoice Number: INV-2026-09-8812",
            "Billing Period: September 2026",
            "Customer: Pro Production Team (team_tidyos)",
            "Account ID: acc_vercel_881293",
            "Line Items:",
            "- Serverless Functions Compute: $12.50",
            "- Edge Middleware Requests: $3.50",
            "- Bandwidth & CDN Delivery: $4.00",
            "Total Amount Due: $20.00",
            "Payment Status: Paid in Full on September 12, 2026.",
        ],
    )

    print(" -> Creating Distractor Files (notes.md, photo_lunch.png)")
    (downloads / "notes.md").write_text(
        "# Personal Notes & Errands\n\n"
        "- Pick up dry cleaning on Elm St.\n"
        "- Buy groceries: almond milk, fresh sourdough, organic avocados, coffee beans.\n"
        "- Plan weekend hiking trail around Mount Tamalpais.\n",
        encoding="utf-8",
    )
    make_distractor_image(downloads / "photo_lunch.png")

    print(" -> Creating Protected Next.js Environment (Projects/storefront)")
    (storefront / "package.json").write_text(
        '{\n  "name": "storefront",\n  "version": "1.0.0",\n  "dependencies": {\n    "next": "14.2.3",\n    "react": "18.3.1"\n  }\n}',
        encoding="utf-8",
    )
    (storefront / "next.config.js").write_text(
        "/** @type {import('next').NextConfig} */\nconst nextConfig = { reactStrictMode: true };\nmodule.exports = nextConfig;\n",
        encoding="utf-8",
    )
    (storefront_app / "page.tsx").write_text(
        "export default function Home() {\n  return <main><h1>Storefront E-Commerce App</h1></main>;\n}\n",
        encoding="utf-8",
    )

    # Identical invoice in Next.js public directory (Environmental contrast invariant)
    make_pdf(
        storefront_public / "invoice.pdf",
        "Vercel Inc. Hosting Invoice",
        [
            "Invoice Number: INV-2026-09-8812",
            "Billing Period: September 2026",
            "Customer: Pro Production Team (team_tidyos)",
            "Total Amount Due: $20.00",
            "Public Asset in Storefront Web Application.",
        ],
    )

    # 4. Reset Database State if requested
    if reset_db:
        print(" -> Resetting TidyOS database state and onboarding preferences...")
        repo = StorageRepository(config.database_path)
        repo.clear_all_data()
        repo.set_first_run_completed(False)

        # Pre-seed managed roots pointing to the clean demo folders
        r_down = repo.add_managed_root(str(downloads), mode="REVIEW")
        r_docs = repo.add_managed_root(str(documents), mode="AUTO")
        r_proj = repo.add_managed_root(str(projects), mode="AUTO")

        # Register existing organized folder structure
        repo.upsert_folders([
            DirectoryRecord(
                managed_root_id=r_docs.id,
                path=str(vercel_folder),
                relative_path="Finance/Invoices/Vercel",
                name="Vercel",
            )
        ])

        # Register protected root
        prot_mgr = ProtectionManager(repo)
        prot_mgr.check_and_register_directory(str(storefront))

    print("\n[OK] Demo sandbox successfully prepared!")
    print(f"    Downloads: {downloads}")
    print(f"    Documents: {documents}")
    print(f"    Projects:  {projects}")
    return demo_root


if __name__ == "__main__":
    reset_demo()
