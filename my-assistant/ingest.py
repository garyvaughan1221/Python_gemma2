"""
ingest.py — Document ingestion with Gemini embeddings.

Usage:
    python ingest.py                  # ingest all .pdf and .txt files in ./data
    python ingest.py path/to/file     # ingest a single file (pdf or txt)

Tracks ingested files by SHA-256 hash in ingested.json to avoid re-processing.
A file is only re-ingested if its content has actually changed.
CHROMA_DIR can be overridden via env var (e.g. a GCS FUSE mount point).
"""
from dotenv import load_dotenv
load_dotenv()

import json
import os
import sys
import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR      = Path(os.environ.get("DATA_DIR",      "./data"))
CHROMA_DIR    = os.environ.get("CHROMA_DIR",         "./db")
TRACKER       = Path(os.environ.get("TRACKER",       "./data/ingested.json"))
CHUNK_SIZE    = int(os.environ.get("CHUNK_SIZE",     "800"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP",  "100"))

SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def file_hash(path: Path) -> str:
    """SHA-256 of file contents — used as the stable change-detection key."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_tracker() -> dict:
    if TRACKER.exists():
        return json.loads(TRACKER.read_text())
    return {}


def save_tracker(data: dict):
    TRACKER.parent.mkdir(parents=True, exist_ok=True)
    TRACKER.write_text(json.dumps(data, indent=2))


def get_loader(path: Path):
    """Return the appropriate LangChain loader for the file type."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(str(path))
    elif ext == ".txt":
        return TextLoader(str(path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── Core ──────────────────────────────────────────────────────────────────────
def ingest_file(file_path: Path, vectorstore: Chroma, tracker: dict) -> bool:
    """
    Ingest a single file into ChromaDB.
    Skips if the file hash matches what was previously ingested (no changes).
    Returns True if the file was ingested, False if skipped.
    """
    fhash = file_hash(file_path)
    key = str(file_path)

    if tracker.get(key) == fhash:
        print(f"  [skip] {file_path.name} — already ingested, no changes")
        return False

    print(f"  [load] {file_path.name}")
    try:
        loader = get_loader(file_path)
        docs = loader.load()
    except Exception as e:
        print(f"  [error] Failed to load {file_path.name}: {e}")
        return False

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    print(f"         → {len(chunks)} chunks")

    vectorstore.add_documents(chunks)
    tracker[key] = fhash
    return True


def main():
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings,
    )

    tracker = load_tracker()
    changed = False

    # Accept an explicit file arg, or walk DATA_DIR for all supported types
    if len(sys.argv) > 1:
        targets = [Path(sys.argv[1])]
    else:
        targets = sorted(
            f for f in DATA_DIR.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )

    if not targets:
        print(f"No supported files (.pdf, .txt) found in {DATA_DIR}")
        return

    print(f"Found {len(targets)} file(s) to check...\n")

    for file in targets:
        if not file.exists():
            print(f"  [warn] {file} not found — skipping")
            continue
        if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(f"  [skip] {file.name} — unsupported type")
            continue
        if ingest_file(file, vectorstore, tracker):
            changed = True

    print()
    if changed:
        save_tracker(tracker)
        print("Done. Tracker updated.")
    else:
        print("Nothing new to ingest.")


if __name__ == "__main__":
    main()