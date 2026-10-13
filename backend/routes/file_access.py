"""Authenticated access rules for sensitive storage prefixes served by
`GET /api/files/{path}`.

Public prefixes (cover/, landing/, cms/, label-logo/, cover art) stay open —
they back marketing pages and release artwork. Everything holding legal
documents, financial data, paid deliverables or private uploads requires a
logged-in user that owns the referenced resource (or an admin).
"""
from typing import Any, Dict

from .deps import db, is_admin_identity, get_labels_for_user, LABEL_ROLE

# Prefixes that need an authenticated, authorized request (still resolved to a
# short-lived presigned R2 URL after authorization).
AUTHENTICATED_PREFIXES = (
    "contract/", "copyright/", "csv/", "csv-repair/", "csv-replacements/",
    "background-inputs/", "direct-uploads/", "remix-permission/",
    "addon-delivery/", "chat/", "audio/", "ticket/",
)

# Admin-only prefixes — no member-side ownership rule exists for these.
_ADMIN_ONLY_PREFIXES = ("csv/", "csv-repair/", "csv-replacements/",
                        "background-inputs/", "direct-uploads/")


def _file_ref(path: str) -> str:
    return f"/api/files/{path}"


async def _label_ids(user: Dict[str, Any]) -> set:
    try:
        return {lab["id"] for lab in await get_labels_for_user(user)}
    except Exception:
        return set()


async def _owns_release(path: str, prefix: str, label_ids: set) -> bool:
    release_id = path[len(prefix):].split("/", 1)[0].rsplit(".", 1)[0]
    rel = await db.releases.find_one({"id": release_id, "label_id": {"$in": list(label_ids)}},
                                     {"_id": 0, "id": 1})
    return bool(rel)


async def authorize_file_path(path: str, user: Dict[str, Any]) -> bool:
    """True when `user` may fetch the object at `path`."""
    if is_admin_identity(user):
        return True
    if path.startswith(_ADMIN_ONLY_PREFIXES):
        return False
    if user.get("role") != LABEL_ROLE:
        return False
    label_ids = await _label_ids(user)
    if not label_ids:
        return False

    if path.startswith("contract/proof_"):
        doc = await db.withdraw_requests.find_one(
            {"label_id": {"$in": list(label_ids)}, "payment_proof_url": _file_ref(path)},
            {"_id": 0, "id": 1})
        return bool(doc)
    if path.startswith("contract/"):
        doc = await db.contracts.find_one(
            {"label_id": {"$in": list(label_ids)}, "file_url": _file_ref(path)},
            {"_id": 0, "id": 1})
        return bool(doc)
    if path.startswith("copyright/"):
        return await _owns_release(path, "copyright/", label_ids)
    if path.startswith("remix-permission/"):
        return await _owns_release(path, "remix-permission/", label_ids)
    if path.startswith("addon-delivery/"):
        order_id = path[len("addon-delivery/"):].rsplit(".", 1)[0]
        doc = await db.addon_orders.find_one({"id": order_id, "label_id": {"$in": list(label_ids)}},
                                             {"_id": 0, "id": 1})
        return bool(doc)
    # Ticket attachments land in two places: generic files under ticket/ and
    # ticket audio under audio/ticket_*.wav (upload_ticket_attachment). Both
    # resolve through the owning support ticket — checked before audio/ so a
    # label can fetch their own ticket WAV.
    if path.startswith("ticket/") or path.startswith("audio/ticket_"):
        ref = _file_ref(path)
        if await db.support_tickets.find_one(
                {"label_id": {"$in": list(label_ids)}, "attachments": ref},
                {"_id": 0, "id": 1}):
            return True
        comment = await db.ticket_comments.find_one(
            {"attachments": ref}, {"_id": 0, "ticket_id": 1})
        if not comment:
            return False
        return bool(await db.support_tickets.find_one(
            {"id": comment["ticket_id"], "label_id": {"$in": list(label_ids)}},
            {"_id": 0, "id": 1}))
    if path.startswith("audio/"):
        track_id = path[len("audio/"):].rsplit(".", 1)[0]
        track = await db.tracks.find_one({"id": track_id}, {"_id": 0, "release_id": 1})
        if not track:
            return False
        rel = await db.releases.find_one({"id": track["release_id"], "label_id": {"$in": list(label_ids)}},
                                         {"_id": 0, "id": 1})
        return bool(rel)
    if path.startswith("chat/"):
        msg = await db.chat_messages.find_one(
            {"attachment.url": _file_ref(path)},
            {"_id": 0, "conversation_id": 1})
        if not msg:
            return False
        conv = await db.chat_conversations.find_one(
            {"id": msg["conversation_id"]},
            {"_id": 0, "kind": 1, "label_id": 1, "label_user_id": 1, "participant_ids": 1})
        if not conv:
            return False
        if conv.get("kind") == "internal":
            return user["id"] in conv.get("participant_ids", [])
        return conv.get("label_user_id") == user["id"] or conv.get("label_id") in label_ids
    return False
