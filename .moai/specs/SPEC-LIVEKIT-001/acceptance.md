# SPEC-LIVEKIT-001: Acceptance Criteria

**SPEC ID**: SPEC-LIVEKIT-001
**Title**: LiveKit Foundation & Infrastructure
**Status**: Draft
**Priority**: P0 (Critical)

---

## Acceptance Overview

This document defines the acceptance criteria for SPEC-LIVEKIT-001. All scenarios must pass before the SPEC can be marked as complete and merged to the main branch.

**Test Strategy**: Given-When-Then format for clarity and traceability
**Test Coverage Target**: 90%+ for lifecycle code
**Quality Gate**: TRUST 5 criteria (Test-first, Readable, Unified, Secured, Trackable)

---

## Acceptance Scenarios

### Scenario 1: Agent Deployment and Health Check

**Priority**: Critical
**Category**: Deployment
**Test Type**: Integration

**GIVEN** a Railway project is configured with LiveKit credentials
**AND** the Nora LiveKit agent codebase is pushed to the repository
**WHEN** Railway deployment is triggered via `railway up`
**THEN** the deployment completes successfully without errors
**AND** the Railway dashboard shows the service status as "Active"
**AND** the health check endpoint at `/health` returns HTTP 200 OK
**AND** the health check response body matches:
```json
{
  "status": "healthy",
  "service": "nora-livekit"
}
```
**AND** the health check response time is less than 100ms (99th percentile)

**Verification Method**:
```bash
# Deploy to Railway
railway up

# Check health endpoint
curl -w "\nResponse time: %{time_total}s\n" https://<railway-url>/health

# Expected output:
# {"status":"healthy","service":"nora-livekit"}
# Response time: 0.045s
```

**Success Metrics**:
- Deployment completes in < 5 minutes
- Health check consistently returns 200 OK
- Response time < 100ms

**TAG-TEST-FOUNDATION-005**, **TAG-TEST-FOUNDATION-006**

---

### Scenario 2: Room Connection Lifecycle

**Priority**: Critical
**Category**: Agent Lifecycle
**Test Type**: Integration

**GIVEN** a valid LiveKit Cloud instance is available
**AND** environment variables are configured:
```env
LIVEKIT_URL=wss://test.livekit.cloud
LIVEKIT_API_KEY=valid-api-key
LIVEKIT_API_SECRET=valid-api-secret
LIVEKIT_TEST_ROOM=test-room-001
```
**WHEN** the agent process starts via `python -m nora_livekit.agent`
**THEN** the agent initializes within 2 seconds
**AND** the agent connects to the LiveKit server via WebSocket
**AND** the agent joins the test room within 5 seconds of startup
**AND** the agent logs the following events in JSON format:
```json
{"event": "agent.starting", "level": "info", "timestamp": "2025-11-24T10:00:00Z"}
{"event": "agent.connected", "level": "info", "timestamp": "2025-11-24T10:00:02Z"}
{"event": "agent.room_joined", "level": "info", "room_name": "test-room-001", "timestamp": "2025-11-24T10:00:03Z"}
```
**AND** the LiveKit dashboard shows the agent as a participant in the test room

**Verification Method**:
```bash
# Start agent with timing
time poetry run python -m nora_livekit.agent

# Check logs for room join event
tail -f logs/agent.log | grep "agent.room_joined"

# Verify in LiveKit dashboard
# Navigate to Rooms → test-room-001 → Participants
# Confirm agent appears in participant list
```

**Success Metrics**:
- Agent startup < 5 seconds (from process start to room join)
- WebSocket connection established successfully
- Room join event logged within 5 seconds
- Agent visible in LiveKit dashboard

**TAG-TEST-FOUNDATION-003**, **TAG-TEST-FOUNDATION-006**

---

### Scenario 3: Graceful Shutdown

**Priority**: Critical
**Category**: Agent Lifecycle
**Test Type**: Integration

**GIVEN** the agent is running and connected to a LiveKit room
**AND** the agent has been active in the room for at least 10 seconds
**WHEN** a SIGTERM signal is sent to the agent process
**THEN** the agent begins graceful shutdown within 1 second
**AND** the agent logs the following events:
```json
{"event": "agent.shutdown_signal_received", "level": "info", "signal": 15, "timestamp": "2025-11-24T10:05:00Z"}
{"event": "agent.shutting_down", "level": "info", "timestamp": "2025-11-24T10:05:00Z"}
{"event": "agent.room_disconnected", "level": "info", "reason": "graceful_shutdown", "timestamp": "2025-11-24T10:05:02Z"}
{"event": "agent.stopped", "level": "info", "timestamp": "2025-11-24T10:05:03Z"}
```
**AND** the agent disconnects from the LiveKit room cleanly
**AND** the agent process exits with status code 0
**AND** the total shutdown time is less than 5 seconds (from SIGTERM to process exit)
**AND** the LiveKit dashboard shows the agent is no longer a participant in the room

**Verification Method**:
```bash
# Start agent
poetry run python -m nora_livekit.agent &
AGENT_PID=$!

# Wait for agent to join room
sleep 15

# Send SIGTERM and measure shutdown time
time kill -TERM $AGENT_PID
wait $AGENT_PID

# Check exit code
echo "Exit code: $?"

# Verify logs show graceful shutdown
grep "agent.stopped" logs/agent.log
```

**Success Metrics**:
- Shutdown initiated within 1 second of signal
- Room disconnection completes cleanly
- Process exits within 5 seconds total
- Exit code is 0 (success)
- No error logs during shutdown

**TAG-TEST-FOUNDATION-004**, **TAG-TEST-FOUNDATION-006**

---

### Scenario 4: Configuration Validation

**Priority**: High
**Category**: Configuration
**Test Type**: Unit

**GIVEN** the agent is starting up
**AND** the environment variable `LIVEKIT_URL` is missing
**WHEN** the configuration loader attempts to load environment variables
**THEN** the configuration loader raises a `ValueError` with the message:
```
LIVEKIT_URL is required
```
**AND** the agent process exits with status code 1 (failure)
**AND** the error is logged before process termination:
```json
{"event": "config.validation_failed", "level": "error", "missing_variable": "LIVEKIT_URL", "timestamp": "2025-11-24T10:00:00Z"}
```

**Verification Method**:
```python
# tests/test_config.py
import pytest
from nora_livekit.config import Config

def test_config_missing_livekit_url(monkeypatch):
    # Remove LIVEKIT_URL from environment
    monkeypatch.delenv("LIVEKIT_URL", raising=False)

    with pytest.raises(ValueError, match="LIVEKIT_URL is required"):
        Config.from_env()
```

**Success Metrics**:
- Test passes
- Clear error message indicates missing variable
- Process fails fast (within 1 second)

**TAG-TEST-FOUNDATION-001**

---

### Scenario 5: Poetry Dependency Installation

**Priority**: Critical
**Category**: Project Setup
**Test Type**: Integration

**GIVEN** a fresh clone of the Nora LiveKit repository
**AND** Poetry 1.8+ is installed on the system
**AND** Python 3.12+ is available
**WHEN** the command `poetry install` is executed
**THEN** Poetry resolves all dependencies from `poetry.lock`
**AND** all dependencies are installed without errors
**AND** the LiveKit Agents SDK version 1.0.x is installed
**AND** the installation completes within 60 seconds
**AND** the command `poetry show livekit-agents` displays:
```
name         : livekit-agents
version      : 1.0.x
description  : LiveKit Agents framework for building real-time voice agents
dependencies : [list of dependencies]
```

**Verification Method**:
```bash
# Fresh clone
git clone <repository-url>
cd nora-livekit

# Install dependencies with timing
time poetry install

# Verify LiveKit Agents SDK installation
poetry show livekit-agents

# Expected output includes:
# name         : livekit-agents
# version      : 1.0.x
```

**Success Metrics**:
- `poetry install` completes successfully
- No dependency resolution conflicts
- LiveKit Agents SDK v1.0.x installed
- Installation time < 60 seconds

**TAG-TEST-FOUNDATION-001**

---

### Scenario 6: Docker Build and Local Execution

**Priority**: High
**Category**: Deployment
**Test Type**: Integration

**GIVEN** the Dockerfile exists in the project root
**AND** the `src/` directory contains the Nora LiveKit source code
**WHEN** the command `docker build -t nora-livekit .` is executed
**THEN** the Docker build completes successfully without errors
**AND** the multi-stage build uses `python:3.12-slim` as the base image
**AND** the final image size is less than 500MB
**AND** the image contains the virtual environment at `/app/.venv`
**AND** the image contains the source code at `/app/src`
**WHEN** the container is started with `docker run --env-file .env nora-livekit`
**THEN** the agent starts successfully
**AND** the health check endpoint responds with HTTP 200 OK

**Verification Method**:
```bash
# Build Docker image
docker build -t nora-livekit .

# Check image size
docker images nora-livekit
# Expected: SIZE < 500MB

# Run container locally
docker run --env-file .env -p 8080:8080 nora-livekit &

# Wait for startup
sleep 5

# Test health check
curl http://localhost:8080/health
# Expected: {"status":"healthy","service":"nora-livekit"}

# Check container logs
docker logs <container-id>
# Expected: agent.room_joined event
```

**Success Metrics**:
- Docker build succeeds
- Image size < 500MB
- Container starts without errors
- Health check responds within 5 seconds

**TAG-TEST-FOUNDATION-006**

---

### Scenario 7: Structured Logging Output

**Priority**: Medium
**Category**: Logging
**Test Type**: Integration

**GIVEN** the agent is configured with `LOG_FORMAT=json`
**AND** the agent is running and connected to a LiveKit room
**WHEN** the agent logs operational events
**THEN** all log entries are in valid JSON format
**AND** each log entry contains the following fields:
- `event`: String describing the event (e.g., "agent.room_joined")
- `level`: Log level (debug, info, warning, error)
- `timestamp`: ISO 8601 formatted timestamp
**AND** room join events include `room_name` field
**AND** error events include `error` and `traceback` fields

**Verification Method**:
```bash
# Start agent and capture logs
poetry run python -m nora_livekit.agent > logs/agent.log 2>&1 &

# Wait for room join
sleep 10

# Validate JSON format
cat logs/agent.log | jq '.'
# Expected: All lines parse as valid JSON

# Verify required fields
cat logs/agent.log | jq 'select(.event == "agent.room_joined") | {event, level, timestamp, room_name}'
# Expected: All fields present
```

**Success Metrics**:
- All log entries are valid JSON
- Required fields present in all logs
- Room-specific events include room_name
- Logs are parseable by `jq` without errors

**TAG-IMPL-FOUNDATION-003**

---

### Scenario 8: Test Coverage Verification

**Priority**: High
**Category**: Code Quality
**Test Type**: Unit + Integration

**GIVEN** the complete test suite is implemented in `tests/`
**AND** pytest-cov is installed
**WHEN** the command `poetry run pytest --cov=src/nora_livekit --cov-report=term` is executed
**THEN** all tests pass without failures or errors
**AND** the test coverage report shows:
- `src/nora_livekit/config.py`: ≥ 95% coverage
- `src/nora_livekit/agent.py`: ≥ 90% coverage
- `src/nora_livekit/server.py`: 100% coverage
- Overall coverage: ≥ 90%
**AND** the coverage report includes the following tested areas:
- Configuration loading (valid, invalid, missing variables)
- Agent initialization
- Room join (mocked and real)
- Graceful shutdown (with timeout)
- Health check endpoint

**Verification Method**:
```bash
# Run tests with coverage
poetry run pytest --cov=src/nora_livekit --cov-report=term-missing

# Expected output:
# src/nora_livekit/config.py     95%
# src/nora_livekit/agent.py      92%
# src/nora_livekit/server.py    100%
# -----------------------------------------
# TOTAL                          90%

# Generate HTML coverage report
poetry run pytest --cov=src/nora_livekit --cov-report=html
open htmlcov/index.html
```

**Success Metrics**:
- All tests pass (0 failures, 0 errors)
- Overall coverage ≥ 90%
- No critical code paths uncovered
- Coverage report is reviewable in HTML format

**TAG-TEST-FOUNDATION-001**, **TAG-TEST-FOUNDATION-002**, **TAG-TEST-FOUNDATION-003**, **TAG-TEST-FOUNDATION-004**, **TAG-TEST-FOUNDATION-005**

---

## Quality Gate Criteria (TRUST 5)

### Test-first ✅

- **Requirement**: All code written following TDD RED-GREEN-REFACTOR cycle
- **Verification**: Git commit history shows test commits before implementation
- **Acceptance**: 90%+ test coverage achieved

### Readable ✅

- **Requirement**: Code is clear, well-documented, with type hints
- **Verification**:
  - `poetry run mypy src/` passes with zero errors
  - All functions have docstrings
  - Variable names are descriptive
- **Acceptance**: Mypy type checking passes, code review confirms readability

### Unified ✅

- **Requirement**: Consistent code style and patterns
- **Verification**:
  - `poetry run black --check .` passes with zero changes
  - `poetry run ruff check .` passes with zero errors
- **Acceptance**: Black and Ruff checks pass without modifications

### Secured ✅

- **Requirement**: No hardcoded credentials, input validation for environment variables
- **Verification**:
  - Code review confirms no `.env` files committed
  - Configuration loader validates all inputs
  - All credentials loaded from environment
- **Acceptance**: Security review passes, no credentials in code

### Trackable ✅

- **Requirement**: All changes logged, traceability tags present
- **Verification**:
  - All operational events logged with structured logging
  - TAG-IMPL and TAG-TEST tags documented
  - Git commit messages follow conventional commits
- **Acceptance**: Full traceability from SPEC to implementation to tests

---

## Definition of Done

### Code Complete

- ✅ All 8 acceptance scenarios pass
- ✅ Test coverage ≥ 90%
- ✅ Mypy, Black, Ruff checks pass
- ✅ All TAG-IMPL and TAG-TEST tags documented

### Deployment Ready

- ✅ Docker build succeeds, image size < 500MB
- ✅ Railway deployment completes successfully
- ✅ Health check endpoint accessible and responsive
- ✅ Agent joins LiveKit room within 5 seconds

### Documentation Complete

- ✅ README.md provides clear setup instructions
- ✅ `.env.template` documents all required variables
- ✅ Code includes comprehensive docstrings
- ✅ Implementation plan and acceptance criteria reviewed

### Quality Validated

- ✅ TRUST 5 criteria met (Test-first, Readable, Unified, Secured, Trackable)
- ✅ Manual testing checklist completed
- ✅ Performance metrics meet targets (startup < 5s, shutdown < 5s, health check < 100ms)
- ✅ No critical or high-severity issues in code review

---

## Manual Testing Checklist

### Local Development

- [ ] Clone repository from GitHub
- [ ] Install dependencies: `poetry install`
- [ ] Configure `.env` file with LiveKit credentials
- [ ] Run tests: `poetry run pytest`
- [ ] Start agent: `poetry run python -m nora_livekit.agent`
- [ ] Verify health check: `curl localhost:8080/health`
- [ ] Verify agent joins LiveKit room (check LiveKit dashboard)
- [ ] Send SIGTERM and verify graceful shutdown

### Docker Testing

- [ ] Build Docker image: `docker build -t nora-livekit .`
- [ ] Check image size: `docker images nora-livekit` (should be < 500MB)
- [ ] Run container: `docker run --env-file .env -p 8080:8080 nora-livekit`
- [ ] Verify health check: `curl localhost:8080/health`
- [ ] Verify agent joins room (check Docker logs)
- [ ] Stop container and verify graceful shutdown in logs

### Railway Deployment

- [ ] Deploy to Railway: `railway up`
- [ ] Verify deployment status in Railway dashboard (should show "Active")
- [ ] Access health check: `curl https://<railway-url>/health`
- [ ] Review Railway logs for agent startup events
- [ ] Verify agent joins LiveKit room (check LiveKit dashboard)
- [ ] Restart Railway service and verify graceful shutdown + restart

### LiveKit Integration

- [ ] Create test room in LiveKit dashboard
- [ ] Configure agent with test room name
- [ ] Start agent and verify it joins test room
- [ ] Verify agent appears in LiveKit dashboard participant list
- [ ] Stop agent and verify it leaves room cleanly
- [ ] Check LiveKit logs for connection/disconnection events

---

## Traceability Matrix

| Requirement ID | Implementation Tag         | Test Tag                   | Acceptance Scenario |
|----------------|----------------------------|----------------------------|---------------------|
| REQ-F-001      | TAG-IMPL-FOUNDATION-001    | TAG-TEST-FOUNDATION-001    | Scenario 5          |
| REQ-F-002      | TAG-IMPL-FOUNDATION-001    | TAG-TEST-FOUNDATION-001    | Scenario 5          |
| REQ-F-003      | TAG-IMPL-FOUNDATION-007    | TAG-TEST-FOUNDATION-001    | Scenario 4          |
| REQ-F-004      | TAG-IMPL-FOUNDATION-002    | TAG-TEST-FOUNDATION-002    | Scenario 2          |
| REQ-F-005      | TAG-IMPL-FOUNDATION-002    | TAG-TEST-FOUNDATION-004    | Scenario 3          |
| REQ-F-006      | TAG-IMPL-FOUNDATION-003    | TAG-TEST-FOUNDATION-001    | Scenario 7          |
| REQ-F-007      | TAG-IMPL-FOUNDATION-004    | TAG-TEST-FOUNDATION-005    | Scenario 1          |
| REQ-F-008      | TAG-IMPL-FOUNDATION-004    | TAG-TEST-FOUNDATION-005    | Scenario 1          |
| REQ-F-009      | TAG-IMPL-FOUNDATION-005    | TAG-TEST-FOUNDATION-006    | Scenario 6          |
| REQ-F-010      | TAG-IMPL-FOUNDATION-006    | TAG-TEST-FOUNDATION-006    | Scenario 1          |
| REQ-F-011      | TAG-IMPL-FOUNDATION-003    | TAG-TEST-FOUNDATION-001    | Scenario 4          |
| REQ-NF-001     | TAG-IMPL-FOUNDATION-002    | TAG-TEST-FOUNDATION-001    | Scenario 8          |
| REQ-NF-003     | TAG-IMPL-FOUNDATION-002    | TAG-TEST-FOUNDATION-001-006| Scenario 8          |
| REQ-I-001      | TAG-IMPL-FOUNDATION-004    | TAG-TEST-FOUNDATION-005    | Scenario 1          |
| REQ-I-002      | TAG-IMPL-FOUNDATION-002    | TAG-TEST-FOUNDATION-003    | Scenario 2          |
| REQ-I-003      | TAG-IMPL-FOUNDATION-003    | TAG-TEST-FOUNDATION-001    | Scenario 4          |
| REQ-DC-001     | TAG-IMPL-FOUNDATION-005    | TAG-TEST-FOUNDATION-006    | Scenario 6          |
| REQ-DC-002     | TAG-IMPL-FOUNDATION-006    | TAG-TEST-FOUNDATION-006    | Scenario 1          |

---

## Next SPEC Integration

### Handoff to SPEC-LIVEKIT-002 (Voice Pipeline)

**Prerequisites from SPEC-001**:
- ✅ Agent foundation with room lifecycle (TAG-IMPL-FOUNDATION-002)
- ✅ Configuration system for plugin credentials (TAG-IMPL-FOUNDATION-003)
- ✅ Structured logging infrastructure (TAG-IMPL-FOUNDATION-003)
- ✅ Railway deployment working (TAG-IMPL-FOUNDATION-006)

**Integration Points**:
- Voice pipeline will extend `NoraAgent` class
- STT/TTS plugins will use existing config system
- Voice events will use existing structlog configuration
- Deployment will reuse existing Dockerfile and railway.toml

**Validation**:
- SPEC-002 must verify agent foundation still works after voice integration
- End-to-end test should include basic room join + voice pipeline
- Performance metrics must not degrade (startup time, shutdown time)

---

**TAG-TEST-FOUNDATION-001** through **TAG-TEST-FOUNDATION-006**

**END OF ACCEPTANCE CRITERIA**
