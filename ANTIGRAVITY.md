# ANTIGRAVITY.md

## Project
**TidyOS — Autonomous File System Agent**

TidyOS is a local-first Windows desktop application that understands, organizes, protects, and retrieves a user's files. It is being built as a hackathon MVP, so prioritize a sharp, reliable, demoable product over broad feature coverage.

Core promise:

> **Your files organize themselves, and you never have to remember where anything is again.**

The application must be installable as a normal Windows application. The final user must not need to separately install Python, Node.js, Docker, PostgreSQL, Qdrant, Ollama, Redis, or any development runtime.

---

## 1. Mandatory Engineering Principles

### 1.1 Python-first
Build the application primarily in **Python 3.12**.

Use:
- PySide6 for the native desktop UI
- LangGraph for agent orchestration
- OpenAI for agent reasoning and multimodal understanding
- Pydantic for structured agent contracts
- SQLite for local persistence
- SQLite FTS5 for full-text retrieval
- ONNX Runtime + a bundled compact embedding model for local embeddings
- NumPy for vector similarity
- watchdog for filesystem events
- pathlib/shutil/os for filesystem operations
- PyMuPDF for PDFs
- python-docx for DOCX extraction
- PyInstaller for distributable builds
- Inno Setup for the final Windows installer

Do not introduce a web frontend, FastAPI server, Docker, external vector database, external database server, or Ollama unless a blocker makes it absolutely necessary.

### 1.2 Safety is above AI
No LLM or LangGraph node may directly mutate arbitrary filesystem paths.

Every rename, move, directory creation, or undo request MUST pass through a deterministic `SafetyPolicy` layer.

The safety engine has final authority even when an agent says an operation is safe.

Fail closed:
- Protected => do not mutate
- Unknown/uncertain => review
- Outside approved roots => deny
- Destination protected => deny
- Collision => deny or generate safe non-destructive alternative
- Temporary/incomplete download => wait
- Any unexpected exception => leave original file untouched

### 1.3 Never reorganize software projects
TidyOS must understand that some directory structures are operational structures rather than human document collections.

Protect recognized project roots and descendants.

At minimum detect:
- `.git/`
- `package.json`
- `next.config.js`, `.mjs`, `.ts`
- `package-lock.json`
- `pnpm-lock.yaml`
- `yarn.lock`
- `node_modules/`
- `pyproject.toml`
- `requirements.txt`
- `Pipfile`
- `setup.py`
- `.venv/`, `venv/`
- `Dockerfile`
- `docker-compose.yml`
- `.github/`
- common build/generated directories such as `.next/`, `dist/`, `build/`

A `.git` root is protected by default.

A Next.js repository must be recognized as a structured project. Never move or rename its internal files in the MVP, including apparently ordinary PDFs/images inside `public/`.

Protected projects may be indexed for search only when the user has explicitly included them in the searchable scope.

### 1.4 Preserve the user's existing organization
Do not invent a new hierarchy unnecessarily.

Before suggesting a destination:
1. inspect existing folders;
2. retrieve relevant learned preferences;
3. prefer existing categories;
4. create a new folder only when clearly useful and allowed.

### 1.5 Everything important is reversible
Do not implement permanent deletion in the MVP.

Before every mutation, persist an action transaction containing:
- source path
- destination path
- action type
- timestamp
- agent rationale
- confidence
- status

Undo must be a first-class feature.

### 1.6 Local-first
The following must work locally:
- UI
- folder scanning
- directory/project protection
- filesystem watcher
- file moves/renames
- SQLite
- full-text search
- embeddings
- vector search
- action history
- undo
- existing semantic search index

OpenAI may be used for:
- LangGraph agent reasoning
- semantic document classification
- intelligent naming
- routing decisions
- screenshot/image understanding
- difficult query interpretation

Never require OpenAI for deterministic safety.

---

## 2. Agent Architecture

Implement four meaningful agents using LangGraph.

### Guardian Agent
Responsibility: understand whether a path/directory is safe to operate on.

Inputs:
- path
- directory markers
- managed-root status
- project-root detection
- deterministic safety results

Outputs:
- SAFE / PROTECTED / REVIEW
- project/framework type when known
- explanation

Guardian does not override `SafetyPolicy`.

### Librarian Agent
Responsibility: understand what a file actually is.

Available capabilities:
- metadata
- MIME/type
- PDF text
- DOCX text
- plain text
- image/screenshot description
- parent directory context
- similar indexed files

Produces structured data:
- document/file type
- title/subject
- entities
- date when relevant
- summary
- tags
- category
- confidence

### Organizer Agent
Responsibility: determine a meaningful filename and destination.

Context:
- Librarian output
- current path
- existing folder tree
- user preferences/corrections
- similar files
- allowed roots

Produces:
- suggested filename
- suggested destination
- confidence
- rationale
- requires_review

It proposes only. The deterministic validator executes or rejects.

### Search Agent
Responsibility: interpret natural-language file-finding requests and use multiple retrieval tools.

Tools:
- semantic_search
- full_text_search
- filename_search
- metadata_search
- get_file_details
- open_file
- reveal_in_explorer

Search should be hybrid, not vector-only.

Example:
"Find the PDF about the agent hackathon I downloaded yesterday."

The Search Agent should infer:
- semantic topic: agent hackathon
- file type: PDF
- date constraint: yesterday

Then combine metadata filtering, semantic retrieval, and FTS results.

---

## 3. LangGraph Requirements

Use a typed shared state.

Recommended conceptual state:

```python
class TidyOSState(TypedDict, total=False):
    file_path: str
    managed_root: str
    protected: bool
    protection_reason: str
    project_type: str | None

    metadata: dict
    extracted_text: str | None
    image_description: str | None

    file_type: str | None
    summary: str | None
    tags: list[str]
    category: str | None

    suggested_filename: str | None
    suggested_destination: str | None
    confidence: float
    requires_review: bool

    policy_status: str
    action_id: str | None
    status: str
```

Primary organization graph:

```text
FILE EVENT / SCAN
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
   POLICY VALIDATOR
      /    |    \
    deny review allow
                 |
                 v
              EXECUTE
                 |
                 v
               INDEX
```

The Search Agent can use a separate LangGraph workflow optimized for retrieval.

---

## 4. Semantic Search Is P0

Semantic search is a core product feature, not a stretch goal.

### Indexing pipeline
For every searchable file:
1. gather metadata;
2. extract useful text/description;
3. create a concise searchable representation;
4. generate a local embedding;
5. persist text/metadata in SQLite;
6. persist embedding locally;
7. update FTS5 index.

For images/screenshots, store a semantic description and tags generated by vision when available.

### Retrieval
Combine:
- semantic similarity
- SQLite FTS5
- filename match
- metadata filters
- recency when relevant

Do not market this as "RAG" unless answer generation is actually implemented. The MVP is intelligent file retrieval.

### Local embedding requirement
Bundle a compact embedding model with the application and run it using ONNX Runtime.

Do not require:
- Ollama
- an embedding API
- a vector DB server

For hackathon scale, NumPy cosine/dot-product similarity over locally stored embeddings is acceptable and preferred for simplicity.

---

## 5. Filesystem Watcher

Use `watchdog`.

Watch only user-approved intake folders such as Downloads and Screenshots.

Do not process temporary/incomplete files.

Before indexing a new file:
- ensure size has stabilized;
- ensure it can be opened;
- ignore `.crdownload`, `.part`, `.tmp`, etc.;
- debounce duplicate filesystem events.

New-file flow:

```text
WATCHDOG EVENT
  -> STABILITY CHECK
  -> SCOPE CHECK
  -> PROTECTION CHECK
  -> CONTENT EXTRACTION
  -> LIBRARIAN
  -> EMBEDDING/INDEX
  -> ORGANIZER
  -> POLICY
  -> AUTO / REVIEW / DENY
```

---

## 6. Database

Use SQLite.

Recommended tables:
- `managed_roots`
- `files`
- `folders`
- `protected_roots`
- `actions`
- `preferences`
- `file_text`
- `file_embeddings`
- `review_queue`
- FTS5 virtual table for searchable content

Store canonical absolute paths internally.

Never assume paths are unique forever; maintain file IDs and update paths after mutations.

---

## 7. UI/Threading

The PySide6 main thread must never perform:
- recursive scans
- OpenAI calls
- embedding inference
- PDF extraction across many files
- LangGraph workflows
- bulk filesystem operations

Use `QThread`, `QThreadPool`, or background workers and communicate through Qt signals.

The UI must remain responsive while indexing.

---

## 8. Packaging

Development can use a normal Python virtual environment.

Release requirements:
- PyInstaller builds the self-contained application distribution.
- Bundle Qt dependencies.
- Bundle the embedding ONNX model/tokenizer.
- Bundle required native runtime libraries.
- Create a Windows installer using Inno Setup.
- Final experience should be `TidyOS-Setup.exe -> Install -> Run`.

Do not optimize prematurely for a literal single-file PyInstaller executable. A single installer that installs a self-contained application is preferred.

---

## 9. Development Rules for Antigravity

1. Read `PRD.md`, `TASKS.md`, and `DESIGN.md` before implementation.
2. Follow milestones in `TASKS.md` in order.
3. Do not implement later-phase features while a P0 gate is failing.
4. After each submilestone:
   - run relevant tests;
   - record what works;
   - update task status;
   - fix regressions before moving forward.
5. Use small modules with clear responsibilities.
6. Use type hints.
7. Use Pydantic for LLM/agent structured output.
8. Never silently swallow filesystem errors.
9. Log agent decisions and tool results.
10. Never log full sensitive document content unnecessarily.
11. Never expose unrestricted shell/code execution as an agent tool.
12. Never let an LLM construct and execute raw OS commands.
13. All file mutations go through one audited filesystem service.
14. All file mutations go through `SafetyPolicy`.
15. Prefer deterministic logic over LLM calls where deterministic logic is sufficient.
16. Avoid unnecessary abstractions during the hackathon.
17. Optimize for the demo path first.
18. The app must work on a controlled Windows demo folder before broadening scope.
19. Keep API keys outside source control.
20. Never commit local databases, user documents, secrets, `.env`, build artifacts, or embedding caches.

---

## 10. Definition of Done

The MVP is done when a fresh Windows user can install TidyOS and:

1. choose approved folders;
2. scan a deliberately messy folder;
3. see structured software projects detected and protected;
4. preview suggested file organization;
5. approve safe rename/move operations;
6. undo an operation;
7. leave TidyOS watching Downloads;
8. download a badly named document and see it classified/organized;
9. search naturally for a file by meaning and retrieve it;
10. open or reveal the result in Windows Explorer;
11. see all actions and explanations in Activity;
12. use the app without installing any separate runtime/service.

The strongest demo must prove both sides of the product:
- **autonomy:** files organize themselves;
- **control/intelligence:** TidyOS knows what not to touch and can retrieve files by meaning.
