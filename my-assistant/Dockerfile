# ── Build stage (keeps final image smaller) ───────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY chat.py server.py ingest.py ./

# Copy static frontend
COPY public/ ./public/

# ChromaDB persistence directory
# In Cloud Run, mount a GCS bucket here via Volume Mounts (Cloud Run v2)
# or pre-populate during image build for read-only deployments.
ENV CHROMA_DIR=/app/db
RUN mkdir -p /app/db

# Cloud Run injects PORT; default to 8080
ENV PORT=8080

# GOOGLE_API_KEY must be set via Cloud Run Secret Manager — do NOT hardcode it here.
# In the GCP Console: Cloud Run → Edit → Variables & Secrets → add GOOGLE_API_KEY

EXPOSE 8080

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port $PORT"]
