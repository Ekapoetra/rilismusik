"""Validation and release snapshot helpers for artist social profiles."""
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

from fastapi import HTTPException

from models import new_id, now_iso


SOCIAL_PLATFORMS = {"instagram", "tiktok", "facebook", "youtube", "x", "spotify", "website", "other"}
PLATFORM_HOSTS = {
    "instagram": ("instagram.com",),
    "tiktok": ("tiktok.com",),
    "facebook": ("facebook.com", "fb.com"),
    "youtube": ("youtube.com", "youtu.be"),
    "x": ("x.com", "twitter.com"),
    "spotify": ("open.spotify.com",),
}


def normalize_social_links(values: List[Any], *, required: bool = False, owner: str = "Artis") -> List[Dict[str, str]]:
    links: List[Dict[str, str]] = []
    seen = set()
    for item in values or []:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        platform = str(data.get("platform") or "").strip().lower()
        url = str(data.get("url") or "").strip()
        if not platform and not url:
            continue
        if platform not in SOCIAL_PLATFORMS:
            raise HTTPException(status_code=400, detail=f"Platform sosial {owner} tidak didukung")
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise HTTPException(status_code=400, detail=f"Tautan {platform} untuk {owner} tidak valid")
        host = parsed.netloc.lower().split(":", 1)[0].removeprefix("www.")
        expected = PLATFORM_HOSTS.get(platform)
        if expected and not any(host == domain or host.endswith(f".{domain}") for domain in expected):
            raise HTTPException(status_code=400, detail=f"Tautan {platform} untuk {owner} tidak sesuai platform")
        if platform == "spotify":
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) < 2 or parts[0] != "artist":
                raise HTTPException(status_code=400, detail=f"Tautan Spotify untuk {owner} wajib mengarah ke profil artis")
        dedupe_key = url.rstrip("/").lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        links.append({"platform": platform, "url": url})
    if required and not links:
        raise HTTPException(status_code=400, detail=f"Minimal satu tautan sosial wajib diisi untuk {owner}")
    if len(links) > 10:
        raise HTTPException(status_code=400, detail=f"Maksimal 10 tautan sosial untuk {owner}")
    return links


def artist_credit_snapshot(artist: Dict[str, Any]) -> Dict[str, Any]:
    links = normalize_social_links(artist.get("social_links") or [], required=True, owner=artist.get("artist_name") or "Artis")
    spotify = next((item["url"] for item in links if item["platform"] == "spotify"), None)
    return {"artist_id": artist["id"], "name": artist["artist_name"], "social_links": links, "spotify_url": spotify}


async def resolve_release_artist_credits(db, label_id: str, values: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate every credit first, then persist new profile-only artists as one batch."""
    plans: List[Dict[str, Any]] = []
    new_by_name: Dict[str, Dict[str, Any]] = {}
    for value in values or []:
        name = str(value.get("name") or "").strip()
        artist_id = str(value.get("artist_id") or "").strip() or None
        if artist_id:
            artist = await db.artists.find_one({"id": artist_id, "label_id": label_id}, {"_id": 0})
            if not artist:
                raise HTTPException(status_code=400, detail=f"Artis tersimpan '{name}' tidak ditemukan")
            if not artist.get("social_links"):
                raise HTTPException(status_code=400, detail=f"Lengkapi tautan sosial '{artist.get('artist_name')}' melalui Manajemen Artis")
            plans.append({"snapshot": artist_credit_snapshot(artist)})
            continue

        links = normalize_social_links(value.get("social_links") or [], required=True, owner=name or "Artis baru")
        existing = await db.artists.find_one(
            {"label_id": label_id, "artist_name": {"$regex": f"^{re.escape(name)}$", "$options": "i"}},
            {"_id": 0},
        )
        if existing:
            if not existing.get("social_links"):
                raise HTTPException(status_code=400, detail=f"Lengkapi tautan sosial '{existing.get('artist_name')}' melalui Manajemen Artis")
            plans.append({"snapshot": artist_credit_snapshot(existing)})
            continue

        normalized_name = name.casefold()
        pending = new_by_name.get(normalized_name)
        if not pending:
            artist_id = new_id()
            pending = {
                "doc": {
                    "id": artist_id, "label_id": label_id, "user_id": None,
                    "artist_name": name, "email": None, "whatsapp": None,
                    "social_links": links, "profile_only": True, "source": "release_submission",
                    "visibility_settings": {}, "status": "active",
                    "created_at": now_iso(), "updated_at": now_iso(),
                },
            }
            pending["snapshot"] = artist_credit_snapshot(pending["doc"])
            new_by_name[normalized_name] = pending
        plans.append({"snapshot": pending["snapshot"]})

    if new_by_name:
        await db.artists.insert_many([item["doc"] for item in new_by_name.values()])
    return [plan["snapshot"] for plan in plans]