# TidyOS — Autonomous File System Agent

> **"Your files organize themselves, and you never have to remember where anything is again."**

TidyOS is a local-first Windows desktop application that understands, organizes, protects, and retrieves a user's files.

---

## Key Capabilities

1. **Intelligent Intake & Protection**: Understands user-approved filesystem directories (e.g. Downloads, Screenshots) and protects structured software projects (Next.js, Python, Git, Node) from being disrupted.
2. **Deterministic Safety**: All filesystem mutations pass through an audited deterministic `SafetyPolicy` before execution.
3. **Multi-Agent Architecture (LangGraph)**:
   - **Guardian Agent**: Verifies directory safety and structural boundaries.
   - **Librarian Agent**: Extracts document meaning, metadata, and visual context.
   - **Organizer Agent**: Proposes clean, human-readable names and destinations.
   - **Search Agent**: Hybrid natural-language retrieval combining semantic embeddings, SQLite FTS5, and metadata.
4. **Local-First Semantic Search (P0)**: Fast on-device vector similarity + full-text search without requiring external database servers or Ollama.
5. **Activity Ledger & Reversibility**: Every operation is logged with an agent explanation and full Undo support.

---

## Architecture & Tech Stack

- **UI**: PySide6 (Qt for Python), dark-mode native desktop interface
- **Agents**: LangGraph, OpenAI Python SDK, Pydantic
- **Search & Storage**: SQLite FTS5, local ONNX Runtime embeddings, NumPy similarity
- **Filesystem**: `watchdog`, `pathlib`, `shutil`, `PyMuPDF`, `python-docx`
- **Distribution**: PyInstaller, Inno Setup

---

## Getting Started

### Prerequisites

- Windows 10/11
- Python 3.12 (64-bit)

### Installation

1. Clone the repository:
   ```powershell
   git clone https://github.com/tidyos/tidyos.git
   cd tidyos
   ```

2. Create and activate a Python 3.12 virtual environment:
   ```powershell
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

4. Configure environment (optional):
   ```powershell
   copy .env.example .env
   ```

5. Run tests:
   ```powershell
   pytest
   ```

6. Launch the application:
   ```powershell
   python -m tidyos.main
   ```
