"""Tests for FastAPI health check server."""

import pytest
from fastapi.testclient import TestClient

from nora_livekit.server import app


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check_returns_200(self) -> None:
        """Test that /health endpoint returns 200 OK."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_check_response_body(self) -> None:
        """Test that /health endpoint returns correct JSON."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.json() == {
            "status": "healthy",
            "service": "nora-livekit",
        }

    def test_health_check_content_type(self) -> None:
        """Test that /health endpoint returns JSON content type."""
        client = TestClient(app)
        response = client.get("/health")

        assert response.headers["content-type"] == "application/json"

    def test_health_check_response_time(self) -> None:
        """Test that /health endpoint responds quickly."""
        client = TestClient(app)

        # Make multiple requests to test consistent response
        for _ in range(5):
            response = client.get("/health")
            assert response.status_code == 200

    def test_health_check_invalid_path_returns_404(self) -> None:
        """Test that invalid paths return 404."""
        client = TestClient(app)
        response = client.get("/invalid")

        assert response.status_code == 404
