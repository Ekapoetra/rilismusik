"""Phase 28 — Auto-create Artists during CSV ingestion tests.

Covers:
  - Royalty CSV auto-creates Artists (not just Label/Release/Track) for new
    (label_id, artist_name) combinations.
  - artist_id is set on royalty_lines immediately at ingestion (no need to
    run Materialize Artists manually afterwards).
  - The Artist Management page (`GET /api/admin/artists`) shows the new
    artists with revenue rollups right after publish.
  - Existing (label_id, artist_name) combos do NOT create duplicates.
  - "Unknown" / blank artist names are skipped (not auto-created).
  - Cleanup: deleting the import also deletes auto-created artists.
"""
import io
import os
import time
import uuid
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lanjut-core.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

SUPER = {"email": "superadmin@rilismusik.com", "password": "SuperAdmin#2026"}


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds, timeout=30)
    assert r.status_code == 200, f"login {creds['email']} -> {r.status_code} {r.text[:200]}"
    return r.json()["access_token"]


def _h(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def super_tok():
    return _login(SUPER)


def _make_csv(rows):
    """rows = list of dicts with keys: label_name, artist, release_title,
    track_title, isrc, upc, period (optional)."""
    header = "Bulan laporan;Nama Label;Nama Artis;Judul rilis;Judul track;UPC;ISRC;Pendapatan Bersih"
    lines = [header]
    for r in rows:
        period = r.get("period", "2024-06")
        revenue = r.get("revenue", "1,2345")
        lines.append(
            f"{period};{r['label_name']};{r['artist']};{r['release_title']};{r['track_title']};{r['upc']};{r['isrc']};{revenue}"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _upload(super_tok, csv_bytes, filename="auto_artists.csv", rate="17000"):
    r = requests.post(
        f"{API}/royalty/admin/imports",
        headers=_h(super_tok),
        files={"file": (filename, csv_bytes, "text/csv")},
        data={"rate_eur_idr": rate},
        timeout=120,
    )
    assert r.status_code == 200, r.text
    return r.json()


# =======================================================================
# Core: auto_created_artists counter must appear in response
# =======================================================================
def test_autocreate_artist_counter_appears_in_import_response(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AA_{sfx}"
    artist_name = f"TEST_Artist_AA_{sfx}"
    csv_bytes = _make_csv([{
        "label_name": label_name, "artist": artist_name,
        "release_title": "RelA", "track_title": "TrackA",
        "isrc": f"IDAA{sfx}A", "upc": f"UPAA{sfx}A",
    }])
    body = _upload(super_tok, csv_bytes, filename=f"aa1_{sfx}.csv")
    assert body.get("auto_created_labels", 0) >= 1
    assert body.get("auto_created_releases", 0) >= 1
    assert body.get("auto_created_tracks", 0) >= 1
    assert body.get("auto_created_artists", 0) >= 1, body


# =======================================================================
# Artist Management endpoint shows new artist with revenue rollup
# =======================================================================
def test_artist_appears_in_admin_artists_endpoint(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AAEnd_{sfx}"
    artist_name = f"TEST_Artist_End_{sfx}"
    csv_bytes = _make_csv([{
        "label_name": label_name, "artist": artist_name,
        "release_title": "RelE", "track_title": "TrackE",
        "isrc": f"IDEND{sfx}A", "upc": f"UPEND{sfx}A",
        "revenue": "5,0000",
    }])
    _upload(super_tok, csv_bytes, filename=f"aaend_{sfx}.csv")

    # Artist Management list endpoint
    r = requests.get(f"{API}/admin/artists?q={artist_name}", headers=_h(super_tok), timeout=30)
    assert r.status_code == 200, r.text
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    matched = [x for x in items if x.get("artist_name") == artist_name]
    assert matched, f"new artist {artist_name} not found in /admin/artists"
    art = matched[0]
    assert art.get("imported_legacy") is True, art
    assert art.get("auto_created_from_lines") is True, art
    assert art.get("label_name", "").lower().startswith("test_aaend"), art
    # Revenue rollup should be hydrated
    assert art.get("revenue_eur", 0) >= 5.0, art
    assert art.get("royalty_lines_count", 0) >= 1, art
    assert art.get("last_active_period") == "2024-06", art


# =======================================================================
# royalty_lines artist_id is populated at ingestion (not null)
# =======================================================================
def test_royalty_lines_have_artist_id_populated(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AAId_{sfx}"
    artist_name = f"TEST_Artist_Id_{sfx}"
    csv_bytes = _make_csv([{
        "label_name": label_name, "artist": artist_name,
        "release_title": "RelI", "track_title": "TrackI",
        "isrc": f"IDID{sfx}A", "upc": f"UPID{sfx}A",
    }])
    body = _upload(super_tok, csv_bytes, filename=f"aaid_{sfx}.csv")
    import_id = body.get("id") or body.get("import_id")
    assert import_id

    # Read the rich import detail to access the line sample
    r = requests.get(f"{API}/royalty/admin/imports/{import_id}", headers=_h(super_tok), timeout=30)
    assert r.status_code == 200, r.text
    payload = r.json()
    lines = payload.get("lines") or []
    assert lines, "no lines in import detail"
    # Every line for this isrc must have artist_id set (not None/"")
    matched_lines = [l for l in lines if l.get("isrc") == f"IDID{sfx}A"]
    assert matched_lines, "test isrc not found in lines"
    for line in matched_lines:
        assert line.get("artist_id"), f"artist_id is empty on line: {line}"


# =======================================================================
# Idempotency: 2nd CSV with same (label, artist) does NOT create dup artist
# =======================================================================
def test_duplicate_artist_combo_not_created_twice(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AADup_{sfx}"
    artist_name = f"TEST_Artist_Dup_{sfx}"

    # First upload — creates label + artist
    csv1 = _make_csv([{
        "label_name": label_name, "artist": artist_name,
        "release_title": "Rel1", "track_title": "Trk1",
        "isrc": f"IDDUP{sfx}1", "upc": f"UPDUP{sfx}1",
    }])
    body1 = _upload(super_tok, csv1, filename=f"aadup1_{sfx}.csv")
    assert body1.get("auto_created_artists", 0) == 1, body1

    # Second upload — same label_name + artist_name, but different ISRC/UPC.
    # Label should match (fuzzy), artist should match by (label_id, slug) ->
    # NO new artist created.
    csv2 = _make_csv([{
        "label_name": label_name.upper(), "artist": artist_name,
        "release_title": "Rel2", "track_title": "Trk2",
        "isrc": f"IDDUP{sfx}2", "upc": f"UPDUP{sfx}2",
    }])
    body2 = _upload(super_tok, csv2, filename=f"aadup2_{sfx}.csv")
    assert body2.get("auto_created_labels", 0) == 0, body2
    assert body2.get("auto_created_artists", 0) == 0, body2  # KEY ASSERTION


# =======================================================================
# Skip Unknown / blank artist names
# =======================================================================
def test_unknown_and_blank_artist_names_are_skipped(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AASkip_{sfx}"

    # Mix: row with "Unknown" + row with blank + row with real name
    csv_bytes = _make_csv([
        {"label_name": label_name, "artist": "Unknown",
         "release_title": "R1", "track_title": "T1",
         "isrc": f"IDSK{sfx}1", "upc": f"UPSK{sfx}1"},
        {"label_name": label_name, "artist": "",
         "release_title": "R2", "track_title": "T2",
         "isrc": f"IDSK{sfx}2", "upc": f"UPSK{sfx}2"},
        {"label_name": label_name, "artist": f"REAL_Artist_{sfx}",
         "release_title": "R3", "track_title": "T3",
         "isrc": f"IDSK{sfx}3", "upc": f"UPSK{sfx}3"},
    ])
    body = _upload(super_tok, csv_bytes, filename=f"aaskip_{sfx}.csv")
    # Only 1 artist auto-created (the "REAL_Artist") — Unknown + blank skipped
    assert body.get("auto_created_artists", 0) == 1, body
    # All 3 lines matched (label is auto-created)
    assert body.get("matched_lines", body.get("matched", 0)) == 3, body


# =======================================================================
# Multiple distinct artists in same CSV all get created
# =======================================================================
def test_multiple_distinct_artists_in_same_csv(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AAMulti_{sfx}"
    rows = []
    for i in range(3):
        rows.append({
            "label_name": label_name, "artist": f"ArtistMulti_{sfx}_{i}",
            "release_title": f"R{i}", "track_title": f"T{i}",
            "isrc": f"IDML{sfx}{i}", "upc": f"UPML{sfx}{i}",
        })
    csv_bytes = _make_csv(rows)
    body = _upload(super_tok, csv_bytes, filename=f"aamulti_{sfx}.csv")
    assert body.get("auto_created_artists", 0) == 3, body


# =======================================================================
# Delete import also deletes auto-created artists
# =======================================================================
def test_delete_import_also_deletes_auto_created_artists(super_tok):
    sfx = uuid.uuid4().hex[:6].upper()
    label_name = f"TEST_AADel_{sfx}"
    artist_name = f"TEST_Artist_Del_{sfx}"
    csv_bytes = _make_csv([{
        "label_name": label_name, "artist": artist_name,
        "release_title": "RDel", "track_title": "TDel",
        "isrc": f"IDDEL{sfx}A", "upc": f"UPDEL{sfx}A",
    }])
    body = _upload(super_tok, csv_bytes, filename=f"aadel_{sfx}.csv")
    import_id = body.get("id") or body.get("import_id")
    assert import_id

    # Confirm artist exists
    r = requests.get(f"{API}/admin/artists?q={artist_name}", headers=_h(super_tok), timeout=30)
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    assert any(x.get("artist_name") == artist_name for x in items), "artist not created"

    # Delete the import — async returns 202 then background delete
    rd = requests.delete(f"{API}/royalty/admin/imports/{import_id}", headers=_h(super_tok), timeout=30)
    assert rd.status_code in (200, 202), rd.text

    # Poll until import is gone (delete is bg)
    for _ in range(20):
        rg = requests.get(f"{API}/royalty/admin/imports/{import_id}", headers=_h(super_tok), timeout=15)
        if rg.status_code == 404:
            break
        time.sleep(1)
    else:
        pytest.fail("import was not deleted after 20s")

    # Artist should be gone too
    r2 = requests.get(f"{API}/admin/artists?q={artist_name}", headers=_h(super_tok), timeout=30)
    items2 = r2.json() if isinstance(r2.json(), list) else r2.json().get("items", [])
    remaining = [x for x in items2 if x.get("artist_name") == artist_name]
    assert not remaining, f"artist {artist_name} should be deleted but found: {remaining}"
