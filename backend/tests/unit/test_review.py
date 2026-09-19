"""
tests/unit/test_review.py

Unit tests for review score approval and issue flagging endpoints.
"""
from __future__ import annotations


def test_approve_score_and_flag_issue(api_client) -> None:
    """Test approval of score and flagging an issue for a sheet."""
    # First get or create a reviewable sheet via upload
    import io
    fake_jpg = io.BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")
    files = {"files": ("review_test.jpg", fake_jpg, "image/jpeg")}
    upload_res = api_client.post("/api/v1/sheets/upload", data={"exam_id": "1"}, files=files)
    assert upload_res.status_code == 200
    sheet_id = upload_res.json()["sheet_ids"][0]

    # Test review details fetch
    review_res = api_client.get(f"/api/v1/sheets/{sheet_id}/review")
    assert review_res.status_code == 200
    assert review_res.json()["sheetId"] == sheet_id

    # Test score approval
    approve_res = api_client.post(f"/api/v1/sheets/{sheet_id}/approve", json={"score": 8.5, "teacher_id": "teacher_test"})
    assert approve_res.status_code == 200
    assert approve_res.json()["score"] == 8.5
    assert approve_res.json()["reviewStatus"] == "APPROVED"

    # Test issue flagging
    flag_res = api_client.post(f"/api/v1/sheets/{sheet_id}/flag", json={"reason": "Handwriting difficult to decipher"})
    assert flag_res.status_code == 200
    assert flag_res.json()["reviewStatus"] == "FLAGGED"
