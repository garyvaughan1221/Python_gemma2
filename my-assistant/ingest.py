from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
import os
import json

DATA_DIR    = "./data"
DB_DIR      = "./db"
TRACKER     = "./data/ingested.json"

# Load tracker
if os.path.exists(TRACKER):
    with open(TRACKER, "r") as f:
        already_ingested = json.load(f)
else:
    already_ingested = []

docs = []
newly_ingested = []

for filename in os.listdir(DATA_DIR):
    if filename in already_ingested:
        print(f"Skipping {filename} — already ingested.")
        continue

    filepath = os.path.join(DATA_DIR, filename)

    if filename.endswith(".pdf"):
        loader = PyPDFLoader(filepath)
        docs.extend(loader.load())
        newly_ingested.append(filename)
    elif filename.endswith(".txt"):
        loader = TextLoader(filepath, encoding="utf-8")
        docs.extend(loader.load())
        newly_ingested.append(filename)

if not docs:
    print("Nothing new to ingest.")
else:
    print(f"Ingesting {len(newly_ingested)} new file(s)...")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    print(f"Split into {len(chunks)} chunks — embedding now...")

    embeddings = OllamaEmbeddings(model="gemma2:2b")
    vectorstore = Chroma.from_documents(chunks, embeddings, persist_directory=DB_DIR)

    # Update tracker
    already_ingested.extend(newly_ingested)
    with open(TRACKER, "w") as f:
        json.dump(already_ingested, f, indent=2)

    print(f"Done. Tracker updated: {already_ingested}")