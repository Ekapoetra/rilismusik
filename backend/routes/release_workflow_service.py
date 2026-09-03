"""Release submission validation and admin workflow guards."""
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import HTTPException


EDITABLE_STATUSES = ("draft", "need_revision")
RELEASE_TYPES = ("single", "ep", "album")


def _filled(value: Any) -> bool:
    return bool(str(value or "").strip())


def validate_spotify_artist_url(value: Optional[str], field: str) -> None:
    if not _filled(value):
        return
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in ("http", "https") or parsed.netloc.lower() not in ("open.spotify.com", "www.open.spotify.com"):
        raise HTTPException(status_code=400, detail=f"{field} harus berupa URL profil artist Spotify")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "artist":
        raise HTTPException(status_code=400, detail=f"{field} harus mengarah ke profil /artist/ Spotify")


def validate_artist_web_url(value: Optional[str]) -> None:
    if not _filled(value):
        raise HTTPException(status_code=400, detail="URL web artist atau channel YouTube wajib diisi")
    parsed = urlparse(str(value).strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="URL web artist atau YouTube tidak valid")
    host = parsed.netloc.lower().removeprefix("www.")
    if host in ("youtube.com", "m.youtube.com"):
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[0] != "channel" or not parts[1].startswith("UC"):
            raise HTTPException(status_code=400, detail="Gunakan URL channel asli YouTube dengan format youtube.com/channel/UC…")


def normalize_artist_credits(values: List[Any], fallback_name: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    credits: List[Dict[str, Optional[str]]] = []
    for item in values or []:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        name = str(data.get("name") or "").strip()
        if not name:
            continue
        spotify_url = str(data.get("spotify_url") or "").strip() or None
        validate_spotify_artist_url(spotify_url, f"URL Spotify {name}")
        credits.append({"name": name, "spotify_url": spotify_url})
    if not credits and _filled(fallback_name):
        credits.append({"name": str(fallback_name).strip(), "spotify_url": None})
    return credits


def validate_release_date(value: str) -> date:
    try:
        release_date = date.fromisoformat(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Tanggal rilis digital tidak valid")
    if release_date < date.today() + timedelta(days=7):
        raise HTTPException(status_code=400, detail="Tanggal rilis digital minimal 7 hari setelah submit")
    return release_date


def validate_release_submission(release: Dict[str, Any], tracks: List[Dict[str, Any]]) -> None:
    required_release = {
        "release_title": "Judul rilisan", "genre": "Genre", "subgenre": "Sub Genre",
        "copyright_line": "C Line", "p_line": "P Line", "label_name_snapshot": "Nama label",
        "responsible_name": "Nama penanggung jawab", "artist_web_url": "URL web artist atau YouTube",
    }
    missing = [label for field, label in required_release.items() if not _filled(release.get(field))]
    if release.get("release_type") not in RELEASE_TYPES:
        missing.append("Tipe rilisan SINGLE/EP/ALBUM")
    if not release.get("year"):
        missing.append("Tahun produksi")
    primary = release.get("primary_artists") or []
    if not primary:
        missing.append("Minimal satu artist utama")
    for item in primary:
        validate_spotify_artist_url(item.get("spotify_url"), f"URL Spotify {item.get('name') or 'artist'}")
    for item in release.get("featured_artists") or []:
        validate_spotify_artist_url(item.get("spotify_url"), f"URL Spotify {item.get('name') or 'featuring'}")
    validate_artist_web_url(release.get("artist_web_url"))
    validate_release_date(release.get("release_date"))
    if not release.get("cover_url") or release.get("cover_width") != 3000 or release.get("cover_height") != 3000:
        missing.append("Cover JPG/PNG tepat 3000×3000")
    if not tracks:
        missing.append("Minimal satu track")
    if release.get("release_type") == "single" and len(tracks) != 1:
        missing.append("SINGLE harus memiliki tepat satu track")
    for index, track in enumerate(tracks, start=1):
        prefix = f"Track {index}"
        for field, label in (
            ("track_title", "judul"), ("lyricist", "nama pencipta/writer"),
            ("composer", "nama komposer"), ("title_language", "bahasa judul"),
        ):
            if not _filled(track.get(field)):
                missing.append(f"{prefix}: {label}")
        if track.get("vocal_type") not in ("vocal", "instrumental"):
            missing.append(f"{prefix}: instrumental atau vokal")
        if track.get("vocal_type") == "instrumental":
            track["lyrics"] = "Instrumental"
            track["lyric_language"] = "Instrumental"
        else:
            if not _filled(track.get("lyric_language")):
                missing.append(f"{prefix}: bahasa lirik")
            if not _filled(track.get("lyrics")):
                missing.append(f"{prefix}: lirik lengkap")
        if not track.get("audio_url") or track.get("audio_sample_rate") not in (44100, 48000):
            missing.append(f"{prefix}: audio WAV 44,1/48 kHz")
    if missing:
        unique = list(dict.fromkeys(missing))
        raise HTTPException(status_code=400, detail="Data rilisan belum lengkap: " + "; ".join(unique))


def require_status(release: Dict[str, Any], allowed: tuple[str, ...], action_label: str) -> None:
    if release.get("status") not in allowed:
        allowed_text = ", ".join(allowed)
        raise HTTPException(status_code=409, detail=f"{action_label} hanya tersedia dari status: {allowed_text}")