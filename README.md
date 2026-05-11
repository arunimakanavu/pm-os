# ⬡ PM OS — AI-Powered Product Manager OS

A personal AI system for PMs built on local LLMs, RAG, and agents. Manages your roadmap, standup notes, PRD drafts, and product knowledge — no API key required, everything runs on your machine.

## Features

| Module | What it does |
|--------|-------------|
| 💬 **Chat** | Conversational interface — auto-routes to the right agent |
| 🗺️ **Roadmap** | Track features with status, priority, owner, quarter |
| 📋 **Standup** | Paste raw notes → structured done/doing/blocked |
| 📄 **PRD Builder** | Describe a feature → full PRD draft grounded in your docs |
| 📚 **Knowledge Base** | Upload PDFs, DOCX, CSVs → chunked & indexed for RAG |
| 📊 **Digest** | AI weekly summary of roadmap + team velocity |

## Architecture

```
Streamlit UI
    ↓
Orchestrator Agent  (keyword heuristics + LLM fallback)
    ├── Roadmap Agent   → SQLite
    ├── Standup Agent   → SQLite + RAG
    ├── PRD Agent       → RAG + local LLM
    ├── Query Agent     → RAG + local LLM
    └── Digest Agent    → SQLite + local LLM

RAG Pipeline
    Upload → Parse → Chunk → Embed (all-MiniLM-L6-v2) → ChromaDB
```

## Stack

| Layer | Tool |
|-------|------|
| UI | Streamlit |
| LLM | HuggingFace `transformers` (local, free) |
| Default model | `microsoft/Phi-3-mini-4k-instruct` |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store | ChromaDB (persistent, local) |
| Database | SQLite |
| File parsing | pypdf, python-docx, pandas |

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <your-repo>
cd pm-os
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
streamlit run app.py
```

No API key needed. The model downloads from HuggingFace on first launch (~2GB for Phi-3-mini) and is cached locally.

## Models

Switch models from the sidebar dropdown at runtime. Recommended choices by hardware:

| RAM | Model |
|-----|-------|
| 4GB | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` |
| 8GB | `microsoft/Phi-3-mini-4k-instruct` ← default |
| 16GB | `Qwen/Qwen2.5-3B-Instruct` |
| 32GB+ | `mistralai/Mistral-7B-Instruct-v0.3` |

You can also set a model via environment variable before launching:
```bash
PM_OS_MODEL=Qwen/Qwen2.5-3B-Instruct streamlit run app.py
```

## File Structure

```
pm-os/
├── app.py              # Streamlit UI (6 pages)
├── agents.py           # Orchestrator + 5 agents
├── rag.py              # RAG pipeline (chunking, embedding, retrieval)
├── database.py         # SQLite layer (features, standups, PRDs, chat history)
├── requirements.txt
├── .streamlit/
│   └── config.toml     # Disables file watcher (required for PyTorch compatibility)
└── data/
    ├── pm_os.db        # SQLite database
    ├── chroma/         # ChromaDB vector store
    └── uploads/        # Uploaded documents
```

## Supported Upload Formats

| Format | Best used for |
|--------|--------------|
| `.pdf` | PRDs, research docs, competitor analysis |
| `.docx` | Specs, meeting notes, strategy docs |
| `.md` / `.txt` | Transcripts, notes, changelogs |
| `.csv` | Roadmap exports, user research data |

Uploaded docs are chunked with section-aware splitting (PRDs split by section, transcripts by speaker turn, everything else fixed-size with overlap) and stored in ChromaDB. Every agent query retrieves relevant chunks before calling the LLM.

## Agent Routing

The orchestrator uses keyword heuristics first (fast, no LLM call) and falls back to the local model for ambiguous inputs.

| Example input | Routed to |
|---------------|-----------|
| "Add dark mode to Q3 roadmap" | Roadmap Agent |
| "Done: fixed auth. Doing: onboarding flow. Blocked: design review" | Standup Agent |
| "Write a PRD for real-time collaboration" | PRD Agent |
| "What did we decide about pricing last month?" | Query Agent (RAG) |
| "Give me a weekly summary" | Digest Agent |

You can also force a specific agent from the Chat page dropdown.

## Known Issues & Fixes

**PyTorch + Streamlit watcher conflict**
Streamlit's file watcher errors on `torch._classes`. Fixed by `.streamlit/config.toml`:
```toml
[server]
fileWatcherType = "none"
```

**ChromaDB telemetry warnings**
Suppressed via `ANONYMIZED_TELEMETRY=false` in `rag.py`. Not an error — safe to ignore if they appear.

## Roadmap

- [ ] OpenVINO integration (INT4 LLM, accelerated embeddings, Whisper STT)
- [ ] Voice standup input via mic
- [ ] Slack / Notion sync agent
- [ ] Multi-user support
