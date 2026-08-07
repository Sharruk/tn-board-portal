# ======================================================================
# TN Board Portal — Backend Dockerfile
# ======================================================================
# Base image: python:3.12-slim (small, current LTS Python)
# Security: runs as non-root user
# Layer caching: dependencies installed before app code is copied
# ======================================================================

FROM python:3.12-slim AS base

# ── System dependencies ──────────────────────────────────────────────
# curl is included for Render/Docker health check probes
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user ────────────────────────────────────────────────────
RUN groupadd --gid 1001 appgroup \
    && useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# ── Working directory ────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ──────────────────────────────────────
# Copy requirements first so Docker layer cache is reused when only
# application code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Copy application code ────────────────────────────────────────────
COPY app/ ./app/

# ── Switch to non-root user ──────────────────────────────────────────
USER appuser

# ── Expose port ──────────────────────────────────────────────────────
EXPOSE 8000

# ── Health check ─────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ── Start server ─────────────────────────────────────────────────────
# workers=1 for free Render tier; increase for paid instances.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
