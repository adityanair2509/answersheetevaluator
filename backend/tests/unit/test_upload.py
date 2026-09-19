"""
tests/unit/test_upload.py

Unit and integration tests for the answer sheet upload endpoint.
"""
from __future__ import annotations
import io


def test_upload_validation_rejects_unsupported_file(api_client) -> None:
    """Uploading unsupported file extension like .txt must return 400 Bad Request."""
    fake_txt = io.BytesIO(b"Dummy text content")
    files = {"files": ("test.txt", fake_txt, "text/plain")}
    response = api_client.post("/api/v1/sheets/upload", data={"exam_id": "1"}, files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_valid_image_returns_success(api_client) -> None:
    """Uploading valid image/jpeg sheet returns 200 OK and sheet IDs."""
    fake_jpg = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")
    files = {"files": ("sample_student_sheet.jpg", fake_jpg, "image/jpeg")}
    data = {"exam_id": "1", "student_roll": "2024TEST001"}
    response = api_client.post("/api/v1/sheets/upload", data=data, files=files)
    assert response.status_code == 200
    res_data = response.json()
    assert "sheet_ids" in res_data
    assert len(res_data["sheet_ids"]) == 1
    assert "job_ids" in res_data
    assert len(res_data["job_ids"]) == 1
