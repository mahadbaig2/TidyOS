# TASKS.md

# TidyOS Hackathon Build Plan

Status convention:
- `[ ]` not started
- `[-]` in progress
- `[x]` complete
- `[!]` blocked

Do not skip milestone gates.

---

# Phase 0 — Foundation

## M0.1 Repository and Environment
- [x] P0.1.1 Create Python 3.12 project and virtual environment
- [x] P0.1.2 Add dependency management
- [x] P0.1.3 Create source package structure
- [x] P0.1.4 Add `.gitignore`, `.env.example`, README stub
- [x] P0.1.5 Add structured logging
- [x] P0.1.6 Add basic pytest setup

### Gate M0.1
- [x] Application imports successfully
- [x] Tests run
- [x] Secrets/build artifacts ignored

## M0.2 PySide6 Shell
- [x] P0.2.1 Create application entry point
- [x] P0.2.2 Create main window
- [x] P0.2.3 Create sidebar navigation
- [x] P0.2.4 Create placeholder Home/Search/Organize/Review/Activity/Settings views
- [x] P0.2.5 Add global theme/QSS
- [x] P0.2.6 Add system tray skeleton

### Gate M0.2
- [x] Native desktop app opens reliably
- [x] Navigation works
- [x] No console dependency for normal launch

---

# Phase 1 — Local Filesystem Core

## M1.1 Managed Roots
- [x] P1.1.1 Implement folder picker
- [x] P1.1.2 Persist approved roots in SQLite
- [x] P1.1.3 Add AUTO / REVIEW mode per root
- [x] P1.1.4 Add exclusions
- [x] P1.1.5 Enforce scope checks

## M1.2 SQLite Schema
- [x] P1.2.1 `managed_roots`
- [x] P1.2.2 `files`
- [x] P1.2.3 `folders`
- [x] P1.2.4 `protected_roots`
- [x] P1.2.5 `actions`
- [x] P1.2.6 `preferences`
- [x] P1.2.7 `review_queue`
- [x] P1.2.8 `file_text`
- [x] P1.2.9 migrations/bootstrap

## M1.3 Scanner
- [x] P1.3.1 Recursive directory scan
- [x] P1.3.2 File metadata extraction
- [x] P1.3.3 MIME/extension handling
- [x] P1.3.4 Stable internal file IDs
- [x] P1.3.5 Background worker implementation
- [x] P1.3.6 Progress signals to UI

### Gate M1
- [x] User can select a demo directory
- [x] TidyOS indexes paths and metadata without moving anything
- [x] UI remains responsive during scan


---

# Phase 2 — Safety and Structured Directory Intelligence

## M2.1 Project Root Detector
- [x] P2.1.1 Detect `.git`
- [x] P2.1.2 Detect Node/package-managed projects
- [x] P2.1.3 Detect Next.js
- [x] P2.1.4 Detect Python projects
- [x] P2.1.5 Detect Docker/project tooling
- [x] P2.1.6 Propagate protection to descendants
- [x] P2.1.7 Record project type and reason

## M2.2 Deterministic SafetyPolicy
- [x] P2.2.1 Deny operations outside managed roots
- [x] P2.2.2 Deny source mutations inside protected roots
- [x] P2.2.3 Deny destinations inside protected roots
- [x] P2.2.4 Prevent overwrites
- [x] P2.2.5 Validate Windows filenames
- [x] P2.2.6 Handle path length/collision cases
- [x] P2.2.7 Fail closed on uncertainty

## M2.3 Guardian Agent
- [x] P2.3.1 Define Guardian structured schema
- [x] P2.3.2 Create LangGraph Guardian node
- [x] P2.3.3 Feed deterministic detector results into Guardian
- [x] P2.3.4 Produce human-readable protection explanation
- [x] P2.3.5 Ensure Guardian cannot override SafetyPolicy

### Gate M2
Create a test folder containing:
- loose PDFs/images
- a Next.js repository
- a Python repository

Pass criteria:
- [x] loose files marked eligible
- [x] Next.js root and descendants protected
- [x] Python root and descendants protected
- [x] attempted protected mutation is rejected
- [x] UI clearly shows protected project badge


**Do not continue to autonomous file movement until this gate passes.**

---

# Phase 3 — Content Understanding and Librarian Agent

## M3.1 Extractors
- [x] P3.1.1 TXT/Markdown extraction
- [x] P3.1.2 PDF extraction with PyMuPDF
- [x] P3.1.3 DOCX extraction
- [x] P3.1.4 Metadata-only fallback
- [x] P3.1.5 Content truncation/minimization strategy

## M3.2 Image Understanding
- [x] P3.2.1 Image file detection
- [x] P3.2.2 OpenAI vision wrapper
- [x] P3.2.3 Screenshot semantic description
- [x] P3.2.4 Tags/subject extraction
- [x] P3.2.5 Graceful offline/failure fallback

## M3.3 Librarian Agent
- [x] P3.3.1 Pydantic `FileUnderstanding` schema
- [x] P3.3.2 LangGraph Librarian node
- [x] P3.3.3 Tool: metadata
- [x] P3.3.4 Tool: extract text
- [x] P3.3.5 Tool: image description
- [x] P3.3.6 Structured type/category/title/entities/date/summary/tags/confidence
- [x] P3.3.7 Persist understanding in SQLite

### Gate M3
- [x] Badly named invoice is understood correctly
- [x] Hackathon PDF is understood correctly
- [x] Resume is understood correctly
- [x] Screenshot receives useful semantic description
- [x] Protected files are not mutated during understanding

---

# Phase 4 — Semantic Search P0

## M4.1 Local Embedding Runtime
- [x] P4.1.1 Select compact embedding model suitable for redistribution
- [x] P4.1.2 Export/obtain ONNX model
- [x] P4.1.3 Bundle tokenizer/assets
- [x] P4.1.4 Implement local inference with ONNX Runtime
- [x] P4.1.5 Normalize embeddings
- [x] P4.1.6 Batch indexing support

## M4.2 Local Vector Index
- [x] P4.2.1 Define embedding storage format
- [x] P4.2.2 Persist file vectors locally
- [x] P4.2.3 Load/cache vector matrix
- [x] P4.2.4 NumPy similarity search
- [x] P4.2.5 Metadata filtering

## M4.3 Full-Text Search
- [x] P4.3.1 Create SQLite FTS5 virtual table
- [x] P4.3.2 Index filename
- [x] P4.3.3 Index extracted text/summary/tags
- [x] P4.3.4 Implement FTS query

## M4.4 Hybrid Retrieval
- [x] P4.4.1 Semantic score
- [x] P4.4.2 FTS score
- [x] P4.4.3 Filename score
- [x] P4.4.4 Metadata/date/type filters
- [x] P4.4.5 Rank fusion
- [x] P4.4.6 Return reason/snippet

## M4.5 Search Agent
- [x] P4.5.1 Define search intent schema
- [x] P4.5.2 LangGraph Search workflow
- [x] P4.5.3 Tool: semantic search
- [x] P4.5.4 Tool: full-text search
- [x] P4.5.5 Tool: filename search
- [x] P4.5.6 Tool: metadata search
- [x] P4.5.7 Tool: file details
- [x] P4.5.8 Tool: open file
- [x] P4.5.9 Tool: reveal in Explorer
- [x] P4.5.10 Parse natural date/type constraints

## M4.6 Search UI
- [x] P4.6.1 Hero search field
- [x] P4.6.2 Search state/loading
- [x] P4.6.3 Result cards
- [x] P4.6.4 Match reason
- [x] P4.6.5 Path/category metadata
- [x] P4.6.6 Open
- [x] P4.6.7 Show in Folder

### Gate M4
Using deliberately poor filenames, queries must successfully retrieve:
- [x] "the PDF about the agent hackathon"
- [x] "my latest AI resume"
- [x] "the screenshot with the FastAPI error"
- [x] an exact phrase via FTS
- [x] a query with file-type/date constraints

**Semantic search is not optional. Do not demote this milestone.**

---

# Phase 5 — Organizer Agent and First-Run Cleanup

## M5.1 Existing Structure Context
- [x] P5.1.1 Build compact folder-tree representation
- [x] P5.1.2 Find relevant candidate destination folders
- [x] P5.1.3 Retrieve learned preferences
- [x] P5.1.4 Prefer existing hierarchy

## M5.2 Organizer Agent
- [x] P5.2.1 Pydantic `OrganizationProposal`
- [x] P5.2.2 LangGraph Organizer node
- [x] P5.2.3 Meaningful filename proposal
- [x] P5.2.4 Destination proposal
- [x] P5.2.5 Confidence
- [x] P5.2.6 Rationale
- [x] P5.2.7 `requires_review`

## M5.3 Review Queue
- [x] P5.3.1 Persist proposed actions
- [x] P5.3.2 Approve
- [x] P5.3.3 Reject
- [x] P5.3.4 Change destination
- [x] P5.3.5 Simple approve / reject actions (scope-cut: no bulk approval needed)

## M5.4 Mutation Service
- [x] P5.4.1 Centralized rename/move service
- [x] P5.4.2 SafetyPolicy integration
- [x] P5.4.3 Pre-action ledger
- [x] P5.4.4 Atomic/error-safe execution where possible
- [x] P5.4.5 Update file index after move
- [x] P5.4.6 Preserve embedding/search association

## M5.5 Undo
- [x] P5.5.1 Inverse move/rename
- [x] P5.5.2 Collision/safety check on undo
- [x] P5.5.3 Mark action reversed
- [x] P5.5.4 Update index/path
- [x] P5.5.5 UI feedback

## M5.6 Cleanup Plan UI
- [x] P5.6.1 Scan summary
- [x] P5.6.2 Safe/protected/review counts
- [x] P5.6.3 Before -> after proposal rows
- [x] P5.6.4 Confidence indicator
- [x] P5.6.5 Why/explanation
- [x] P5.6.6 Approve/reject
- [x] P5.6.7 Execute approved plan

### Gate M5
- [x] First-run scan produces sensible proposals
- [x] Next.js project remains untouched
- [x] User approves proposal
- [x] Files move/rename correctly
- [x] Search still finds moved files
- [x] Undo restores a selected file

---

# Phase 6 — Continuous Agent / Watch Mode

## M6.1 Watchdog
- [x] P6.1.1 Watch approved intake roots
- [x] P6.1.2 Debounce duplicate events
- [x] P6.1.3 Ignore temp extensions
- [x] P6.1.4 File stability check
- [x] P6.1.5 Queue processing

## M6.2 Autonomous New-File Graph
- [x] P6.2.1 Watch event -> Guardian
- [x] P6.2.2 Librarian
- [x] P6.2.3 Index/embed
- [x] P6.2.4 Organizer
- [x] P6.2.5 Policy validation
- [x] P6.2.6 Auto-execute only above configured confidence
- [x] P6.2.7 Otherwise review
- [x] P6.2.8 Persist/log everything

## M6.3 Notifications
- [x] P6.3.1 System tray status
- [x] P6.3.2 Organized-file notification
- [x] P6.3.3 Review-needed notification
- [x] P6.3.4 Quick Undo from app/activity

### Gate M6
Live demo:
- [x] Download poorly named PDF
- [x] TidyOS detects it
- [x] waits until complete
- [x] understands it
- [x] indexes it
- [x] renames/routes it or asks for review
- [x] shows activity
- [x] semantic search finds it immediately

---

# Phase 7 — Product UI and Trust Layer

## M7.1 Home
- [x] P7.1.1 Files indexed
- [x] P7.1.2 Organized count
- [x] P7.1.3 Protected projects
- [x] P7.1.4 Review count
- [x] P7.1.5 Recent activity
- [x] P7.1.6 Watch status

## M7.2 Activity
- [x] P7.2.1 Timeline
- [x] P7.2.2 Before/after paths
- [x] P7.2.3 Agent rationale
- [x] P7.2.4 Confidence
- [x] P7.2.5 Undo
- [x] P7.2.6 Filters

## M7.3 Protected Project UX
- [x] P7.3.1 Shield badge
- [x] P7.3.2 Framework/project label
- [x] P7.3.3 Explanation: "TidyOS will not reorganize this structure"
- [x] P7.3.4 Search-index status

## M7.4 Settings
- [x] P7.4.1 Managed folders
- [x] P7.4.2 Exclusions
- [x] P7.4.3 Auto/review mode
- [x] P7.4.4 Confidence threshold
- [x] P7.4.5 API key handling
- [x] P7.4.6 Pause watcher

### Gate M7
- [x] Product looks coherent and demo-ready
- [x] Safety and autonomy are visible, not hidden implementation details

---

# Phase 8 — Packaging

## M8.1 PyInstaller
- [x] P8.1.1 Create spec file
- [x] P8.1.2 Bundle PySide6
- [x] P8.1.3 Bundle LangGraph/OpenAI dependencies
- [x] P8.1.4 Bundle ONNX Runtime
- [x] P8.1.5 Bundle embedding model/tokenizer
- [x] P8.1.6 Bundle icons/resources
- [x] P8.1.7 Resolve hidden imports
- [x] P8.1.8 Test clean launch

## M8.2 Windows Installer (Optional Hackathon Cut)
- [-] P8.2.1 Inno Setup configuration (Cut per hackathon time prioritization; source and portable builds prioritized)

## M8.3 Clean-Machine Test
- [x] P8.3.1 Test on Windows environment without external database servers
- [x] P8.3.2 Confirm no external Node server required
- [x] P8.3.3 Confirm no DB/vector server required
- [x] P8.3.4 Confirm local embeddings work
- [x] P8.3.5 Confirm OpenAI error is graceful when offline

### Gate M8
- [x] Reliable standalone application execution on Windows

---

# Phase 9 — Hackathon Demo Hardening

## M9.1 Controlled Demo Dataset
- [x] P9.1.1 Create messy Downloads demo folder (`TidyOS_Demo/Downloads`)
- [x] P9.1.2 Add invoices (`document (17).pdf`)
- [x] P9.1.3 Add resumes (`resume_final_3.pdf`)
- [x] P9.1.4 Add hackathon PDF (`document_42.pdf`)
- [x] P9.1.5 Add screenshots (`Screenshot_20260912.png`)
- [x] P9.1.6 Add Next.js project (`Projects/storefront`)
- [x] P9.1.7 Add distractors (`notes.md`, `photo_lunch.png`)
- [x] P9.1.8 Scripted repeatable reset (`scripts/reset_demo.py`)

## M9.2 Demo Sequence
- [x] P9.2.1 Show messy folder
- [x] P9.2.2 Scan & Onboarding
- [x] P9.2.3 Show protected Next.js project
- [x] P9.2.4 Show cleanup plan
- [x] P9.2.5 Approve organization
- [x] P9.2.6 Download new badly named file
- [x] P9.2.7 Show autonomous organization
- [x] P9.2.8 Search "the PDF about the agent hackathon"
- [x] P9.2.9 Open result
- [x] P9.2.10 Undo an action

## M9.3 Reliability
- [x] P9.3.1 Cache/pre-index demo data where appropriate
- [x] P9.3.2 Handle API timeout / offline gracefully
- [x] P9.3.3 Handle locked file
- [x] P9.3.4 Handle duplicate destination (collision prevention)
- [x] P9.3.5 Handle offline state (100% heuristic fallback)
- [ ] P9.3.6 No destructive operations
- [ ] P9.3.7 Repeat full demo at least 3 times

### Final Gate
- [ ] Demo can run end-to-end without manual code intervention
- [ ] Search wow moment works
- [ ] Agent architecture is visible/explainable
- [ ] Safety story is demonstrable
- [ ] Installer works
