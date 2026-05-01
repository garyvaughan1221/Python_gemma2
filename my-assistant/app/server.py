from dotenv import load_dotenv
load_dotenv()

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.chat import query

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Pierce County AI Assistant")

# CORS — tighten allowed_origins to your Firebase domain in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Serve static files (index.html + any assets) from /public
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "../public")
if os.path.isdir(PUBLIC_DIR):
    app.mount("/public", StaticFiles(directory=PUBLIC_DIR), name="static")


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    index = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index):
        return FileResponse(index)
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    """Cloud Run health check endpoint."""
    return {"status": "ok"}


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]


@app.post("/ask", response_model=QueryResponse)
def ask(req: QueryRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    result = query(req.question)
    return QueryResponse(**result)


# ── Local dev entry point ─────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)