"""Iter 49: live duplicate-audit API smoke checks (read-only, active-job reuse)."""
import os
import time

import requests

from tests.support_config import SUPERADMIN


BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"


def _login_token() -> str:
    response = requests.post(f"{API}/auth/login", json=SUPERADMIN, timeout=30)
    assert response.status_code == 200, response.text
    data = response.json()
    token = data.get("access_token")
    assert isinstance(token, str) and token
    return token


def test_duplicate_audit_preview_reuses_active_job_and_rows_are_objectid_safe():
    token = _login_token()
    headers = {"Authorization": f"Bearer {token}"}

    first = requests.post(f"{API}/royalty/admin/duplicate-audit/preview", headers=headers, timeout=30)
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert isinstance(first_body.get("job_id"), str) and first_body["job_id"]
    assert first_body.get("status") in {"queued", "processing"}

    second = requests.post(f"{API}/royalty/admin/duplicate-audit/preview", headers=headers, timeout=30)
    assert second.status_code == 200, second.text
    second_body = second.json()
    # Reuse is required only when first job is still active.
    if second_body.get("already_running") is True:
        assert second_body.get("job_id") == first_body.get("job_id")
    else:
        assert isinstance(second_body.get("job_id"), str) and second_body["job_id"]

    job_id = first_body["job_id"]
    deadline = time.time() + 20
    last_job = None
    while time.time() < deadline:
        job_response = requests.get(f"{API}/royalty/admin/duplicate-audit/jobs/{job_id}", headers=headers, timeout=30)
        assert job_response.status_code == 200, job_response.text
        last_job = job_response.json()
        if last_job.get("status") in {"done", "error"}:
            break
        time.sleep(1)

    assert isinstance(last_job, dict)
    assert "_id" not in last_job
    assert last_job.get("kind") == "royalty_duplicate_audit"

    rows_response = requests.get(
        f"{API}/royalty/admin/duplicate-audit/jobs/{job_id}/rows",
        headers=headers,
        params={"page": 1, "limit": 5},
        timeout=30,
    )
    assert rows_response.status_code == 200, rows_response.text
    rows_body = rows_response.json()
    assert rows_body.get("read_only") is True
    assert rows_body.get("page") == 1
    assert rows_body.get("limit") == 5
    assert "items" in rows_body and isinstance(rows_body["items"], list)

    for row in rows_body["items"]:
        assert "_id" not in row
        assert row.get("read_only") is True
        assert isinstance(row.get("id"), str) and row["id"]
        assert "canonical_import" in row and "duplicate_import" in row
