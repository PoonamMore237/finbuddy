# ─────────────────────────────────────────────────────────
# FinBuddy 3.0 — Production Dockerfile
# Optimized for Render, Railway, Google Cloud Run, and Fly.io
# ─────────────────────────────────────────────────────────

FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    DATABASE_URL="sqlite:////data/finbuddy.db"

WORKDIR /app

# Install system dependencies needed for bcrypt and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create persistent data directory for SQLite database
RUN mkdir -p /data && chmod 777 /data

# Expose port (FastAPI default)
EXPOSE 8000

# Health check probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Launch uvicorn listening on the cloud-assigned PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
