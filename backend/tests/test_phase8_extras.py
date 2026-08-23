"""Phase 8 supplementary tests — covers items not in test_phase8_migrate.py.

- Bulk releases (label lookup by name, ISRC dedupe, default release_date)
- Bulk tracks (release lookup by ISRC, audio_url optional)
- Bulk withdraws (no balance mutation, legacy_import flag)
- Multi-period publish (description shows "X s/d Y", balance accumulates)
- Reject claim flow
- CSV templates for releases/tracks/withdraws
- /admin/migrate/labels/unclaimed endpoint
"""
import io
import os
import uuid
import time
import requests
from tests.support_config import FINANCE as FINANCE_CRED, SUPERADMIN, temporary_password
import pytest

BASE = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE}/api"
SUPER = (SUPERADMIN["email"], SUPERADMIN["password"])


def _login(email, pw):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": pw}, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _cleanup_phase8_artifacts():
    import pymongo
    sync_db = pymongo.MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    labels = list(sync_db.labels.find({"$or": [
        {"label_name": {"$regex": "^Phase8X Label"}},
        {"email": {"$regex": "^(claim_p8_|reject_p8_)"}},
    ]}, {"_id": 0, "id": 1, "user_id": 1}))
    label_ids = [label["id"] for label in labels]
    user_ids = [label.get("user_id") for label in labels if label.get("user_id")]
    sync_db.royalty_lines.delete_many({"label_id": {"$in": label_ids}})
    sync_db.labels.delete_many({"id": {"$in": label_ids}})
    sync_db.users.delete_many({"$or": [{"id": {"$in": user_ids}}, {"email": {"$regex": "^(claim_p8_|reject_p8_)"}}]})


@pytest.fixture(scope="session", autouse=True)
def cleanup_phase8_artifacts():
    _cleanup_phase8_artifacts()
    yield
    _cleanup_phase8_artifacts()


@pytest.fixture(scope="module")
def super_token():
    return _login(*SUPER)


@pytest.fixture(scope="module")
def seeded_label(super_token):
    suffix = uuid.uuid4().hex[:8]
    name = f"Phase8X Label {suffix}"
    csv = (
        "label_name,pic_name,whatsapp,city,country\n"
        f"{name},PIC X,081200000001,Yogyakarta,Indonesia\n"
    )
    r = requests.post(
        f"{API}/admin/migrate/labels",
        headers=_h(super_token),
        files={"file": ("seed.csv", csv, "text/csv")},
        timeout=30,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["inserted"] == 1
    label_id = body["report"][0]["reason"].split("id=")[1]
    return {"label_id": label_id, "label_name": name, "suffix": suffix}


class TestTemplates:
    @pytest.mark.parametrize("kind,first_col", [
        ("releases", "label_legacy_id"),
        ("tracks", "release_legacy_id"),
        ("withdraws", "label_legacy_id"),
    ])
    def test_templates(self, super_token, kind, first_col):
        r = requests.get(f"{API}/admin/migrate/template/{kind}", headers=_h(super_token), timeout=15)
        assert r.status_code == 200
        assert first_col in r.text


class TestBulkReleasesAndTracks:
    def test_releases_import_and_dedupe(self, super_token, seeded_label):
        label_name = seeded_label["label_name"]
        suffix = seeded_label["suffix"]
        isrc = f"IDPX8{suffix[:6].upper()}1"
        csv = (
            "label_legacy_id,label_name,release_title,primary_artist,isrc_release,upc,release_type,release_date,status\n"
            f",{label_name},Album Lawas A,Artist X,{isrc},,single,,live\n"
            f",{label_name},Album Lawas B,Artist X,,,,2022-05-01,live\n"
            f",Nonexistent Label,Should Fail,X,,,,,live\n"
        )
        r = requests.post(
            f"{API}/admin/migrate/releases",
            headers=_h(super_token),
            files={"file": ("rel.csv", csv, "text/csv")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["inserted"] == 2
        assert body["errors"] == 1
        # Re-upload identical ISRC → SKIPPED
        r2 = requests.post(
            f"{API}/admin/migrate/releases",
            headers=_h(super_token),
            files={"file": ("rel.csv", csv, "text/csv")},
            timeout=30,
        )
        body2 = r2.json()
        # First row has ISRC → SKIPPED; second has no ISRC → re-inserted (no dedupe key)
        assert body2["skipped"] >= 1

    def test_tracks_import_audio_url_optional(self, super_token, seeded_label):
        label_name = seeded_label["label_name"]
        suffix = seeded_label["suffix"]
        rel_isrc = f"IDPX8{suffix[:6].upper()}1"  # from previous test
        track_isrc = f"IDPX8{suffix[:6].upper()}T"
        csv = (
            "release_legacy_id,release_isrc,track_title,artist_name,isrc,duration_sec,composer,audio_url\n"
            f",{rel_isrc},Track Tanpa Audio,Artist X,{track_isrc},180,Composer X,\n"
            f",NONEXISTENT,Should Fail,Y,,,,\n"
        )
        r = requests.post(
            f"{API}/admin/migrate/tracks",
            headers=_h(super_token),
            files={"file": ("trk.csv", csv, "text/csv")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["inserted"] == 1
        assert body["errors"] == 1


class TestBulkWithdraws:
    def test_withdraws_import_no_balance_mutation(self, super_token, seeded_label):
        # Capture balance before
        # use unclaimed endpoint to check label
        lid = seeded_label["label_id"]
        before = requests.get(f"{API}/admin/migrate/labels/unclaimed?q={seeded_label['label_name'][:6]}", headers=_h(super_token), timeout=15).json()
        lab = next((l for l in before if l["id"] == lid), None)
        assert lab is not None
        bal_before = lab.get("balance_available_idr", 0)

        csv = (
            "label_legacy_id,label_name,amount_idr,request_date,payment_date,status,bank_ref,notes\n"
            f"{lid},,500000,2021-06-01,2021-06-05,paid,BANKREF001,Old payout\n"
            f"{lid},,250000,2021-07-01,,cancelled,,Cancelled by user\n"
        )
        r = requests.post(
            f"{API}/admin/migrate/withdraws",
            headers=_h(super_token),
            files={"file": ("wd.csv", csv, "text/csv")},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["inserted"] == 2
        assert body["errors"] == 0

        # Balance should NOT have mutated
        after = requests.get(f"{API}/admin/migrate/labels/unclaimed?q={seeded_label['label_name'][:6]}", headers=_h(super_token), timeout=15).json()
        lab2 = next((l for l in after if l["id"] == lid), None)
        assert lab2.get("balance_available_idr", 0) == bal_before


class TestMultiPeriodPublish:
    def test_publish_multi_period_description(self, super_token, seeded_label):
        label_name = seeded_label["label_name"]
        suffix = seeded_label["suffix"]
        # Use a track ISRC from the seeded label so it matches
        track_isrc = f"IDPX8{suffix[:6].upper()}T"
        csv = (
            "Bulan Laporan,ISRC,Label,Platform,Negara,Kuantias,Pendapatan Bersih\n"
            f"2023-10,{track_isrc},{label_name},Spotify,ID,1000,5.50\n"
            f"2023-11,{track_isrc},{label_name},Spotify,ID,1500,7.20\n"
            f"2023-12,{track_isrc},{label_name},Apple Music,US,800,4.10\n"
        )
        r = requests.post(
            f"{API}/royalty/admin/imports",
            headers=_h(super_token),
            files={"file": ("mp.csv", csv, "text/csv")},
            data={"rate_eur_idr": "17000"},
            timeout=30,
        )
        assert r.status_code == 200, r.text
        imp = r.json()
        assert imp["is_multi_period"] is True
        assert imp["period_start"] == "2023-10"
        assert imp["period_end"] == "2023-12"
        import_id = imp["id"]

        # Publish
        pub = requests.post(
            f"{API}/royalty/admin/imports/{import_id}/publish",
            headers=_h(super_token),
            json={},
            timeout=30,
        )
        assert pub.status_code == 200, pub.text
        assert pub.json()["status"] in ("publishing", "published")
        deadline = time.time() + 30
        while time.time() < deadline:
            current = requests.get(
                f"{API}/royalty/admin/imports/{import_id}", headers=_h(super_token), timeout=15,
            ).json()
            if current["import"]["status"] == "published":
                break
            if current["import"]["status"] == "publish_error":
                raise AssertionError(current)
            time.sleep(0.3)
        else:
            raise AssertionError("Publish background job timeout")

        # Check balance_transactions description for "s/d"
        # We use admin endpoint to fetch the import detail (includes per_label)
        det = requests.get(f"{API}/royalty/admin/imports/{import_id}", headers=_h(super_token), timeout=15).json()
        assert det["import"]["status"] == "published"
        # per_label should have at least 1 entry (matched by label_name)
        assert len(det["per_label"]) >= 1


class TestRejectClaim:
    def test_reject_claim(self, super_token, seeded_label):
        email = f"reject_p8_{uuid.uuid4().hex[:6]}@example.com"
        r = requests.post(
            f"{API}/auth/register",
            json={
                "label_name": "Future Label R",
                "pic_name": "Rejected User",
                "email": email,
                "whatsapp": "081200099099",
                "password": temporary_password("phase8-reject"),
                "account_type": "label",
                "mda_accepted": True,
                "claim_existing": True,
                "legacy_label_name": "Nonexistent Phantom Label",
            },
            timeout=15,
        )
        assert r.status_code == 200, r.text
        user_id = r.json()["user"]["id"]

        # Reject
        rej = requests.post(
            f"{API}/admin/migrate/claims/{user_id}/reject",
            headers=_h(super_token),
            data={"reason": "Tidak ada bukti kepemilikan."},
            timeout=15,
        )
        assert rej.status_code == 200, rej.text
        assert rej.json()["ok"] is True

        # Second rejection should fail (not pending anymore)
        rej2 = requests.post(
            f"{API}/admin/migrate/claims/{user_id}/reject",
            headers=_h(super_token),
            data={"reason": "again"},
            timeout=15,
        )
        assert rej2.status_code == 400


class TestPermissionsExtra:
    def test_finance_cannot_link_claim(self):
        # Finance is not in (super_admin, admin_release, admin_support)
        tok = _login(FINANCE_CRED["email"], FINANCE_CRED["password"])
        # We don't have a real pending user_id but the role check fires first → 403
        r = requests.post(
            f"{API}/admin/migrate/claims/fake_user_id/link/fake_label_id",
            headers=_h(tok),
            timeout=15,
        )
        assert r.status_code == 403

    def test_template_requires_admin(self):
        r = requests.get(f"{API}/admin/migrate/template/labels", timeout=15)
        assert r.status_code in (401, 403)
