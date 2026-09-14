"""Admin role/permission and configurable navigation endpoints."""
import re
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from models import AdminRoleCreateIn, AdminRoleUpdateIn, AdminUiSettingsIn, PermissionSetIn, new_id, now_iso
from .admin_permission_service import (
    ALL_PERMISSIONS, DEFAULT_NAV_ITEMS, assert_admin_permission, default_navigation,
    enrich_admin_user, permission_catalog, has_permission,
    compute_permission_warnings, preview_access,
)
from .deps import db, require_admin, log_activity


access_r = APIRouter(prefix="/admin", tags=["admin-access"])


def _validate_permissions(values: List[str]) -> List[str]:
    unique = list(dict.fromkeys(values or []))
    unknown = sorted(set(unique) - set(ALL_PERMISSIONS))
    if unknown:
        raise HTTPException(status_code=400, detail=f"Permission tidak dikenal: {', '.join(unknown)}")
    return unique


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
           "normalized_name": normalized, "description": body.description, "builtin": False,
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
        if role.get("key") == "super_admin" and not body.active:
            raise HTTPException(status_code=400, detail="Role Super Admin tidak dapat dinonaktifkan")
        update["active"] = body.active
    await db.admin_roles.update_one({"id": role_id}, {"$set": update})
    result = await db.admin_roles.find_one({"id": role_id}, {"_id": 0})
    await log_activity(user["id"], "update_admin_role", "admin_role", role_id, before=role, after=result)
    return result


@access_r.delete("/access/roles/{role_id}")
async def delete_role(role_id: str, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "access.roles.manage")
    role = await db.admin_roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role tidak ditemukan")
    if role.get("builtin"):
        raise HTTPException(status_code=400, detail="Role bawaan tidak dapat dihapus")
    if await db.users.find_one({"admin_role_id": role_id, "status": {"$ne": "disabled"}}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=409, detail="Role masih digunakan oleh pengguna admin")
    await db.admin_roles.delete_one({"id": role_id})
    await log_activity(user["id"], "delete_admin_role", "admin_role", role_id, before=role)
    return {"ok": True}


@access_r.get("/navigation")
async def admin_navigation(user: dict = Depends(require_admin)):
    config = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0}) or default_navigation()
    enriched = await enrich_admin_user(db, user)
    allowed = set(enriched.get("permissions") or [])
    if enriched.get("role") == "super_admin": allowed = set(ALL_PERMISSIONS)
    items = [item for item in config.get("items", []) if item.get("key") != "label_rates" and item.get("visible", True) and has_permission(enriched, item.get("permission"))]
    return {"default_locale": config.get("default_locale", "id"), "items": sorted(items, key=lambda item: item.get("order", 0)),
            "role": {"id": enriched.get("admin_role_id"), "name": enriched.get("role_name")}, "permissions": list(allowed)}


@access_r.get("/ui-settings")
async def get_ui_settings(user: dict = Depends(require_admin)):
    assert_admin_permission(user, "ui.settings.view")
    config = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0}) or default_navigation()
    return {**config, "items": [item for item in config.get("items", []) if item.get("key") != "label_rates"]}


@access_r.put("/ui-settings")
async def update_ui_settings(body: AdminUiSettingsIn, user: dict = Depends(require_admin)):
    assert_admin_permission(user, "ui.settings.manage")
    allowed_items = {item[0]: item for item in DEFAULT_NAV_ITEMS}
    seen = set(); items = []
    for index, item in enumerate(body.items):
        if item.key not in allowed_items or item.key in seen:
            raise HTTPException(status_code=400, detail=f"Tab tidak valid atau duplikat: {item.key}")
        seen.add(item.key)
        default = allowed_items[item.key]
        if item.route != default[1]:
            raise HTTPException(status_code=400, detail="Route internal tidak dapat diubah")
        if not item.labels.get("id", "").strip() or not item.labels.get("en", "").strip():
            raise HTTPException(status_code=400, detail=f"Label Indonesia dan Inggris wajib diisi: {item.key}")
        if item.parent_key and item.parent_key not in allowed_items:
            raise HTTPException(status_code=400, detail=f"Parent tab tidak valid: {item.parent_key}")
        if item.parent_key == item.key:
            raise HTTPException(status_code=400, detail="Tab tidak dapat menjadi parent dirinya sendiri")
        items.append({**item.model_dump(), "permission": default[3], "icon": default[2], "order": index})
    missing = [key for key in allowed_items if key not in seen]
    if missing:
        raise HTTPException(status_code=400, detail=f"Konfigurasi tab belum lengkap: {', '.join(missing)}")
    parent_map = {item["key"]: item.get("parent_key") for item in items}
    for key, parent in parent_map.items():
        if parent and parent_map.get(parent):
            raise HTTPException(status_code=400, detail=f"Subtab hanya boleh satu tingkat: {key}")
    doc = {"key": "admin_navigation", "default_locale": body.default_locale, "items": items,
           "updated_at": now_iso(), "updated_by": user["id"]}
    before = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0})
    await db.admin_ui_settings.replace_one({"key": "admin_navigation"}, doc, upsert=True)
    await log_activity(user["id"], "update_admin_ui_navigation", "admin_ui", "admin_navigation", before=before, after=doc)
    return doc