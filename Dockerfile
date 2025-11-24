# Multi-stage build for Nora LiveKit Agent

# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.8.3

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies to virtual environment
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --only main

# Stage 2: Runtime
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ /app/src/

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Run agent
CMD ["python", "-m", "nora_livekit.agent"]
