# ─── UMAY AI Agent ──────────────────────────────────────────────────────────
# Python 3.13 slim base image
# Playwright + Chromium for browser automation
# ChromaDB for vector storage
# Ollama connection via host network
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim AS base

# System dependencies
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system packages needed by Playwright/Chromium and general tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libwayland-client0 \
    # General tools
    git \
    curl \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for minimal size)
RUN python -m playwright install chromium --with-deps 2>/dev/null || \
    python -m playwright install chromium

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs/memory logs/email_cache logs/screenshots logs/research \
    memory/chroma rag/chroma knowledge/tam

# Expose Flask UI port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/health')" || exit 1

# Default command — Flask UI (non-interactive)
CMD ["python", "-m", "ui.panel_server"]
