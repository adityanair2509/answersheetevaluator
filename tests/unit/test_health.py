"""
tests/unit/test_health.py

Smoke tests for the /health endpoint.
"""
from __future__ import annotations


def test_health_returns_ok(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "environment" in data
    assert "version" in data


def test_health_has_process_time_header(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get("/health")
    assert "x-process-time-ms" in response.headers


def test_teachers_endpoint(api_client) -> None:  # type: ignore[no-untyped-def]
    response = api_client.get("/api/v1/teachers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
