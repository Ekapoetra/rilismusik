"""Phase 22 — Legacy withdraw CSV migration (period_end → last_withdrawn_period).

Maps the user's existing `music_withdrawals.csv` (columns: nama_label,
period_start, period_end, amount, exchange_rate, status, …) into the modern
FIFO withdraw system.

Key assertions:
  - Dry-run mode does NOT mutate any data.
  - Fuzzy label matcher handles inconsistent casing/punctuation/'PT' prefix.
  - On commit, labels.last_withdrawn_period is set to MAX(period_end) per label.
  - Idempotent: re-running with the same CSV adds 0 new docs / updates 0 labels.
  - Only super_admin can run; other admin roles get 403.
"""
import io
import os
import time
import uuid
import requests
from tests.support_config import SUPPORT as SUPPORT_CRED, SUPERADMIN
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])
SUPPORT = (SUPPORT_CRED["email"], SUPPORT_CRED["password"])


def _mongo_db():
    import pymongo
    client = pymongo.MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    return client[os.environ.get("DB_NAME", "rilismusik_db")]


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


def _wait_job(job_id, token, max_wait=30):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        response = requests.get(
            f"{API}/admin/migrate/jobs/{job_id}", headers=_hdr(token), timeout=15,
        )
        response.raise_for_status()
        job = response.json()
        if job["status"] in ("done", "error"):
            return job
        time.sleep(0.25)
    raise AssertionError(f"job {job_id} did not finish within {max_wait}s")


def _preview_and_wait(csv_bytes, token):
    response = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("preview.csv", csv_bytes, "text/csv")},
        data={"dry_run": "true"}, headers=_hdr(token), timeout=30,
    )
    assert response.status_code == 200, response.text
    queued = response.json()
    job = _wait_job(queued["job_id"], token)
    assert job["status"] == "done", job.get("error_message")
    return job["result"]


def _make_csv(rows):
    """Generate a music_withdrawals.csv-shaped CSV from a list of dicts.
    Cells are double-quoted to handle commas inside label names.
    """
    import csv as _csv
    header = ["id", "trx_id", "nama_label", "amount", "exchange_rate", "status",
              "request_date", "payment_date", "period_start", "period_end", "created_at"]
    buf = io.StringIO()
    writer = _csv.writer(buf, quoting=_csv.QUOTE_ALL)
    writer.writerow(header)
    for i, r in enumerate(rows, start=1):
        writer.writerow([str(r.get(c, "")) for c in header])
    return buf.getvalue().encode("utf-8")


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def seeded_labels():
    """Seed 3 test labels with deliberately mismatched casing/punctuation,
    so the fuzzy matcher must handle them."""
    db = _mongo_db()
    test_id = uuid.uuid4().hex[:8]
    labels = [
        {"id": f"phase22-A-{test_id}", "label_name": "Phase22 Music Label", "last_withdrawn_period": None,
         "balance_available_idr": 0, "balance_pending_idr": 0, "balance_withdraw_requested_idr": 0,
         "status": "active", "account_status": "active", "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": f"phase22-B-{test_id}", "label_name": "Phase22 Sound", "last_withdrawn_period": "2024-06",
         "balance_available_idr": 0, "balance_pending_idr": 0, "balance_withdraw_requested_idr": 0,
         "status": "active", "account_status": "active", "created_at": "2026-01-01T00:00:00+00:00"},
        {"id": f"phase22-C-{test_id}", "label_name": "Phase22 Production", "last_withdrawn_period": None,
         "balance_available_idr": 0, "balance_pending_idr": 0, "balance_withdraw_requested_idr": 0,
         "status": "active", "account_status": "active", "created_at": "2026-01-01T00:00:00+00:00"},
    ]
    for lab in labels:
        db.labels.insert_one(lab)
    yield {"test_id": test_id, "labels": labels}
    # cleanup
    db.labels.delete_many({"id": {"$regex": f"phase22-.*-{test_id}"}})
    db.withdraw_requests.delete_many({"label_id": {"$regex": f"phase22-.*-{test_id}"}})


def test_rbac_non_super_admin_rejected(seeded_labels):
    t = _login(*SUPPORT)
    csv = _make_csv([])
    r = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("x.csv", b"nama_label,period_end\n", "text/csv")},
        data={"dry_run": "true"},
        headers=_hdr(t), timeout=30,
    )
    assert r.status_code == 403, r.text


def test_empty_csv_rejected(super_token):
    r = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("empty.csv", b"", "text/csv")},
        data={"dry_run": "true"}, headers=_hdr(super_token), timeout=30,
    )
    assert r.status_code == 400


def test_missing_period_end_column_rejected(super_token):
    csv = b"nama_label,amount\nAli,100\n"
    r = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("bad.csv", csv, "text/csv")},
        data={"dry_run": "true"}, headers=_hdr(super_token), timeout=30,
    )
    assert r.status_code == 400
    assert "period_end" in r.text


def test_dry_run_does_not_mutate(super_token, seeded_labels):
    db = _mongo_db()
    test_id = seeded_labels["test_id"]
    rows = [
        {"trx_id": "T1", "nama_label": "Phase22 Music Label", "period_start": "2023-01", "period_end": "2024-12"},
        {"trx_id": "T2", "nama_label": "phase22 sound", "period_start": "2024-07", "period_end": "2025-06"},
    ]
    csv = _make_csv(rows)
    before = db.labels.find_one({"id": f"phase22-A-{test_id}"}, {"last_withdrawn_period": 1})
    body = _preview_and_wait(csv, super_token)
    assert body["dry_run"] is True
    assert body["matched_labels"] == 2
    assert body["totals_preview"]["labels_period_will_advance"] == 2
    # DB unchanged
    after = db.labels.find_one({"id": f"phase22-A-{test_id}"}, {"last_withdrawn_period": 1})
    assert after.get("last_withdrawn_period") == before.get("last_withdrawn_period") is None
    # No legacy withdraw_requests inserted
    n_wd = db.withdraw_requests.count_documents({"label_id": f"phase22-A-{test_id}", "legacy_import": True})
    assert n_wd == 0


def test_fuzzy_matcher_handles_punctuation_and_pt_prefix(super_token, seeded_labels):
    """CSV variants like 'PT, Phase22 Music Label' and 'phase22 - music - label'
    should all match the same labels.label_name='Phase22 Music Label'.
    """
    csv = _make_csv([
        {"trx_id": "F1", "nama_label": "PT, Phase22 Music Label", "period_start": "2023-01", "period_end": "2023-12"},
        {"trx_id": "F2", "nama_label": "phase22 - music - label", "period_start": "2024-01", "period_end": "2024-06"},
        {"trx_id": "F3", "nama_label": "PHASE22 MUSIC LABEL.", "period_start": "2024-07", "period_end": "2025-03"},
    ])
    body = _preview_and_wait(csv, super_token)
    assert body["matched_labels"] == 1  # all 3 collapse to one label
    sm = body["label_summaries"][0]
    assert sm["new_last_withdrawn_period"] == "2025-03"  # MAX of 3 period_ends
    assert sm["csv_row_count"] == 3
    assert len(sm["csv_names"]) == 3  # all 3 raw variants captured


def _commit_and_wait(csv_bytes, super_token, max_wait=20):
    """Phase 26: commit returns 200 with `commit.queued=true` + job_id and runs
    the heavy writes in a background task. Poll until the job finishes, then
    return a synthetic body where `commit` looks like the old sync response so
    legacy assertions keep working."""
    r = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("a.csv", csv_bytes, "text/csv")},
        data={"dry_run": "false"}, headers=_hdr(super_token), timeout=60,
    )
    assert r.status_code == 200, r.text
    queued = r.json()
    job_id = queued["job_id"]
    job = _wait_job(job_id, super_token, max_wait=max_wait)
    if job["status"] == "error":
        raise AssertionError(f"job errored: {job.get('error_message')}")
    body = job.get("preview_result") or {}
    body["commit"] = {**job["result"], "queued": True, "job_id": job_id}
    return body


def test_commit_idempotent(super_token, seeded_labels):
    db = _mongo_db()
    test_id = seeded_labels["test_id"]
    csv = _make_csv([
        {"trx_id": f"IDEM-{test_id}-1", "nama_label": "Phase22 Music Label",
         "period_start": "2023-01", "period_end": "2024-12", "amount": "1500", "exchange_rate": "16000"},
        {"trx_id": f"IDEM-{test_id}-2", "nama_label": "Phase22 Sound",
         "period_start": "2024-07", "period_end": "2025-06", "amount": "500", "exchange_rate": "16000"},
        {"trx_id": f"IDEM-{test_id}-3", "nama_label": "Phase22 Production",
         "period_start": "2022-01", "period_end": "2023-05"},
    ])
    # First commit (now async — wait for the BG job to finish)
    body1 = _commit_and_wait(csv, super_token)
    assert body1["commit"]["applied"] is True
    assert body1["commit"]["labels_period_updated"] == 3
    assert body1["commit"]["history_docs_inserted"] == 3

    # Verify A updated, B advanced (was 2024-06, now 2025-06), C set fresh
    a = db.labels.find_one({"id": f"phase22-A-{test_id}"})
    b = db.labels.find_one({"id": f"phase22-B-{test_id}"})
    c = db.labels.find_one({"id": f"phase22-C-{test_id}"})
    assert a["last_withdrawn_period"] == "2024-12"
    assert b["last_withdrawn_period"] == "2025-06"
    assert c["last_withdrawn_period"] == "2023-05"

    # Re-run with the SAME csv → no updates, no new history docs
    body2 = _commit_and_wait(csv, super_token)
    assert body2["commit"]["labels_period_updated"] == 0
    assert body2["commit"]["history_docs_inserted"] == 0

    # Total legacy docs for these 3 labels should still be exactly 3
    n = db.withdraw_requests.count_documents({
        "label_id": {"$regex": f"phase22-.*-{test_id}"},
        "legacy_import": True,
    })
    assert n == 3


def test_b_label_only_advances_not_regresses(super_token, seeded_labels):
    """Label B started with last_withdrawn_period='2024-06'. After commit it
    should be at 2025-06 (advanced). Now upload a CSV with an OLDER period_end
    — it must NOT regress B's value.
    """
    db = _mongo_db()
    test_id = seeded_labels["test_id"]
    # Sanity: B is now at 2025-06 from previous test
    b_before = db.labels.find_one({"id": f"phase22-B-{test_id}"})
    assert b_before["last_withdrawn_period"] == "2025-06"

    csv = _make_csv([
        {"trx_id": f"OLD-{test_id}", "nama_label": "Phase22 Sound",
         "period_start": "2020-01", "period_end": "2022-03"},  # older
    ])
    body = _commit_and_wait(csv, super_token)
    sm = body["label_summaries"][0]
    assert sm["period_will_advance"] is False
    assert sm["new_last_withdrawn_period"] == "2025-06"  # unchanged

    b_after = db.labels.find_one({"id": f"phase22-B-{test_id}"})
    assert b_after["last_withdrawn_period"] == "2025-06"
