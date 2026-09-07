"""Realtime (polling-based) chat: label↔support inbox and admin↔admin internal DMs, with presence."""
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from models import now_iso, new_id
from .deps import db, get_current_user, is_admin_identity, admin_user_ids
from .admin_permission_service import has_permission

chat_r = APIRouter(prefix="/chat", tags=["chat"])
ONLINE_WINDOW_SECONDS = 35


class SendMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


def _is_support(user: Dict[str, Any]) -> bool:
    return user.get("role") == "super_admin" or has_permission(user, "support.manage")


def _online(last_seen: Any) -> bool:
    if not last_seen:
        return False
    try:
        ts = datetime.fromisoformat(str(last_seen))
    except (TypeError, ValueError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() < ONLINE_WINDOW_SECONDS


async def _presence_map(user_ids: List[str]) -> Dict[str, bool]:
    ids = [uid for uid in user_ids if uid]
    if not ids:
        return {}
    docs = await db.chat_presence.find({"user_id": {"$in": ids}}, {"_id": 0, "user_id": 1, "last_seen": 1}).to_list(len(ids))
    return {d["user_id"]: _online(d.get("last_seen")) for d in docs}


async def _support_user_ids() -> List[str]:
    return await admin_user_ids(("super_admin", "admin_support"))


async def _any_support_online() -> bool:
    ids = await _support_user_ids()
    presence = await _presence_map(ids)
    return any(presence.values())


async def _ensure_support_conversation(label: Dict[str, Any]) -> Dict[str, Any]:
    conv = await db.chat_conversations.find_one({"kind": "support", "label_id": label["id"]}, {"_id": 0})
    if conv:
        return conv
    conv = {
        "id": new_id(), "kind": "support", "label_id": label["id"],
        "label_user_id": label.get("user_id"), "label_name": label.get("label_name"),
        "created_at": now_iso(), "updated_at": now_iso(),
        "last_message_at": None, "last_message_preview": None,
    }
    await db.chat_conversations.insert_one(dict(conv))
    return conv


async def _ensure_internal_conversation(a: str, b: str) -> Dict[str, Any]:
    pair = sorted([a, b])
    conv = await db.chat_conversations.find_one({"kind": "internal", "participant_ids": pair}, {"_id": 0})
    if conv:
        return conv
    conv = {
        "id": new_id(), "kind": "internal", "participant_ids": pair,
        "created_at": now_iso(), "updated_at": now_iso(),
        "last_message_at": None, "last_message_preview": None,
    }
    await db.chat_conversations.insert_one(dict(conv))
    return conv


async def _messages(conversation_id: str) -> List[Dict[str, Any]]:
    return await db.chat_messages.find({"conversation_id": conversation_id}, {"_id": 0}).sort("created_at", 1).to_list(500)


async def _mark_read(conversation_id: str, user_id: str) -> None:
    await db.chat_messages.update_many(
        {"conversation_id": conversation_id, "sender_id": {"$ne": user_id}, "read_by": {"$ne": user_id}},
        {"$addToSet": {"read_by": user_id}},
    )


async def _post_message(conv: Dict[str, Any], user: Dict[str, Any], body: str) -> Dict[str, Any]:
    text = body.strip()
    sender_name = user.get("name") or user.get("email") or "Pengguna"
    msg = {
        "id": new_id(), "conversation_id": conv["id"], "sender_id": user["id"],
        "sender_role": user.get("role"), "sender_name": sender_name,
        "body": text, "created_at": now_iso(), "read_by": [user["id"]],
    }
    await db.chat_messages.insert_one(dict(msg))
    await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {
        "updated_at": now_iso(), "last_message_at": now_iso(),
        "last_message_preview": text[:120],
    }})
    return msg


async def _user_conversation_ids(user: Dict[str, Any]) -> List[str]:
    if not is_admin_identity(user):
        label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1})
        if not label:
            return []
        convs = await db.chat_conversations.find({"kind": "support", "label_id": label["id"]}, {"_id": 0, "id": 1}).to_list(5)
        return [c["id"] for c in convs]
    ids: List[str] = []
    if _is_support(user):
        support = await db.chat_conversations.find({"kind": "support"}, {"_id": 0, "id": 1}).to_list(5000)
        ids += [c["id"] for c in support]
    internal = await db.chat_conversations.find({"kind": "internal", "participant_ids": user["id"]}, {"_id": 0, "id": 1}).to_list(5000)
    ids += [c["id"] for c in internal]
    return ids


async def _unread_count(conversation_ids: List[str], user_id: str) -> int:
    if not conversation_ids:
        return 0
    return await db.chat_messages.count_documents({
        "conversation_id": {"$in": conversation_ids}, "sender_id": {"$ne": user_id}, "read_by": {"$ne": user_id},
    })


# ---------------- Presence & unread ----------------
@chat_r.post("/heartbeat")
async def heartbeat(user: dict = Depends(get_current_user)):
    await db.chat_presence.update_one(
        {"user_id": user["id"]},
        {"$set": {"user_id": user["id"], "last_seen": now_iso(), "role": user.get("role"), "name": user.get("name")}},
        upsert=True,
    )
    return {"ok": True}


@chat_r.get("/unread")
async def unread(user: dict = Depends(get_current_user)):
    conv_ids = await _user_conversation_ids(user)
    return {"unread": await _unread_count(conv_ids, user["id"])}


# ---------------- Label side ----------------
@chat_r.get("/label/thread")
async def label_thread(user: dict = Depends(get_current_user)):
    if is_admin_identity(user):
        raise HTTPException(status_code=403, detail="Hanya untuk akun label")
    label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label belum tersedia")
    conv = await _ensure_support_conversation(label)
    await _mark_read(conv["id"], user["id"])
    return {"conversation_id": conv["id"], "messages": await _messages(conv["id"]), "support_online": await _any_support_online()}


@chat_r.post("/label/thread")
async def label_send(body: SendMessageIn, user: dict = Depends(get_current_user)):
    if is_admin_identity(user):
        raise HTTPException(status_code=403, detail="Hanya untuk akun label")
    label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label belum tersedia")
    conv = await _ensure_support_conversation(label)
    return await _post_message(conv, user, body.body)


# ---------------- Admin side ----------------
def _require_admin(user: dict) -> None:
    if not is_admin_identity(user):
        raise HTTPException(status_code=403, detail="Akses admin diperlukan")


@chat_r.get("/admin/labels")
async def admin_label_inbox(user: dict = Depends(get_current_user)):
    _require_admin(user)
    if not _is_support(user):
        raise HTTPException(status_code=403, detail="Hanya staff Support atau Super Admin")
    convs = await db.chat_conversations.find({"kind": "support"}, {"_id": 0}).sort("last_message_at", -1).to_list(2000)
    presence = await _presence_map([c.get("label_user_id") for c in convs])
    items = []
    for conv in convs:
        unread = await db.chat_messages.count_documents({"conversation_id": conv["id"], "sender_id": {"$ne": user["id"]}, "read_by": {"$ne": user["id"]}})
        items.append({
            "conversation_id": conv["id"], "label_id": conv.get("label_id"),
            "label_name": conv.get("label_name"), "online": presence.get(conv.get("label_user_id"), False),
            "last_message_at": conv.get("last_message_at"), "last_message_preview": conv.get("last_message_preview"),
            "unread": unread,
        })
    return {"items": items, "is_super_admin": user.get("role") == "super_admin"}


@chat_r.get("/admin/admins")
async def admin_directory(user: dict = Depends(get_current_user)):
    _require_admin(user)
    admins = await db.users.find(
        {"role": {"$in": ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_custom"]}, "id": {"$ne": user["id"]}, "status": {"$ne": "suspended"}},
        {"_id": 0, "id": 1, "name": 1, "email": 1, "role": 1},
    ).to_list(1000)
    presence = await _presence_map([a["id"] for a in admins])
    my_convs = await db.chat_conversations.find({"kind": "internal", "participant_ids": user["id"]}, {"_id": 0}).to_list(2000)
    conv_by_other = {}
    for conv in my_convs:
        other = next((pid for pid in conv.get("participant_ids", []) if pid != user["id"]), None)
        if other:
            unread = await db.chat_messages.count_documents({"conversation_id": conv["id"], "sender_id": {"$ne": user["id"]}, "read_by": {"$ne": user["id"]}})
            conv_by_other[other] = {"conversation_id": conv["id"], "unread": unread, "last_message_at": conv.get("last_message_at")}
    items = [{
        "user_id": a["id"], "name": a.get("name") or a.get("email"), "role": a.get("role"),
        "online": presence.get(a["id"], False),
        "conversation_id": conv_by_other.get(a["id"], {}).get("conversation_id"),
        "unread": conv_by_other.get(a["id"], {}).get("unread", 0),
    } for a in admins]
    items.sort(key=lambda x: (not x["online"], x["name"].lower()))
    return {"items": items}


@chat_r.post("/admin/internal/{other_id}")
async def admin_open_internal(other_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    other = await db.users.find_one({"id": other_id}, {"_id": 0, "id": 1, "name": 1, "role": 1})
    if not other or not is_admin_identity(other):
        raise HTTPException(status_code=404, detail="Admin tidak ditemukan")
    conv = await _ensure_internal_conversation(user["id"], other_id)
    await _mark_read(conv["id"], user["id"])
    return {"conversation_id": conv["id"], "title": other.get("name"), "messages": await _messages(conv["id"])}


async def _authorize_conversation(conversation_id: str, user: dict) -> Dict[str, Any]:
    conv = await db.chat_conversations.find_one({"id": conversation_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Percakapan tidak ditemukan")
    if conv["kind"] == "support":
        if not (is_admin_identity(user) and _is_support(user)):
            raise HTTPException(status_code=403, detail="Tidak diizinkan")
    else:
        if user["id"] not in conv.get("participant_ids", []):
            raise HTTPException(status_code=403, detail="Tidak diizinkan")
    return conv


@chat_r.get("/admin/thread/{conversation_id}")
async def admin_thread(conversation_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    conv = await _authorize_conversation(conversation_id, user)
    await _mark_read(conv["id"], user["id"])
    online = None
    if conv["kind"] == "support":
        presence = await _presence_map([conv.get("label_user_id")])
        online = presence.get(conv.get("label_user_id"), False)
    return {"conversation_id": conv["id"], "kind": conv["kind"], "label_name": conv.get("label_name"), "online": online, "messages": await _messages(conv["id"])}


@chat_r.post("/admin/thread/{conversation_id}")
async def admin_send(conversation_id: str, body: SendMessageIn, user: dict = Depends(get_current_user)):
    _require_admin(user)
    conv = await _authorize_conversation(conversation_id, user)
    return await _post_message(conv, user, body.body)
