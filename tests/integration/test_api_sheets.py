"""
tests/integration/test_api_sheets.py

Integration tests for the /api/v1/answer-sheets endpoints.
"""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

# ── Helpers ───────────────────────────────────────────────────────────────────


def _create_exam(api_client: TestClient, headers: dict) -> int:
    """Helper: create a minimal exam and return its id."""
    resp = api_client.post(
        "/api/v1/exams",
        json={
            "title": "Sheet Test Exam",
            "questions": [
                {"question_number": 1, "question_text": "Q1", "max_marks": 5.0},
                {"question_number": 2, "question_text": "Q2", "max_marks": 5.0},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _upload_sheet(
    api_client: TestClient,
    headers: dict,
    exam_id: int,
    jpeg_bytes: bytes,
    student_roll: str | None = None,
) -> dict:
    """Helper: upload a minimal JPEG and return the response dict."""
    files = {"file": ("test_sheet.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    data = {"exam_id": str(exam_id)}
    if student_roll:
        data["student_roll"] = student_roll
    resp = api_client.post(
        "/api/v1/answer-sheets",
        files=files,
        data=data,
        headers=headers,
    )
    return resp


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_upload_sheet_success(
    api_client: TestClient,
    teacher_headers: dict,
    tiny_jpeg_bytes: bytes,
) -> None:
    """POST /api/v1/answer-sheets → 201, returns answer_sheet_id and job_id."""
    exam_id = _create_exam(api_client, teacher_headers)

    resp = _upload_sheet(api_client, teacher_headers, exam_id, tiny_jpeg_bytes, "ROLL001")
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "answer_sheet_id" in data
    assert "job_id" in data
    assert data["status"] == "pending"


def test_upload_sheet_unknown_exam(
    api_client: TestClient,
    teacher_headers: dict,
    tiny_jpeg_bytes: bytes,
) -> None:
    """Upload to a non-existent exam → 404."""
    resp = _upload_sheet(api_client, teacher_headers, 99999, tiny_jpeg_bytes)
    assert resp.status_code == 404


def test_upload_sheet_no_auth(tiny_jpeg_bytes: bytes, api_client: TestClient) -> None:
    """Upload without teacher header → 422."""
    files = {"file": ("test.jpg", io.BytesIO(tiny_jpeg_bytes), "image/jpeg")}
    resp = api_client.post(
        "/api/v1/answer-sheets",
        files=files,
        data={"exam_id": "1"},
    )
    assert resp.status_code == 422


def test_get_sheet_status(
    api_client: TestClient,
    teacher_headers: dict,
    tiny_jpeg_bytes: bytes,
) -> None:
    """GET /api/v1/answer-sheets/{id} → 200 with sheet fields."""
    exam_id = _create_exam(api_client, teacher_headers)
    upload_resp = _upload_sheet(api_client, teacher_headers, exam_id, tiny_jpeg_bytes)
    assert upload_resp.status_code == 201
    sheet_id = upload_resp.json()["answer_sheet_id"]

    resp = api_client.get(f"/api/v1/answer-sheets/{sheet_id}", headers=teacher_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == sheet_id
    assert data["exam_id"] == exam_id
    assert "status" in data
    assert "pages" in data
    assert isinstance(data["pages"], list)
    assert len(data["pages"]) == 1


def test_get_sheet_not_found(api_client: TestClient, teacher_headers: dict) -> None:
    """GET non-existent sheet → 404."""
    resp = api_client.get("/api/v1/answer-sheets/99999", headers=teacher_headers)
    assert resp.status_code == 404


def test_get_extracted_answers_empty(
    api_client: TestClient,
    teacher_headers: dict,
    tiny_jpeg_bytes: bytes,
) -> None:
    """
    GET /api/v1/answer-sheets/{id}/answers before OCR completes
    should return an empty list (or OCR results if the job has already run).
    Either way, the endpoint must return 200 with a list.
    """
    exam_id = _create_exam(api_client, teacher_headers)
    upload_resp = _upload_sheet(api_client, teacher_headers, exam_id, tiny_jpeg_bytes)
    assert upload_resp.status_code == 201
    sheet_id = upload_resp.json()["answer_sheet_id"]

    resp = api_client.get(f"/api/v1/answer-sheets/{sheet_id}/answers", headers=teacher_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)


def test_get_answers_sheet_not_found(api_client: TestClient, teacher_headers: dict) -> None:
    """GET answers for non-existent sheet → 404."""
    resp = api_client.get("/api/v1/answer-sheets/99999/answers", headers=teacher_headers)
    assert resp.status_code == 404


def test_process_sheet_enqueues_job(
    api_client: TestClient,
    teacher_headers: dict,
    tiny_jpeg_bytes: bytes,
) -> None:
    """POST /api/v1/answer-sheets/{id}/process → 202 with job_id."""
    exam_id = _create_exam(api_client, teacher_headers)
    upload_resp = _upload_sheet(api_client, teacher_headers, exam_id, tiny_jpeg_bytes)
    assert upload_resp.status_code == 201
    sheet_id = upload_resp.json()["answer_sheet_id"]

    resp = api_client.post(
        f"/api/v1/answer-sheets/{sheet_id}/process",
        headers=teacher_headers,
    )
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert "job_id" in data
    assert data["status"] in ("pending", "running", "completed")


def test_process_sheet_not_found(api_client: TestClient, teacher_headers: dict) -> None:
    """POST process on non-existent sheet → 404."""
    resp = api_client.post(
        "/api/v1/answer-sheets/99999/process",
        headers=teacher_headers,
    )
    assert resp.status_code == 404
