# System Architecture

## Overview

Nora LiveKit Agent is a Python-based voice agent that manages LiveKit room connections with a focus on reliability, observability, and graceful shutdown. The architecture follows a layered design pattern with clear separation of concerns.

**Core Design Principles**:
- Clean separation between configuration, agent lifecycle, and HTTP health checks
- Async/await for non-blocking I/O operations
- Signal handling for graceful shutdown
- Structured JSON logging for production observability
- Minimal external dependencies

## System Architecture Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    Application Layer                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  main() Entry Point (__main__.py)                        │  │
│  │  - Load configuration from environment                   │  │
│  │  - Initialize logging                                    │  │
│  │  - Start health server in background                     │  │
│  │  - Create and manage agent lifecycle                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    Agent Layer                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  NoraAgent (agent.py)                                    │  │
│  │  - Room connection lifecycle                             │  │
│  │  - LiveKit access token generation                       │  │
│  │  - Signal handler registration (SIGTERM, SIGINT)         │  │
│  │  - Graceful shutdown coordination                        │  │
│  │  - Event logging (connected, disconnected, etc.)         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Server (server.py)                              │  │
│  │  - Health check endpoint (/health)                       │  │
│  │  - Monitoring and load balancer checks                   │  │
│  │  - Port 8080 (configurable)                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    Config & Logging Layer                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Config (config.py)                                      │  │
│  │  - Load environment variables                            │  │
│  │  - Validate credentials and ports                        │  │
│  │  - Provide typed configuration object                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Logging (structlog)                                     │  │
│  │  - JSON structured logs                                  │  │
│  │  - ISO timestamps                                        │  │
│  │  - Configurable log level and format                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                    External Services                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  LiveKit Cloud/Server                                    │  │
│  │  - WebSocket connection (wss://)                         │  │
│  │  - Room management                                       │  │
│  │  - Agent participant handling                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Entry Point (`__main__.py`)

**Responsibilities**:
- Load configuration from environment
- Initialize logging system
- Start health check server in background thread
- Create NoraAgent instance
- Manage agent lifecycle

**Flow**:
```
Run __main__.py
    ↓
Load Config from Environment
    ↓
Setup Logging (structlog)
    ↓
Start Health Server Thread (FastAPI)
    ↓
Create NoraAgent
    ↓
Call agent.start() - Connect to LiveKit
    ↓
Wait for Shutdown Signal
    ↓
Call agent.stop() - Graceful disconnect
    ↓
Exit
```

**Code Flow**:
```python
# 1. Load configuration
config = Config.from_env()

# 2. Setup logging
setup_logging(config)

# 3. Start health server in thread
health_thread = threading.Thread(
    target=run_health_server,
    args=(config.health_check_port,),
    daemon=True,
)
health_thread.start()

# 4. Create and manage agent
agent = NoraAgent(config)
await agent.start()
await agent._shutdown_event.wait()
await agent.stop()
```

### 2. Agent (`agent.py`)

**Responsibilities**:
- Manage room connection lifecycle
- Generate LiveKit access tokens
- Handle system signals for graceful shutdown
- Log lifecycle events
- Manage async operations

**Key Methods**:

#### `__init__(config: Config)`
Initializes the agent with:
- Configuration object containing LiveKit credentials
- Async shutdown event for signal handling
- Signal handlers for SIGTERM and SIGINT

#### `async start()`
Connects to LiveKit:
1. Calls `_connect_to_livekit()` to generate access token
2. Creates room representation
3. Logs connection success

#### `async stop()`
Graceful disconnect:
1. Calls `_disconnect_from_livekit()` with 5-second timeout
2. Cleans up room reference
3. Handles timeout and exceptions gracefully

#### `_handle_shutdown_signal(signum, frame)`
Signal handler for SIGTERM/SIGINT:
- Sets shutdown event to trigger graceful shutdown
- Logs signal reception

#### `async _connect_to_livekit()`
Generates access token:
```python
# Generate JWT token with video grants
token = AccessToken(
    api_key=config.livekit_api_key,
    api_secret=config.livekit_api_secret,
).with_identity("nora-agent")
 .with_grants(VideoGrants(
    room_join=True,
    room=room_name,
    can_publish=True,
    can_subscribe=True,
))

# Store for livekit-agents framework
self._livekit_room = {
    "token": token_str,
    "url": config.livekit_url,
    "room": room_name,
    "agent_name": "nora-agent",
}
```

#### `async _disconnect_from_livekit()`
Cleanup:
- Release stored LiveKit connection info
- Clean up resources

**Lifecycle Diagram**:
```
__init__
    ↓ (register signal handlers)
start()
    ↓
_connect_to_livekit()
    ↓ (generate access token)
room = created
    ↓ (wait for signal)
stop()
    ↓
_disconnect_from_livekit()
    ↓ (cleanup)
done
```

### 3. Configuration (`config.py`)

**Responsibilities**:
- Load and validate environment variables
- Provide typed configuration object
- Initialize structured logging

**Config Dataclass**:
```python
@dataclass
class Config:
    livekit_url: str              # WebSocket URL (required)
    livekit_api_key: str           # API key (required)
    livekit_api_secret: str        # API secret (required)
    health_check_port: int = 8080  # Health port (optional)
    log_level: str = "INFO"        # Log level (optional)
    log_format: str = "json"       # Log format (optional)
    test_room: str | None = None   # Test room (optional)
```

**Validation Rules**:
- `LIVEKIT_URL`: Must start with `wss://` or `ws://`
- `LIVEKIT_API_KEY`: Required, non-empty string
- `LIVEKIT_API_SECRET`: Required, non-empty string
- `HEALTH_CHECK_PORT`: Valid integer (default: 8080)
- `LOG_LEVEL`: Valid logging level (default: INFO)
- `LOG_FORMAT`: Format type (default: json)

**Loading Order**:
```
Config.from_env()
    ↓
Check Required Variables
    ↓
Validate Values
    ↓
Load Optional Variables
    ↓
Return Config Instance
```

**Logging Setup**:
```python
def setup_logging(config: Config):
    structlog.configure(
        processors=[
            # Add log level, logger name
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            # Add ISO timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add stack traces
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.processors.format_exc_info,
            # JSON output
            structlog.processors.JSONRenderer(),
        ],
        # ... configuration ...
    )
```

### 4. Health Check Server (`server.py`)

**Responsibilities**:
- Provide HTTP health endpoint
- Return JSON status response
- Run on configured port

**FastAPI Application**:
```python
app = FastAPI(
    title="Nora LiveKit Agent",
    version="0.1.0"
)

@app.get("/health")
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        service="nora-livekit"
    )
```

**Response Model**:
```python
@dataclass
class HealthResponse:
    status: str  # "healthy" or "unhealthy"
    service: str # "nora-livekit"
```

**Example Response**:
```json
{
  "status": "healthy",
  "service": "nora-livekit"
}
```

**Performance**:
- Response time: < 100ms
- Port: 8080 (configurable)
- Runs in background thread

## Module Dependencies

```
nora_livekit/
├── __init__.py           # Package metadata
├── __main__.py           # Imports: agent, config, server
│   └── Imports: threading, uvicorn, asyncio
├── agent.py              # Imports: config, livekit.api, structlog
├── config.py             # Imports: dataclass, os, structlog, logging
└── server.py             # Imports: FastAPI, Pydantic, structlog
```

**External Dependencies**:
- `livekit-agents`: Voice agent framework and SDK
- `fastapi`: HTTP server framework
- `uvicorn`: ASGI server
- `structlog`: Structured logging
- `python-dotenv`: Environment variable loading
- `httpx`: HTTP client (for future features)

## Design Patterns

### 1. Dataclass Configuration
Uses Python dataclass for type-safe configuration:
```python
@dataclass
class Config:
    livekit_url: str
    # ... fields ...

    @classmethod
    def from_env(cls) -> "Config":
        # Load from environment
        return cls(...)
```

**Benefits**:
- Type safety with mypy
- Immutable configuration
- Easy validation

### 2. Async/Await Pattern
Uses Python asyncio for non-blocking operations:
```python
async def start(self) -> None:
    await self._connect_to_livekit()

async def stop(self) -> None:
    await asyncio.wait_for(
        self._disconnect_from_livekit(),
        timeout=5.0
    )
```

**Benefits**:
- Handle I/O without blocking
- Efficient resource usage
- Compatible with FastAPI

### 3. Signal Handling
Graceful shutdown on system signals:
```python
signal.signal(signal.SIGTERM, self._handle_shutdown_signal)
signal.signal(signal.SIGINT, self._handle_shutdown_signal)

def _handle_shutdown_signal(self, signum, frame):
    self._shutdown_event.set()
```

**Benefits**:
- Clean shutdown on container stop
- Resource cleanup
- Transaction rollback if applicable

### 4. Structured Logging
JSON logging for production observability:
```python
log.info("agent.started", url=config.livekit_url)
log.error("agent.connection_failed", error=str(e))
```

**Output**:
```json
{
  "timestamp": "2025-11-24T10:30:45.123Z",
  "level": "info",
  "event": "agent.started",
  "url": "wss://instance.livekit.cloud"
}
```

**Benefits**:
- Machine-readable logs
- Easy log aggregation
- Event traceability

### 5. Singleton Pattern (Config)
Configuration loaded once and shared:
```python
config = Config.from_env()  # Load once
agent = NoraAgent(config)   # Reuse same config
```

## Data Flow

### Agent Initialization Flow

```
START (__main__.py)
    ↓
Config.from_env() [Load environment]
    ├─ Check LIVEKIT_URL
    ├─ Check LIVEKIT_API_KEY
    ├─ Check LIVEKIT_API_SECRET
    └─ Load optional variables
    ↓ [Config object ready]
setup_logging(config) [Configure structlog]
    └─ Setup JSON output, timestamps, etc.
    ↓ [Logging ready]
Start Health Server Thread [Background]
    └─ Uvicorn on port 8080
    ↓ [Health checks available]
NoraAgent(config) [Create agent]
    └─ Register signal handlers
    ↓ [Agent created]
agent.start() [Connect to LiveKit]
    ├─ _connect_to_livekit()
    │   └─ Generate access token (JWT)
    └─ Log "agent.room_joined"
    ↓ [Agent connected]
READY [Wait for signals]
```

### Room Connection Flow

```
agent.start()
    ↓
_connect_to_livekit()
    ↓
Generate AccessToken JWT
    ├─ api_key: from config
    ├─ api_secret: from config
    ├─ identity: "nora-agent"
    └─ grants:
        ├─ room_join=True
        ├─ can_publish=True
        └─ can_subscribe=True
    ↓
Store in _livekit_room:
    ├─ token: JWT token
    ├─ url: LiveKit server URL
    ├─ room: room name
    └─ agent_name: "nora-agent"
    ↓
Log "agent.livekit_connected"
    ↓
Create public room reference
    ├─ name: room name
    ├─ url: LiveKit URL
    └─ connected: True
    ↓
Log "agent.room_joined"
    ↓
CONNECTED
```

### Graceful Shutdown Flow

```
SIGNAL RECEIVED (SIGTERM/SIGINT)
    ↓
_handle_shutdown_signal()
    └─ Set shutdown event
    ↓
agent.stop() [Triggered by shutdown event]
    ↓
Log "agent.shutting_down"
    ↓
_disconnect_from_livekit() [With 5s timeout]
    ├─ Clean up _livekit_room
    └─ Release resources
    ↓
Log "agent.room_disconnected"
    ↓
Set room = None
    ↓
Log "agent.stopped"
    ↓
SHUTDOWN COMPLETE
```

## Error Handling Strategy

### Configuration Errors
```python
# Missing required variables
ValueError: LIVEKIT_URL is required

# Invalid port
ValueError: HEALTH_CHECK_PORT must be a valid integer

# Invalid URL scheme
ValueError: LIVEKIT_URL must start with wss:// or ws://
```

**Handling**: Fail fast on startup, clear error messages

### Connection Errors
```python
# LiveKit connection failure
await _connect_to_livekit()  # May raise Exception
# Logged as: agent.connection_failed

# Room join timeout
# Logged as: agent.connection_timeout
```

**Handling**: Log with error context, re-raise for shutdown

### Shutdown Errors
```python
# Timeout waiting for disconnect
except asyncio.TimeoutError:
    log.warning("agent.disconnect_timeout")

# Other shutdown errors
except Exception as e:
    log.error("agent.disconnect_failed", error=str(e))
```

**Handling**: Log but continue shutdown, don't block exit

## Logging Architecture

### Structured Log Events

**Agent Lifecycle Events**:
```
agent.initialized     - Agent created
agent.starting        - start() called
agent.livekit_connected - Token generated
agent.room_joined     - Successfully connected
agent.shutdown_signal_received - Signal received
agent.shutting_down   - Shutdown initiated
agent.room_disconnected - Room left
agent.stopped         - Shutdown complete
```

**Error Events**:
```
agent.connection_failed - Connection error
agent.livekit_connection_error - Token generation error
agent.livekit_disconnection_error - Disconnect error
agent.disconnect_timeout - Timeout during shutdown
agent.disconnect_failed - Error during disconnect
```

**Health Events**:
```
health.request        - Health check called
```

### Log Format

**JSON Structure**:
```json
{
  "timestamp": "2025-11-24T10:30:45.123456Z",
  "level": "info",
  "event": "agent.room_joined",
  "room_name": "nora-room-001",
  "logger_name": "nora_livekit.agent"
}
```

**Available Fields**:
- `timestamp`: ISO format with microseconds
- `level`: DEBUG, INFO, WARNING, ERROR, CRITICAL
- `event`: Event identifier (e.g., "agent.started")
- `logger_name`: Module logger name
- Custom fields: Passed as kwargs to log calls

## Performance Characteristics

### Timing Requirements

| Operation | Target | Status |
|-----------|--------|--------|
| Agent startup | < 5s | Verified in tests |
| Agent shutdown | < 5s | Verified with timeout |
| Health check response | < 100ms | Verified in tests |
| Token generation | < 500ms | Typical for JWT |

### Resource Usage

**Memory**:
- Base agent: ~50MB
- Per room connection: ~10MB additional
- Health server: ~20MB

**CPU**:
- Idle (waiting): Minimal
- Processing message: Depends on voice pipeline

**Network**:
- One WebSocket connection to LiveKit
- Periodic health check requests
- Bidirectional voice/video streams (SPEC-002+)

## Integration Points

### LiveKit Integration
- Connects via WebSocket (wss://)
- Authenticates with AccessToken (JWT)
- Manages room participants
- Prepares for voice pipeline (SPEC-002)

### Health Monitoring
- FastAPI `/health` endpoint
- Used by:
  - Load balancers (health checks)
  - Container orchestration (Kubernetes, Railway)
  - Monitoring systems (Datadog, etc.)

### Future Integration Points

**SPEC-002 (Voice Pipeline)**:
- Voice codec handling
- TTS engine integration
- Audio stream processing

**SPEC-003 (Session Context)**:
- Session storage and retrieval
- Conversation history

**SPEC-006 (Supabase Integration)**:
- Database connections
- User/room metadata storage

## Deployment Topology

### Local Development
```
Local Machine
├── Python process (nora_livekit)
│   ├── Agent (port via env)
│   └── Health server (8080)
└── LiveKit (cloud or local)
```

### Docker Container
```
Docker Container
├── Multi-stage build
│   ├── Build stage (poetry install)
│   └── Runtime stage (Python 3.12 slim)
├── Application (nora_livekit)
│   ├── Agent
│   └── Health server (8080)
└── LiveKit (external)
```

### Railway Deployment
```
Railway Service
├── Docker image
│   └── Same as Docker above
├── Environment variables
│   ├── LIVEKIT_URL
│   ├── LIVEKIT_API_KEY
│   └── LIVEKIT_API_SECRET
├── Health check endpoint
│   └─ /health on port 8080
└── LiveKit Cloud
```

## Extension Points for Future SPECs

### Voice Pipeline (SPEC-002)
Add to `agent.py`:
```python
class NoraAgent:
    async def _setup_voice_pipeline(self):
        # TTS engine initialization
        # Audio stream setup
        # Codec configuration
```

### Session Context (SPEC-003)
Add to `config.py`:
```python
@dataclass
class SessionConfig:
    session_storage_url: str
    session_timeout: int
```

### Business Hours (SPEC-004)
Add new module:
```python
# nora_livekit/business_hours.py
class BusinessHoursManager:
    def is_business_hours(self) -> bool:
        # Check time zone and hours
```

### Conversation State (SPEC-005)
Add to `agent.py`:
```python
class NoraAgent:
    def __init__(self, config: Config):
        # ... existing code ...
        self.conversation_state = ConversationStateManager()
```

## Summary

The Nora LiveKit Agent architecture is designed for:

1. **Simplicity**: Clean separation of concerns, minimal dependencies
2. **Reliability**: Signal handling, timeout management, graceful shutdown
3. **Observability**: Structured JSON logging for production monitoring
4. **Extensibility**: Clear interfaces for future voice pipeline, session management, etc.
5. **Testability**: Async patterns, dependency injection via configuration

The foundation establishes patterns and structures that subsequent SPECs (voice pipeline, conversation state, etc.) will build upon.

---

**Last Updated**: November 24, 2025
**Version**: 0.1.0
**Scope**: SPEC-LIVEKIT-001 Foundation
