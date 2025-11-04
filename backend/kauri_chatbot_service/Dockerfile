# ============================================
# KAURI Chatbot Service - Dockerfile Multi-Stage
# ============================================

# ====================
# Stage 1: Builder
# ====================
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# Pre-download embedding model (BGE-M3) at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3', cache_folder='/opt/models')" || true

# ====================
# Stage 2: Runtime
# ====================
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy pre-downloaded models
COPY --from=builder /opt/models /opt/models
ENV HF_HOME=/opt/models
ENV TRANSFORMERS_CACHE=/opt/models

# Create app user (security best practice)
RUN useradd -m -u 1000 kauri && \
    mkdir -p /app /app/logs /app/data/chroma_db && \
    chown -R kauri:kauri /app && \
    chown -R kauri:kauri /opt/models

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=kauri:kauri . /app/

# Switch to non-root user
USER kauri

# Expose port
EXPOSE 3202

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-3202}/api/v1/health || exit 1

# Start application with warm-up
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-3202} --workers 1"]
