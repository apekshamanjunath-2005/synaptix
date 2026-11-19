# ==============================================================================
# Synaptix - Multi-Agent AI Personal Productivity Assistant
# Production Dockerfile optimized for Python 3.12 and Google Cloud Run
# ==============================================================================

FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Set working directory
WORKDIR /app

# Install security updates and build requirements if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ ./app/

# Create a non-root system user for security compliance
RUN useradd -m -u 1000 synaptixuser && \
    chown -R synaptixuser:synaptixuser /app

# Switch to unprivileged user
USER synaptixuser

# Expose server port (Cloud Run automatically injects $PORT at runtime)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch production server with dynamic Cloud Run port handling
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
