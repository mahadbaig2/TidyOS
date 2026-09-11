# PRD.md

# TidyOS — Product Requirements Document

## 1. Product Summary

**TidyOS** is an autonomous, local-first file system agent for Windows.

It addresses two persistent problems:

1. People accumulate chaotic files faster than they can organize them.
2. Even after organizing files, people often cannot remember the exact filename or folder needed to find them again.

TidyOS gives the filesystem an intelligent agent layer. It understands what files are, understands which directory structures must never be disturbed, learns the user's existing organizational patterns, cleans existing clutter, continuously handles new files, and retrieves files by meaning.

### Product promise

> **Your files organize themselves, and you never have to remember where anything is again.**

### Hackathon thesis

Agents should live where work already happens. TidyOS lives in the filesystem itself rather than forcing users to move documents into a chat interface.

The filesystem provides context that a standalone chatbot does not naturally have:
- file paths;
- folder hierarchy;
- existing organizational patterns;
- file metadata;
- project boundaries;
- download events;
- user corrections;
- document contents;
- temporal information;
- actual ability to rename, move, reveal, and open files.

---

## 2. Problem

A typical computer contains:
- `document (17).pdf`
- `resume-final-v2.pdf`
- screenshots with timestamps as names
- invoices scattered across Downloads
- PDFs downloaded for temporary research
- duplicated files
- project assets mixed with personal documents
- years of partially organized folders

The user is currently the routing algorithm:

```text
Download file
  -> inspect it
  -> understand what it is
  -> rename it
  -> decide where it belongs
  -> navigate to folder
  -> move it
  -> later remember where it went
```

This is repetitive cognitive work.

Traditional operating systems provide filename search and folder navigation, but they do not understand the semantic meaning of the user's information.

At the same time, naïve AI organization is dangerous. A system that sees a Next.js repository as "a collection of files" could rename or move `package.json`, source files, assets, or configuration and break the application.

Therefore TidyOS must solve organization and retrieval while also understanding **structural boundaries**.

---

## 3. Goals

### Primary goals
1. Safely understand user-approved areas of the filesystem.
2. Detect structured directories that must not be reorganized.
3. Understand the semantic meaning of supported files.
4. Suggest meaningful filenames.
5. Route files into sensible locations based on existing organization.
6. Clean an existing messy folder through a reviewable first-run plan.
7. Continuously watch intake folders such as Downloads.
8. Automatically process high-confidence new files.
9. Retrieve files through natural-language semantic search.
10. Make every filesystem mutation explainable and reversible.
11. Ship as an installable Windows application with no separate runtime/service installation.

### Secondary goals
- learn lightweight preferences from user corrections;
- provide a clear review queue;
- make protected project detection visible;
- provide an activity history.

---

## 4. Non-Goals for MVP

Do not build:
- permanent file deletion;
- cloud drive synchronization;
- multi-user collaboration;
- a full Windows Explorer replacement;
- email ingestion;
- document chat/RAG answer generation;
- full local LLM inference;
- automatic refactoring of software projects;
- source-code restructuring;
- arbitrary system-wide filesystem access;
- mobile application;
- external database infrastructure.

---

## 5. Target User

Primary MVP user:
- Windows knowledge worker, developer, designer, student, founder, researcher, or professional;
- regularly downloads PDFs, images, documents, resumes, invoices, screenshots, references, and project assets;
- has a messy Downloads/Desktop/Documents structure;
- wants automation but cannot risk AI breaking important files.

---

## 6. Core User Stories

### First-run cleanup
As a user, I want TidyOS to scan folders I explicitly approve and show me how it would organize them before changing anything.

### Structured project protection
As a developer, I want TidyOS to recognize that a Next.js/Python/Git project has meaningful internal structure and must not be reorganized.

### Continuous organization
As a user, when I download a badly named document, I want TidyOS to understand, rename, and route it automatically when confidence is high.

### Review
As a user, when TidyOS is uncertain, I want it to leave the file untouched and ask me.

### Semantic retrieval
As a user, I want to search:
> "the PDF about the agent hackathon"

without knowing the exact filename or folder.

### Explainability
As a user, I want to know why a file was moved.

### Undo
As a user, I want to reverse a TidyOS action.

---

## 7. Product Experience

## 7.1 Onboarding

The user launches TidyOS.

TidyOS explains:
- it only accesses folders the user approves;
- protected software projects will not be reorganized;
- changes are logged and reversible;
- local search/indexing remains on-device;
- OpenAI is used for agent reasoning/vision.

User selects managed folders such as:
- Downloads
- Desktop
- Documents
- Pictures/Screenshots

Each managed root can be:
- **Auto:** high-confidence safe actions may execute automatically;
- **Review:** proposals always require approval.

User may define exclusions.

---

## 7.2 First Scan

TidyOS recursively maps approved roots.

It identifies:
- loose user files;
- folders;
- supported file types;
- project roots;
- protected descendants;
- files eligible for semantic indexing.

Example summary:

```text
1,284 files scanned

211 eligible for organization
1,014 protected/index-only
43 already organized
16 need review
```

No bulk mutation occurs during initial analysis.

---

## 7.3 Directory Structure Intelligence

Every candidate path is classified before mutation.

### SAFE / ORGANIZABLE
Examples:
- Downloads
- Screenshots
- loose PDFs
- normal document collections

May receive organization proposals.

### PROTECTED / STRUCTURED
Examples:
- Git repositories
- Next.js projects
- Node projects
- Python projects
- package-managed directories
- generated/build/tool-controlled directories

No rename/move/reorganization in MVP.

### UNCERTAIN
TidyOS cannot prove the directory is safe.

Remain read-only and require review.

### Next.js requirement

Given:

```text
mahad-ai-portfolio/
├── .git/
├── app/
├── components/
├── public/
├── package.json
├── next.config.ts
├── tsconfig.json
└── pnpm-lock.yaml
```

TidyOS must mark the repository root and descendants as protected.

Even if `public/invoice.pdf` looks like an invoice, TidyOS must not move it.

---

## 8. Multi-Agent System

TidyOS uses **LangGraph** to orchestrate four agents.

## 8.1 Guardian Agent

Purpose:
> What is safe to touch?

Inputs:
- path
- managed root
- deterministic project detector
- project markers
- directory structure

Outputs:
- SAFE / PROTECTED / REVIEW
- project/framework type
- explanation

The Guardian augments the safety experience but does not override deterministic policies.

---

## 8.2 Librarian Agent

Purpose:
> What is this file?

Uses:
- metadata
- extracted document text
- image/screenshot understanding
- parent context
- similar indexed files

Produces:
- file/document type
- semantic title
- entities
- date
- summary
- tags
- category
- confidence

Example:

```json
{
  "file_type": "invoice",
  "title": "Vercel September 2026 Invoice",
  "entities": ["Vercel"],
  "category": "finance",
  "summary": "Monthly Vercel invoice for September 2026.",
  "tags": ["invoice", "Vercel", "hosting", "September 2026"],
  "confidence": 0.97
}
```

---

## 8.3 Organizer Agent

Purpose:
> What should this file be called and where should it live?

Uses:
- Librarian understanding
- current filename/path
- existing folder structure
- candidate destinations
- learned user preferences
- similar files

Produces:

```json
{
  "suggested_filename": "Vercel_Invoice_Sep_2026.pdf",
  "suggested_destination": "Finance/Software/Vercel",
  "confidence": 0.96,
  "reason": "This is a Vercel software invoice and similar invoices are stored under Finance/Software.",
  "requires_review": false
}
```

The output is a proposal. `SafetyPolicy` decides whether it can execute.

---

## 8.4 Search Agent

Purpose:
> Find what the user means, not only what they typed.

Tools:
- semantic search
- FTS5
- filename search
- metadata filters
- file detail lookup
- open file
- reveal in Explorer

Example query:

> "Find the PDF about the agent hackathon I downloaded yesterday."

Interpretation:
- topic: agent hackathon
- file type: PDF
- date: yesterday

Search Agent performs hybrid retrieval and returns ranked file results.

---

## 9. LangGraph Workflows

### File organization graph

```text
FILE EVENT
    |
    v
GUARDIAN
 |       |
protected safe
 |       |
INDEX   LIBRARIAN
          |
          v
      ORGANIZER
          |
          v
    SAFETY POLICY
      /   |   \
   deny review allow
                |
                v
             EXECUTE
                |
                v
              INDEX
```

### Search workflow

```text
USER QUERY
    |
    v
SEARCH AGENT
    |
    +-> semantic search
    +-> full-text search
    +-> filename search
    +-> metadata filters
    |
    v
RANK / INSPECT
    |
    v
RESULTS
```

---

## 10. Semantic Search

Semantic search is a P0 feature and a major demo moment.

### Why
A clean folder hierarchy does not solve memory. Users often remember meaning rather than filenames.

Example queries:
- "the PDF about the agent hackathon"
- "my latest AI resume"
- "the screenshot where FastAPI had a CORS error"
- "the Vercel bill from last month"
- "documents about RAG I downloaded recently"

### Local indexing pipeline

```text
FILE
 -> metadata
 -> text/description extraction
 -> searchable representation
 -> local embedding model
 -> embedding vector
 -> local vector index
 -> SQLite FTS5
```

### Hybrid retrieval

Use:
- semantic similarity;
- FTS relevance;
- filename similarity;
- metadata filters;
- recency when relevant.

A conceptual rank fusion may weight semantic similarity highest, but exact weights can be tuned using the demo corpus.

### Images/screenshots
For screenshots, use multimodal understanding to generate a local description and tags.

Example:
`Screenshot_20260911_192234.png`

becomes semantically indexed as:
> VS Code screenshot showing a FastAPI CORS configuration error.

Search:
> "the FastAPI error screenshot"

can retrieve it.

---

## 11. Continuous Watch Mode

TidyOS monitors approved intake roots using `watchdog`.

It must:
- debounce duplicate events;
- ignore temporary extensions;
- wait for size stability;
- avoid locked/incomplete downloads.

Pipeline:

```text
NEW FILE
 -> stable?
 -> scope?
 -> protected?
 -> understand
 -> index
 -> organize proposal
 -> safety
 -> auto / review / deny
 -> activity
```

High-confidence safe files in an Auto root may execute.

Low-confidence files go to Review.

---

## 12. File Mutation and Undo

All mutations go through one centralized service.

Before mutation:
1. validate source;
2. validate destination;
3. ensure both respect managed-root policy;
4. ensure no protected project is affected;
5. prevent overwrite;
6. persist pending action.

After successful mutation:
- update action status;
- update file path in index;
- retain semantic index association;
- notify UI.

Undo:
- validates inverse operation;
- moves file back;
- updates index;
- marks action reversed.

No permanent delete in MVP.

---

## 13. Local-First Architecture

### Runs locally
- PySide6 UI
- scanner
- watcher
- safety engine
- project detection
- SQLite
- FTS5
- embeddings
- vector similarity
- action ledger
- undo
- file operations

### Uses OpenAI
- LangGraph reasoning
- Librarian semantic understanding
- Organizer reasoning
- image/screenshot understanding
- complex search intent parsing when needed

The app should degrade gracefully when internet/OpenAI is unavailable. Existing search and deterministic filesystem features should remain usable.

---

## 14. Detailed Technology Stack

### Python 3.12
Primary implementation language.

### PySide6 / Qt
Native Windows desktop interface, system tray, dialogs, navigation, background-worker signals.

### LangGraph
Stateful multi-agent orchestration, conditional routing, agent/tool workflows.

### OpenAI Python SDK
LLM and multimodal reasoning.

### Pydantic
Strict structured outputs/contracts for agent decisions.

### pathlib / shutil / os
Native filesystem inspection and safe move/rename operations.

### watchdog
Filesystem event monitoring for Downloads/Screenshots.

### SQLite
Local persistent application database.

### SQLite FTS5
Exact/full-text document retrieval.

### ONNX Runtime
Runs the bundled embedding model locally.

### Compact ONNX embedding model
Generates semantic vectors without requiring an embedding API or Ollama.

### NumPy
Fast local similarity calculations for hackathon-scale vector retrieval.

### PyMuPDF
PDF text extraction.

### python-docx
DOCX text extraction.

### hashlib
Content hashes and future duplicate detection support.

### QThread / QThreadPool
Keep scanning, indexing, AI calls, and embeddings off the UI thread.

### PyInstaller
Bundles Python and application dependencies into a self-contained distributable.

### Inno Setup
Creates `TidyOS-Setup.exe`.

---

## 15. Core Screens

1. **Home**
   - health/status
   - files indexed
   - organized count
   - protected projects
   - review count
   - recent activity

2. **Search**
   - dominant natural-language search
   - ranked semantic results
   - match explanation
   - Open
   - Show in Folder

3. **Organize**
   - first-run scan
   - proposed before/after paths
   - confidence
   - approve/reject

4. **Review**
   - ambiguous decisions
   - choose destination
   - approve/reject

5. **Activity**
   - chronological actions
   - why
   - confidence
   - undo

6. **Settings**
   - managed roots
   - exclusions
   - Auto/Review
   - confidence threshold
   - API configuration
   - watcher pause

---

## 16. Trust Requirements

TidyOS must visibly communicate:
- what it can access;
- what it protected;
- what it changed;
- why it changed it;
- how confident it was;
- how to undo it.

Trust is part of the product, not a settings-page concern.

---

## 17. MVP Success Criteria

A successful MVP can demonstrate:

1. Install and launch as a desktop application.
2. Select a real local directory.
3. Scan and index its contents.
4. Detect a Next.js project and protect it.
5. Understand multiple supported documents.
6. Generate a cleanup plan.
7. Approve safe rename/move actions.
8. Undo a move.
9. Watch Downloads.
10. Process a newly downloaded file.
11. Semantically retrieve a badly named file using natural language.
12. Open/reveal the result.
13. Show an auditable activity trail.

---

## 18. Demo Story

### Beat 1 — Chaos
Show a messy Downloads folder.

### Beat 2 — Understanding
TidyOS scans it and shows:
- eligible files;
- review items;
- protected Next.js project.

### Beat 3 — Organization
Approve a cleanup plan.
The loose files receive meaningful names/locations.
The software project remains untouched.

### Beat 4 — Autonomy
Download a badly named PDF.
TidyOS detects, understands, indexes, renames, and routes it.

### Beat 5 — Retrieval
Search:

> "the PDF about the agent hackathon"

TidyOS finds the correct file instantly despite the user not knowing its name/path.

### Beat 6 — Control
Show "Why?" and Undo.

End:

> **Your files organize themselves, and you never have to remember where anything is again.**
