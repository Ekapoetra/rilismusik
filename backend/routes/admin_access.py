"""Admin role/permission and configurable navigation endpoints."""
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from models import AdminRoleCreateIn, AdminRoleUpdateIn, AdminUiSettingsIn, PermissionSetIn, new_id, now_iso
from .admin_permission_service import (
    ALL_PERMISSIONS, DEFAULT_NAV_ITEMS, DEFAULT_NAV_GROUPS, NAV_GROUP_MAP, assert_admin_permission, default_navigation,
    enrich_admin_user, permission_catalog, has_permission,
    compute_permission_warnings, preview_access, bump_role_members, SYSTEM_ROLE,
    pending_capability_review, complete_capability_review, PERMISSION_NAMES,
)
from .deps import db, require_admin, log_activity


access_r = APIRouter(prefix="/admin", tags=["admin-access"])


def _validate_permissions(values: List[str]) -> List[str]:
    unique = list(dict.fromkeys(values or []))
    unknown = sorted(set(unique) - set(ALL_PERMISSIONS))
    if unknown:
        raise HTTPException(status_code=400, detail=f"Permission tidak dikenal: {', '.join(unknown)}")
    return unique


def _merge_default_nav(config: Dict[str, Any]) -> Dict[str, Any]:
    """Append missing DEFAULT_NAV_ITEMS, re-sync non-customizable fields
    (permission/icon/route), and ensure the groups layer exists."""
    defaults = {item[0]: item for item in DEFAULT_NAV_ITEMS}
    items = list(config.get("items", []))
    present = set()
    for item in items:
        d = defaults.get(item.get("key"))
        if d:
            item["permission"], item["icon"], item["route"] = d[3], d[2], d[1]
        present.add(item.get("key"))
    max_order = max((item.get("order", 0) for item in items), default=-1)
    for key, route, icon, permission, label_id, label_en, parent in DEFAULT_NAV_ITEMS:
        if key not in present:
            max_order += 1
            items.append({"key": key, "route": route, "icon": icon, "permission": permission,
                          "labels": {"id": label_id, "en": label_en}, "parent_key": parent,
                          "group_id": NAV_GROUP_MAP.get(key), "visible": True, "order": max_order})
    # Groups layer: seed defaults if missing, then guarantee every item has a valid group_id.
    groups = list(config.get("groups", []))
    if not groups:
        groups = [{"id": gid, "labels": {"id": lid, "en": len_}, "order": i}
                  for i, (gid, lid, len_) in enumerate(DEFAULT_NAV_GROUPS)]
    existing_group_ids = {g.get("id") for g in groups}
    gorder = max((g.get("order", 0) for g in groups), default=-1)
    for gid, lid, len_ in DEFAULT_NAV_GROUPS:
        if gid not in existing_group_ids:
            gorder += 1
            groups.append({"id": gid, "labels": {"id": lid, "en": len_}, "order": gorder})
            existing_group_ids.add(gid)
    fallback_group = groups[0]["id"] if groups else DEFAULT_NAV_GROUPS[0][0]
    for item in items:
        if not item.get("group_id") or item.get("group_id") not in existing_group_ids:
            item["group_id"] = NAV_GROUP_MAP.get(item.get("key")) or fallback_group
    # A subtab must live in the same group as its parent (keeps sidebar + validation consistent
    # even for legacy data saved before the groups layer existed).
    by_key = {it.get("key"): it for it in items}
    for item in items:
        parent = by_key.get(item.get("parent_key"))
        if parent:
            item["group_id"] = parent.get("group_id", item["group_id"])
    config["items"] = items
    config["groups"] = groups
    return config


@access_r.get("/access/catalog")
async def access_catalog(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.view")
    config = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0}) or default_navigation()
    nav = sorted([item for item in config.get("items", []) if item.get("key") != "label_rates"], key=lambda item: item.get("order", 0))
    return {"modules": permission_catalog(), "all_permissions": ALL_PERMISSIONS, "navigation": nav}


@access_r.get("/access/roles")
async def list_roles(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.view")
    return await db.admin_roles.find({}, {"_id": 0}).sort([("builtin", -1), ("name", 1)]).to_list(500)


@access_r.get("/access/config-review")
async def get_config_review(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.view")
    return await pending_capability_review(db)


def _perm_label(key: str) -> str:
    return PERMISSION_NAMES.get(key, (key, key))[0]


@access_r.get("/access/role-audit")
async def role_audit(role_id: str = None, limit: int = 100, user: dict = Depends(require_admin)):
    """Audit trail of role permission changes with a computed diff (who changed which
    permissions on which role, and when)."""
    assert_admin_permission(user, "access.roles.view")
    filt: Dict[str, Any] = {"module": "admin_role"}
    if role_id:
        filt["reference_id"] = role_id
    logs = await db.activity_logs.find(filt, {"_id": 0}).sort("created_at", -1).to_list(min(max(limit, 1), 300))
    actor_ids = list({l.get("user_id") for l in logs if l.get("user_id")})
    users = await db.users.find({"id": {"$in": actor_ids}}, {"_id": 0, "id": 1, "name": 1, "email": 1}).to_list(len(actor_ids) or 1)
    who = {u["id"]: (u.get("name") or u.get("email") or u["id"]) for u in users}
    entries = []
    for l in logs:
        before, after = l.get("before_data") or {}, l.get("after_data") or {}
        action = l.get("action")
        if action == "create_admin_role":
            bset, aset = set(), set(after.get("permissions") or [])
            role_name = after.get("name")
        elif action == "delete_admin_role":
            bset, aset = set(before.get("permissions") or []), set()
            role_name = before.get("name")
        else:  # update_admin_role
            bset, aset = set(before.get("permissions") or []), set(after.get("permissions") or [])
            role_name = after.get("name") or before.get("name")
        added = sorted(aset - bset)
        removed = sorted(bset - aset)
        name_from, name_to = before.get("name"), after.get("name")
        active_from, active_to = before.get("active"), after.get("active")
        # Skip noise: updates that changed neither permissions, name, nor active status
        if action == "update_admin_role" and not added and not removed and name_from == name_to and active_from == active_to:
            continue
        entries.append({
            "id": l.get("id") or f"{l.get('reference_id')}-{l.get('created_at')}",
            "at": l.get("created_at"), "action": action,
            "actor_id": l.get("user_id"), "actor_name": who.get(l.get("user_id"), "Sistem"),
            "role_id": l.get("reference_id"), "role_name": role_name or "—",
            "added": [{"key": k, "label": _perm_label(k)} for k in added],
            "removed": [{"key": k, "label": _perm_label(k)} for k in removed],
            "name_changed": (name_from != name_to and action == "update_admin_role"),
            "name_from": name_from, "name_to": name_to,
            "active_changed": (active_from != active_to and action == "update_admin_role"),
            "active_to": active_to,
        })
    return {"entries": entries, "count": len(entries)}


@access_r.post("/access/config-review/complete")
async def post_config_review_complete(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.manage")
    result = await complete_capability_review(db, user["id"])
    await log_activity(user["id"], "permission_review_completed", "admin_role", None, after=result)
    return result


@access_r.post("/access/validate")
async def validate_role_config(body: PermissionSetIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.view")
    return {"warnings": compute_permission_warnings(body.permissions)}


@access_r.post("/access/preview")
async def preview_role_access(body: PermissionSetIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.view")
    return preview_access(body.permissions, body.active)


@access_r.get("/access/role-options")
async def role_options(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.users.view")
    return await db.admin_roles.find({"active": {"$ne": False}}, {"_id": 0, "id": 1, "key": 1, "name": 1, "builtin": 1}).sort("name", 1).to_list(500)


@access_r.post("/access/roles")
async def create_role(body: AdminRoleCreateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.manage")
    normalized = body.name.strip().casefold()
    if await db.admin_roles.find_one({"normalized_name": normalized}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=409, detail="Nama role sudah digunakan")
    role_id = new_id()
    doc = {"id": role_id, "key": f"custom_{role_id.replace('-', '')[:12]}", "name": body.name.strip(),
           "normalized_name": normalized, "description": body.description, "builtin": False, "system": False,
           "permissions": _validate_permissions(body.permissions), "active": True,
           "created_at": now_iso(), "updated_at": now_iso(), "created_by": user["id"]}
    await db.admin_roles.insert_one(doc); doc.pop("_id", None)
    await log_activity(user["id"], "create_admin_role", "admin_role", role_id, after=doc)
    return doc


@access_r.patch("/access/roles/{role_id}")
async def update_role(role_id: str, body: AdminRoleUpdateIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.manage")
    role = await db.admin_roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan")
    update: Dict[str, Any] = {"updated_at": now_iso(), "updated_by": user["id"]}
    if body.name is not None:
        normalized = body.name.strip().casefold()
        duplicate = await db.admin_roles.find_one({"normalized_name": normalized, "id": {"$ne": role_id}}, {"_id": 0, "id": 1})
        if duplicate:
            raise HTTPException(status_code=409, detail="Nama role sudah digunakan")
        update.update({"name": body.name.strip(), "normalized_name": normalized})
    if body.description is not None: update["description"] = body.description
    if body.permissions is not None: update["permissions"] = _validate_permissions(body.permissions)
    if body.active is not None:
        if role.get("system") or role.get("key") == SYSTEM_ROLE:
            if not body.active:
                raise HTTPException(status_code=400, detail="Role Super Admin tidak dapat dinonaktifkan")
        update["active"] = body.active
    await db.admin_roles.update_one({"id": role_id}, {"$set": update})
    # Session invalidation: any change to permissions or active status must drop stale JWTs
    # so affected admins immediately lose (or gain) access on their next request.
    if body.permissions is not None or body.active is not None:
        await bump_role_members(db, role_id)
    result = await db.admin_roles.find_one({"id": role_id}, {"_id": 0})
    await log_activity(user["id"], "update_admin_role", "admin_role", role_id, before=role, after=result)
    return result


@access_r.delete("/access/roles/{role_id}")
async def delete_role(role_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.manage")
    role = await db.admin_roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan")
    if role.get("system") or role.get("key") == SYSTEM_ROLE:
        raise HTTPException(status_code=400, detail="Role sistem (Super Admin) tidak dapat dihapus")
    if await db.users.find_one({"$or": [{"admin_role_id": role_id}, {"admin_role_id": role.get("key")}, {"role": role.get("key")}],
                                "status": {"$ne": "disabled"}}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=409, detail="Role masih digunakan oleh pengguna admin")
    await db.admin_roles.delete_one({"id": role_id})
    await log_activity(user["id"], "delete_admin_role", "admin_role", role_id, before=role)
    return {"ok": True}


@access_r.get("/navigation")
async def admin_navigation(user: dict = Depends(require_admin)):
    config = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0}) or default_navigation()
    config = _merge_default_nav(config)
    enriched = await enrich_admin_user(db, user)
    allowed = set(enriched.get("permissions") or [])
    if enriched.get("role") == "super_admin": allowed = set(ALL_PERMISSIONS)
    items = [item for item in config.get("items", []) if item.get("key") != "label_rates" and item.get("visible", True) and has_permission(enriched, item.get("permission"))]
    return {"default_locale": config.get("default_locale", "id"), "groups": sorted(config.get("groups", []), key=lambda g: g.get("order", 0)),
            "items": sorted(items, key=lambda item: item.get("order", 0)),
            "role": {"id": enriched.get("admin_role_id"), "name": enriched.get("role_name")}, "permissions": list(allowed)}


@access_r.get("/ui-settings")
async def get_ui_settings(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "ui.settings.view")
    config = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0}) or default_navigation()
    config = _merge_default_nav(config)
    return {**config, "items": [item for item in config.get("items", []) if item.get("key") != "label_rates"]}


@access_r.put("/ui-settings")
async def update_ui_settings(body: AdminUiSettingsIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "ui.settings.manage")
    allowed_items = {item[0]: item for item in DEFAULT_NAV_ITEMS}
    # Groups: keep non-empty labels, unique ids, stable order.
    groups = []
    group_ids = set()
    for gi, g in enumerate(body.groups):
        if g.id in group_ids:
            raise HTTPException(status_code=400, detail=f"Group duplikat: {g.id}")
        if not g.labels.get("id", "").strip():
            raise HTTPException(status_code=400, detail="Nama group wajib diisi")
        group_ids.add(g.id)
        groups.append({"id": g.id, "labels": {"id": g.labels.get("id", "").strip(), "en": (g.labels.get("en") or g.labels.get("id") or "").strip()}, "order": gi})
    if not groups:
        raise HTTPException(status_code=400, detail="Minimal satu group navigasi")
    seen = set(); items = []
    for index, item in enumerate(body.items):
        if item.key not in allowed_items or item.key in seen:
            raise HTTPException(status_code=400, detail=f"Tab tidak valid atau duplikat: {item.key}")
        seen.add(item.key)
        default = allowed_items[item.key]
        if item.route != default[1]:
            raise HTTPException(status_code=400, detail="Route internal tidak dapat diubah")
        if not item.labels.get("id", "").strip():
            raise HTTPException(status_code=400, detail=f"Label menu wajib diisi: {item.key}")
        if item.parent_key and item.parent_key not in allowed_items:
            raise HTTPException(status_code=400, detail=f"Parent tab tidak valid: {item.parent_key}")
        if item.parent_key == item.key:
            raise HTTPException(status_code=400, detail="Tab tidak dapat menjadi parent dirinya sendiri")
        if item.group_id not in group_ids:
            raise HTTPException(status_code=400, detail=f"Group tidak valid untuk menu: {item.key}")
        labels = {"id": item.labels.get("id", "").strip(), "en": (item.labels.get("en") or default[5] or item.labels.get("id") or "").strip()}
        items.append({"key": item.key, "route": default[1], "labels": labels, "parent_key": item.parent_key,
                      "group_id": item.group_id, "visible": item.visible, "permission": default[3], "icon": default[2], "order": index})
    missing = [key for key in allowed_items if key not in seen]
    if missing:
        raise HTTPException(status_code=400, detail=f"Konfigurasi tab belum lengkap: {', '.join(missing)}")
    parent_map = {item["key"]: item.get("parent_key") for item in items}
    group_map = {item["key"]: item.get("group_id") for item in items}
    for key, parent in parent_map.items():
        if parent and parent_map.get(parent):
            raise HTTPException(status_code=400, detail=f"Subtab hanya boleh satu tingkat: {key}")
        if parent and group_map.get(parent) != group_map.get(key):
            raise HTTPException(status_code=400, detail=f"Subtab harus berada di group yang sama dengan parent-nya: {key}")
    doc = {"key": "admin_navigation", "default_locale": body.default_locale, "groups": groups, "items": items,
           "updated_at": now_iso(), "updated_by": user["id"]}
    before = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0})
    await db.admin_ui_settings.replace_one({"key": "admin_navigation"}, doc, upsert=True)
    await log_activity(user["id"], "update_admin_ui_navigation", "admin_ui", "admin_navigation", before=before, after=doc)
    return doc