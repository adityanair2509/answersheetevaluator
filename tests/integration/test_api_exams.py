"""
tests/integration/test_api_exams.py

Integration tests for the /api/v1/exams endpoints.
Uses the session-scoped TestClient (no DB override — hits the dev SQLite).
Each test that writes data uses a unique title to avoid cross-test interference.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# ── Helpers ───────────────────────────────────────────────────────────────────


def _exam_payload(suffix: str = "") -> dict:
    return {
        "title": f"Integration Test Exam {suffix}",
        "course_code": f"TEST{suffix[:3].upper()}",
        "questions": [
            {
                "question_number": 1,
                "question_text": "Define recursion.",
                "max_marks": 5.0,
                "rubric_hints": "Must mention base case",
            },
            {
                "question_number": 2,
                "question_text": "What is Big-O notation?",
                "max_marks": 5.0,
            },
        ],
    }


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_create_exam_success(api_client: TestClient, teacher_headers: dict) -> None:
    """POST /api/v1/exams → 201, returns id and question_count = 2."""
    response = api_client.post(
        "/api/v1/exams",
        json=_exam_payload("create_success"),
        headers=teacher_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["question_count"] == 2
    assert data["title"].startswith("Integration Test Exam")
    assert "id" in data
    assert data["status"] == "draft"


def test_create_exam_no_questions(api_client: TestClient, teacher_headers: dict) -> None:
    """POST /api/v1/exams with no questions should still return 201."""
    response = api_client.post(
        "/api/v1/exams",
        json={"title": "Exam with no questions", "course_code": "NOQ01"},
        headers=teacher_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["question_count"] == 0


def test_create_exam_no_auth(api_client: TestClient) -> None:
    """POST without X-Teacher-Id header → 422 (missing required header)."""
    response = api_client.post("/api/v1/exams", json=_exam_payload("no_auth"))
    # FastAPI returns 422 when a required Header dependency is missing
    assert response.status_code == 422


def test_create_exam_bad_teacher(api_client: TestClient) -> None:
    """POST with an unknown teacher ID → 403."""
    response = api_client.post(
        "/api/v1/exams",
        json=_exam_payload("bad_teacher"),
        headers={"X-Teacher-Id": "impostor"},
    )
    assert response.status_code == 403


def test_list_exams(api_client: TestClient, teacher_headers: dict) -> None:
    """GET /api/v1/exams → 200, returns a list."""
    # Ensure at least one exam exists
    api_client.post("/api/v1/exams", json=_exam_payload("list"), headers=teacher_headers)

    response = api_client.get("/api/v1/exams", headers=teacher_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Each item should have the expected fields
    item = data[0]
    assert "id" in item
    assert "title" in item
    assert "question_count" in item


def test_get_exam_not_found(api_client: TestClient, teacher_headers: dict) -> None:
    """GET /api/v1/exams/99999 → 404."""
    response = api_client.get("/api/v1/exams/99999", headers=teacher_headers)
    assert response.status_code == 404


def test_get_exam_success(api_client: TestClient, teacher_headers: dict) -> None:
    """GET /api/v1/exams/{id} → 200 with correct fields."""
    create = api_client.post(
        "/api/v1/exams",
        json=_exam_payload("get_one"),
        headers=teacher_headers,
    )
    assert create.status_code == 201
    exam_id = create.json()["id"]

    response = api_client.get(f"/api/v1/exams/{exam_id}", headers=teacher_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == exam_id
    assert data["question_count"] == 2


def test_add_answer_key(api_client: TestClient, teacher_headers: dict) -> None:
    """POST /api/v1/exams/{id}/answer-key → 201, returns answer_key_id."""
    # Create an exam first
    create = api_client.post(
        "/api/v1/exams",
        json=_exam_payload("ak_test"),
        headers=teacher_headers,
    )
    assert create.status_code == 201
    exam_id = create.json()["id"]

    # Upload answer key
    response = api_client.post(
        f"/api/v1/exams/{exam_id}/answer-key",
        json={
            "raw_text": "Q1: A recursive function calls itself. Q2: Big-O measures worst-case complexity.",
            "version": 1,
        },
        headers=teacher_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert "id" in data
    assert data["exam_id"] == exam_id
    assert data["status"] == "uploaded"
    assert data["version"] == 1


def test_answer_key_exam_not_found(api_client: TestClient, teacher_headers: dict) -> None:
    """POST answer key to a non-existent exam → 404."""
    response = api_client.post(
        "/api/v1/exams/99999/answer-key",
        json={"raw_text": "Some answer key text.", "version": 1},
        headers=teacher_headers,
    )
    assert response.status_code == 404
