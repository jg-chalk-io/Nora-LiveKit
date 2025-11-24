#!/bin/bash

echo "=========================================="
echo "Starting Nora LiveKit Agent"
echo "=========================================="
echo ""
echo "Environment:"
echo "- LIVEKIT_URL: ${LIVEKIT_URL:-'(from .env)'}"
echo "- Port: 8080"
echo ""
echo "Logs will appear below (JSON format):"
echo "Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Set Python to unbuffered mode and redirect stderr to stdout
exec poetry run python -u -m nora_livekit.agent 2>&1
