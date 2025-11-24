# Nora LiveKit Agent

LiveKit-based voice agent for Nora (migrated from Ultravox/Jambonz).

## Prerequisites

- Python 3.12+
- Poetry 1.8+
- LiveKit Cloud account or self-hosted instance
- Railway account (for deployment)

## Setup

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Configure environment:
   ```bash
   cp .env.template .env
   # Edit .env with your LiveKit credentials
   ```

3. Run tests:
   ```bash
   poetry run pytest --cov=src/nora_livekit
   ```

4. Run locally:
   ```bash
   poetry run python -m nora_livekit.agent
   ```

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/nora_livekit

# Run specific test
poetry run pytest tests/test_agent.py -v
```

## Deployment

```bash
# Deploy to Railway
railway up

# View logs
railway logs
```

## Health Check

The agent exposes a health check endpoint at `/health` on port 8080:

```bash
curl http://localhost:8080/health
```

## Architecture

- `src/nora_livekit/agent.py`: Main agent class with LiveKit room lifecycle
- `src/nora_livekit/config.py`: Environment configuration loader
- `src/nora_livekit/server.py`: FastAPI health check server
