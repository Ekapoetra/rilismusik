"""Normalize new label ticket workflows; historical tickets remain unchanged."""
import re
from urllib.parse import urlparse, parse_qs
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .deps import db

TICKET_CATEGORY_LABELS = {
    "takedown": "Takedown Rilisan", "edit_metadata": "Edit Metadata",
    "edit_audio": "Edit Audio", "edit_cover": "Edit Cover",
    "content_id_claim": "Pengajuan YouTube Content ID", "content_id_release": "Cabut YouTube Content ID",
    "royalty_issue": "Masalah Royalti", "other": "Lainnya",
}
ACTIVE_CATEGORIES = tuple(key for key in TICKET_CATEGORY_LABELS if key not in {"royalty_issue", "other"})
AUTO_SUBJECT_CATEGORIES = {"takedown", "edit_metadata", "content_id_claim", "content_id_release"}
CONTENT_ID_CATEGORIES = {"content_id_claim", "content_id_release"}
TAKEDOWN_REASONS = {"Revisi Metadata", "Pindah Aggregator", "Konflik Hak Cipta", "Konflik Internal"}
METADATA_KEYS = ("release_title", "artist_name", "genre", "language", "copyright_line", "p_line")


class TicketCreatedOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    ticket_no: str
    release_id: str
    label_id: str
    subject: str
    description: str
    category: str
    status: str
    upc: str | None = None
    isrcs: list[str] = Field(default_factory=list)
    release_tracks: list[dict] = Field(default_factory=list)
    youtube_urls: list[str] = Field(default_factory=list)


def validate_youtube_urls(values: list[str]) -> list[str]:
    if not values:
        raise HTTPException(400, "Minimal satu link video YouTube wajib diisi")
    output, seen = [], set()
    for index, value in enumerate(values):
        url = value.strip()
        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower().removeprefix("www.")
            if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port not in (None, 443) or len(url) > 500:
                raise ValueError()
            parts = parsed.path.strip("/").split("/")
            if host == "youtu.be" and len(parts) == 1:
                video_id = parts[0]
            elif host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
                if parts == ["watch"]:
                    video_id = parse_qs(parsed.query).get("v", [""])[0]
                elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
                    video_id = parts[1]
                else:
                    raise ValueError()
            else:
                raise ValueError()
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
                raise ValueError()
        except ValueError:
            raise HTTPException(400, f"Link YouTube ke-{index + 1} harus berupa URL video HTTPS yang valid")
        if video_id in seen:
            raise HTTPException(400, f"Video YouTube ke-{index + 1} sudah ditambahkan")
        seen.add(video_id)
        output.append(url)
    return output


async def prepare_ticket_submission(body, release: dict) -> dict:
    tracks = await db.tracks.find({"release_id": release["id"]}, {
        "_id": 0, "id": 1, "track_title": 1, "track_number": 1, "isrc": 1,
    }).sort("track_number", 1).to_list(None)
    track_snapshots = [{"track_id": track["id"], "track_title": track.get("track_title") or "",
                        "track_number": track.get("track_number") or index + 1, "isrc": str(track["isrc"]).strip() if track.get("isrc") else None}
                       for index, track in enumerate(tracks)]
    isrcs = list(dict.fromkeys(track["isrc"] for track in track_snapshots if track["isrc"]))
    if not isrcs and release.get("isrc"):
        isrcs = [str(release["isrc"]).strip()]
    description = body.description.strip()
    reason = (body.reason or "").strip()
    subject = body.subject.strip()
    original = {key: str(release.get(key) or "") for key in METADATA_KEYS}
    new_metadata = None
    youtube_urls = []
    if body.category in AUTO_SUBJECT_CATEGORIES:
        subject = f"{TICKET_CATEGORY_LABELS[body.category]} — {release.get('release_title') or release['id']}"[:200]
    if body.category == "takedown":
        if reason not in TAKEDOWN_REASONS:
            raise HTTPException(400, "Pilih salah satu dari empat alasan takedown yang tersedia")
    if body.category in {"takedown", "edit_audio", "edit_cover"} and len(description) < 3:
        raise HTTPException(400, "Deskripsi wajib diisi minimal 3 karakter")
    if body.category in {"edit_audio", "edit_cover"} and len(subject) < 3:
        raise HTTPException(400, "Subjek wajib diisi minimal 3 karakter")
    if body.category == "edit_metadata":
        if not reason:
            raise HTTPException(400, "Alasan perubahan wajib diisi")
        if not body.new_metadata:
            raise HTTPException(400, "Metadata baru wajib diisi")
        if any(key not in METADATA_KEYS or not isinstance(value, str) or len(value) > 1000 for key, value in body.new_metadata.items()):
            raise HTTPException(400, "Kolom metadata tidak valid")
        new_metadata = {**original, **{key: value.strip() for key, value in body.new_metadata.items()}}
        description = ""
    if body.category in CONTENT_ID_CATEGORIES:
        if body.originality_declared is not True:
            raise HTTPException(400, "Pernyataan originalitas wajib disetujui")
        youtube_urls = validate_youtube_urls(body.youtube_urls or ([body.youtube_url] if body.youtube_url else []))
    return {
        "subject": subject, "description": description, "reason": reason or None,
        "upc": str(release["upc"]).strip() if release.get("upc") else None, "isrcs": isrcs, "release_tracks": track_snapshots,
        "original_metadata": original if body.category == "edit_metadata" else None,
        "new_metadata": new_metadata, "youtube_urls": youtube_urls,
        "youtube_url": youtube_urls[0] if youtube_urls else None,
        "originality_declared": bool(body.originality_declared) if body.category in CONTENT_ID_CATEGORIES else None,
    }