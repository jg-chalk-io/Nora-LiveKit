# API Reference

Complete API documentation for Nora LiveKit Agent modules, classes, and functions.

## Table of Contents

1. [Configuration Module](#configuration-module)
2. [Agent Module](#agent-module)
3. [Server Module](#server-module)
4. [Main Module](#main-module)
5. [Logging Reference](#logging-reference)
6. [Environment Variables](#environment-variables)
7. [Error Codes](#error-codes)

## Configuration Module

**Module**: `src/nora_livekit/config.py`

Handles environment variable loading, validation, and structured logging setup.

### Config Class

```python
@dataclass
class Config:
    """Configuration for Nora LiveKit Agent.

    All fields are typed and validated on instantiation.
    """

    # Required Fields
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str

    # Optional Fields
    health_check_port: int = 8080
    log_level: str = "INFO"
    log_format: str = "json"
    test_room: str | None = None
```

### Config Fields

#### `livekit_url` (required)
**Type**: `str`

WebSocket URL to LiveKit server.

**Format**: `wss://` for secure, `ws://` for insecure
**Example**: `wss://your-instance.livekit.cloud`
**Validation**: Must start with `wss://` or `ws://`

```python
config = Config(
    livekit_url="wss://your-instance.livekit.cloud",
    # ... other fields
)
```

#### `livekit_api_key` (required)
**Type**: `str`

API key for LiveKit authentication.

**Source**: LiveKit Cloud dashboard
**Required**: Yes, non-empty string
**Example**: `devkey-abc123...`

```python
config = Config(
    livekit_api_key="devkey-abc123",
    # ... other fields
)
```

#### `livekit_api_secret` (required)
**Type**: `str`

API secret for JWT token generation.

**Source**: LiveKit Cloud dashboard
**Required**: Yes, non-empty string
**Sensitive**: Keep secure, never commit
**Example**: `secret-xyz789...`

```python
config = Config(
    livekit_api_secret="secret-xyz789",
    # ... other fields
)
```

#### `health_check_port` (optional)
**Type**: `int`
**Default**: `8080`

Port for FastAPI health check endpoint.

**Range**: 1 - 65535
**Example**: `8080`, `3000`, `8000`

```python
config = Config(
    health_check_port=3000,
    # ... other fields
)
```

#### `log_level` (optional)
**Type**: `str`
**Default**: `"INFO"`

Logging level for output.

**Valid Values**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

```python
config = Config(
    log_level="DEBUG",  # Verbose output
    # ... other fields
)
```

#### `log_format` (optional)
**Type**: `str`
**Default**: `"json"`

Log output format.

**Valid Values**:
- `"json"`: Structured JSON logs (recommended for production)
- `"text"`: Human-readable text (not yet implemented)

```python
config = Config(
    log_format="json",
    # ... other fields
)
```

#### `test_room` (optional)
**Type**: `str | None`
**Default**: `None`

Room name for development/testing.

**When None**: Uses `"default-room"`
**Example**: `"test-room-001"`, `"dev-room"`

```python
config = Config(
    test_room="test-room-001",
    # ... other fields
)
```

### Config Methods

#### `Config.from_env()` (classmethod)

**Signature**:
```python
@classmethod
def from_env(cls) -> "Config"
```

Load configuration from environment variables.

**Returns**:
- `Config`: Loaded and validated configuration instance

**Raises**:
- `ValueError`: If required variables missing or invalid

**Example**:
```python
from nora_livekit.config import Config

# Load from .env file or system environment
config = Config.from_env()

# Use configuration
print(config.livekit_url)  # "wss://..."
```

**Validation Performed**:
1. Checks all required variables exist
2. Validates URL format (wss:// or ws://)
3. Validates port is integer
4. Validates log level
5. Sets defaults for optional variables

**Environment Variables Loaded**:
```
LIVEKIT_URL              (required)
LIVEKIT_API_KEY          (required)
LIVEKIT_API_SECRET       (required)
HEALTH_CHECK_PORT        (optional, default: 8080)
LOG_LEVEL                (optional, default: INFO)
LOG_FORMAT               (optional, default: json)
LIVEKIT_TEST_ROOM        (optional, default: None)
```

### setup_logging Function

**Signature**:
```python
def setup_logging(config: Config) -> None
```

Configure structlog with JSON output.

**Parameters**:
- `config` (`Config`): Configuration instance

**Effects**:
- Configures structlog for JSON output
- Sets log level from config
- Adds ISO timestamps
- Adds stack traces for exceptions

**Example**:
```python
from nora_livekit.config import Config, setup_logging

config = Config.from_env()
setup_logging(config)

import structlog
log = structlog.get_logger()
log.info("application.started")  # JSON output
```

**Log Output Format**:
```json
{
  "timestamp": "2025-11-24T10:30:45.123456Z",
  "level": "info",
  "event": "application.started",
  "logger_name": "__main__"
}
```

## Agent Module

**Module**: `src/nora_livekit/agent.py`

Manages LiveKit room connection lifecycle.

### NoraAgent Class

```python
class NoraAgent:
    """LiveKit agent with room connection lifecycle management.

    Manages connection to LiveKit rooms, graceful shutdown on signals,
    and logging of all lifecycle events.
    """
```

### NoraAgent.__init__

**Signature**:
```python
def __init__(self, config: Config) -> None
```

Initialize the Nora agent.

**Parameters**:
- `config` (`Config`): Configuration instance with LiveKit credentials

**Effects**:
- Stores configuration reference
- Initializes room state (None until connected)
- Creates shutdown event for signal handling
- Registers signal handlers for SIGTERM and SIGINT
- Logs initialization

**Example**:
```python
from nora_livekit.config import Config
from nora_livekit.agent import NoraAgent

config = Config.from_env()
agent = NoraAgent(config)
```

**Initialization Logging**:
```json
{
  "event": "agent.initialized",
  "url": "wss://instance.livekit.cloud"
}
```

### NoraAgent.start

**Signature**:
```python
async def start(self) -> None
```

Connect to LiveKit server and join room.

**Effects**:
- Calls `_connect_to_livekit()` to generate access token
- Creates public room reference
- Sets room state
- Logs connection success

**Raises**:
- `Exception`: If connection or room join fails

**Example**:
```python
agent = NoraAgent(config)
try:
    await agent.start()
    print("Agent connected!")
except Exception as e:
    print(f"Connection failed: {e}")
```

**Success Logging**:
```json
{
  "event": "agent.room_joined",
  "room_name": "nora-room"
}
```

**Error Logging**:
```json
{
  "event": "agent.connection_failed",
  "error": "LIVEKIT_URL is invalid"
}
```

### NoraAgent.stop

**Signature**:
```python
async def stop(self) -> None
```

Gracefully disconnect from LiveKit room.

**Effects**:
- Calls `_disconnect_from_livekit()` with 5-second timeout
- Clears room state
- Logs shutdown completion
- Handles timeout and exceptions gracefully

**Example**:
```python
agent = NoraAgent(config)
await agent.start()

# Later, on shutdown
await agent.stop()
print("Agent stopped")
```

**Success Logging**:
```json
{
  "event": "agent.room_disconnected",
  "reason": "graceful_shutdown"
}
```

**Timeout Handling**:
```json
{
  "event": "agent.disconnect_timeout"
}
```

### NoraAgent._handle_shutdown_signal

**Signature**:
```python
def _handle_shutdown_signal(self, signum: int, frame: Any) -> None
```

Handle shutdown signals (SIGTERM, SIGINT).

**Parameters**:
- `signum` (`int`): Signal number (SIGTERM=15, SIGINT=2)
- `frame` (`Any`): Current stack frame

**Effects**:
- Sets shutdown event
- Logs signal reception
- Allows `start()` method's shutdown event wait to complete

**Auto-Registered For**:
- SIGTERM: Container/process termination
- SIGINT: Ctrl+C from terminal

**Logging**:
```json
{
  "event": "agent.shutdown_signal_received",
  "signal": 15
}
```

### NoraAgent._connect_to_livekit

**Signature**:
```python
async def _connect_to_livekit(self) -> None
```

Connect to LiveKit server and generate access token.

**Effects**:
- Generates JWT access token
- Stores connection info in `_livekit_room`
- Sets video grants (publish, subscribe, room join)
- Logs connection attempt

**Raises**:
- `Exception`: If token generation fails

**Access Token Details**:
```python
token = api.AccessToken(
    api_key=config.livekit_api_key,
    api_secret=config.livekit_api_secret,
).with_identity("nora-agent")
 .with_name("nora-agent")
 .with_grants(api.VideoGrants(
    room_join=True,
    room=room_name,
    can_publish=True,
    can_subscribe=True,
))
```

**Success Logging**:
```json
{
  "event": "agent.livekit_connected",
  "room_name": "nora-room",
  "agent_name": "nora-agent"
}
```

### NoraAgent._disconnect_from_livekit

**Signature**:
```python
async def _disconnect_from_livekit(self) -> None
```

Disconnect from LiveKit server and clean up resources.

**Effects**:
- Logs disconnection
- Clears `_livekit_room` reference
- Releases resources

**Logging**:
```json
{
  "event": "agent.livekit_disconnected"
}
```

### NoraAgent Properties

#### `room`
**Type**: `dict[str, Any] | None`

Public room reference when connected.

**Structure**:
```python
{
    "name": "room-name",
    "url": "wss://...",
    "connected": True
}
```

**Access**:
```python
agent = NoraAgent(config)
await agent.start()
print(agent.room["name"])  # "room-name"
```

## Server Module

**Module**: `src/nora_livekit/server.py`

FastAPI application for health checks.

### HealthResponse Class

```python
class HealthResponse(BaseModel):
    """Health check response model."""
    status: str      # "healthy" or status value
    service: str     # Service name
```

### health_check Endpoint

**HTTP Details**:
- **Path**: `/health`
- **Method**: `GET`
- **Port**: Configured via `HEALTH_CHECK_PORT` (default: 8080)
- **Response**: JSON

**Signature**:
```python
@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse
```

**Returns**:
- `HealthResponse`: Status and service information

**Example Request**:
```bash
curl http://localhost:8080/health
```

**Example Response**:
```json
{
  "status": "healthy",
  "service": "nora-livekit"
}
```

**Status Codes**:
- `200`: Healthy, ready for traffic
- (Future: `503` for unhealthy state)

**Performance**:
- Response time: < 100ms
- CPU impact: Minimal
- No external calls

### FastAPI App

**Variable**: `app`
**Type**: `FastAPI`

FastAPI application instance.

**Configuration**:
```python
app = FastAPI(
    title="Nora LiveKit Agent",
    version="0.1.0"
)
```

**Usage in __main__.py**:
```python
def run_health_server(port: int) -> None:
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="warning",
    )
```

## Main Module

**Module**: `src/nora_livekit/__main__.py`

Entry point for the agent.

### run_health_server Function

**Signature**:
```python
def run_health_server(port: int) -> None
```

Run FastAPI health check server in background thread.

**Parameters**:
- `port` (`int`): Port to listen on for health checks

**Effects**:
- Starts Uvicorn ASGI server
- Binds to 0.0.0.0:port
- Runs in caller's thread
- Sets log level to "warning"

**Example**:
```python
import threading
from nora_livekit.__main__ import run_health_server

health_thread = threading.Thread(
    target=run_health_server,
    args=(8080,),
    daemon=True,
)
health_thread.start()

# Server now running on port 8080
```

### main Function

**Signature**:
```python
async def main() -> None
```

Main agent entry point.

**Flow**:
1. Load configuration from environment
2. Setup logging
3. Start health server in background thread
4. Create NoraAgent
5. Call agent.start()
6. Wait for shutdown signal
7. Call agent.stop()

**Example**:
```python
import asyncio
from nora_livekit.__main__ import main

asyncio.run(main())
```

**Entry Point**:
```bash
python -m nora_livekit
```

## Logging Reference

### Log Events

All log events are JSON-formatted with the following structure:

```json
{
  "timestamp": "ISO8601",
  "level": "info|warning|error|debug|critical",
  "event": "event.name",
  "logger_name": "module.name",
  "...": "additional fields"
}
```

### Agent Lifecycle Events

#### agent.initialized
**When**: Agent object created
**Log Level**: INFO
**Fields**: `url` (LiveKit URL)

```json
{"event": "agent.initialized", "url": "wss://..."}
```

#### agent.starting
**When**: `start()` method called
**Log Level**: INFO
**Fields**: `url` (LiveKit URL)

```json
{"event": "agent.starting", "url": "wss://..."}
```

#### agent.livekit_connected
**When**: Access token generated successfully
**Log Level**: INFO
**Fields**: `room_name`, `agent_name`

```json
{"event": "agent.livekit_connected", "room_name": "room-1", "agent_name": "nora-agent"}
```

#### agent.room_joined
**When**: Room connection established
**Log Level**: INFO
**Fields**: `room_name`

```json
{"event": "agent.room_joined", "room_name": "room-1"}
```

#### agent.shutdown_signal_received
**When**: SIGTERM or SIGINT received
**Log Level**: INFO
**Fields**: `signal` (signal number)

```json
{"event": "agent.shutdown_signal_received", "signal": 15}
```

#### agent.shutting_down
**When**: `stop()` method called
**Log Level**: INFO
**Fields**: None

```json
{"event": "agent.shutting_down"}
```

#### agent.room_disconnected
**When**: Room disconnect successful
**Log Level**: INFO
**Fields**: `reason` (e.g., "graceful_shutdown")

```json
{"event": "agent.room_disconnected", "reason": "graceful_shutdown"}
```

#### agent.stopped
**When**: Agent fully stopped
**Log Level**: INFO
**Fields**: None

```json
{"event": "agent.stopped"}
```

### Error Events

#### agent.connection_failed
**When**: Room connection fails
**Log Level**: ERROR
**Fields**: `error` (error message)

```json
{"event": "agent.connection_failed", "error": "Connection timeout"}
```

#### agent.livekit_connection_error
**When**: Token generation fails
**Log Level**: ERROR
**Fields**: `error`, `exc_info`

```json
{"event": "agent.livekit_connection_error", "error": "..."}
```

#### agent.disconnect_timeout
**When**: Disconnect times out (> 5 seconds)
**Log Level**: WARNING
**Fields**: None

```json
{"event": "agent.disconnect_timeout"}
```

#### agent.disconnect_failed
**When**: Disconnect error occurs
**Log Level**: ERROR
**Fields**: `error`, `exc_info`

```json
{"event": "agent.disconnect_failed", "error": "..."}
```

### Health Events

#### health.request
**When**: `/health` endpoint called
**Log Level**: DEBUG
**Fields**: None

```json
{"event": "health.request"}
```

## Environment Variables

All configuration uses environment variables. Create a `.env` file or set in your environment.

### Required Variables

```bash
# LiveKit server WebSocket URL
LIVEKIT_URL=wss://your-instance.livekit.cloud

# LiveKit API key (from dashboard)
LIVEKIT_API_KEY=devkey-abc123...

# LiveKit API secret (from dashboard)
LIVEKIT_API_SECRET=secret-xyz789...
```

### Optional Variables

```bash
# Health check server port (default: 8080)
HEALTH_CHECK_PORT=8080

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
LOG_LEVEL=INFO

# Log format (default: json)
LOG_FORMAT=json

# Test room name for development (default: none)
LIVEKIT_TEST_ROOM=test-room-001
```

### Environment File Example

```bash
# .env file
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=devkey-abc123...
LIVEKIT_API_SECRET=secret-xyz789...
HEALTH_CHECK_PORT=8080
LOG_LEVEL=INFO
LOG_FORMAT=json
LIVEKIT_TEST_ROOM=dev-room
```

## Error Codes

### Configuration Errors

#### `ValueError: LIVEKIT_URL is required`
**Cause**: Environment variable `LIVEKIT_URL` not set
**Solution**: Set `LIVEKIT_URL` in `.env` or environment

#### `ValueError: LIVEKIT_URL must start with wss:// or ws://`
**Cause**: URL format invalid
**Solution**: Use `wss://` for secure or `ws://` for insecure

#### `ValueError: LIVEKIT_API_KEY is required`
**Cause**: Environment variable missing
**Solution**: Set `LIVEKIT_API_KEY` from LiveKit dashboard

#### `ValueError: LIVEKIT_API_SECRET is required`
**Cause**: Environment variable missing
**Solution**: Set `LIVEKIT_API_SECRET` from LiveKit dashboard

#### `ValueError: HEALTH_CHECK_PORT must be a valid integer`
**Cause**: Port value is not an integer
**Solution**: Use integer between 1-65535

### Runtime Errors

#### Connection Timeout
**Cause**: LiveKit server unreachable
**Solution**: Verify `LIVEKIT_URL` and network connectivity

#### Invalid Credentials
**Cause**: Wrong `LIVEKIT_API_KEY` or `LIVEKIT_API_SECRET`
**Solution**: Verify credentials from LiveKit dashboard

#### Port Already in Use
**Cause**: Health check port already bound
**Solution**: Change `HEALTH_CHECK_PORT` or stop other services

## Quick Reference

### Import Statements

```python
# Configuration
from nora_livekit.config import Config, setup_logging

# Agent
from nora_livekit.agent import NoraAgent

# Server
from nora_livekit.server import app, HealthResponse

# Main entry point
from nora_livekit import __main__
```

### Basic Usage Pattern

```python
import asyncio
from nora_livekit.config import Config, setup_logging
from nora_livekit.agent import NoraAgent

async def main():
    # Load configuration
    config = Config.from_env()
    setup_logging(config)

    # Create agent
    agent = NoraAgent(config)

    # Connect to LiveKit
    await agent.start()

    # Do work...

    # Gracefully disconnect
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

**Last Updated**: November 24, 2025
**Version**: 0.1.0
**Scope**: SPEC-LIVEKIT-001 Foundation
