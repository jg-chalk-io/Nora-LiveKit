# Nora LiveKit Agent

LiveKit-based voice agent for Nora - part of a strategic migration from Ultravox/Jambonz to LiveKit with full voice pipeline integration.

**Current Status**: Foundation Complete (SPEC-LIVEKIT-001) | Version 0.1.0

## Overview

Nora is a Python-based conversational voice agent powered by LiveKit Agents SDK. This project establishes the foundational infrastructure for a full-featured voice interaction platform with support for:

- LiveKit room lifecycle management
- Structured JSON logging and observability
- Health check endpoints for monitoring
- Docker deployment support
- Railway cloud platform integration

### Strategic Roadmap

This is **SPEC-001** in an 8-specification migration roadmap:

| SPEC | Component | Status |
|------|-----------|--------|
| SPEC-001 | LiveKit Foundation & Infrastructure | ✅ Complete |
| SPEC-002 | Voice Pipeline & TTS Integration | Planned |
| SPEC-003 | Session Context Management | Planned |
| SPEC-004 | Business Hours Configuration | Planned |
| SPEC-005 | Conversation State Tracking | Planned |
| SPEC-006 | Supabase Integration | Planned |
| SPEC-007 | Tool Integration Framework | Planned |
| SPEC-008 | End-to-End Testing | Planned |

### Key Features (Foundation)

- **LiveKit Integration**: Connect to LiveKit Cloud or self-hosted instances
- **Agent Lifecycle**: Automatic room join/leave with graceful shutdown
- **Health Monitoring**: FastAPI endpoint for deployment health checks
- **Structured Logging**: JSON-formatted logs for production observability
- **Configuration Management**: Environment-based configuration with validation
- **Docker Support**: Multi-stage build for optimized container deployment
- **Railway Ready**: Pre-configured for Railway cloud deployment

## Prerequisites

- **Python 3.12 or later**
- **Poetry 1.8 or later** (dependency management)
- **LiveKit Cloud account** or self-hosted LiveKit instance
  - [Create free account](https://cloud.livekit.io)
  - Obtain API credentials from dashboard
- **Railway account** (optional, for deployment)
  - [Create free account](https://railway.app)

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd Nora-LiveKit
```

### 2. Install Dependencies

```bash
# Install all project dependencies with Poetry
poetry install

# Activate the virtual environment (optional, poetry run handles this)
poetry shell
```

### 3. Configure Environment

```bash
# Copy environment template to .env
cp .env.template .env

# Edit .env with your LiveKit credentials
# Required fields:
#   - LIVEKIT_URL: wss://your-instance.livekit.cloud
#   - LIVEKIT_API_KEY: your-api-key
#   - LIVEKIT_API_SECRET: your-api-secret
```

See [Configuration Guide](#configuration) for detailed environment variable documentation.

### 4. Run Tests

```bash
# Run all tests with coverage
poetry run pytest --cov=src/nora_livekit

# Run specific test file
poetry run pytest tests/test_agent.py -v

# Run with output
poetry run pytest -s
```

**Expected Result**: 47 tests passing with 90% coverage

### 5. Start Development Server

```bash
# Run the agent locally
poetry run python -m nora_livekit

# In another terminal, check health endpoint
curl http://localhost:8080/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "nora-livekit"
}
```

## Project Structure

```
Nora-LiveKit/
├── src/nora_livekit/          # Main package
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Entry point (python -m nora_livekit)
│   ├── agent.py               # NoraAgent class with room lifecycle
│   ├── config.py              # Configuration loader and logging setup
│   └── server.py              # FastAPI health check server
├── tests/                     # Test suite
│   ├── test_agent.py          # Agent lifecycle tests
│   ├── test_config.py         # Configuration tests
│   ├── test_main.py           # Entry point tests
│   └── test_server.py         # Health endpoint tests
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System design and component architecture
│   ├── API_REFERENCE.md       # API and module documentation
│   └── DEPLOYMENT.md          # Deployment procedures
├── pyproject.toml             # Poetry dependencies and config
├── Dockerfile                 # Multi-stage production build
├── railway.toml               # Railway deployment configuration
├── .env.template              # Environment variables template
└── README.md                  # This file
```

## Architecture Overview

The Nora agent follows a clean architecture pattern with clear separation of concerns:

```
┌─────────────────────────────────────────────┐
│         FastAPI Health Server               │
│  (Port 8080, async in background thread)    │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│         NoraAgent Class                     │
│  ┌──────────────────────────────────────┐   │
│  │ Room Lifecycle Management            │   │
│  │ - Connect to LiveKit                 │   │
│  │ - Join room with access token        │   │
│  │ - Graceful shutdown on signals       │   │
│  └──────────────────────────────────────┘   │
└────────────────┬────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────┐
│    LiveKit Agents SDK & Access Token        │
│  ┌──────────────────────────────────────┐   │
│  │ Configuration from environment vars  │   │
│  │ Signal handlers (SIGTERM/SIGINT)     │   │
│  │ Structured JSON logging with Structlog
│  └──────────────────────────────────────┘   │
└────────────────┬────────────────────────────┘
                 │
                 ↓
     ┌───────────────────────────┐
     │   LiveKit Cloud/Server    │
     │  (WebSocket connection)   │
     └───────────────────────────┘
```

### Key Components

1. **NoraAgent** (`agent.py`): Manages room connection lifecycle and graceful shutdown
2. **Config** (`config.py`): Loads and validates environment variables
3. **FastAPI Server** (`server.py`): Provides `/health` endpoint for monitoring
4. **Entry Point** (`__main__.py`): Orchestrates startup and shutdown

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed system design.

## Configuration

All configuration uses environment variables loaded from `.env` file or system environment.

### Required Variables

```env
# LiveKit server WebSocket URL (secure: wss://, insecure: ws://)
LIVEKIT_URL=wss://your-instance.livekit.cloud

# LiveKit API credentials (obtain from dashboard)
LIVEKIT_API_KEY=your-api-key-here
LIVEKIT_API_SECRET=your-api-secret-here
```

### Optional Variables

```env
# Health check endpoint port (default: 8080)
HEALTH_CHECK_PORT=8080

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
LOG_LEVEL=INFO

# Log format: json for structured logs, text for human-readable (default: json)
LOG_FORMAT=json

# Optional test room name for development/testing
LIVEKIT_TEST_ROOM=test-room-name
```

### Obtaining LiveKit Credentials

1. Visit [LiveKit Cloud Console](https://cloud.livekit.io)
2. Sign up or log in
3. Create a new project
4. Generate API key and secret
5. Copy credentials to `.env` file

See [DEPLOYMENT.md - LiveKit Integration](docs/DEPLOYMENT.md#livekit-integration) for detailed setup.

## Testing

### Run All Tests

```bash
# With coverage report
poetry run pytest --cov=src/nora_livekit

# Verbose output
poetry run pytest -v

# Specific test file
poetry run pytest tests/test_agent.py -v

# Specific test
poetry run pytest tests/test_agent.py::test_agent_initialization -v
```

### Test Coverage

Current test coverage: **90%** (47 tests passing)

Coverage breakdown:
- `src/nora_livekit/__init__.py`: 100%
- `src/nora_livekit/__main__.py`: 95%
- `src/nora_livekit/agent.py`: 80%
- `src/nora_livekit/config.py`: 100%
- `src/nora_livekit/server.py`: 100%

### Code Quality Checks

```bash
# Format code with Black
poetry run black src/ tests/

# Lint with Ruff
poetry run ruff check src/ tests/

# Type checking with Mypy (strict mode)
poetry run mypy src/
```

## Development Workflow

### Local Development Setup

1. **Install dependencies**: `poetry install`
2. **Configure environment**: `cp .env.template .env` and fill credentials
3. **Run tests**: `poetry run pytest --cov=src/nora_livekit`
4. **Start server**: `poetry run python -m nora_livekit`
5. **Check health**: `curl http://localhost:8080/health`

### TDD Development Cycle

This project follows Test-Driven Development (TDD):

1. **RED**: Write failing test for desired behavior
2. **GREEN**: Implement minimum code to pass test
3. **REFACTOR**: Improve code quality while keeping tests passing

Example:
```bash
# 1. RED - Write test
# Edit tests/test_new_feature.py

# 2. GREEN - Make it pass
poetry run pytest tests/test_new_feature.py
# Edit src/ to make test pass

# 3. REFACTOR - Improve code
poetry run black src/
poetry run ruff check src/
poetry run mypy src/
poetry run pytest --cov=src/nora_livekit
```

### Code Style Requirements

- **Formatter**: Black (line length: 100)
- **Linter**: Ruff
- **Type Checker**: Mypy (strict mode)
- **Python Version**: 3.12+

All checks must pass before committing:
```bash
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/
poetry run pytest --cov=src/nora_livekit
```

## Deployment

### Local Testing

```bash
# Run the agent locally
poetry run python -m nora_livekit

# In another terminal, test health endpoint
curl http://localhost:8080/health
```

### Docker Deployment

```bash
# Build Docker image
docker build -t nora-livekit:latest .

# Run container locally
docker run --env-file .env -p 8080:8080 nora-livekit:latest

# Test health endpoint
curl http://localhost:8080/health
```

### Railway Deployment

```bash
# Install Railway CLI (if not already installed)
npm install -g @railway/cli

# Login to Railway
railway login

# Deploy
railway up

# View logs
railway logs

# Check health
curl https://<your-railway-domain>/health
```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete deployment guide with troubleshooting.

## Health Check

The agent exposes a health check endpoint for monitoring and load balancer checks:

```bash
# Health check endpoint
curl http://localhost:8080/health

# Expected response
{
  "status": "healthy",
  "service": "nora-livekit"
}
```

**Response Time**: < 100ms
**Port**: 8080 (configurable via `HEALTH_CHECK_PORT`)

## Technology Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Runtime language |
| Poetry | 1.8+ | Dependency management |
| LiveKit Agents | ~1.0 | Voice agent framework |
| FastAPI | ~0.115 | Health check server |
| Uvicorn | ~0.32 | ASGI server |
| Structlog | ~24.4 | Structured logging |
| Pytest | ~8.3 | Testing framework |
| Mypy | ~1.13 | Type checking |
| Black | ~24.10 | Code formatting |
| Ruff | ~0.7 | Linting |

## Troubleshooting

### Common Issues

**Problem**: `LIVEKIT_URL is required` error
- **Solution**: Ensure `.env` file exists and contains `LIVEKIT_URL`. Check [Configuration](#configuration) section.

**Problem**: Connection timeout to LiveKit
- **Solution**: Verify LiveKit credentials are correct. Check network connectivity to LiveKit instance.

**Problem**: Health endpoint slow or unresponsive
- **Solution**: Check agent logs. Ensure health server started successfully. See [DEPLOYMENT.md](docs/DEPLOYMENT.md) troubleshooting.

**Problem**: Tests failing
- **Solution**: Run `poetry install` to ensure dependencies up to date. Check Python version is 3.12+.

See [DEPLOYMENT.md - Troubleshooting](docs/DEPLOYMENT.md#troubleshooting) for more solutions.

## Contributing

This project follows SPEC-first development with MoAI-ADK framework:

1. **Understand the SPEC**: Each feature has an associated SPEC document
2. **Follow TDD**: Write tests first, then implementation
3. **Check Code Quality**: Run `black`, `ruff`, and `mypy`
4. **Ensure Coverage**: Maintain 90% test coverage
5. **Document Changes**: Update documentation when adding features

### Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/SPEC-LIVEKIT-002

# 2. Develop with TDD
poetry run pytest  # Run existing tests
# Edit tests/test_new_feature.py (RED)
# Edit src/ (GREEN)
# Run checks (REFACTOR)

# 3. Ensure quality
poetry run pytest --cov=src/nora_livekit
poetry run black src/ tests/
poetry run ruff check src/ tests/
poetry run mypy src/

# 4. Commit changes
git add .
git commit -m "feat: implement new feature per SPEC-LIVEKIT-002"

# 5. Push and create PR
git push origin feature/SPEC-LIVEKIT-002
```

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: System design, component architecture, and design patterns
- **[API_REFERENCE.md](docs/API_REFERENCE.md)**: Complete API documentation with examples
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Deployment procedures and troubleshooting
- **[CLAUDE.md](CLAUDE.md)**: MoAI-ADK execution guidelines

## Support

For issues or questions:

1. **Check Documentation**: See links above
2. **Review Tests**: Test cases demonstrate correct usage
3. **Check Logs**: Enable `LOG_LEVEL=DEBUG` for detailed output
4. **LiveKit Documentation**: [livekit.io/docs](https://livekit.io/docs)

## License

[Add license information if applicable]

## Acknowledgments

This project is part of Nora voice agent migration from Ultravox/Jambonz to LiveKit infrastructure.

---

**Last Updated**: November 24, 2025
**Version**: 0.1.0
**Maintainer**: [Add maintainer info]
