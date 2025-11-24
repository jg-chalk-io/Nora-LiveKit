# SPEC-LIVEKIT-001: Implementation Plan

**SPEC ID**: SPEC-LIVEKIT-001
**Title**: LiveKit Foundation & Infrastructure
**Status**: Draft
**Priority**: P0 (Critical)
**Estimated LOC**: 300 (excluding tests)

---

## Implementation Overview

This plan outlines the step-by-step implementation of the LiveKit Foundation infrastructure. The implementation follows a phased approach, starting with project initialization and progressing through agent lifecycle, health checks, and Railway deployment.

**Development Approach**: Test-Driven Development (TDD) with RED-GREEN-REFACTOR cycle
**Estimated Duration**: 3 implementation phases
**Test Coverage Target**: 90%+ for lifecycle code

---

## Phase 1: Project Initialization

**Goal**: Establish Python project structure with Poetry dependency management

### Tasks

#### Task 1.1: Initialize Poetry Project
**Priority**: Critical
**Dependencies**: None

**Steps**:
1. Create project directory: `nora-livekit/`
2. Initialize Poetry: `poetry init`
3. Set Python version constraint: `python = "^3.12"`
4. Configure project metadata (name, description, author)

**Deliverables**:
- `pyproject.toml` with project metadata
- Poetry virtual environment created

**Verification**:
- `poetry --version` confirms Poetry installation
- `pyproject.toml` exists with valid TOML syntax

**TAG-IMPL-FOUNDATION-001**

---

#### Task 1.2: Add Core Dependencies
**Priority**: Critical
**Dependencies**: Task 1.1

**Steps**:
1. Add LiveKit Agents SDK with extras:
   ```bash
   poetry add "livekit-agents[openai,deepgram,cartesia,turn-detector]~=1.0"
   ```
2. Add FastAPI and uvicorn:
   ```bash
   poetry add "fastapi~=0.115" "uvicorn[standard]~=0.32"
   ```
3. Add utility libraries:
   ```bash
   poetry add "python-dotenv~=1.0" "structlog~=24.4" "httpx~=0.27"
   ```
4. Lock dependencies: `poetry lock`

**Deliverables**:
- `poetry.lock` with pinned dependency versions
- All dependencies installed in virtual environment

**Verification**:
- `poetry show livekit-agents` confirms v1.0.x installation
- `poetry install` completes without errors

**TAG-IMPL-FOUNDATION-001**

---

#### Task 1.3: Add Development Dependencies
**Priority**: High
**Dependencies**: Task 1.2

**Steps**:
1. Add testing frameworks:
   ```bash
   poetry add --group dev "pytest~=8.3" "pytest-asyncio~=0.24" "pytest-cov~=6.0"
   ```
2. Add code quality tools:
   ```bash
   poetry add --group dev "ruff~=0.7" "black~=24.10" "mypy~=1.13"
   ```

**Deliverables**:
- Development dependencies added to pyproject.toml
- Tool configurations in pyproject.toml

**Verification**:
- `poetry run pytest --version` works
- `poetry run ruff --version` works
- `poetry run black --version` works
- `poetry run mypy --version` works

**TAG-IMPL-FOUNDATION-001**

---

#### Task 1.4: Create Directory Structure
**Priority**: Critical
**Dependencies**: Task 1.1

**Steps**:
1. Create source directory: `src/nora_livekit/`
2. Create test directory: `tests/`
3. Add `__init__.py` files to make packages importable
4. Create placeholder files:
   - `src/nora_livekit/agent.py`
   - `src/nora_livekit/config.py`
   - `src/nora_livekit/server.py`

**Deliverables**:
```
nora-livekit/
├── src/
│   └── nora_livekit/
│       ├── __init__.py
│       ├── agent.py
│       ├── config.py
│       └── server.py
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_config.py
│   └── test_server.py
└── pyproject.toml
```

**Verification**:
- Directory structure matches specification
- All `__init__.py` files exist

**TAG-IMPL-FOUNDATION-001**

---

#### Task 1.5: Create Environment Configuration Template
**Priority**: High
**Dependencies**: Task 1.4

**Steps**:
1. Create `.env.template` file
2. Document all required environment variables:
   ```env
   # LiveKit Configuration
   LIVEKIT_URL=wss://your-livekit-instance.livekit.cloud
   LIVEKIT_API_KEY=your-api-key
   LIVEKIT_API_SECRET=your-api-secret

   # FastAPI Health Check
   HEALTH_CHECK_PORT=8080

   # Logging Configuration
   LOG_LEVEL=INFO
   LOG_FORMAT=json

   # Optional: Test Room
   LIVEKIT_TEST_ROOM=test-room-001
   ```
3. Add inline comments explaining each variable
4. Create `.env.example` as copy of `.env.template`

**Deliverables**:
- `.env.template` with all configuration variables
- `.env.example` for local development

**Verification**:
- Template includes all variables used in code
- Comments are clear and helpful

**TAG-IMPL-FOUNDATION-007**

---

#### Task 1.6: Create .gitignore
**Priority**: Medium
**Dependencies**: Task 1.4

**Steps**:
1. Create `.gitignore` file
2. Add Python-specific ignores:
   ```
   # Python
   __pycache__/
   *.py[cod]
   *$py.class
   .venv/
   venv/
   ENV/

   # Poetry
   poetry.lock

   # Environment
   .env
   .env.local

   # IDE
   .vscode/
   .idea/
   *.swp

   # Testing
   .coverage
   .pytest_cache/
   htmlcov/

   # Build
   dist/
   build/
   *.egg-info/
   ```

**Deliverables**:
- `.gitignore` file

**Verification**:
- Git status does not show ignored files

**TAG-IMPL-FOUNDATION-001**

---

## Phase 2: Agent Lifecycle Implementation

**Goal**: Implement LiveKit agent with room connection lifecycle and graceful shutdown

### Tasks

#### Task 2.1: Implement Configuration Loader (TDD)
**Priority**: Critical
**Dependencies**: Phase 1 complete

**RED Phase** (Write failing test):
```python
# tests/test_config.py
import pytest
from nora_livekit.config import Config

def test_config_from_env_success(monkeypatch):
    monkeypatch.setenv("LIVEKIT_URL", "wss://test.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")

    config = Config.from_env()

    assert config.livekit_url == "wss://test.livekit.cloud"
    assert config.livekit_api_key == "test-key"
    assert config.livekit_api_secret == "test-secret"

def test_config_from_env_missing_required(monkeypatch):
    with pytest.raises(ValueError, match="LIVEKIT_URL is required"):
        Config.from_env()
```

**GREEN Phase** (Implement minimal code):
```python
# src/nora_livekit/config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: str | None = None

    @classmethod
    def from_env(cls) -> "Config":
        url = os.getenv("LIVEKIT_URL")
        if not url:
            raise ValueError("LIVEKIT_URL is required")

        api_key = os.getenv("LIVEKIT_API_KEY")
        if not api_key:
            raise ValueError("LIVEKIT_API_KEY is required")

        api_secret = os.getenv("LIVEKIT_API_SECRET")
        if not api_secret:
            raise ValueError("LIVEKIT_API_SECRET is required")

        return cls(
            livekit_url=url,
            livekit_api_key=api_key,
            livekit_api_secret=api_secret,
            health_check_port=int(os.getenv("HEALTH_CHECK_PORT", "8080")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            test_room=os.getenv("LIVEKIT_TEST_ROOM"),
        )
```

**REFACTOR Phase**: Add URL validation, type hints, docstrings

**Deliverables**:
- `src/nora_livekit/config.py` with Config dataclass
- `tests/test_config.py` with 90%+ coverage

**Verification**:
- `poetry run pytest tests/test_config.py -v` passes
- `poetry run pytest --cov=src/nora_livekit/config` shows 90%+ coverage

**TAG-IMPL-FOUNDATION-003**, **TAG-TEST-FOUNDATION-001**

---

#### Task 2.2: Setup Structured Logging
**Priority**: High
**Dependencies**: Task 2.1

**Steps**:
1. Configure structlog in `config.py`:
   ```python
   import structlog

   def setup_logging(config: Config):
       structlog.configure(
           processors=[
               structlog.stdlib.add_log_level,
               structlog.stdlib.add_logger_name,
               structlog.processors.TimeStamper(fmt="iso"),
               structlog.processors.StackInfoRenderer(),
               structlog.processors.format_exc_info,
               structlog.processors.JSONRenderer()
           ],
           wrapper_class=structlog.stdlib.BoundLogger,
           context_class=dict,
           logger_factory=structlog.stdlib.LoggerFactory(),
           cache_logger_on_first_use=True,
       )
   ```
2. Create logger instance: `log = structlog.get_logger()`
3. Test log output format (should be JSON)

**Deliverables**:
- Structlog configuration in `config.py`
- Logger instance available for import

**Verification**:
- Log output is valid JSON
- Log entries include timestamp, level, event

**TAG-IMPL-FOUNDATION-003**

---

#### Task 2.3: Implement Agent Class Skeleton (TDD)
**Priority**: Critical
**Dependencies**: Task 2.2

**RED Phase** (Write failing test):
```python
# tests/test_agent.py
import pytest
from nora_livekit.agent import NoraAgent
from nora_livekit.config import Config

@pytest.fixture
def mock_config():
    return Config(
        livekit_url="wss://test.livekit.cloud",
        livekit_api_key="test-key",
        livekit_api_secret="test-secret"
    )

def test_agent_initialization(mock_config):
    agent = NoraAgent(mock_config)
    assert agent.config == mock_config
    assert agent.room is None
```

**GREEN Phase** (Implement minimal code):
```python
# src/nora_livekit/agent.py
from dataclasses import dataclass
from nora_livekit.config import Config
import structlog

log = structlog.get_logger()

class NoraAgent:
    def __init__(self, config: Config):
        self.config = config
        self.room = None
        log.info("agent.initialized", config=config)
```

**REFACTOR Phase**: Add type hints, docstrings

**Deliverables**:
- `src/nora_livekit/agent.py` with NoraAgent class
- `tests/test_agent.py` with initialization test

**Verification**:
- Test passes
- Agent logs initialization event

**TAG-IMPL-FOUNDATION-002**, **TAG-TEST-FOUNDATION-002**

---

#### Task 2.4: Implement Room Join Logic (TDD)
**Priority**: Critical
**Dependencies**: Task 2.3

**RED Phase** (Write failing async test):
```python
# tests/test_agent.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_start_joins_room(mock_config):
    with patch("nora_livekit.agent.connect_to_room") as mock_connect:
        mock_room = AsyncMock()
        mock_connect.return_value = mock_room

        agent = NoraAgent(mock_config)
        await agent.start()

        assert agent.room == mock_room
        mock_connect.assert_called_once()
```

**GREEN Phase** (Implement room join):
```python
# src/nora_livekit/agent.py
from livekit import agents, rtc
import asyncio

class NoraAgent:
    async def start(self):
        log.info("agent.starting", url=self.config.livekit_url)

        # Connect to LiveKit server
        self.room = await agents.connect_to_room(
            url=self.config.livekit_url,
            token=self._generate_token(),
        )

        log.info("agent.room_joined", room_name=self.room.name)

    def _generate_token(self) -> str:
        # Generate LiveKit access token
        # (Implementation uses livekit-api library)
        pass
```

**REFACTOR Phase**: Extract token generation, add error handling

**Deliverables**:
- Room join logic in `agent.py`
- Async test for room join

**Verification**:
- Test passes with mocked LiveKit connection
- Logs show room join event

**TAG-IMPL-FOUNDATION-002**, **TAG-TEST-FOUNDATION-003**

---

#### Task 2.5: Implement Graceful Shutdown (TDD)
**Priority**: Critical
**Dependencies**: Task 2.4

**RED Phase** (Write failing test):
```python
# tests/test_agent.py
import pytest
import asyncio

@pytest.mark.asyncio
async def test_agent_stop_disconnects_gracefully(mock_config):
    agent = NoraAgent(mock_config)
    agent.room = AsyncMock()

    start_time = asyncio.get_event_loop().time()
    await agent.stop()
    end_time = asyncio.get_event_loop().time()

    assert end_time - start_time < 5.0  # Must complete in < 5 seconds
    agent.room.disconnect.assert_called_once()
```

**GREEN Phase** (Implement shutdown):
```python
# src/nora_livekit/agent.py
import signal

class NoraAgent:
    def __init__(self, config: Config):
        self.config = config
        self.room = None
        self._shutdown_event = asyncio.Event()

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        log.info("agent.shutdown_signal_received", signal=signum)
        self._shutdown_event.set()

    async def stop(self):
        log.info("agent.shutting_down")

        if self.room:
            await asyncio.wait_for(
                self.room.disconnect(),
                timeout=5.0
            )

        log.info("agent.stopped")
```

**REFACTOR Phase**: Add timeout handling, cleanup resources

**Deliverables**:
- Graceful shutdown logic in `agent.py`
- Test verifying shutdown timeout < 5 seconds

**Verification**:
- Test passes
- Agent disconnects cleanly on SIGTERM/SIGINT

**TAG-IMPL-FOUNDATION-002**, **TAG-TEST-FOUNDATION-004**

---

#### Task 2.6: Implement Main Entry Point
**Priority**: High
**Dependencies**: Task 2.5

**Steps**:
1. Add `__main__.py` to enable `python -m nora_livekit.agent`:
   ```python
   # src/nora_livekit/__main__.py
   import asyncio
   from nora_livekit.agent import NoraAgent
   from nora_livekit.config import Config, setup_logging

   async def main():
       config = Config.from_env()
       setup_logging(config)

       agent = NoraAgent(config)
       await agent.start()

       # Wait for shutdown signal
       await agent._shutdown_event.wait()
       await agent.stop()

   if __name__ == "__main__":
       asyncio.run(main())
   ```

**Deliverables**:
- `src/nora_livekit/__main__.py` entry point

**Verification**:
- `poetry run python -m nora_livekit.agent` starts agent

**TAG-IMPL-FOUNDATION-002**

---

## Phase 3: Health Check and Deployment

**Goal**: Implement FastAPI health check endpoint and Railway deployment configuration

### Tasks

#### Task 3.1: Implement Health Check Endpoint (TDD)
**Priority**: Critical
**Dependencies**: Phase 2 complete

**RED Phase** (Write failing test):
```python
# tests/test_server.py
from fastapi.testclient import TestClient
from nora_livekit.server import app

def test_health_check_returns_200():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "nora-livekit"
    }
```

**GREEN Phase** (Implement endpoint):
```python
# src/nora_livekit/server.py
from fastapi import FastAPI
import structlog

log = structlog.get_logger()
app = FastAPI(title="Nora LiveKit Agent")

@app.get("/health")
async def health_check():
    log.debug("health.request")
    return {
        "status": "healthy",
        "service": "nora-livekit"
    }
```

**REFACTOR Phase**: Add response model, OpenAPI documentation

**Deliverables**:
- `src/nora_livekit/server.py` with health endpoint
- `tests/test_server.py` with endpoint tests

**Verification**:
- Test passes
- `curl localhost:8080/health` returns 200 OK

**TAG-IMPL-FOUNDATION-004**, **TAG-TEST-FOUNDATION-005**

---

#### Task 3.2: Run Health Check Server in Background
**Priority**: High
**Dependencies**: Task 3.1

**Steps**:
1. Modify `__main__.py` to start FastAPI server in separate thread:
   ```python
   import threading
   import uvicorn
   from nora_livekit.server import app

   def run_health_server(port: int):
       uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")

   async def main():
       config = Config.from_env()
       setup_logging(config)

       # Start health check server in background
       health_thread = threading.Thread(
           target=run_health_server,
           args=(config.health_check_port,),
           daemon=True
       )
       health_thread.start()

       # Start agent
       agent = NoraAgent(config)
       await agent.start()

       await agent._shutdown_event.wait()
       await agent.stop()
   ```

**Deliverables**:
- Health server runs concurrently with agent
- Agent can be stopped without affecting health checks

**Verification**:
- Health endpoint responds while agent is running
- Agent shutdown does not block health server

**TAG-IMPL-FOUNDATION-004**

---

#### Task 3.3: Create Dockerfile
**Priority**: Critical
**Dependencies**: Task 3.2

**Steps**:
1. Create `Dockerfile` with multi-stage build:
   ```dockerfile
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

   # Health check
   HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
       CMD python -c "import httpx; httpx.get('http://localhost:8080/health')"

   # Run agent
   CMD ["python", "-m", "nora_livekit.agent"]
   ```

**Deliverables**:
- `Dockerfile` with multi-stage build
- Image size < 500MB

**Verification**:
- `docker build -t nora-livekit .` succeeds
- `docker images nora-livekit` shows size < 500MB
- `docker run --env-file .env nora-livekit` starts successfully

**TAG-IMPL-FOUNDATION-005**

---

#### Task 3.4: Create Railway Configuration
**Priority**: Critical
**Dependencies**: Task 3.3

**Steps**:
1. Create `railway.toml`:
   ```toml
   [build]
   builder = "DOCKERFILE"
   dockerfilePath = "Dockerfile"

   [deploy]
   startCommand = "python -m nora_livekit.agent"
   healthcheckPath = "/health"
   healthcheckTimeout = 100
   restartPolicyType = "ON_FAILURE"
   restartPolicyMaxRetries = 3

   [[deploy.environmentVariables]]
   name = "HEALTH_CHECK_PORT"
   value = "8080"
   ```

**Deliverables**:
- `railway.toml` configuration file

**Verification**:
- `railway up` deploys successfully
- Railway dashboard shows healthy status

**TAG-IMPL-FOUNDATION-006**

---

#### Task 3.5: Create README
**Priority**: Medium
**Dependencies**: All previous tasks

**Steps**:
1. Create `README.md` with sections:
   - Project overview
   - Prerequisites (Python 3.12+, Poetry, Railway CLI)
   - Local setup instructions
   - Environment variable configuration
   - Running locally
   - Running tests
   - Deployment to Railway
   - Troubleshooting

**Example README Structure**:
```markdown
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

3. Run locally:
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
```

**Deliverables**:
- Comprehensive `README.md`

**Verification**:
- README instructions can be followed by new developers

**TAG-IMPL-FOUNDATION-007**

---

## Phase 4: Integration Testing and Validation

**Goal**: Validate complete system with real LiveKit instance

### Tasks

#### Task 4.1: Create E2E Test Suite
**Priority**: High
**Dependencies**: Phase 3 complete

**Steps**:
1. Create `tests/test_integration.py`:
   ```python
   import pytest
   import asyncio
   from nora_livekit.agent import NoraAgent
   from nora_livekit.config import Config

   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_agent_joins_real_room():
       # Requires LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in env
       config = Config.from_env()
       agent = NoraAgent(config)

       await agent.start()
       assert agent.room is not None

       await asyncio.sleep(2)  # Wait for stable connection
       await agent.stop()
   ```

2. Add pytest marker configuration:
   ```toml
   # pyproject.toml
   [tool.pytest.ini_options]
   markers = [
       "integration: marks tests as integration tests (requires LiveKit)",
   ]
   ```

**Deliverables**:
- Integration test suite
- Pytest configuration for test markers

**Verification**:
- `poetry run pytest -m integration` passes with real LiveKit instance
- Agent successfully joins and leaves room

**TAG-TEST-FOUNDATION-006**

---

#### Task 4.2: Validate Railway Deployment
**Priority**: Critical
**Dependencies**: Task 4.1

**Manual Validation Steps**:
1. Deploy to Railway: `railway up`
2. Check deployment status in Railway dashboard
3. Verify health check endpoint: `curl https://<railway-url>/health`
4. Check Railway logs for agent startup events
5. Verify agent joins LiveKit room (check LiveKit dashboard)
6. Send SIGTERM and verify graceful shutdown in logs

**Success Criteria**:
- Railway deployment shows "Active" status
- Health check returns 200 OK
- Agent logs show room join event
- Graceful shutdown completes within 5 seconds

**Deliverables**:
- Deployment validation report (checklist)

**Verification**:
- All manual validation steps pass

**TAG-IMPL-FOUNDATION-006**

---

#### Task 4.3: Measure Performance Metrics
**Priority**: Medium
**Dependencies**: Task 4.2

**Metrics to Measure**:
1. Agent startup time (from process start to room join)
2. Health check response time
3. Graceful shutdown time
4. Docker image size
5. Memory usage (Railway metrics)

**Tools**:
- `time` command for startup measurement
- `curl -w` for health check latency
- `docker images` for image size
- Railway dashboard for memory metrics

**Success Criteria**:
- Startup time < 5 seconds
- Health check < 100ms
- Shutdown time < 5 seconds
- Image size < 500MB
- Memory usage < 256MB

**Deliverables**:
- Performance measurement report

**Verification**:
- All metrics meet success criteria

---

## Test Coverage Requirements

### Unit Tests (90%+ coverage)

**Files to Cover**:
- `src/nora_livekit/config.py`: 95%+ (all validation paths)
- `src/nora_livekit/agent.py`: 90%+ (core lifecycle)
- `src/nora_livekit/server.py`: 100% (simple endpoint)

**Test Categories**:
- Configuration validation (valid, invalid, missing variables)
- Agent initialization
- Room join (mocked LiveKit SDK)
- Graceful shutdown (with timeout)
- Health check endpoint response

### Integration Tests

**Scenarios**:
- Agent connects to real LiveKit room
- Agent handles reconnection on disconnect
- Health check endpoint responds during agent operation
- Graceful shutdown with active room connection

### Manual Tests

**Validation Checklist**:
- [ ] Docker build succeeds
- [ ] Docker image size < 500MB
- [ ] Railway deployment completes
- [ ] Health check endpoint accessible
- [ ] Agent logs visible in Railway dashboard
- [ ] Agent joins LiveKit room (verify in LiveKit dashboard)
- [ ] Graceful shutdown on Railway restart

---

## Dependencies and Risks

### Critical Path

```
Phase 1 (Project Init)
    ↓
Phase 2 (Agent Lifecycle)
    ↓
Phase 3 (Health Check + Deployment)
    ↓
Phase 4 (Integration Testing)
```

**Blocking Dependencies**:
- LiveKit Cloud instance must be provisioned before integration testing
- Railway account must be configured before deployment testing

### Risk Mitigation

**RISK-001: LiveKit SDK version incompatibility**
- **Mitigation**: Pin exact version ~1.0, test immediately after installation
- **Contingency**: Downgrade to stable version if breaking changes detected

**RISK-002: Railway deployment failure**
- **Mitigation**: Test Docker build locally before deploying
- **Contingency**: Debug using `railway logs` and `railway shell`

**RISK-003: Missing environment variables**
- **Mitigation**: Validate all required variables on startup with clear error messages
- **Contingency**: Provide `.env.template` with examples

**RISK-006: WebSocket connection instability**
- **Mitigation**: Implement retry logic with exponential backoff
- **Contingency**: Add connection timeout and fallback error handling

---

## Success Criteria

### Functional Success

- ✅ Agent joins LiveKit room successfully
- ✅ Health check endpoint returns 200 OK
- ✅ Graceful shutdown completes within 5 seconds
- ✅ All tests pass with 90%+ coverage
- ✅ Railway deployment succeeds

### Quality Success

- ✅ Mypy type checking passes with zero errors
- ✅ Ruff linting passes with zero errors
- ✅ Black formatting passes with zero changes
- ✅ Poetry dependencies lock without conflicts

### Performance Success

- ✅ Agent startup < 5 seconds
- ✅ Health check response < 100ms
- ✅ Docker image size < 500MB
- ✅ Memory usage < 256MB

---

## Next Steps

After SPEC-LIVEKIT-001 completion:

1. **SPEC-LIVEKIT-002 (Voice Pipeline)**:
   - Integrate Deepgram STT
   - Integrate Cartesia Sonic TTS
   - Implement voice activity detection (turn-detector)

2. **SPEC-LIVEKIT-003 (Session Context)**:
   - Add conversation state management
   - Implement session metadata tracking

3. **SPEC-LIVEKIT-004 (Business Hours)**:
   - Add business hours validation
   - Implement closed message handling

---

**TAG-IMPL-FOUNDATION-001** through **TAG-IMPL-FOUNDATION-008**
**TAG-TEST-FOUNDATION-001** through **TAG-TEST-FOUNDATION-006**

**END OF IMPLEMENTATION PLAN**
