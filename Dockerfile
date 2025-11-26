# Nora LiveKit Voice Agent - Production Dockerfile
# Optimized for Railway deployment

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash agent
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml ./
COPY README.md ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install \
    livekit-agents==1.3.5 \
    livekit-plugins-deepgram==1.3.5 \
    livekit-plugins-cartesia==1.3.5 \
    livekit-plugins-openai==1.3.5 \
    livekit-plugins-silero==1.3.5 \
    python-dotenv \
    structlog

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Set ownership to non-root user
RUN chown -R agent:agent /app
USER agent

# Health check endpoint
EXPOSE 8081

# Default command - runs the voice agent
CMD ["python", "scripts/run_voice_agent.py", "start"]
