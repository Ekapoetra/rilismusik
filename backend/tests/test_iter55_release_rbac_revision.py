"""Iter 55 — release RBAC and need_revision resubmit behavior."""
import uuid

import requests

from tests.support_config import SUPERADMIN, FINANCE
from tests.test_phase43_release_approval_invoice import (
    API, _cleanup, _db, _headers, _login, _seed_ppr_label,
)
from tests.test_phase65_release_submission_workflow import _payload


# RBAC: only owner label can edit/submit release draft
def test_only_owner_label_can_edit_release_draft():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    owner = _seed_ppr_label(db, f"owner-{suffix}")
    outsider = _seed_ppr_label(db, f"outsider-{suffix}")
    release_id = ""
    try:
        owner_token = _login(owner["email"], owner["password"])
        outsider_token = _login(outsider["email"], outsider["password"])
        created = requests.post(f"{API}/releases/draft", json=_payload("RBAC Owner Draft"), headers=_headers(owner_token), timeout=30)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]

        blocked_patch = requests.patch(f"{API}/releases/{release_id}", json=_payload("Blocked outsider edit"), headers=_headers(outsider_token), timeout=30)
        assert blocked_patch.status_code == 403

        blocked_submit = requests.post(
            f"{API}/releases/{release_id}/submit",
            json={"contract_declaration_checked": True, "addon_product_ids": []},
            headers=_headers(outsider_token), timeout=30,
        )
        assert blocked_submit.status_code == 403
    finally:
        _cleanup(db, owner, release_id, f"iter55-unused-{suffix}")
        _cleanup(db, outsider, "", f"iter55-unused2-{suffix}")


# Workflow: need_revision remains editable, resubmit clears active note and keeps history
def test_need_revision_resubmit_clears_active_note_preserves_history():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix)
    release_id = ""
    note = "Perbaiki metadata title case"
    try:
        label_token = _login(seeded["email"], seeded["password"])
        admin_token = _login(SUPERADMIN["email"], SUPERADMIN["password"])
        created = requests.post(f"{API}/releases/draft", json=_payload("Need Revision Round"), headers=_headers(label_token), timeout=30)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]

        db.releases.update_one({"id": release_id}, {"$set": {
            "cover_url": "/api/files/iter55-cover.jpg", "cover_width": 3000, "cover_height": 3000,
        }})
        db.tracks.update_many({"release_id": release_id}, {"$set": {
            "audio_url": "/api/files/iter55.wav", "audio_filename": "iter55.wav", "audio_sample_rate": 44100,
        }})

        submitted = requests.post(
            f"{API}/releases/{release_id}/submit",
            json={"contract_declaration_checked": True, "addon_product_ids": []},
            headers=_headers(label_token), timeout=30,
        )
        assert submitted.status_code == 200 and submitted.json()["status"] == "submitted"
        requests.post(f"{API}/releases/{release_id}/admin/action", json={"action": "start_review"}, headers=_headers(admin_token), timeout=30).raise_for_status()
        revision = requests.post(
            f"{API}/releases/{release_id}/admin/action",
            json={"action": "need_revision", "note": note},
            headers=_headers(admin_token), timeout=30,
        )
        assert revision.status_code == 200 and revision.json()["status"] == "need_revision"
        assert revision.json().get("admin_note") == note

        detail = requests.get(f"{API}/releases/{release_id}", headers=_headers(label_token), timeout=30).json()
        edited = _payload("Need Revision Round 2")
        for index, track in enumerate(edited["tracks"]):
            track["id"] = detail["tracks"][index]["id"]
            track["audio_url"] = detail["tracks"][index]["audio_url"]
        patched = requests.patch(f"{API}/releases/{release_id}", json=edited, headers=_headers(label_token), timeout=30)
        assert patched.status_code == 200, patched.text

        resubmitted = requests.post(
            f"{API}/releases/{release_id}/submit",
            json={"contract_declaration_checked": True, "addon_product_ids": []},
            headers=_headers(label_token), timeout=30,
        )
        assert resubmitted.status_code == 200 and resubmitted.json()["status"] == "submitted"
        assert resubmitted.json().get("admin_note") is None

        history = db.releases.find_one({"id": release_id}, {"_id": 0, "status_history": 1})["status_history"]
        assert any(item.get("to") == "need_revision" and item.get("note") == note for item in history)
        assert history[-1]["to"] == "submitted"
    finally:
        _cleanup(db, seeded, release_id, f"iter55-unused-{suffix}")


# RBAC: finance/support cannot run release workflow action mutations
def test_finance_cannot_mutate_release_workflow():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix)
    release_id = ""
    try:
        label_token = _login(seeded["email"], seeded["password"])
        finance_token = _login(FINANCE["email"], FINANCE["password"])
        created = requests.post(f"{API}/releases/draft", json=_payload("Finance RBAC"), headers=_headers(label_token), timeout=30)
        assert created.status_code == 200, created.text
        release_id = created.json()["id"]

        forbidden = requests.post(
            f"{API}/releases/{release_id}/admin/action",
            json={"action": "start_review"},
            headers=_headers(finance_token), timeout=30,
        )
        assert forbidden.status_code == 403
    finally:
        _cleanup(db, seeded, release_id, f"iter55-unused-{suffix}")


def test_draft_rejects_custom_youtube_handle():
    db = _db()
    suffix = uuid.uuid4().hex[:10]
    seeded = _seed_ppr_label(db, suffix)
    try:
        label_token = _login(seeded["email"], seeded["password"])
        payload = _payload("Invalid YouTube Handle")
        payload["artist_web_url"] = "https://youtube.com/@customhandle"
        response = requests.post(
            f"{API}/releases/draft", json=payload,
            headers=_headers(label_token), timeout=30,
        )
        assert response.status_code == 400
        assert "channel/UC" in response.text
    finally:
        _cleanup(db, seeded, "", f"iter55-unused-{suffix}")
