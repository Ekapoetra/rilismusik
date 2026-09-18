"""Shared dependencies, helpers, and global state.

All route modules import from here so we have a single source of truth
for: db connection, auth dependencies, notification helpers, activity
logging, redaction rules, and the upload directory.
"""
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import HTTPException, Depends, Request
from motor.motor_asyncio import AsyncIOMotorClient

from auth_utils import (
    make_get_current_user,
    LABEL_ROLE, ARTIST_ROLE, ADMIN_ROLES, SUPER_ADMIN,
)
from models import now_iso, new_id
from .admin_permission_service import (
    enrich_admin_user, is_admin_identity, permission_for_request,
    assert_admin_permission, has_permission,
)


logger = logging.getLogger("rilismusik")

# ---------- Upload directory ----------
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/backend/uploads"))
for sub in ("audio", "cover", "csv", "contract", "ticket", "landing"):
    (UPLOAD_DIR / sub).mkdir(parents=True, exist_ok=True)

# ---------- DB ----------
# Primary client used by every user-facing FastAPI route. It inherits whatever
# CSOT timeoutMS Atlas/Emergent set in MONGO_URL (e.g. 10s on the production
# connection string) — short caps protect web requests from hung queries.
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

# Long-running background jobs (royalty publish, mark_dana_received, recovery
# pipelines) crunch 1M+ documents and would always trip the 10s CSOT cap on
# production Atlas. We open a SECOND client without CSOT cap so those tasks
# can take minutes when needed. Server-side cluster timeouts (maxTimeMS) still
# apply where set, so this is safe — only the client-side ceiling is lifted.
client_bg = AsyncIOMotorClient(
    os.environ["MONGO_URL"],
    timeoutMS=None,            # disable PyMongo client-side operation timeout (CSOT)
    socketTimeoutMS=None,      # no socket read timeout for long cursors
    serverSelectionTimeoutMS=30000,  # still bail fast if primary is unreachable
    connectTimeoutMS=20000,
)
db_bg = client_bg[os.environ["DB_NAME"]]

_base_get_current_user = make_get_current_user(db)


async def get_current_user(request: Request) -> dict:
    user = await _base_get_current_user(request)
    if is_admin_identity(user):
        return await enrich_admin_user(db, user)
    return user


# ---------- Role-based dependencies ----------
KYC_ALLOWED_LABEL_PREFIXES = (
    "/api/label/me", "/api/label/account", "/api/label/active-label", "/api/label/dashboard", "/api/label/bank-account",
    "/api/label/kyc", "/api/label/logo", "/api/label/claim", "/api/contracts/label",
    "/api/label/addon-orders",
)


async def require_label(request: Request, user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != LABEL_ROLE:
        raise HTTPException(status_code=403, detail="Hanya untuk akun label")
    if not any(request.url.path.startswith(prefix) for prefix in KYC_ALLOWED_LABEL_PREFIXES):
        from .kyc_service import ensure_label_kyc
        await ensure_label_kyc(user)
    return user


async def require_kyc_for_label_user(user: dict = Depends(get_current_user)) -> dict:
    """Apply KYC only when a shared endpoint is accessed by a label account."""
    if user.get("role") == LABEL_ROLE:
        from .kyc_service import ensure_label_kyc
        await ensure_label_kyc(user)
    return user


async def require_artist(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != ARTIST_ROLE:
        raise HTTPException(status_code=403, detail="Hanya untuk akun artist")
    return user


async def require_admin(request: Request, user: dict = Depends(get_current_user)) -> dict:
    if not is_admin_identity(user) or not user.get("admin_role_active", True):
        raise HTTPException(status_code=403, detail="Akses admin diperlukan")
    permission = permission_for_request(request.url.path, request.method)
    if permission:
        assert_admin_permission(user, permission)
    return user


async def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin diperlukan")
    return user


# ---------- User / label helpers ----------
def public_user(u: dict) -> dict:
    u = {**u}
    u.pop("password_hash", None)
    u.pop("_id", None)
    return u


async def get_labels_for_user(user: dict) -> list:
    """All labels owned by an account (Multi Label may own several)."""
    return await db.labels.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", 1).to_list(200)


def _account_authority(labels: list, user: dict) -> dict:
    """The label that holds the account entitlement (Multi Label tier), else the
    primary/first label. Used to resolve account-level benefits."""
    from .entitlements import resolve_label_entitlements
    if not labels:
        return {}
    multi = next((l for l in labels if resolve_label_entitlements(l)["multi_label"]), None)
    if multi:
        return multi
    primary_id = user.get("primary_label_id")
    return next((l for l in labels if l.get("id") == primary_id), None) or labels[0]


async def get_label_by_user(user: dict) -> dict:
    """Return the ACTIVE operational label for the account.

    Single-label accounts behave exactly as before. Multi Label accounts resolve
    the active label from user.active_label_id (falling back to the account
    authority / first label). Financial aggregation is handled separately.
    """
    labels = await get_labels_for_user(user)
    if not labels:
        raise HTTPException(status_code=404, detail="Label belum diset")
    if len(labels) == 1:
        return labels[0]
    active_id = user.get("active_label_id")
    chosen = next((l for l in labels if l.get("id") == active_id), None)
    if chosen:
        return chosen
    return _account_authority(labels, user)


async def account_entitlements(user: dict) -> dict:
    """Resolve account-level capabilities (Multi Label inherits VIP benefits)."""
    from .entitlements import resolve_label_entitlements
    labels = await get_labels_for_user(user)
    authority = _account_authority(labels, user) if labels else {}
    ent = resolve_label_entitlements(authority)
    ent["label_count"] = len(labels)
    return ent


# Fields hidden from label/artist when returning label profile data.
# Labels MUST NOT see their own royalty percentage or distributor fee.
LABEL_HIDDEN_FIELDS = (
    "package_change_history",
    "royalty_percentage_default",
    "royalty_percentage_history",
    "default_royalty_share",
)


def redact_label_for_self(label: dict) -> dict:
    """Strip royalty percentage info from a label dict before sending to the label itself."""
    safe = {k: v for k, v in (label or {}).items() if k not in LABEL_HIDDEN_FIELDS}
    safe["logo_url"] = f"/api/files/{safe['logo_storage_key']}" if safe.get("logo_storage_key") else None
    return safe


# ---------- Activity log ----------
async def log_activity(actor_id: str, action: str, module: str, ref_id: Optional[str] = None,
                       before: Optional[dict] = None, after: Optional[dict] = None) -> None:
    def _clean(d):
        if not isinstance(d, dict):
            return d
        return {k: v for k, v in d.items() if k != "_id"}
    await db.activity_logs.insert_one({
        "id": new_id(),
        "user_id": actor_id,
        "action": action,
        "module": module,
        "reference_id": ref_id,
        "before_data": _clean(before),
        "after_data": _clean(after),
        "created_at": now_iso(),
    })


# ---------- Notification helpers ----------
async def notify(user_id: str, ntype: str, title: str, body: str,
                 link: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    """Create an in-app notification for a user."""
    doc = {
        "id": new_id(),
        "user_id": user_id,
        "type": ntype,
        "title": title,
        "body": body,
        "link": link,
        "meta": meta or {},
        "read_at": None,
        "created_at": now_iso(),
    }
    await db.notifications.insert_one(doc)
    return doc


async def notify_many(user_ids: List[str], ntype: str, title: str, body: str,
                      link: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
    if not user_ids:
        return
    now = now_iso()
    docs = [{
        "id": new_id(), "user_id": uid, "type": ntype, "title": title, "body": body,
        "link": link, "meta": meta or {}, "read_at": None, "created_at": now,
    } for uid in user_ids]
    await db.notifications.insert_many(docs)


async def admin_user_ids(allowed_roles: tuple = ADMIN_ROLES) -> List[str]:
    role_permissions = {
        "admin_release": ["releases.review", "wami.manage", "contracts.manage"],
        "admin_finance": ["payments.manage", "royalty.manage", "withdraw.manage"],
        "admin_support": ["support.manage", "kyc.review", "labels.accounts"],
        "admin_content": ["cms.manage"], "admin_ui": ["ui.settings.manage"],
    }
    if "admin_custom" in allowed_roles or set(allowed_roles) == set(ADMIN_ROLES):
        custom_role_ids = await db.admin_roles.distinct("id", {"builtin": False, "active": {"$ne": False}})
    else:
        required = [permission for role in allowed_roles for permission in role_permissions.get(role, [])]
        custom_role_ids = await db.admin_roles.distinct("id", {"builtin": False, "active": {"$ne": False}, "permissions": {"$in": required}}) if required else []
    ids = []
    async for u in db.users.find(
        {"$or": [{"role": {"$in": list(allowed_roles)}}, {"admin_role_id": {"$in": custom_role_ids}}], "status": {"$nin": ["suspended", "disabled"]}},
        {"_id": 0, "id": 1},
    ):
        ids.append(u["id"])
    return ids


async def label_user_ids(label_id: str) -> List[str]:
    label = await db.labels.find_one({"id": label_id}, {"_id": 0, "user_id": 1})
    return [label["user_id"]] if label and label.get("user_id") else []


__all__ = [
    "logger", "UPLOAD_DIR", "client", "db",
    "get_current_user", "require_label", "require_artist",
    "require_admin", "require_super_admin", "assert_admin_permission", "has_permission",
    "public_user", "get_label_by_user", "get_labels_for_user", "account_entitlements", "redact_label_for_self",
    "LABEL_HIDDEN_FIELDS",
    "log_activity",
    "notify", "notify_many", "admin_user_ids", "label_user_ids",
    "LABEL_ROLE", "ARTIST_ROLE", "ADMIN_ROLES", "SUPER_ADMIN",
]
