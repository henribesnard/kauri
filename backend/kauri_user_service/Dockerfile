# ============================================
# KAURI User Service - Dockerfile Multi-Stage
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
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

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

# Create app user (security best practice)
RUN useradd -m -u 1000 kauri && \
    mkdir -p /app /app/logs && \
    chown -R kauri:kauri /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=kauri:kauri . /app/

# Switch to non-root user
USER kauri

# Expose port (will be overridden by environment variable)
EXPOSE 3201

# Health check (uses SERVICE_PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-3201}/api/v1/health || exit 1

# Start application (port from environment variable)
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${SERVICE_PORT:-3201} --workers 2"]
