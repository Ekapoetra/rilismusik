"""Realtime (polling-based) chat: label↔support inbox and admin↔admin internal DMs, with presence."""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from pydantic import BaseModel, Field

import storage_service
from models import now_iso, new_id
from .deps import db, get_current_user, is_admin_identity, admin_user_ids, notify
from .admin_permission_service import has_permission

chat_r = APIRouter(prefix="/chat", tags=["chat"])
ONLINE_WINDOW_SECONDS = 35
TYPING_WINDOW_SECONDS = 6
ATTACH_EXTS = {"jpg", "jpeg", "png", "webp", "gif", "pdf", "txt", "doc", "docx"}
IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_ATTACH_BYTES = 15 * 1024 * 1024


class ChatAttachment(BaseModel):
    url: str
    filename: str
    content_type: Optional[str] = None
    kind: str = "file"


class SendMessageIn(BaseModel):
    body: str = Field(default="", max_length=4000)
    attachment: Optional[ChatAttachment] = None


def _is_support(user: Dict[str, Any]) -> bool:
    return user.get("role") == "super_admin" or has_permission(user, "support.manage")


def _within(value: Any, seconds: int) -> bool:
    if not value:
        return False
    try:
        ts = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds() < seconds


def _online(last_seen: Any) -> bool:
    return _within(last_seen, ONLINE_WINDOW_SECONDS)


async def _presence_map(user_ids: List[str]) -> Dict[str, bool]:
    ids = [uid for uid in user_ids if uid]
    if not ids:
        return {}
    docs = await db.chat_presence.find({"user_id": {"$in": ids}}, {"_id": 0, "user_id": 1, "last_seen": 1}).to_list(len(ids))
    return {d["user_id"]: _online(d.get("last_seen")) for d in docs}


async def _support_user_ids() -> List[str]:
    return await admin_user_ids(("super_admin", "admin_support"))


async def _support_staff_ids() -> List[str]:
    """Support staff only (excludes super_admin) — used for label-facing online status."""
    return await admin_user_ids(("admin_support",))


DEFAULT_CHAT_SETTINGS = {
    "id": "chat_settings",
    "timezone": "Asia/Jakarta",
    "workdays": [0, 1, 2, 3, 4],
    "sessions": [{"start": "08:00", "end": "12:00"}, {"start": "13:30", "end": "17:00"}],
    "holidays": [],
    "auto_reply_enabled": True,
    "auto_reply_message": "Terima kasih telah menghubungi Support RILIS MUSIK. Saat ini di luar jam operasional kami (Sen–Jum 08.00–12.00 & 13.30–17.00 WIB). Pesan Anda sudah tercatat dan akan kami balas pada jam kerja berikutnya.",
}


async def _get_chat_settings() -> Dict[str, Any]:
    doc = await db.app_settings.find_one({"id": "chat_settings"}, {"_id": 0})
    return {**DEFAULT_CHAT_SETTINGS, **(doc or {})}


def _operational_now(settings: Dict[str, Any]) -> bool:
    try:
        now = datetime.now(ZoneInfo(settings.get("timezone") or "Asia/Jakarta"))
    except Exception:
        now = datetime.now(ZoneInfo("Asia/Jakarta"))
    if now.weekday() not in (settings.get("workdays") or []):
        return False
    if now.strftime("%Y-%m-%d") in (settings.get("holidays") or []):
        return False
    cur = now.strftime("%H:%M")
    for s in settings.get("sessions") or []:
        if str(s.get("start", "")) <= cur < str(s.get("end", "")):
            return True
    return False


async def _label_support_status() -> Dict[str, Any]:
    settings = await _get_chat_settings()
    within = _operational_now(settings)
    presence = await _presence_map(await _support_staff_ids())
    return {"support_online": bool(within and any(presence.values())), "within_hours": within}


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
        "status": "active", "created_at": now_iso(), "updated_at": now_iso(),
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
    await db.notifications.update_many(
        {"user_id": user_id, "type": "chat_message", "read_at": None, "meta.conversation_id": conversation_id},
        {"$set": {"read_at": now_iso()}},
    )


async def _typing_names(conversation_id: str, exclude_user_id: str) -> List[str]:
    docs = await db.chat_typing.find({"conversation_id": conversation_id, "user_id": {"$ne": exclude_user_id}}, {"_id": 0, "name": 1, "at": 1}).to_list(20)
    return [d.get("name") or "Seseorang" for d in docs if _within(d.get("at"), TYPING_WINDOW_SECONDS)]


async def _notify_recipients(conv: Dict[str, Any], sender: Dict[str, Any]) -> List[tuple]:
    if conv["kind"] == "support":
        if not is_admin_identity(sender):
            ids = await _support_user_ids()
            return [(uid, True) for uid in ids if uid != sender["id"]]
        owner = conv.get("label_user_id")
        return [(owner, False)] if owner and owner != sender["id"] else []
    return [(pid, True) for pid in conv.get("participant_ids", []) if pid != sender["id"]]


async def _post_message(conv: Dict[str, Any], user: Dict[str, Any], body: str, attachment: Optional[ChatAttachment] = None) -> Dict[str, Any]:
    text = (body or "").strip()
    if not text and not attachment:
        raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")
    sender_name = user.get("name") or user.get("email") or "Pengguna"
    msg = {
        "id": new_id(), "conversation_id": conv["id"], "sender_id": user["id"],
        "sender_role": user.get("role"), "sender_name": sender_name,
        "body": text, "attachment": attachment.model_dump() if attachment else None,
        "created_at": now_iso(), "read_by": [user["id"]],
    }
    await db.chat_messages.insert_one(dict(msg))
    preview = text[:120] if text else (f"📎 {attachment.filename}" if attachment else "")
    await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {
        "updated_at": now_iso(), "last_message_at": now_iso(),
        "last_message_preview": preview, "status": "active",
    }})
    await db.chat_typing.delete_one({"conversation_id": conv["id"], "user_id": user["id"]})
    recipients = await _notify_recipients(conv, user)
    for rid, is_admin in recipients:
        await db.notifications.delete_many({"user_id": rid, "type": "chat_message", "read_at": None, "meta.conversation_id": conv["id"]})
        await notify(rid, "chat_message", f"💬 {sender_name}", preview or "Pesan baru", "/admin/dashboard" if is_admin else "/label/dashboard", {"conversation_id": conv["id"]})
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


@chat_r.post("/upload")
async def chat_upload(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    ext = (file.filename or "").lower().rsplit(".", 1)[-1] if "." in (file.filename or "") else ""
    if ext not in ATTACH_EXTS:
        raise HTTPException(status_code=400, detail="Format tidak didukung (gambar, PDF, atau dokumen)")
    data = await file.read()
    if len(data) > MAX_ATTACH_BYTES:
        raise HTTPException(status_code=400, detail="Ukuran file maksimal 15MB")
    key = f"chat/{new_id()}.{ext}"
    ct = file.content_type or storage_service.guess_content_type(file.filename or key)
    await storage_service.upload_bytes(key=key, data=data, content_type=ct)
    return {"url": f"/api/files/{key}", "filename": file.filename, "content_type": ct, "kind": "image" if ext in IMAGE_EXTS else "file"}


@chat_r.post("/typing/{conversation_id}")
async def set_typing(conversation_id: str, user: dict = Depends(get_current_user)):
    await db.chat_typing.update_one(
        {"conversation_id": conversation_id, "user_id": user["id"]},
        {"$set": {"conversation_id": conversation_id, "user_id": user["id"], "name": user.get("name") or "Seseorang", "at": now_iso()}},
        upsert=True,
    )
    return {"ok": True}


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
    status = await _label_support_status()
    return {"conversation_id": conv["id"], "messages": await _messages(conv["id"]), "support_online": status["support_online"], "within_hours": status["within_hours"], "typing": await _typing_names(conv["id"], user["id"])}


@chat_r.post("/label/thread")
async def label_send(body: SendMessageIn, user: dict = Depends(get_current_user)):
    if is_admin_identity(user):
        raise HTTPException(status_code=403, detail="Hanya untuk akun label")
    label = await db.labels.find_one({"user_id": user["id"]}, {"_id": 0, "id": 1, "label_name": 1, "user_id": 1})
    if not label:
        raise HTTPException(status_code=404, detail="Label belum tersedia")
    conv = await _ensure_support_conversation(label)
    msg = await _post_message(conv, user, body.body, body.attachment)
    settings = await _get_chat_settings()
    if settings.get("auto_reply_enabled") and not _operational_now(settings):
        threshold = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()
        recent_auto = await db.chat_messages.find_one({"conversation_id": conv["id"], "is_auto_reply": True, "created_at": {"$gte": threshold}}, {"_id": 0, "id": 1})
        if not recent_auto:
            auto = {
                "id": new_id(), "conversation_id": conv["id"], "sender_id": "system",
                "sender_role": "support_bot", "sender_name": "Support (Auto)",
                "body": settings.get("auto_reply_message") or "", "attachment": None,
                "created_at": now_iso(), "read_by": [], "is_auto_reply": True,
            }
            await db.chat_messages.insert_one(dict(auto))
            await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {"last_message_at": now_iso(), "last_message_preview": (settings.get("auto_reply_message") or "")[:120]}})
    return msg


# ---------------- Admin side ----------------
def _require_admin(user: dict) -> None:
    if not is_admin_identity(user):
        raise HTTPException(status_code=403, detail="Akses admin diperlukan")


@chat_r.get("/admin/labels")
async def admin_label_inbox(user: dict = Depends(get_current_user), status: str = "active"):
    _require_admin(user)
    if not _is_support(user):
        raise HTTPException(status_code=403, detail="Hanya staff Support atau Super Admin")
    query = {"kind": "support"}
    if status == "resolved":
        query["status"] = "resolved"
    else:
        query["status"] = {"$ne": "resolved"}
    convs = await db.chat_conversations.find(query, {"_id": 0}).sort("last_message_at", -1).to_list(2000)
    presence = await _presence_map([c.get("label_user_id") for c in convs])
    items = []
    for conv in convs:
        unread = await db.chat_messages.count_documents({"conversation_id": conv["id"], "sender_id": {"$ne": user["id"]}, "read_by": {"$ne": user["id"]}})
        items.append({
            "conversation_id": conv["id"], "label_id": conv.get("label_id"),
            "label_name": conv.get("label_name"), "online": presence.get(conv.get("label_user_id"), False),
            "last_message_at": conv.get("last_message_at"), "last_message_preview": conv.get("last_message_preview"),
            "unread": unread, "status": conv.get("status", "active"),
        })
    return {"items": items, "is_super_admin": user.get("role") == "super_admin"}


@chat_r.get("/admin/admins")
async def admin_directory(user: dict = Depends(get_current_user)):
    _require_admin(user)
    admins = await db.users.find(
        {"role": {"$in": ["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_custom"]}, "id": {"$ne": user["id"]}, "status": {"$nin": ["suspended", "disabled"]}, "deleted_at": {"$in": [None]}},
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
    return {
        "conversation_id": conv["id"], "kind": conv["kind"], "label_name": conv.get("label_name"),
        "online": online, "status": conv.get("status", "active"),
        "messages": await _messages(conv["id"]), "typing": await _typing_names(conv["id"], user["id"]),
    }


@chat_r.post("/admin/thread/{conversation_id}")
async def admin_send(conversation_id: str, body: SendMessageIn, user: dict = Depends(get_current_user)):
    _require_admin(user)
    conv = await _authorize_conversation(conversation_id, user)
    return await _post_message(conv, user, body.body, body.attachment)


@chat_r.post("/admin/thread/{conversation_id}/resolve")
async def admin_resolve(conversation_id: str, user: dict = Depends(get_current_user)):
    _require_admin(user)
    conv = await _authorize_conversation(conversation_id, user)
    if conv["kind"] != "support":
        raise HTTPException(status_code=400, detail="Hanya percakapan support yang bisa diarsipkan")
    await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {"status": "resolved", "resolved_at": now_iso(), "resolved_by": user["id"], "updated_at": now_iso()}})
    await _post_message(conv, user, "✔️ Percakapan ditandai selesai oleh tim support.")
    await db.chat_conversations.update_one({"id": conv["id"]}, {"$set": {"status": "resolved"}})
    return {"ok": True, "status": "resolved"}


class ChatSettingsIn(BaseModel):
    timezone: str = "Asia/Jakarta"
    workdays: List[int] = Field(default_factory=lambda: [0, 1, 2, 3, 4])
    sessions: List[Dict[str, str]] = Field(default_factory=list)
    holidays: List[str] = Field(default_factory=list)
    auto_reply_enabled: bool = True
    auto_reply_message: str = ""


@chat_r.get("/admin/settings")
async def get_chat_settings(user: dict = Depends(get_current_user)):
    _require_admin(user)
    if not _is_support(user):
        raise HTTPException(status_code=403, detail="Hanya staff Support atau Super Admin")
    return await _get_chat_settings()


@chat_r.put("/admin/settings")
async def update_chat_settings(body: ChatSettingsIn, user: dict = Depends(get_current_user)):
    _require_admin(user)
    if not _is_support(user):
        raise HTTPException(status_code=403, detail="Hanya staff Support atau Super Admin")
    doc = {"id": "chat_settings", **body.model_dump()}
    await db.app_settings.update_one({"id": "chat_settings"}, {"$set": doc}, upsert=True)
    return doc
