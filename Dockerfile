# Nora LiveKit Voice Agent - Production Dockerfile
# Optimized for Railway deployment with fast rebuilds

FROM python:3.12-slim

# Set environment variables - use /app/.cache for ALL caches
# This ensures models are found at runtime regardless of user
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Model cache directories - consistent for build and runtime
    HF_HOME=/app/.cache/huggingface \
    TORCH_HOME=/app/.cache/torch \
    XDG_CACHE_HOME=/app/.cache \
    HOME=/app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with /app as home directory
RUN useradd --home-dir /app --shell /bin/bash agent
WORKDIR /app

# Create cache directories early (owned by root initially)
RUN mkdir -p /app/.cache/huggingface /app/.cache/torch /app/temp /app/scripts

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies (CACHED - only rebuilds if pyproject.toml changes)
RUN pip install --upgrade pip && \
    pip install \
    livekit-agents==1.3.5 \
    livekit-plugins-deepgram==1.3.5 \
    livekit-plugins-cartesia==1.3.5 \
    livekit-plugins-openai==1.3.5 \
    livekit-plugins-silero==1.3.5 \
    livekit-plugins-turn-detector==1.3.5 \
    huggingface_hub \
    python-dotenv \
    structlog

# Copy model download script (separate layer for caching)
COPY scripts/download_models.py ./scripts/download_models.py

# Download ML models (CACHED - only rebuilds if download script changes)
RUN python scripts/download_models.py

# Copy application code LAST (changes most frequently)
COPY src/ ./src/
COPY scripts/run_voice_agent.py ./scripts/run_voice_agent.py

# Set ownership to non-root user
RUN chown -R agent:agent /app
USER agent

# Health check endpoint
EXPOSE 8081

# Default command - runs the voice agent
CMD ["python", "scripts/run_voice_agent.py", "start"]
