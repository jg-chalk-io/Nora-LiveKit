---
id: SPEC-LIVEKIT-001
version: 1.0.0
status: completed
created: 2025-11-24
updated: 2025-11-24
completed_at: 2025-11-24
author: @user
priority: P0
domain: INFRA
estimated_loc: 300
actual_loc: 471
complexity: low
dependencies: []
---

# SPEC-LIVEKIT-001: LiveKit Foundation & Infrastructure

## HISTORY

### [1.0.0] - 2025-11-24
- Initial specification created
- Foundation for 8-SPEC LiveKit migration
- User approved Python approach with Cartesia Sonic TTS

---

## Executive Summary

This specification establishes the foundational infrastructure for migrating Nora voice agent from Ultravox/Jambonz to LiveKit. It defines the Python project structure, LiveKit Agents SDK integration, Railway deployment configuration, and basic room connection lifecycle.

**Strategic Importance**: This is the first and most critical SPEC in the 8-SPEC migration roadmap. All subsequent SPECs (Voice Pipeline, Session Context, Business Hours, Conversation State, Supabase Integration, Tool Integrations, and End-to-End Testing) depend on this foundation.

**Scope**: Infrastructure setup only. Voice pipeline, business logic, and tool integrations are explicitly out of scope for this SPEC.

---

## Environment

### Technical Environment

**Development Environment**:
- Python 3.12+ with Poetry dependency management
- LiveKit Cloud or self-hosted server
- Railway deployment platform
- Git version control

**Runtime Environment**:
- Railway cloud platform
- LiveKit Agents SDK v1.0 with plugins
- FastAPI for health check endpoints
- Structlog for JSON logging

**External Dependencies**:
- LiveKit Cloud instance (wss://your-livekit-instance.livekit.cloud)
- Railway account with deployment permissions
- Environment variables: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET

### Operational Context

**Deployment Model**: Containerized Python application deployed to Railway
**Scaling Model**: Single agent instance per Railway service (horizontal scaling in future SPECs)
**Monitoring**: Railway dashboard logs, health check endpoint
**Security**: Environment-based credential management, no hardcoded secrets

---

## Assumptions

### Technology Assumptions

**ASM-T-001**: LiveKit Agents SDK v1.0 API remains stable during development lifecycle
**ASM-T-002**: Railway platform supports Python 3.12+ Docker containers
**ASM-T-003**: LiveKit Cloud WebSocket connectivity is reliable (99.9% uptime SLA)
**ASM-T-004**: Poetry lock file ensures reproducible dependency installation
**ASM-T-005**: FastAPI health check endpoint is sufficient for Railway health monitoring

### Business Assumptions

**ASM-B-001**: Foundation infrastructure is prioritized over feature development
**ASM-B-002**: Existing Supabase schema can be reused without migration
**ASM-B-003**: Cartesia Sonic TTS integration will be implemented in SPEC-LIVEKIT-002
**ASM-B-004**: Railway deployment costs are acceptable for initial development phase

### Constraint Assumptions

**ASM-C-001**: No voice pipeline or business logic in this SPEC (deferred to SPEC-002 through SPEC-007)
**ASM-C-002**: Test coverage target is 90%+ for lifecycle code (excluding infrastructure boilerplate)
**ASM-C-003**: Graceful shutdown must complete within 5 seconds
**ASM-C-004**: Agent must join LiveKit room within 5 seconds of startup

---

## Requirements

### Functional Requirements

#### Project Structure

**REQ-F-001**: MUST provide Python project structure with Poetry dependency management
- **Rationale**: Ensures reproducible builds and dependency isolation
- **Verification**: `poetry install` completes without errors
- **Traceability**: Links to pyproject.toml, poetry.lock

**REQ-F-002**: MUST install LiveKit Agents SDK v1.0 with plugins (openai, deepgram, cartesia, turn-detector)
- **Rationale**: Core framework for LiveKit agent development
- **Verification**: `poetry show livekit-agents` confirms v1.0.x installation
- **Traceability**: Links to pyproject.toml dependencies section

**REQ-F-003**: MUST provide .env.template with example configuration
- **Rationale**: Documents required environment variables for developers
- **Verification**: File exists with all required variables documented
- **Traceability**: Links to .env.template file

#### Agent Lifecycle

**REQ-F-004**: MUST implement basic agent class with room join and leave lifecycle methods
- **Rationale**: Core agent functionality for LiveKit room management
- **Verification**: Unit tests verify join/leave methods execute successfully
- **Traceability**: Links to src/nora_livekit/agent.py

**REQ-F-005**: MUST handle graceful shutdown on SIGTERM/SIGINT signals
- **Rationale**: Ensures clean disconnection from LiveKit rooms
- **Verification**: Integration test verifies shutdown completes within 5 seconds
- **Traceability**: Links to agent.py shutdown handler

**REQ-F-006**: MUST log room connection events using structlog with JSON output
- **Rationale**: Enables structured log analysis in Railway dashboard
- **Verification**: Log output contains JSON-formatted events
- **Traceability**: Links to config.py logging setup

#### Health Check

**REQ-F-007**: MUST provide FastAPI health check endpoint at /health returning 200 OK
- **Rationale**: Railway requires health check for deployment monitoring
- **Verification**: `curl localhost:8080/health` returns 200 with JSON response
- **Traceability**: Links to src/nora_livekit/server.py

**REQ-F-008**: SHALL expose health endpoint response format: `{"status": "healthy", "service": "nora-livekit"}`
- **Rationale**: Standardized health check format for monitoring integrations
- **Verification**: Response body matches exact JSON structure
- **Traceability**: Links to server.py health endpoint handler

#### Deployment

**REQ-F-009**: MUST include Dockerfile with multi-stage build (builder + runtime)
- **Rationale**: Optimizes image size and build caching
- **Verification**: Docker build succeeds locally, image size < 500MB
- **Traceability**: Links to Dockerfile

**REQ-F-010**: MUST include railway.toml for Railway deployment configuration
- **Rationale**: Defines Railway service configuration as code
- **Verification**: Railway deployment succeeds using railway.toml
- **Traceability**: Links to railway.toml

**REQ-F-011**: MUST validate required environment variables on startup
- **Rationale**: Fail fast if configuration is incomplete
- **Verification**: Agent exits with clear error if LIVEKIT_URL is missing
- **Traceability**: Links to config.py validation logic

### Non-Functional Requirements

#### Code Quality

**REQ-NF-001**: SHOULD use type hints throughout codebase
- **Rationale**: Enables static type checking with mypy
- **Verification**: mypy runs without errors
- **Traceability**: Links to myproject.toml mypy configuration

**REQ-NF-002**: SHOULD format code with Black and lint with Ruff
- **Rationale**: Ensures consistent code style
- **Verification**: `black --check .` and `ruff check .` pass
- **Traceability**: Links to pyproject.toml tool configurations

**REQ-NF-003**: SHOULD achieve 90%+ test coverage for lifecycle code
- **Rationale**: Ensures reliability of critical infrastructure
- **Verification**: pytest-cov report shows 90%+ coverage
- **Traceability**: Links to tests/test_agent.py

#### Documentation

**REQ-NF-004**: SHOULD include README with clear setup and deployment instructions
- **Rationale**: Enables developers to onboard quickly
- **Verification**: Manual review confirms clarity and completeness
- **Traceability**: Links to README.md

**REQ-NF-005**: SHOULD document all environment variables in .env.template
- **Rationale**: Provides single source of truth for configuration
- **Verification**: All variables in code are documented in template
- **Traceability**: Links to .env.template

#### Performance

**REQ-NF-006**: SHOULD join LiveKit room within 5 seconds of agent startup
- **Rationale**: Ensures responsive agent initialization
- **Verification**: Integration test measures join time < 5s
- **Traceability**: Links to tests/test_agent.py integration tests

**REQ-NF-007**: SHOULD complete graceful shutdown within 5 seconds
- **Rationale**: Prevents Railway deployment delays during updates
- **Verification**: Integration test measures shutdown time < 5s
- **Traceability**: Links to agent.py shutdown handler

### Interface Requirements

**REQ-I-001**: SHALL expose /health endpoint on port 8080
- **Rationale**: Railway standard health check port
- **Verification**: FastAPI binds to 0.0.0.0:8080
- **Traceability**: Links to server.py uvicorn configuration

**REQ-I-002**: SHALL connect to LiveKit server using WebSocket protocol
- **Rationale**: LiveKit Agents SDK default connection method
- **Verification**: LiveKit SDK connection logs show WebSocket upgrade
- **Traceability**: Links to LiveKit SDK configuration

**REQ-I-003**: SHALL use environment variables for all external configuration
- **Rationale**: Follows 12-factor app principles
- **Verification**: No hardcoded URLs or credentials in source code
- **Traceability**: Links to config.py environment loader

### Design Constraints

**REQ-DC-001**: MUST use Python 3.12 or higher
- **Rationale**: Leverage modern Python features and performance improvements
- **Verification**: Dockerfile specifies python:3.12-slim base image
- **Traceability**: Links to Dockerfile and pyproject.toml

**REQ-DC-002**: MUST be deployable to Railway without manual intervention
- **Rationale**: Enables automated CI/CD pipelines
- **Verification**: Railway deployment succeeds via railway up
- **Traceability**: Links to railway.toml

**REQ-DC-003**: MUST NOT include voice pipeline or business logic
- **Rationale**: Maintains clear separation of concerns across SPECs
- **Verification**: Code review confirms no STT/TTS or business hours logic
- **Traceability**: Links to SPEC-LIVEKIT-002 (Voice Pipeline)

**REQ-DC-004**: MUST use Poetry for dependency management
- **Rationale**: Provides reliable lock file and virtual environment management
- **Verification**: pyproject.toml and poetry.lock exist
- **Traceability**: Links to pyproject.toml

---

## Specifications

### Project Structure

```
nora-livekit/
├── src/
│   └── nora_livekit/
│       ├── __init__.py           # Package initialization
│       ├── agent.py              # Main agent class with lifecycle
│       ├── config.py             # Environment configuration loader
│       └── server.py             # FastAPI health check server
├── tests/
│   ├── __init__.py
│   ├── test_agent.py             # Agent lifecycle tests
│   ├── test_config.py            # Configuration loader tests
│   └── test_server.py            # Health endpoint tests
├── .env.template                 # Example environment variables
├── .gitignore                    # Python/LiveKit specific ignores
├── Dockerfile                    # Multi-stage Docker build
├── railway.toml                  # Railway deployment config
├── pyproject.toml                # Poetry dependencies and tools
├── poetry.lock                   # Locked dependency versions
└── README.md                     # Setup and deployment guide
```

### Technology Stack

#### Core Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.12"
livekit-agents = {version = "~1.0", extras = ["openai", "deepgram", "cartesia", "turn-detector"]}
fastapi = "~0.115"
uvicorn = {version = "~0.32", extras = ["standard"]}
python-dotenv = "~1.0"
structlog = "~24.4"
httpx = "~0.27"

[tool.poetry.group.dev.dependencies]
pytest = "~8.3"
pytest-asyncio = "~0.24"
pytest-cov = "~6.0"
ruff = "~0.7"
black = "~24.10"
mypy = "~1.13"
```

**Version Pinning Strategy**:
- Major versions pinned with `~` (compatible releases)
- LiveKit Agents SDK pinned to 1.0.x for stability
- Development dependencies pinned to latest stable versions

#### Environment Configuration

**Required Variables**:
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
```

**Optional Variables**:
```env
# Room Configuration (for testing)
LIVEKIT_TEST_ROOM=test-room-001

# Deployment Environment
RAILWAY_ENVIRONMENT=production
```

### Agent Implementation

#### Agent Class Specification

**File**: `src/nora_livekit/agent.py`

**Key Methods**:
1. `__init__(self, config: Config)`: Initialize agent with configuration
2. `async def start(self)`: Connect to LiveKit server and join room
3. `async def stop(self)`: Gracefully disconnect from room and cleanup
4. `async def on_room_joined(self, room: Room)`: Handle room join event
5. `async def on_room_disconnected(self)`: Handle disconnection event

**Lifecycle Flow**:
```
1. Agent initialization (load config, setup logging)
2. Start method called
3. Connect to LiveKit server via WebSocket
4. Join configured room
5. Log room joined event
6. Wait for shutdown signal (SIGTERM/SIGINT)
7. Call stop method
8. Disconnect from room
9. Cleanup resources
10. Exit process
```

**Error Handling**:
- Connection failures: Log error, retry with exponential backoff (max 3 retries)
- Room join failures: Log error, exit with non-zero status
- Shutdown timeout: Force exit after 5 seconds

#### Configuration Loader Specification

**File**: `src/nora_livekit/config.py`

**Configuration Class**:
```python
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
        """Load configuration from environment variables"""
        # Validate required variables
        # Return Config instance
```

**Validation Rules**:
- `livekit_url`: Must start with `wss://` or `ws://`
- `livekit_api_key`: Non-empty string
- `livekit_api_secret`: Non-empty string
- `health_check_port`: Integer between 1024-65535
- `log_level`: One of DEBUG, INFO, WARNING, ERROR, CRITICAL

#### Health Check Server Specification

**File**: `src/nora_livekit/server.py`

**FastAPI Application**:
```python
from fastapi import FastAPI

app = FastAPI(title="Nora LiveKit Agent")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "nora-livekit"
    }
```

**Startup Configuration**:
- Bind to `0.0.0.0:{HEALTH_CHECK_PORT}`
- Run with uvicorn in separate thread from agent
- Log server startup/shutdown events

### Deployment Specification

#### Dockerfile

**Multi-Stage Build**:

**Stage 1 - Builder**:
```dockerfile
FROM python:3.12-slim as builder

WORKDIR /app

# Install Poetry
RUN pip install poetry==1.8.3

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies to /app/.venv
RUN poetry config virtualenvs.in-project true && \
    poetry install --no-root --only main
```

**Stage 2 - Runtime**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code
COPY src/ /app/src/

# Set Python path
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Run agent
CMD ["python", "-m", "nora_livekit.agent"]
```

**Image Optimization**:
- Use slim base image (reduces size by 70% vs full image)
- Multi-stage build (excludes Poetry and build dependencies)
- Target image size: < 500MB

#### Railway Configuration

**File**: `railway.toml`

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

**Deployment Process**:
1. Railway detects railway.toml
2. Builds Docker image using Dockerfile
3. Deploys container
4. Monitors /health endpoint
5. Restarts on failure (max 3 retries)

### Logging Specification

**Structlog Configuration**:

```python
import structlog

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

**Log Events**:
- `agent.starting`: Agent initialization
- `agent.connected`: LiveKit server connection established
- `agent.room_joined`: Room join success (include room_name)
- `agent.room_disconnected`: Room disconnection (include reason)
- `agent.shutting_down`: Shutdown initiated
- `agent.stopped`: Shutdown complete
- `health.request`: Health check endpoint called

**Log Levels**:
- INFO: Normal operational events (room join, shutdown)
- WARNING: Recoverable errors (connection retry)
- ERROR: Non-recoverable errors (configuration validation failure)
- DEBUG: Detailed diagnostic information (WebSocket messages)

---

## Traceability

### SPEC Dependencies

**Depends On**: None (foundational SPEC)

**Enables**:
- SPEC-LIVEKIT-002 (Voice Pipeline): Requires agent foundation for STT/TTS integration
- SPEC-LIVEKIT-003 (Session Context): Requires agent lifecycle for conversation state
- SPEC-LIVEKIT-004 (Business Hours): Requires agent infrastructure for scheduling logic
- SPEC-LIVEKIT-005 (Conversation State): Requires agent foundation for state machine
- SPEC-LIVEKIT-006 (Supabase Integration): Requires agent for database connections
- SPEC-LIVEKIT-007 (Tool Integrations): Requires agent for tool execution
- SPEC-LIVEKIT-008 (End-to-End Testing): Requires complete agent for testing

### Implementation Tags

**TAG-IMPL-FOUNDATION-001**: pyproject.toml Poetry configuration
**TAG-IMPL-FOUNDATION-002**: src/nora_livekit/agent.py agent class
**TAG-IMPL-FOUNDATION-003**: src/nora_livekit/config.py configuration loader
**TAG-IMPL-FOUNDATION-004**: src/nora_livekit/server.py health check server
**TAG-IMPL-FOUNDATION-005**: Dockerfile multi-stage build
**TAG-IMPL-FOUNDATION-006**: railway.toml deployment configuration
**TAG-IMPL-FOUNDATION-007**: .env.template environment documentation
**TAG-IMPL-FOUNDATION-008**: tests/test_agent.py lifecycle tests

### Test Tags

**TAG-TEST-FOUNDATION-001**: Unit test for config validation
**TAG-TEST-FOUNDATION-002**: Unit test for agent initialization
**TAG-TEST-FOUNDATION-003**: Integration test for room join
**TAG-TEST-FOUNDATION-004**: Integration test for graceful shutdown
**TAG-TEST-FOUNDATION-005**: Integration test for health check endpoint
**TAG-TEST-FOUNDATION-006**: E2E test for Railway deployment

---

## Risk Assessment

| Risk ID | Risk Description | Impact | Probability | Mitigation Strategy | Owner |
|---------|------------------|--------|-------------|---------------------|-------|
| RISK-001 | LiveKit SDK version incompatibility | High | Low | Pin exact version ~1.0, test immediately after installation | TDD Implementer |
| RISK-002 | Railway deployment failure | Medium | Low | Test Docker build locally before deploying, validate railway.toml | DevOps Expert |
| RISK-003 | Missing environment variables | Medium | Medium | Validate all required variables on startup, fail fast with clear errors | Backend Expert |
| RISK-004 | Python version mismatch | Low | Low | Specify Python 3.12 in Dockerfile and pyproject.toml | Backend Expert |
| RISK-005 | Health check timeout | Medium | Low | Ensure /health endpoint responds within 100ms, run in separate thread | Backend Expert |
| RISK-006 | WebSocket connection instability | Medium | Medium | Implement retry logic with exponential backoff, log all connection events | Backend Expert |
| RISK-007 | Graceful shutdown timeout | Medium | Low | Set hard timeout at 5 seconds, force exit if exceeded | Backend Expert |

---

## Success Metrics

### Deployment Metrics

**DM-001**: Railway deployment completes without errors (100% success rate)
**DM-002**: Health check endpoint returns 200 OK within 100ms (99.9% uptime)
**DM-003**: Docker image size < 500MB
**DM-004**: Poetry install completes in < 60 seconds

### Performance Metrics

**PM-001**: Agent joins LiveKit room within 5 seconds of startup (95th percentile)
**PM-002**: Graceful shutdown completes within 5 seconds (99th percentile)
**PM-003**: Health check endpoint responds within 100ms (99th percentile)

### Quality Metrics

**QM-001**: Test coverage ≥ 90% for lifecycle code
**QM-002**: Mypy type checking passes with zero errors
**QM-003**: Ruff linting passes with zero errors
**QM-004**: Black formatting passes with zero changes

---

## Glossary

**LiveKit Agents SDK**: Python framework for building LiveKit agents with voice capabilities
**Railway**: Cloud platform for deploying containerized applications
**Poetry**: Python dependency management and packaging tool
**Structlog**: Structured logging library for Python
**FastAPI**: Modern Python web framework for building APIs
**Multi-stage build**: Docker build process with separate builder and runtime stages
**Graceful shutdown**: Clean disconnection from services before process termination
**Health check endpoint**: HTTP endpoint for monitoring service health
**WebSocket**: Full-duplex communication protocol over TCP
**SIGTERM/SIGINT**: Unix signals for process termination

---

**END OF SPECIFICATION**
