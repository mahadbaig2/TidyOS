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
- [ ] P1.1.1 Implement folder picker
- [ ] P1.1.2 Persist approved roots in SQLite
- [ ] P1.1.3 Add AUTO / REVIEW mode per root
- [ ] P1.1.4 Add exclusions
- [ ] P1.1.5 Enforce scope checks

## M1.2 SQLite Schema
- [ ] P1.2.1 `managed_roots`
- [ ] P1.2.2 `files`
- [ ] P1.2.3 `folders`
- [ ] P1.2.4 `protected_roots`
- [ ] P1.2.5 `actions`
- [ ] P1.2.6 `preferences`
- [ ] P1.2.7 `review_queue`
- [ ] P1.2.8 `file_text`
- [ ] P1.2.9 migrations/bootstrap

## M1.3 Scanner
- [ ] P1.3.1 Recursive directory scan
- [ ] P1.3.2 File metadata extraction
- [ ] P1.3.3 MIME/extension handling
- [ ] P1.3.4 Stable internal file IDs
- [ ] P1.3.5 Background worker implementation
- [ ] P1.3.6 Progress signals to UI

### Gate M1
- [ ] User can select a demo directory
- [ ] TidyOS indexes paths and metadata without moving anything
- [ ] UI remains responsive during scan

---

# Phase 2 — Safety and Structured Directory Intelligence

## M2.1 Project Root Detector
- [ ] P2.1.1 Detect `.git`
- [ ] P2.1.2 Detect Node/package-managed projects
- [ ] P2.1.3 Detect Next.js
- [ ] P2.1.4 Detect Python projects
- [ ] P2.1.5 Detect Docker/project tooling
- [ ] P2.1.6 Propagate protection to descendants
- [ ] P2.1.7 Record project type and reason

## M2.2 Deterministic SafetyPolicy
- [ ] P2.2.1 Deny operations outside managed roots
- [ ] P2.2.2 Deny source mutations inside protected roots
- [ ] P2.2.3 Deny destinations inside protected roots
- [ ] P2.2.4 Prevent overwrites
- [ ] P2.2.5 Validate Windows filenames
- [ ] P2.2.6 Handle path length/collision cases
- [ ] P2.2.7 Fail closed on uncertainty

## M2.3 Guardian Agent
- [ ] P2.3.1 Define Guardian structured schema
- [ ] P2.3.2 Create LangGraph Guardian node
- [ ] P2.3.3 Feed deterministic detector results into Guardian
- [ ] P2.3.4 Produce human-readable protection explanation
- [ ] P2.3.5 Ensure Guardian cannot override SafetyPolicy

### Gate M2
Create a test folder containing:
- loose PDFs/images
- a Next.js repository
- a Python repository

Pass criteria:
- [ ] loose files marked eligible
- [ ] Next.js root and descendants protected
- [ ] Python root and descendants protected
- [ ] attempted protected mutation is rejected
- [ ] UI clearly shows protected project badge

**Do not continue to autonomous file movement until this gate passes.**

---

# Phase 3 — Content Understanding and Librarian Agent

## M3.1 Extractors
- [ ] P3.1.1 TXT/Markdown extraction
- [ ] P3.1.2 PDF extraction with PyMuPDF
- [ ] P3.1.3 DOCX extraction
- [ ] P3.1.4 Metadata-only fallback
- [ ] P3.1.5 Content truncation/minimization strategy

## M3.2 Image Understanding
- [ ] P3.2.1 Image file detection
- [ ] P3.2.2 OpenAI vision wrapper
- [ ] P3.2.3 Screenshot semantic description
- [ ] P3.2.4 Tags/subject extraction
- [ ] P3.2.5 Graceful offline/failure fallback

## M3.3 Librarian Agent
- [ ] P3.3.1 Pydantic `FileUnderstanding` schema
- [ ] P3.3.2 LangGraph Librarian node
- [ ] P3.3.3 Tool: metadata
- [ ] P3.3.4 Tool: extract text
- [ ] P3.3.5 Tool: image description
- [ ] P3.3.6 Structured type/category/title/entities/date/summary/tags/confidence
- [ ] P3.3.7 Persist understanding in SQLite

### Gate M3
- [ ] Badly named invoice is understood correctly
- [ ] Hackathon PDF is understood correctly
- [ ] Resume is understood correctly
- [ ] Screenshot receives useful semantic description
- [ ] Protected files are not mutated during understanding

---

# Phase 4 — Semantic Search P0

## M4.1 Local Embedding Runtime
- [ ] P4.1.1 Select compact embedding model suitable for redistribution
- [ ] P4.1.2 Export/obtain ONNX model
- [ ] P4.1.3 Bundle tokenizer/assets
- [ ] P4.1.4 Implement local inference with ONNX Runtime
- [ ] P4.1.5 Normalize embeddings
- [ ] P4.1.6 Batch indexing support

## M4.2 Local Vector Index
- [ ] P4.2.1 Define embedding storage format
- [ ] P4.2.2 Persist file vectors locally
- [ ] P4.2.3 Load/cache vector matrix
- [ ] P4.2.4 NumPy similarity search
- [ ] P4.2.5 Metadata filtering

## M4.3 Full-Text Search
- [ ] P4.3.1 Create SQLite FTS5 virtual table
- [ ] P4.3.2 Index filename
- [ ] P4.3.3 Index extracted text/summary/tags
- [ ] P4.3.4 Implement FTS query

## M4.4 Hybrid Retrieval
- [ ] P4.4.1 Semantic score
- [ ] P4.4.2 FTS score
- [ ] P4.4.3 Filename score
- [ ] P4.4.4 Metadata/date/type filters
- [ ] P4.4.5 Rank fusion
- [ ] P4.4.6 Return reason/snippet

## M4.5 Search Agent
- [ ] P4.5.1 Define search intent schema
- [ ] P4.5.2 LangGraph Search workflow
- [ ] P4.5.3 Tool: semantic search
- [ ] P4.5.4 Tool: full-text search
- [ ] P4.5.5 Tool: filename search
- [ ] P4.5.6 Tool: metadata search
- [ ] P4.5.7 Tool: file details
- [ ] P4.5.8 Tool: open file
- [ ] P4.5.9 Tool: reveal in Explorer
- [ ] P4.5.10 Parse natural date/type constraints

## M4.6 Search UI
- [ ] P4.6.1 Hero search field
- [ ] P4.6.2 Search state/loading
- [ ] P4.6.3 Result cards
- [ ] P4.6.4 Match reason
- [ ] P4.6.5 Path/category metadata
- [ ] P4.6.6 Open
- [ ] P4.6.7 Show in Folder

### Gate M4
Using deliberately poor filenames, queries must successfully retrieve:
- [ ] "the PDF about the agent hackathon"
- [ ] "my latest AI resume"
- [ ] "the screenshot with the FastAPI error"
- [ ] an exact phrase via FTS
- [ ] a query with file-type/date constraints

**Semantic search is not optional. Do not demote this milestone.**

---

# Phase 5 — Organizer Agent and First-Run Cleanup

## M5.1 Existing Structure Context
- [ ] P5.1.1 Build compact folder-tree representation
- [ ] P5.1.2 Find relevant candidate destination folders
- [ ] P5.1.3 Retrieve learned preferences
- [ ] P5.1.4 Prefer existing hierarchy

## M5.2 Organizer Agent
- [ ] P5.2.1 Pydantic `OrganizationProposal`
- [ ] P5.2.2 LangGraph Organizer node
- [ ] P5.2.3 Meaningful filename proposal
- [ ] P5.2.4 Destination proposal
- [ ] P5.2.5 Confidence
- [ ] P5.2.6 Rationale
- [ ] P5.2.7 `requires_review`

## M5.3 Review Queue
- [ ] P5.3.1 Persist proposed actions
- [ ] P5.3.2 Approve
- [ ] P5.3.3 Reject
- [ ] P5.3.4 Change destination
- [ ] P5.3.5 Bulk approve high-confidence safe proposals

## M5.4 Mutation Service
- [ ] P5.4.1 Centralized rename/move service
- [ ] P5.4.2 SafetyPolicy integration
- [ ] P5.4.3 Pre-action ledger
- [ ] P5.4.4 Atomic/error-safe execution where possible
- [ ] P5.4.5 Update file index after move
- [ ] P5.4.6 Preserve embedding/search association

## M5.5 Undo
- [ ] P5.5.1 Inverse move/rename
- [ ] P5.5.2 Collision/safety check on undo
- [ ] P5.5.3 Mark action reversed
- [ ] P5.5.4 Update index/path
- [ ] P5.5.5 UI feedback

## M5.6 Cleanup Plan UI
- [ ] P5.6.1 Scan summary
- [ ] P5.6.2 Safe/protected/review counts
- [ ] P5.6.3 Before -> after proposal rows
- [ ] P5.6.4 Confidence indicator
- [ ] P5.6.5 Why/explanation
- [ ] P5.6.6 Approve/reject
- [ ] P5.6.7 Execute approved plan

### Gate M5
- [ ] First-run scan produces sensible proposals
- [ ] Next.js project remains untouched
- [ ] User approves a batch
- [ ] Files move/rename correctly
- [ ] Search still finds moved files
- [ ] Undo restores a selected file

---

# Phase 6 — Continuous Agent / Watch Mode

## M6.1 Watchdog
- [ ] P6.1.1 Watch approved intake roots
- [ ] P6.1.2 Debounce duplicate events
- [ ] P6.1.3 Ignore temp extensions
- [ ] P6.1.4 File stability check
- [ ] P6.1.5 Queue processing

## M6.2 Autonomous New-File Graph
- [ ] P6.2.1 Watch event -> Guardian
- [ ] P6.2.2 Librarian
- [ ] P6.2.3 Index/embed
- [ ] P6.2.4 Organizer
- [ ] P6.2.5 Policy validation
- [ ] P6.2.6 Auto-execute only above configured confidence
- [ ] P6.2.7 Otherwise review
- [ ] P6.2.8 Persist/log everything

## M6.3 Notifications
- [ ] P6.3.1 System tray status
- [ ] P6.3.2 Organized-file notification
- [ ] P6.3.3 Review-needed notification
- [ ] P6.3.4 Quick Undo from app/activity

### Gate M6
Live demo:
- [ ] Download poorly named PDF
- [ ] TidyOS detects it
- [ ] waits until complete
- [ ] understands it
- [ ] indexes it
- [ ] renames/routes it or asks for review
- [ ] shows activity
- [ ] semantic search finds it immediately

---

# Phase 7 — Product UI and Trust Layer

## M7.1 Home
- [ ] P7.1.1 Files indexed
- [ ] P7.1.2 Organized count
- [ ] P7.1.3 Protected projects
- [ ] P7.1.4 Review count
- [ ] P7.1.5 Recent activity
- [ ] P7.1.6 Watch status

## M7.2 Activity
- [ ] P7.2.1 Timeline
- [ ] P7.2.2 Before/after paths
- [ ] P7.2.3 Agent rationale
- [ ] P7.2.4 Confidence
- [ ] P7.2.5 Undo
- [ ] P7.2.6 Filters

## M7.3 Protected Project UX
- [ ] P7.3.1 Shield badge
- [ ] P7.3.2 Framework/project label
- [ ] P7.3.3 Explanation: "TidyOS will not reorganize this structure"
- [ ] P7.3.4 Search-index status

## M7.4 Settings
- [ ] P7.4.1 Managed folders
- [ ] P7.4.2 Exclusions
- [ ] P7.4.3 Auto/review mode
- [ ] P7.4.4 Confidence threshold
- [ ] P7.4.5 API key handling
- [ ] P7.4.6 Pause watcher

### Gate M7
- [ ] Product looks coherent and demo-ready
- [ ] Safety and autonomy are visible, not hidden implementation details

---

# Phase 8 — Packaging

## M8.1 PyInstaller
- [ ] P8.1.1 Create spec file
- [ ] P8.1.2 Bundle PySide6
- [ ] P8.1.3 Bundle LangGraph/OpenAI dependencies
- [ ] P8.1.4 Bundle ONNX Runtime
- [ ] P8.1.5 Bundle embedding model/tokenizer
- [ ] P8.1.6 Bundle icons/resources
- [ ] P8.1.7 Resolve hidden imports
- [ ] P8.1.8 Test clean launch

## M8.2 Windows Installer
- [ ] P8.2.1 Inno Setup configuration
- [ ] P8.2.2 Start Menu shortcut
- [ ] P8.2.3 Desktop shortcut optional
- [ ] P8.2.4 App data location
- [ ] P8.2.5 Uninstaller
- [ ] P8.2.6 Installer branding

## M8.3 Clean-Machine Test
- [ ] P8.3.1 Test on Windows environment without project venv
- [ ] P8.3.2 Confirm no Python install required
- [ ] P8.3.3 Confirm no Node required
- [ ] P8.3.4 Confirm no DB/vector server required
- [ ] P8.3.5 Confirm local embeddings work
- [ ] P8.3.6 Confirm OpenAI error is graceful when offline

### Gate M8
- [ ] `TidyOS-Setup.exe` installs and launches a working app

---

# Phase 9 — Hackathon Demo Hardening

## M9.1 Controlled Demo Dataset
- [ ] P9.1.1 Create messy Downloads demo folder
- [ ] P9.1.2 Add invoices
- [ ] P9.1.3 Add resumes
- [ ] P9.1.4 Add hackathon PDF
- [ ] P9.1.5 Add screenshots
- [ ] P9.1.6 Add Next.js project
- [ ] P9.1.7 Add Python project
- [ ] P9.1.8 Add ambiguous files

## M9.2 Demo Sequence
- [ ] P9.2.1 Show messy folder
- [ ] P9.2.2 Scan
- [ ] P9.2.3 Show protected Next.js project
- [ ] P9.2.4 Show cleanup plan
- [ ] P9.2.5 Approve organization
- [ ] P9.2.6 Download new badly named file
- [ ] P9.2.7 Show autonomous organization
- [ ] P9.2.8 Search "the PDF about the agent hackathon"
- [ ] P9.2.9 Open result
- [ ] P9.2.10 Undo an action

## M9.3 Reliability
- [ ] P9.3.1 Cache/pre-index demo data where appropriate
- [ ] P9.3.2 Handle API timeout
- [ ] P9.3.3 Handle locked file
- [ ] P9.3.4 Handle duplicate destination
- [ ] P9.3.5 Handle offline state
- [ ] P9.3.6 No destructive operations
- [ ] P9.3.7 Repeat full demo at least 3 times

### Final Gate
- [ ] Demo can run end-to-end without manual code intervention
- [ ] Search wow moment works
- [ ] Agent architecture is visible/explainable
- [ ] Safety story is demonstrable
- [ ] Installer works
