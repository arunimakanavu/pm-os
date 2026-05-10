# ⬡ PM OS — AI-Powered Product Manager OS

A personal AI system for PMs built with LLMs, RAG, and agents. Manages your roadmap, standup notes, PRD drafts, and product knowledge — all in one place.

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
Orchestrator Agent  (routes intent)
    ├── Roadmap Agent   → SQLite
    ├── Standup Agent   → SQLite + RAG
    ├── PRD Agent       → RAG + Claude API
    └── Query Agent     → RAG + Claude API

RAG Pipeline
    Upload → Parse → Chunk → Embed (sentence-transformers) → ChromaDB
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

Option A — environment variable:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Option B — enter it in the sidebar when you launch.

### 3. Run

```bash
streamlit run app.py
```

## OpenVINO Integration (Local LLM)

To run models locally instead of via API:

```bash
pip install openvino openvino-genai
```

Then in `agents.py`, swap the `llm()` function to use OpenVINO:

```python
from optimum.intel import OVModelForCausalLM
from transformers import AutoTokenizer

# Load Phi-3 or Mistral via OpenVINO
model = OVModelForCausalLM.from_pretrained("microsoft/Phi-3-mini-4k-instruct", export=True)
tokenizer = AutoTokenizer.from_pretrained("microsoft/Phi-3-mini-4k-instruct")
```

For local Whisper STT (voice standup input):
```bash
pip install openvino-whisper
```

**Hybrid mode**: Use OpenVINO for standup parsing + embeddings (fast, private), Claude API for PRD drafting (quality). The `llm()` function in `agents.py` can be toggled per-agent.

## File Structure

```
pm-os/
├── app.py          # Streamlit UI
├── agents.py       # Orchestrator + all agents
├── rag.py          # RAG pipeline (chunking, embedding, retrieval)
├── database.py     # SQLite layer (features, standups, PRDs)
├── requirements.txt
└── data/
    ├── pm_os.db    # SQLite database
    ├── chroma/     # Vector store
    └── uploads/    # Uploaded documents
```

## Supported Upload Formats

- `.pdf` — PRDs, research docs, specs
- `.docx` — Word documents
- `.txt` / `.md` — Notes, transcripts
- `.csv` — Roadmap exports, data

## Agent Routing

The orchestrator automatically detects intent:

| Input | Agent |
|-------|-------|
| "Add dark mode to Q3" | Roadmap |
| "Done: fixed auth bug. Doing: onboarding..." | Standup |
| "Write a PRD for real-time collab" | PRD |
| "What did we decide about pricing?" | Query (RAG) |
| "Give me a weekly summary" | Digest |

You can also force a specific agent from the Chat page dropdown.
