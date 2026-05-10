import os
import logging

# Silence ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "false"
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
import hashlib
from pathlib import Path
from typing import List, Dict

import chromadb
from chromadb.utils import embedding_functions

# --- Config ---
CHROMA_PATH = "data/chroma"
UPLOADS_PATH = "data/uploads"
COLLECTION_NAME = "pm_os_docs"

# Use sentence-transformers for local embeddings (OpenVINO-compatible)
EMBED_MODEL = "all-MiniLM-L6-v2"

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )
    return collection

# --- Chunkers ---
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """Fixed-size chunker with overlap."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]

def chunk_by_section(text: str, doc_type: str = "generic") -> List[Dict]:
    """Smart section-aware chunking for PM docs."""
    chunks = []

    if doc_type == "prd":
        # Split by common PRD section headers
        import re
        sections = re.split(r'\n(?=#+\s|##\s|Problem|Goals?|User Stories|Metrics|Edge Cases|Background|Overview)', text, flags=re.IGNORECASE)
        for section in sections:
            if len(section.strip()) > 50:
                chunks.append({"text": section.strip(), "section_type": "prd_section"})

    elif doc_type == "transcript":
        # Split by speaker turns or time markers
        import re
        lines = text.split('\n')
        current_chunk = []
        for line in lines:
            current_chunk.append(line)
            if len(' '.join(current_chunk)) > 400:
                chunks.append({"text": ' '.join(current_chunk), "section_type": "transcript_segment"})
                current_chunk = current_chunk[-3:]  # small overlap
        if current_chunk:
            chunks.append({"text": ' '.join(current_chunk), "section_type": "transcript_segment"})

    else:
        # Generic fixed-size
        raw_chunks = chunk_text(text)
        chunks = [{"text": c, "section_type": "generic"} for c in raw_chunks]

    return chunks

# --- File parsers ---
def parse_file(file_path: str, filename: str) -> str:
    """Extract raw text from uploaded file."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif ext in [".docx", ".doc"]:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == ".csv":
        import pandas as pd
        df = pd.read_csv(file_path)
        return df.to_string()

    elif ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        return ""

def detect_doc_type(filename: str, text: str) -> str:
    """Heuristic to detect PM doc type."""
    fname = filename.lower()
    text_lower = text.lower()

    if "prd" in fname or "product requirement" in text_lower:
        return "prd"
    elif "transcript" in fname or "meeting" in fname or " >> " in text or "speaker" in text_lower:
        return "transcript"
    elif fname.endswith(".csv"):
        return "csv"
    else:
        return "generic"

def file_hash(file_bytes: bytes) -> str:
    return hashlib.md5(file_bytes).hexdigest()

# --- Ingest ---
def ingest_file(file_bytes: bytes, filename: str) -> Dict:
    """Full pipeline: parse → chunk → embed → store."""
    # Save to disk
    Path(UPLOADS_PATH).mkdir(parents=True, exist_ok=True)
    fhash = file_hash(file_bytes)
    save_path = f"{UPLOADS_PATH}/{fhash}_{filename}"

    with open(save_path, "wb") as f:
        f.write(file_bytes)

    # Parse
    raw_text = parse_file(save_path, filename)
    if not raw_text.strip():
        return {"success": False, "reason": "Could not extract text from file."}

    # Detect type and chunk
    doc_type = detect_doc_type(filename, raw_text)
    chunks = chunk_by_section(raw_text, doc_type)

    if not chunks:
        return {"success": False, "reason": "No chunks generated."}

    # Store in ChromaDB
    collection = get_collection()
    ids = []
    texts = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        chunk_id = f"{fhash}_{i}"
        ids.append(chunk_id)
        texts.append(chunk["text"])
        metadatas.append({
            "filename": filename,
            "doc_type": doc_type,
            "section_type": chunk.get("section_type", "generic"),
            "file_hash": fhash,
            "chunk_index": i
        })

    # Upsert to avoid duplicates on re-upload
    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    return {
        "success": True,
        "filename": filename,
        "doc_type": doc_type,
        "chunks": len(chunks),
        "preview": raw_text[:200]
    }

# --- Retrieval ---
def retrieve(query: str, n_results: int = 5, doc_type_filter: str = None) -> List[Dict]:
    """Semantic search over ingested docs."""
    collection = get_collection()

    where = {"doc_type": doc_type_filter} if doc_type_filter else None

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count() or 1),
            where=where
        )
    except Exception:
        return []

    chunks = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            chunks.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results.get("distances") else None
            })
    return chunks

def list_ingested_docs() -> List[Dict]:
    """List all unique docs in the vector store."""
    collection = get_collection()
    if collection.count() == 0:
        return []
    results = collection.get(include=["metadatas"])
    seen = {}
    for meta in results["metadatas"]:
        fh = meta.get("file_hash", "")
        if fh not in seen:
            seen[fh] = {
                "filename": meta.get("filename", "unknown"),
                "doc_type": meta.get("doc_type", "generic"),
            }
    return list(seen.values())

def get_doc_count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0
