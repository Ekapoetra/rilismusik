"""Phase 22 — extra coverage for testing iteration 25.

Covers items NOT in the existing test_phase22_legacy_withdraw_migration.py:
  - RBAC: admin_finance & admin_release also rejected with 403.
  - flip_royalty_lines=False keeps royalty_lines.status unchanged.
  - flip_royalty_lines=True flips pending/available → withdrawn (period in window).
  - adjust_balances=False keeps balance_pending_idr / balance_available_idr unchanged.
  - create_history_docs=False does NOT insert withdraw_requests on commit.
"""
import io
import os
import uuid
import csv as _csv
import time
import requests
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
SUPER = ("superadmin@rilismusik.com", "SuperAdmin#2026")
FINANCE = ("finance1@rilismusik.com", "Finance#2026")
RELEASE = ("release1@rilismusik.com", "Release#2026")


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


def _make_csv(rows):
    header = ["id", "trx_id", "nama_label", "amount", "exchange_rate", "status",
              "request_date", "payment_date", "period_start", "period_end", "created_at"]
    buf = io.StringIO()
    w = _csv.writer(buf, quoting=_csv.QUOTE_ALL)
    w.writerow(header)
    for r in rows:
        w.writerow([str(r.get(c, "")) for c in header])
    return buf.getvalue().encode("utf-8")


def _commit_and_wait(csv_bytes, token, **options):
    response = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("c.csv", csv_bytes, "text/csv")},
        data={"dry_run": "false", **options},
        headers=_hdr(token), timeout=60,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    job_id = body.get("job_id")
    if not job_id:
        return body
    deadline = time.time() + 30
    while time.time() < deadline:
        job_response = requests.get(f"{API}/admin/migrate/jobs/{job_id}", headers=_hdr(token), timeout=20)
        job_response.raise_for_status()
        job = job_response.json()
        if job["status"] == "done":
            body["commit"] = job["result"]
            return body
        if job["status"] == "error":
            raise AssertionError(job.get("error_message"))
        time.sleep(0.3)
    raise AssertionError(f"job {job_id} timeout")


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def seeded():
    """Seed one fresh label with synthetic royalty_lines spanning a few periods,
    so we can verify flip-on / flip-off / balance-on / balance-off behavior.
    """
    db = _mongo_db()
    tid = uuid.uuid4().hex[:8]
    label = {
        "id": f"p22x-{tid}",
        "label_name": f"Phase22X Label {tid}",
        "last_withdrawn_period": None,
        "balance_available_idr": 100_000,
        "balance_pending_idr": 50_000,
        "balance_withdraw_requested_idr": 0,
        "status": "active",
        "account_status": "active",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    db.labels.insert_one(label)
    lines = []
    # 4 royalty lines across 2 periods that fall under period_end=2024-12 cutoff
    for i, (period, status, amt) in enumerate([
        ("2024-10", "available", 20_000),
        ("2024-11", "available", 30_000),
        ("2024-12", "pending", 25_000),
        ("2025-03", "available", 50_000),  # AFTER cutoff — must NOT flip
    ]):
        lines.append({
            "id": f"rl-p22x-{tid}-{i}",
            "label_id": label["id"],
            "period": period,
            "status": status,
            "label_idr": amt,
            "match_status": "matched",
        })
    db.royalty_lines.insert_many(lines)
    yield {"tid": tid, "label": label, "lines": lines}
    db.labels.delete_many({"id": label["id"]})
    db.royalty_lines.delete_many({"label_id": label["id"]})
    db.withdraw_requests.delete_many({"label_id": label["id"]})


@pytest.mark.parametrize("creds", [FINANCE, RELEASE])
def test_rbac_other_subadmins_rejected(creds):
    t = _login(*creds)
    r = requests.post(
        f"{API}/admin/migrate/withdraws-legacy-period",
        files={"file": ("x.csv", b"nama_label,period_end\nX,2024-01\n", "text/csv")},
        data={"dry_run": "true"},
        headers=_hdr(t), timeout=30,
    )
    assert r.status_code == 403, f"{creds[0]} should be 403 but got {r.status_code}: {r.text}"


def test_flip_lines_false_keeps_statuses(super_token, seeded):
    db = _mongo_db()
    label_id = seeded["label"]["id"]
    csv = _make_csv([
        {"trx_id": f"NOFLIP-{seeded['tid']}", "nama_label": seeded["label"]["label_name"],
         "period_start": "2024-01", "period_end": "2024-12", "amount": "10", "exchange_rate": "16000"},
    ])
    before_statuses = [l["status"] for l in db.royalty_lines.find({"label_id": label_id}, {"_id": 0, "status": 1, "period": 1}).sort("period", 1)]
    body = _commit_and_wait(csv, super_token, flip_royalty_lines="false",
                            adjust_balances="false", create_history_docs="false")
    assert body["commit"]["applied"] is True
    after_statuses = [l["status"] for l in db.royalty_lines.find({"label_id": label_id}, {"_id": 0, "status": 1, "period": 1}).sort("period", 1)]
    assert before_statuses == after_statuses, f"Royalty lines should be unchanged when flip=false: {before_statuses} -> {after_statuses}"
    # Period should still advance (period flag is independent)
    lab = db.labels.find_one({"id": label_id})
    assert lab["last_withdrawn_period"] == "2024-12"
    # No history docs inserted
    n = db.withdraw_requests.count_documents({"label_id": label_id, "legacy_import": True})
    assert n == 0


def test_adjust_balances_false_keeps_balances(super_token, seeded):
    db = _mongo_db()
    label_id = seeded["label"]["id"]
    # Reset label's last_withdrawn_period to None & restore balances to test isolated
    db.labels.update_one({"id": label_id}, {"$set": {
        "last_withdrawn_period": None,
        "balance_available_idr": 100_000,
        "balance_pending_idr": 50_000,
    }})
    db.royalty_lines.update_many({"label_id": label_id}, {"$unset": {
        "legacy_settled": "", "legacy_settled_period_end": "", "legacy_settled_at": "",
    }})
    # Reset royalty_lines too
    db.royalty_lines.update_many({"label_id": label_id, "period": "2024-10"}, {"$set": {"status": "available"}})
    db.royalty_lines.update_many({"label_id": label_id, "period": "2024-11"}, {"$set": {"status": "available"}})
    db.royalty_lines.update_many({"label_id": label_id, "period": "2024-12"}, {"$set": {"status": "pending"}})

    csv = _make_csv([
        {"trx_id": f"NOBAL-{seeded['tid']}", "nama_label": seeded["label"]["label_name"],
         "period_start": "2024-01", "period_end": "2024-12"},
    ])
    _commit_and_wait(csv, super_token, flip_royalty_lines="true",
                     adjust_balances="false", create_history_docs="false")
    lab = db.labels.find_one({"id": label_id})
    # Balances must be unchanged
    assert lab["balance_available_idr"] == 100_000, f"available changed unexpectedly to {lab['balance_available_idr']}"
    assert lab["balance_pending_idr"] == 50_000, f"pending changed unexpectedly to {lab['balance_pending_idr']}"
    # But lines should have flipped (flip flag was true)
    flipped = list(db.royalty_lines.find({"label_id": label_id, "status": "withdrawn"}))
    assert len(flipped) == 3, f"Expected 3 lines flipped (periods 10/11/12), got {len(flipped)}"


def test_flip_lines_true_and_adjust_true_full_effect(super_token, seeded):
    """Reset and run full commit with flip+adjust+history all ON. Verify balances
    decremented by exact summed label_idr, lines flipped, and one history doc inserted.
    """
    db = _mongo_db()
    label_id = seeded["label"]["id"]
    # Reset for an isolated full-effect test
    db.labels.update_one({"id": label_id}, {"$set": {
        "last_withdrawn_period": None,
        "balance_available_idr": 100_000,
        "balance_pending_idr": 50_000,
    }})
    db.royalty_lines.update_many({"label_id": label_id}, {"$unset": {
        "legacy_settled": "", "legacy_settled_period_end": "", "legacy_settled_at": "",
    }})
    db.royalty_lines.update_many({"label_id": label_id, "period": "2024-10"}, {"$set": {"status": "available"}})
    db.royalty_lines.update_many({"label_id": label_id, "period": "2024-11"}, {"$set": {"status": "available"}})
    db.royalty_lines.update_many({"label_id": label_id, "period": "2024-12"}, {"$set": {"status": "pending"}})
    db.royalty_lines.update_many({"label_id": label_id, "period": "2025-03"}, {"$set": {"status": "available"}})
    db.withdraw_requests.delete_many({"label_id": label_id, "legacy_import": True})

    csv = _make_csv([
        {"trx_id": f"FULL-{seeded['tid']}", "nama_label": seeded["label"]["label_name"],
         "period_start": "2024-01", "period_end": "2024-12", "amount": "5", "exchange_rate": "16000"},
    ])
    body = _commit_and_wait(csv, super_token, flip_royalty_lines="true",
                            adjust_balances="true", create_history_docs="true")
    assert body["commit"]["applied"] is True

    # Lines: 3 flipped, 1 (2025-03) untouched
    flipped = list(db.royalty_lines.find({"label_id": label_id, "status": "withdrawn"}))
    assert len(flipped) == 3
    untouched = db.royalty_lines.find_one({"label_id": label_id, "period": "2025-03"})
    assert untouched["status"] == "available"

    # Balances decremented. The 3 flipped lines were:
    #  - 2024-10 available 20k
    #  - 2024-11 available 30k  → total available adjustments = 50k
    #  - 2024-12 pending 25k    → total pending adjustments = 25k
    lab = db.labels.find_one({"id": label_id})
    assert lab["balance_available_idr"] == 100_000 - 50_000, f"got {lab['balance_available_idr']}"
    assert lab["balance_pending_idr"] == 50_000 - 25_000, f"got {lab['balance_pending_idr']}"

    # History doc inserted
    n = db.withdraw_requests.count_documents({"label_id": label_id, "legacy_import": True})
    assert n == 1
    wd = db.withdraw_requests.find_one({"label_id": label_id, "legacy_import": True})
    assert wd["status"] == "paid"
    assert wd.get("legacy_trx_id") == f"FULL-{seeded['tid']}"
