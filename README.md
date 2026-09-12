# TidyOS

**Your filesystem, intelligently organized.**

> *"Your files organize themselves, and you find them by what you remember, not where you put them."*

TidyOS is a local-first autonomous filesystem agent that understands, organizes, and retrieves your files while knowing what it must never touch.

---

## The Problem

People remember what files **mean**, not where they saved them.

Every day, downloads folders fill up with cryptic names (`document (17).pdf`, `Screenshot_20260912.png`, `resume_final_3.pdf`). Traditional file managers require constant manual upkeep, while cloud-sync tools simply mirror the mess without understanding it.

Meanwhile, autonomous AI agents that touch files directly are notoriously dangerous: an agent that misunderstands a developer workspace can delete build artifacts or break software projects.

---

## What TidyOS Does

- **Understands Content & Multimodal Assets**: Extracts text from PDFs, DOCX, text files, and images (OCR + Vision) to understand file semantics, document types, entities, and dates.
- **Natural Language Semantic Search**: Finds files by human memory ("Find the PDF about the agent hackathon I'm attending today" or "Find the screenshot where FastAPI had the CORS error") using hybrid vector retrieval and SQLite FTS5.
- **Safely Organizes Files**: Proposes concise, informative filenames (`Vercel_Invoice_September_2026.pdf`) and routes files into existing folder hierarchies.
- **Protects Structured Environments**: Automatically detects and locks software repositories (Next.js, Python, Git, Node).
- **Watches for New Files**: Monitors approved intake folders in the background and stabilizes downloads before processing.
- **Audit Ledger & 1-Click Rollback**: Every move is recorded in a local SQLite ledger and can be completely reversed with a single click on **Undo**.

---

## Why TidyOS Is Different: "The Filesystem is the Agent's Environment"

Most AI knowledge and desktop systems follow a simple pipeline:
$$\text{INGEST} \longrightarrow \text{INDEX} \longrightarrow \text{RETRIEVE} \longrightarrow \text{ANSWER}$$

TidyOS operates as an active environment agent:
$$\text{OBSERVE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{REASON} \longrightarrow \text{SAFELY ACT} \longrightarrow \text{REMEMBER}$$

### The Environmental Contrast Invariant

A file cannot be safely understood from its contents alone. Its surrounding directory structure fundamentally dictates what an autonomous agent is allowed to do.

| File Location | Classification | Agent Behavior |
|---|---|---|
| `Downloads/invoice.pdf` | **SAFE INTAKE** | TidyOS understands the invoice, matches existing folders (`Documents/Finance/Invoices/Vercel`), proposes renaming, and reorganizes it safely. |
| `Projects/storefront/public/invoice.pdf` | **PROTECTED PROJECT** | TidyOS indexes the file for semantic search, but `SafetyPolicy` **strictly forbids** moving or renaming it because it is a runtime asset inside a Next.js application. |

**The same file produces a different action depending on its environment.**

---

## Core Safety Invariant: Probabilistic Intelligence, Deterministic Authority

- **AI proposes, deterministic software authorizes.**
- LLMs (OpenAI / OpenRouter) and local heuristics are used for probabilistic understanding, classification, and naming.
- An LLM has **zero mutation authority**.
- All physical filesystem mutations are gated by `SafetyPolicy` and executed exclusively through `MutationService`.
- **Fail-Closed Guarantee**: Missing permissions, ambiguous boundaries, destination collisions, and system folders unconditionally result in rejection (`DENY`). Permanent file deletion is strictly disabled.

---

## Architecture

```mermaid
flowchart TD
    FS[Filesystem Events] --> Watcher[FilesystemWatcher<br/>watchdog + debounce]
    FS --> Scanner[FilesystemScanner<br/>Read-only recursive]
    Watcher --> Pipe[PipelineOrchestrator]
    Scanner --> Pipe

    subgraph Intelligence ["Probabilistic Intelligence"]
        Pipe --> Guardian[Guardian Agent<br/>Environment & Boundary Analysis]
        Guardian -->|SAFE| Librarian[Librarian Agent<br/>PDF/DOCX/OCR/Vision]
        Guardian -->|PROTECTED| ReadOnlyIdx[Index Metadata Only<br/>NEVER TOUCH]
        Librarian --> Organizer[Organizer Agent<br/>Zero Mutation Authority<br/>Existing-Structure Matching]
    end

    subgraph Authority ["Deterministic Authority"]
        Organizer --> SafetyPol[SafetyPolicy<br/>Pre-Mutation Validation]
        SafetyPol -->|Review Mode| RevQueue[Review Queue<br/>SQLite review_queue]
        SafetyPol -->|Auto Mode| MutService[MutationService<br/>Atomic Physical Move]
        RevQueue -->|User Approves| MutService
        MutService --> Ledger[Audit Ledger<br/>action_records Table]
        MutService --> SyncIndex[FTS5 + Vector Sync<br/>Updates Path Dynamically]
        Ledger -->|Undo Triggered| Rollback[Atomic Rollback<br/>Restores File & Search Index]
    end

    subgraph Search ["Hybrid Retrieval"]
        Query[Natural Language Search Query] --> SearchAgent[Search Agent]
        SearchAgent --> Hybrid[HybridRetriever<br/>Vector Similarity + SQLite FTS5]
        Hybrid --> Results[Ranked Result Cards<br/>Open / Show in Folder]
    end
```

---

## Technology Stack

- **Desktop Framework**: PySide6 (Qt for Python), custom dark-mode theme
- **Agent Orchestration**: LangGraph, Pydantic v2
- **Language Models**: OpenAI Python SDK with dual provider support (OpenAI + OpenRouter) and 100% offline heuristic fallback
- **Content Extractors**: PyMuPDF (`pymupdf`), `python-docx`, Pillow (`PIL`), Windows OCR / local vision fallback
- **Search & Storage**: SQLite with FTS5 virtual tables, ONNX Runtime for local vector embeddings, NumPy vector cosine ranking
- **Filesystem & Continuous Intake**: `watchdog` (threaded observer), `pathlib`, `shutil`

---

## Running Locally

### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.12 (64-bit)

### Setup & Launch

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/mahadbaig2/TidyOS.git
   cd TidyOS
   ```

2. **Set up virtual environment**:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Run tests**:
   ```powershell
   pytest
   ```

4. **Launch TidyOS**:
   ```powershell
   python -m tidyos.main
   ```

---

## 2-Minute Hero Demo Walkthrough

To experience the complete end-to-end demo:

1. **Reset Demo Environment**:
   ```powershell
   python scripts/reset_demo.py
   ```
   This creates an isolated, repeatable sandbox in `TidyOS_Demo/` containing four benchmark files and a protected Next.js project.

2. **Launch TidyOS**:
   ```powershell
   python -m tidyos.main
   ```

3. **First-Run Onboarding**:
   - The **Welcome Screen** greets you. Click **Get Started**.
   - Select approved folders (`Downloads`, `Documents`, `Projects`) and click **Analyze My Files**.
   - Watch real, stage-based background progress without any UI freezing.
   - The **Workspace Summary** highlights:
     - Real indexed metrics
     - **PROTECTED ENVIRONMENT: storefront (Next.js project)**
   - Click **Review Cleanup Plan** to enter **Fix My Mess**.

4. **Fix My Mess (Controlled Agency)**:
   - Notice proposal: `document (17).pdf` $\rightarrow$ `Vercel_Invoice_September_2026.pdf` targeting `Documents/Finance/Invoices/Vercel`.
   - Click **Approve Move**. TidyOS physically moves and renames the file on disk.
   - Click **Open TidyOS**.

5. **Search by Meaning**:
   - In Search, enter: `"Find the Vercel invoice from September."`
     $\rightarrow$ Returns the file at its **new destination**.
   - In Search, enter: `"Find the PDF about the agent hackathon I'm attending today."`
     $\rightarrow$ Returns `document_42.pdf` as **Rank #1**.
   - In Search, enter: `"Find the screenshot where FastAPI had the CORS error."`
     $\rightarrow$ Returns `Screenshot_20260912.png` as **Rank #1**.
   - In Search, enter: `"Find my latest AI Product Engineering resume."`
     $\rightarrow$ Returns `resume_final_3.pdf` as **Rank #1**.

6. **Environmental Contrast**:
   - Search: `"storefront invoice"`
     $\rightarrow$ Returns `storefront/public/invoice.pdf` flagged as `🛡️ Protected Project`.
   - Attempting to reorganize this file is blocked by `SafetyPolicy`.

7. **Instant Undo**:
   - Go to **Activity**. Click **[ Undo ]** on the Vercel invoice move.
   - The file is immediately restored to `Downloads/document (17).pdf`.
   - Searching again immediately reflects the restored original path.

---

## Hackathon Disclosure

- **Pre-Hackathon Baseline**: Prior to the hackathon, work on this repository consisted of architecture research, design documentation, PRD planning, and a base PySide6 UI mockup interface with placeholder layouts.
- **Hackathon Deliverables**: All functional agents (Guardian, Librarian, Organizer, Search Agent), deterministic safety policy, content extractors (PDF, DOCX, Image/OCR), hybrid search engine (SQLite FTS5 + ONNX Runtime embeddings), continuous background Watch Mode, physical mutation engine, audit ledger, and full Undo restoration were designed, implemented, and verified entirely during the hackathon.
