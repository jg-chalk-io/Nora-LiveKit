# Deployment Guide

Complete guide for deploying Nora LiveKit Agent to production and development environments.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Railway Deployment](#railway-deployment)
4. [LiveKit Integration Setup](#livekit-integration-setup)
5. [Health Check Configuration](#health-check-configuration)
6. [Troubleshooting](#troubleshooting)
7. [Production Readiness Checklist](#production-readiness-checklist)

## Local Development Setup

Get the agent running on your local machine for testing and development.

### Step 1: Prerequisites

Install required software:

```bash
# Check Python version (3.12 or later required)
python3 --version
# Expected: Python 3.12.x or later

# Check Poetry installation
poetry --version
# Expected: Poetry (version 1.8 or later)

# If Poetry not installed, install it:
curl -sSL https://install.python-poetry.org | python3 -
```

### Step 2: Clone Repository

```bash
# Clone the repository
git clone <repository-url> Nora-LiveKit
cd Nora-LiveKit

# Verify directory structure
ls -la
# Should see: src/, tests/, docs/, pyproject.toml, README.md, etc.
```

### Step 3: Install Dependencies

```bash
# Install all dependencies
poetry install

# This installs:
# - Runtime dependencies: livekit-agents, fastapi, uvicorn, structlog
# - Development dependencies: pytest, pytest-cov, black, ruff, mypy

# Verify installation
poetry --version
poetry show  # List installed packages
```

### Step 4: Environment Configuration

```bash
# Copy environment template
cp .env.template .env

# Edit .env with your credentials
# nano .env  or  vim .env  or  code .env
```

**Required changes in .env**:

```bash
# Change these:
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=your-api-key-from-dashboard
LIVEKIT_API_SECRET=your-api-secret-from-dashboard

# Keep these defaults unless needed:
HEALTH_CHECK_PORT=8080
LOG_LEVEL=INFO
LOG_FORMAT=json
```

See [LiveKit Integration Setup](#livekit-integration-setup) for obtaining credentials.

### Step 5: Run Tests

Verify everything is working:

```bash
# Run all tests with coverage
poetry run pytest --cov=src/nora_livekit

# Expected output:
# collected 47 items
# ... [test results] ...
# coverage report
# ======================== 47 passed in X.XXs ========================
```

If tests fail, see [Troubleshooting](#troubleshooting).

### Step 6: Start Development Server

```bash
# Run the agent (Terminal 1)
poetry run python -m nora_livekit

# Expected output:
# INFO:     Started server process [12345]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

In another terminal, verify health endpoint:

```bash
# Test health endpoint (Terminal 2)
curl http://localhost:8080/health

# Expected response:
# {"status":"healthy","service":"nora-livekit"}
```

### Step 7: Verify Logging

Check logs to confirm connection:

```bash
# Look for connection logs in Terminal 1
# Should see JSON log entries like:
# {"event": "agent.initialized", "url": "wss://..."}
# {"event": "agent.starting", "url": "wss://..."}
# {"event": "agent.livekit_connected", "room_name": "..."}
```

If logs don't appear, check configuration and troubleshooting section.

### Local Development Commands

```bash
# Run agent
poetry run python -m nora_livekit

# Run tests
poetry run pytest -v

# Check code style
poetry run black src/ tests/
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/

# View coverage
poetry run pytest --cov=src/nora_livekit --cov-report=html
# Open htmlcov/index.html in browser
```

## Docker Deployment

Deploy the agent in a Docker container for consistent environments.

### Step 1: Build Docker Image

```bash
# Build the image
docker build -t nora-livekit:latest .

# Verify build succeeded
docker images | grep nora-livekit
# Should see: nora-livekit  latest  [IMAGE_ID]  [SIZE]

# Check image size
docker images nora-livekit:latest
# Expected size: ~300-400MB (multi-stage build optimized)
```

### Step 2: Create Environment File

```bash
# Copy template
cp .env.template .env.docker

# Edit with your credentials
nano .env.docker
```

**Content**:
```bash
LIVEKIT_URL=wss://your-instance.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret
HEALTH_CHECK_PORT=8080
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Step 3: Run Container Locally

```bash
# Run container with environment file
docker run \
  --env-file .env.docker \
  -p 8080:8080 \
  --name nora-livekit \
  nora-livekit:latest

# Container is now running
# Output should show logs from the agent
```

### Step 4: Test Health Endpoint

From another terminal:

```bash
# Test health endpoint
curl http://localhost:8080/health

# Expected response:
# {"status":"healthy","service":"nora-livekit"}
```

### Step 5: View Container Logs

```bash
# View logs from running container
docker logs -f nora-livekit

# Or if container stopped:
docker logs nora-livekit

# Stop container
docker stop nora-livekit

# Remove container
docker rm nora-livekit
```

### Docker Commands Reference

```bash
# Build image
docker build -t nora-livekit:latest .

# Run container
docker run --env-file .env -p 8080:8080 nora-livekit:latest

# Run with custom port
docker run --env-file .env -p 3000:8080 nora-livekit:latest

# Run detached (background)
docker run -d --env-file .env -p 8080:8080 --name nora nora-livekit:latest

# View logs
docker logs nora

# Stop container
docker stop nora

# Remove image
docker rmi nora-livekit:latest

# Push to registry
docker tag nora-livekit:latest myregistry/nora-livekit:latest
docker push myregistry/nora-livekit:latest
```

## Railway Deployment

Deploy to Railway cloud platform for scalable, managed hosting.

### Step 1: Create Railway Account

1. Visit [railway.app](https://railway.app)
2. Sign up with GitHub or email
3. Create new project

### Step 2: Install Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Verify installation
railway --version
# Expected: railway/X.X.X

# Alternative installation (Mac):
brew install railway
```

### Step 3: Login to Railway

```bash
# Login to Railway
railway login

# Browser will open for authentication
# Authenticate and return to terminal
```

### Step 4: Configure Railway Environment

Railway automatically detects Python projects. Verify configuration:

```bash
# Initialize Railway project
railway init

# Follow prompts:
# 1. Select "Create a new project"
# 2. Enter project name: "nora-livekit"
# 3. Select environment: "production"
```

**railway.toml** (pre-configured):
```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "python -m nora_livekit"
healthcheckPath = "/health"
healthcheckPort = 8080
```

### Step 5: Set Environment Variables

```bash
# Set variables in Railway dashboard or via CLI
railway variable set LIVEKIT_URL=wss://your-instance.livekit.cloud
railway variable set LIVEKIT_API_KEY=your-api-key
railway variable set LIVEKIT_API_SECRET=your-api-secret
railway variable set HEALTH_CHECK_PORT=8080
railway variable set LOG_LEVEL=INFO

# Verify variables set
railway variable list
```

### Step 6: Deploy

```bash
# Deploy to Railway
railway up

# Watch deployment progress
# Expected output:
# Deploying...
# ✓ Deployment complete
# Service URL: https://nora-livekit-production.up.railway.app
```

### Step 7: Verify Deployment

```bash
# Get service URL
railway logs

# Test health endpoint
curl https://<your-railway-domain>/health

# Expected response:
# {"status":"healthy","service":"nora-livekit"}

# View logs
railway logs --follow
```

### Step 8: Configure Health Checks (Optional)

In Railway dashboard:

1. Go to your project
2. Click "Settings" tab
3. Enable health check:
   - Health check path: `/health`
   - Health check port: `8080`
   - Interval: `30s`
   - Timeout: `5s`

### Railway Commands Reference

```bash
# Login
railway login

# Initialize project
railway init

# Set variables
railway variable set KEY=value
railway variable list
railway variable delete KEY

# Deploy
railway up

# View logs
railway logs
railway logs --follow

# Check status
railway status

# Redeploy current commit
railway up

# Switch environment
railway environment list
railway environment delete production
```

## LiveKit Integration Setup

Set up your LiveKit account and connect to Nora agent.

### Step 1: Create LiveKit Cloud Account

1. Visit [cloud.livekit.io](https://cloud.livekit.io)
2. Sign up with email or OAuth
3. Verify email address
4. Create new project

**Project Settings**:
- Project Name: "Nora Agent"
- Region: Choose closest to your users
- Plan: Start with free tier ($0)

### Step 2: Obtain API Credentials

From LiveKit dashboard:

1. Go to "Settings" → "API Keys"
2. Click "Create API Key"
3. Name: "Nora Agent Development"
4. Copy **API Key** and **API Secret**
5. Store securely (never commit to git)

**Example Credentials**:
```
API Key: devkey-abc123...
API Secret: secret-xyz789...
```

### Step 3: Get Server URL

From LiveKit dashboard:

1. Go to "Settings" → "Ingress"
2. Copy **WebSocket URL**
3. Format: `wss://your-project-name.livekit.cloud`

**Verify URL**:
- Must start with `wss://` (secure)
- Or `ws://` (insecure, development only)
- No trailing slash

### Step 4: Add to Configuration

Update `.env` file:

```bash
LIVEKIT_URL=wss://your-project-name.livekit.cloud
LIVEKIT_API_KEY=devkey-abc123...
LIVEKIT_API_SECRET=secret-xyz789...
```

### Step 5: Test Connection

```bash
# Run agent with new credentials
poetry run python -m nora_livekit

# Check logs for successful connection
# Look for: {"event": "agent.livekit_connected"}

# If error, see Troubleshooting section
```

### Step 6: Monitor in LiveKit Dashboard

While agent is running:

1. Go to [cloud.livekit.io](https://cloud.livekit.io)
2. Click "Room List"
3. See active rooms and participants
4. View: "nora-agent" participant
5. Check logs and metrics

### LiveKit Console Features

- **Room List**: See all rooms and participants
- **Analytics**: View bandwidth and connection metrics
- **Logs**: Real-time server logs
- **Webhooks**: For future integration

## Health Check Configuration

Configure health checks for monitoring and load balancers.

### Health Endpoint Details

**URL**: `http://localhost:8080/health`
**Method**: `GET`
**Response**: JSON
**Status Code**: `200` (always healthy in current version)

**Response Format**:
```json
{
  "status": "healthy",
  "service": "nora-livekit"
}
```

### Local Health Check

```bash
# Simple health check
curl http://localhost:8080/health

# With verbose output
curl -v http://localhost:8080/health

# With timeout
curl --max-time 5 http://localhost:8080/health
```

### Docker Health Check

In `Dockerfile`:
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
```

**Test health check**:
```bash
# Check health status
docker inspect --format='{{.State.Health}}' nora-livekit

# Expected output:
# {healthy 0 0 0}
```

### Railway Health Check

In `railway.toml`:
```toml
[deploy]
healthcheckPath = "/health"
healthcheckPort = 8080
```

In Railway dashboard settings:
- Health Check Interval: 30s
- Health Check Timeout: 5s
- Start Period: 10s (wait before first check)
- Healthy Threshold: 2 consecutive
- Unhealthy Threshold: 3 consecutive

### Kubernetes Health Check

In Kubernetes manifest:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nora-livekit
spec:
  template:
    spec:
      containers:
      - name: nora-livekit
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 2
```

## Troubleshooting

Common issues and solutions.

### Connection Issues

#### Error: "LIVEKIT_URL is required"

**Cause**: Environment variable not set

**Solution**:
```bash
# Check if .env file exists
ls -la .env

# Check if variable is set
echo $LIVEKIT_URL

# If not set, add to .env:
echo "LIVEKIT_URL=wss://..." >> .env

# Reload environment
source .env
```

#### Error: "Connection timeout"

**Cause**: Can't reach LiveKit server

**Solution**:
```bash
# Verify URL is correct
echo $LIVEKIT_URL
# Should be: wss://your-instance.livekit.cloud

# Test connectivity
curl -v wss://your-instance.livekit.cloud
# If fails, check:
# 1. Is URL correct?
# 2. Is internet connected?
# 3. Is firewall blocking?
```

#### Error: "Invalid credentials"

**Cause**: Wrong API key or secret

**Solution**:
```bash
# Get correct credentials from LiveKit dashboard
# 1. Go to cloud.livekit.io
# 2. Settings → API Keys
# 3. Copy API Key and Secret
# 4. Update .env file

# Verify format (should be long strings)
echo $LIVEKIT_API_KEY
echo $LIVEKIT_API_SECRET
```

### Port Issues

#### Error: "Address already in use"

**Cause**: Port 8080 already in use

**Solution**:
```bash
# Find what's using port 8080
lsof -i :8080
# Or on some systems:
netstat -tulpn | grep 8080

# Either:
# 1. Change HEALTH_CHECK_PORT in .env
HEALTH_CHECK_PORT=3000

# 2. Or stop the other service
kill -9 <PID>

# 3. Or use different port in deployment
docker run -p 3000:8080 nora-livekit:latest
```

### Tests Failing

#### Error: "Python 3.12 required"

**Cause**: Wrong Python version

**Solution**:
```bash
# Check Python version
python3 --version
# Minimum: Python 3.12.0

# If using pyenv:
pyenv install 3.12.x
pyenv local 3.12.x
python3 --version

# Then reinstall dependencies
poetry install
poetry run pytest --cov=src/nora_livekit
```

#### Error: "Dependency conflicts"

**Cause**: Poetry cache out of date

**Solution**:
```bash
# Clear Poetry cache
poetry cache clear . --all

# Reinstall all dependencies
poetry install --no-cache

# Rebuild environment
poetry env remove
poetry install
```

#### Error: "Import nora_livekit failed"

**Cause**: Package not installed in Poetry venv

**Solution**:
```bash
# Reinstall package in development mode
poetry install --no-cache

# Verify installation
poetry show nora-livekit

# Run with poetry
poetry run pytest --cov=src/nora_livekit
```

### Docker Issues

#### Error: "Docker build failed"

**Cause**: Docker not installed or syntax error

**Solution**:
```bash
# Check Docker installation
docker --version

# Build with verbose output
docker build -t nora-livekit:latest . --verbose

# Check Dockerfile syntax
docker build --help

# If Dockerfile error, check line numbers in error message
nano Dockerfile
```

#### Error: "Container won't start"

**Cause**: Missing environment variables or port conflict

**Solution**:
```bash
# Check if .env file is correct
cat .env.docker

# Run with explicit environment
docker run -e LIVEKIT_URL=wss://... -e LIVEKIT_API_KEY=... -p 8080:8080 nora-livekit:latest

# View container logs
docker logs <container-id>

# Run interactively for debugging
docker run -it --env-file .env nora-livekit:latest /bin/bash
```

### Railway Issues

#### Error: "Deployment failed"

**Cause**: Various - check logs

**Solution**:
```bash
# View deployment logs
railway logs

# Check variables are set
railway variable list

# Try manual deployment
railway up

# Check if service is running
railway status
```

#### Error: "Health check failing"

**Cause**: Service not responding to health requests

**Solution**:
```bash
# Check health endpoint locally first
curl http://localhost:8080/health

# In Railway dashboard:
# 1. Settings → Health Check
# 2. Verify path: /health
# 3. Verify port: 8080
# 4. Increase timeout if needed

# View service logs
railway logs
```

#### Error: "Connection to LiveKit timeout"

**Cause**: Railway container can't reach LiveKit

**Solution**:
```bash
# Check environment variables in Railway dashboard
railway variable list

# Verify LIVEKIT_URL is set correctly
railway variable get LIVEKIT_URL

# Check if URL is accessible from Railway
# (Should be cloud.livekit.io which is publicly accessible)

# If problem persists, use self-hosted LiveKit or different cloud region
```

## Production Readiness Checklist

Before deploying to production, verify all items:

### Configuration & Secrets

- [ ] LIVEKIT_URL set and accessible
- [ ] LIVEKIT_API_KEY stored securely (not in code)
- [ ] LIVEKIT_API_SECRET stored securely (not in code)
- [ ] HEALTH_CHECK_PORT configured appropriately
- [ ] LOG_LEVEL set to INFO (not DEBUG)
- [ ] No hardcoded secrets in code or Dockerfile

### Code Quality

- [ ] All tests passing (47/47)
- [ ] Code coverage at least 85% (target: 90%)
- [ ] Black formatting verified
- [ ] Ruff linting passed
- [ ] Mypy type checking passed
- [ ] No TODO comments remaining

### Testing

- [ ] Local tests passing with coverage
- [ ] Docker build and run verified
- [ ] Health endpoint responding correctly
- [ ] Agent connects to LiveKit successfully
- [ ] Graceful shutdown verified (SIGTERM handling)
- [ ] Logs are clear and helpful

### Documentation

- [ ] README.md updated with current version
- [ ] ARCHITECTURE.md describes current design
- [ ] API_REFERENCE.md documents all public APIs
- [ ] DEPLOYMENT.md instructions verified
- [ ] Code comments explain non-obvious logic

### Deployment

- [ ] Dockerfile builds without warnings
- [ ] Docker image size acceptable (< 500MB)
- [ ] Railway configuration reviewed and tested
- [ ] Health checks configured and verified
- [ ] Monitoring/logging aggregation configured
- [ ] Backup and recovery plan documented

### Security

- [ ] Environment variables validated on startup
- [ ] No secrets in logs (structured logging safe)
- [ ] HTTPS/WSS used for all connections
- [ ] Firewall rules allow only necessary ports
- [ ] Regular dependency updates planned
- [ ] Security scanning enabled (if available)

### Monitoring

- [ ] Health endpoint configured for load balancer
- [ ] Logs aggregated and searchable
- [ ] Error alerts configured
- [ ] Performance metrics monitored
- [ ] Uptime monitoring enabled
- [ ] Incident response plan documented

### Operations

- [ ] Rollback procedure documented
- [ ] Scaling procedures documented
- [ ] Team trained on deployment and monitoring
- [ ] On-call rotation established
- [ ] Incident escalation path defined
- [ ] Runbooks created for common issues

---

**Last Updated**: November 24, 2025
**Version**: 0.1.0
**Scope**: SPEC-LIVEKIT-001 Foundation
