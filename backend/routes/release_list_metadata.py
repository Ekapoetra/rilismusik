"""Read-only, batched artist and track-code enrichment for release lists."""
from collections import defaultdict
from typing import List, Union
from pydantic import BaseModel, ConfigDict, Field


class TrackIdentifier(BaseModel):
    id: str
    track_number: Union[int, str]
    track_title: str
    isrc: str


class ReleaseListItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    display_primary_artists: List[str] = Field(default_factory=list)
    display_featured_artists: List[str] = Field(default_factory=list)
    track_identifiers: List[TrackIdentifier] = Field(default_factory=list)


def _credits(value):
    if isinstance(value, str):
        return [{"name": value}] if value.strip() else []
    return [item if isinstance(item, dict) else {"name": item} for item in (value or []) if isinstance(item, (str, dict))]


async def enrich_release_list(db, releases):
    if not releases:
        return releases
    grouped = defaultdict(list)
    projection = {"_id": 0, "id": 1, "release_id": 1, "track_number": 1, "track_title": 1,
                  "isrc": 1, "artist_id": 1, "artist_name": 1, "primary_artists": 1, "featured_artists": 1}
    async for track in db.tracks.find({"release_id": {"$in": [r["id"] for r in releases]}}, projection):
        grouped[track["release_id"]].append(track)
    artist_ids = set()
    for release in releases:
        for record in [release, *grouped[release["id"]]]:
            for credit in [record, *_credits(record.get("primary_artists")), *_credits(record.get("featured_artists"))]:
                if isinstance(credit.get("artist_id"), str):
                    artist_ids.add(credit["artist_id"])
    artists = {}
    if artist_ids:
        async for artist in db.artists.find({"id": {"$in": list(artist_ids)}}, {"_id": 0, "id": 1, "label_id": 1, "artist_name": 1, "name": 1}):
            artists[artist["id"]] = artist

    def name_for(credit, label_id):
        name = credit.get("name") or credit.get("artist_name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        artist = artists.get(credit.get("artist_id"), {})
        return (artist.get("artist_name") or artist.get("name") or "").strip() if artist.get("label_id") == label_id else ""

    def track_order(track):
        try:
            return int(track.get("track_number") or 0), str(track.get("id") or "")
        except (ValueError, TypeError):
            return 0, str(track.get("id") or "")

    for release in releases:
        tracks = sorted(grouped[release["id"]], key=track_order)
        release["display_cover_url"] = (release.get("internal_cover_url") if release.get("imported_legacy") else None) or release.get("cover_url")
        primary, featured = {}, {}
        for record in [release, *tracks]:
            main_credits = _credits(record.get("primary_artists"))
            names = [name_for(credit, release.get("label_id")) for credit in main_credits]
            if not any(names):
                names = [name_for(record, release.get("label_id"))]
            for name in names:
                if name:
                    primary.setdefault(name.casefold(), name)
            for credit in _credits(record.get("featured_artists")):
                name = name_for(credit, release.get("label_id"))
                if name:
                    featured.setdefault(name.casefold(), name)
        release["display_primary_artists"] = list(primary.values())
        release["display_featured_artists"] = list(featured.values())
        release["track_identifiers"] = [{"id": str(track.get("id") or index), "track_number": track.get("track_number") or index + 1,
                                         "track_title": track.get("track_title") or "", "isrc": str(track.get("isrc") or "").strip()}
                                        for index, track in enumerate(tracks)]
    return releases