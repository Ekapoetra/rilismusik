"""Dynamic admin roles, permissions, and navigation configuration."""
from copy import deepcopy
from typing import Any, Dict, List, Optional

from fastapi import HTTPException


PERMISSION_MODULES = [
    {"key": "dashboard", "label_id": "Dashboard", "label_en": "Dashboard", "actions": [("dashboard.view", "Lihat dashboard", "View dashboard")]},
    {"key": "analytics", "label_id": "Analitik", "label_en": "Analytics", "actions": [("analytics.view", "Lihat analitik", "View analytics"), ("analytics.manage", "Hitung ulang analitik", "Recompute analytics")]},
    {"key": "labels", "label_id": "Label", "label_en": "Labels", "actions": [("labels.view", "Lihat label", "View labels"), ("labels.manage", "Edit label", "Edit labels"), ("labels.package", "Ubah Paket Label", "Change Label Package"), ("labels.rate", "Ubah Langsung Rate/Fee", "Direct Rate/Fee Change"), ("labels.rate.request", "Ajukan Perubahan Rate/Fee", "Request Rate/Fee Change"), ("labels.rate.request.view", "Lihat Permintaan Rate/Fee", "View Rate/Fee Requests"), ("labels.rate.approve", "Setujui/Tolak Rate/Fee", "Approve/Reject Rate/Fee"), ("labels.accounts", "Kelola akun label", "Manage label accounts"), ("labels.bank", "Kelola rekening", "Manage bank accounts")]},
    {"key": "kyc", "label_id": "Verifikasi Akun", "label_en": "Account Verification", "actions": [("kyc.view", "Lihat Verifikasi Akun", "View account verification"), ("kyc.review", "Setujui/tolak Verifikasi Akun", "Approve/reject account verification")]},
    {"key": "artists", "label_id": "Artis", "label_en": "Artists", "actions": [("artists.view", "Lihat artis", "View artists"), ("artists.manage", "Edit artis", "Edit artists")]},
    {"key": "releases", "label_id": "Rilisan", "label_en": "Releases", "actions": [("releases.view", "Lihat rilisan", "View releases"), ("releases.review", "Review dan ubah status", "Review and update status")]},
    {"key": "payments", "label_id": "Pembayaran", "label_en": "Payments", "actions": [("payments.view", "Lihat pembayaran", "View payments"), ("payments.manage", "Kelola pembayaran/produk", "Manage payments/products")]},
    {"key": "royalty", "label_id": "Royalti", "label_en": "Royalty", "actions": [("royalty.view", "Lihat royalti", "View royalty"), ("royalty.import", "Impor/publish royalti", "Import/publish royalty"), ("royalty.manage", "Audit dan rekonsiliasi", "Audit and reconcile"), ("royalty.delete", "Hapus import", "Delete import")]},
    {"key": "withdraw", "label_id": "Penarikan Dana", "label_en": "Withdrawals", "actions": [("withdraw.view", "Lihat penarikan", "View withdrawals"), ("withdraw.manage", "Approve/bayar/edit", "Approve/pay/edit")]},
    {"key": "wami", "label_id": "WAMI", "label_en": "WAMI", "actions": [("wami.view", "Lihat WAMI", "View WAMI"), ("wami.manage", "Ubah status WAMI", "Update WAMI status")]},
    {"key": "support", "label_id": "Tiket Bantuan", "label_en": "Support Tickets", "actions": [("support.view", "Lihat tiket", "View tickets"), ("support.manage", "Balas/ubah status", "Reply/update status")]},
    {"key": "cms", "label_id": "CMS", "label_en": "CMS", "actions": [("cms.view", "Lihat CMS", "View CMS"), ("cms.manage", "Edit konten/aset", "Edit content/assets")]},
    {"key": "contracts", "label_id": "Kontrak", "label_en": "Contracts", "actions": [("contracts.view", "Lihat kontrak", "View contracts"), ("contracts.manage", "Buat/perpanjang/akhiri", "Create/extend/terminate")]},
    {"key": "access", "label_id": "Kontrol Akses", "label_en": "Access Control", "actions": [("access.users.view", "Lihat pengguna admin", "View admin users"), ("access.users.manage", "Buat/edit pengguna admin", "Create/edit admin users"), ("access.roles.view", "Lihat role", "View roles"), ("access.roles.manage", "Buat/edit role", "Create/edit roles")]},
    {"key": "ui", "label_id": "Pengaturan UI", "label_en": "UI Settings", "actions": [("ui.settings.view", "Lihat pengaturan UI", "View UI settings"), ("ui.settings.manage", "Edit bahasa/navigasi", "Edit language/navigation")]},
    {"key": "migration", "label_id": "Migrasi", "label_en": "Migration", "actions": [("migration.view", "Lihat migrasi/klaim", "View migration/claims"), ("migration.manage", "Jalankan migrasi/klaim", "Run migration/claims"), ("migration.claims", "Verifikasi klaim label", "Verify label claims")]},
    {"key": "activity", "label_id": "Log Aktivitas", "label_en": "Activity Logs", "actions": [("activity.view", "Lihat log aktivitas", "View activity logs")]},
    {"key": "notifications", "label_id": "Notifikasi", "label_en": "Notifications", "actions": [("notifications.view", "Lihat riwayat notifikasi", "View notification history")]},
    {"key": "automation", "label_id": "Otomasi", "label_en": "Automation", "actions": [("automation.manage", "Jalankan tugas terjadwal", "Trigger scheduled jobs")]},
]

ALL_PERMISSIONS = [action[0] for module in PERMISSION_MODULES for action in module["actions"]]
_ALL_PERMISSIONS_SET = set(ALL_PERMISSIONS)
PERMISSION_NAMES = {a[0]: (a[1], a[2]) for m in PERMISSION_MODULES for a in m["actions"]}

# Rich permission metadata. Only non-default entries are listed; permission_meta()
# fills defaults (type=view for *.view else standard). type ∈ view|standard|sensitive|approval|direct
PERMISSION_META = {
    "labels.rate": {"type": "direct", "sensitive": True, "depends_on": ["labels.view"],
        "desc_id": "Mengubah persentase royalti/fee label secara LANGSUNG tanpa persetujuan.",
        "desc_en": "Change a label royalty/fee percentage DIRECTLY without approval.",
        "boundary_id": "Hanya pemegang izin tepercaya; setiap perubahan diaudit.",
        "boundary_en": "Trusted holders only; every change is audited."},
    "labels.rate.request": {"type": "sensitive", "sensitive": True, "requires_approval": True, "depends_on": ["labels.view"],
        "desc_id": "Mengajukan perubahan rate/fee label untuk disetujui Super Admin.",
        "desc_en": "Submit a label rate/fee change for Super Admin approval.",
        "boundary_id": "Nilai live tidak berubah sampai permintaan disetujui.",
        "boundary_en": "The live value stays unchanged until the request is approved."},
    "labels.rate.request.view": {"type": "view", "depends_on": ["labels.view"],
        "desc_id": "Melihat antrean permintaan perubahan rate/fee.",
        "desc_en": "View the rate/fee change request queue."},
    "labels.rate.approve": {"type": "approval", "sensitive": True, "depends_on": ["labels.rate.request.view"],
        "desc_id": "Menyetujui atau menolak permintaan perubahan rate/fee (efektif hanya Super Admin).",
        "desc_en": "Approve or reject rate/fee change requests (effectively Super Admin only)."},
}

_META_DEFAULT = {"type": "standard", "sensitive": False, "requires_approval": False,
                 "depends_on": None, "lifecycle": "active",
                 "desc_id": "", "desc_en": "", "boundary_id": "", "boundary_en": ""}


def permission_meta(key: str) -> Dict[str, Any]:
    base = dict(_META_DEFAULT)
    if key.endswith(".view"):
        base["type"] = "view"
    base.update(PERMISSION_META.get(key, {}))
    return base


def resolve_deps(key: str) -> List[str]:
    explicit = PERMISSION_META.get(key, {}).get("depends_on")
    if explicit is not None:
        return list(explicit)
    if key.endswith(".view"):
        return []
    candidate = f"{key.split('.')[0]}.view"
    return [candidate] if candidate != key and candidate in _ALL_PERMISSIONS_SET else []

BUILTIN_ROLE_DEFAULTS = {
    "super_admin": ALL_PERMISSIONS,
    "admin_release": ["dashboard.view", "notifications.view", "labels.view", "labels.manage", "labels.accounts", "artists.view", "artists.manage", "releases.view", "releases.review", "wami.view", "wami.manage", "contracts.view", "contracts.manage", "activity.view", "automation.manage"],
    "admin_finance": ["dashboard.view", "notifications.view", "analytics.view", "analytics.manage", "labels.view", "labels.manage", "labels.package", "labels.rate.request", "labels.rate.request.view", "labels.bank", "artists.view", "releases.view", "payments.view", "payments.manage", "royalty.view", "royalty.import", "royalty.manage", "withdraw.view", "withdraw.manage", "activity.view", "automation.manage"],
    "admin_support": ["dashboard.view", "notifications.view", "labels.view", "labels.manage", "labels.accounts", "labels.bank", "kyc.view", "kyc.review", "artists.view", "payments.view", "payments.manage", "support.view", "support.manage", "migration.view", "migration.manage", "migration.claims"],
    "admin_content": ["dashboard.view", "notifications.view", "cms.view", "cms.manage"],
    "admin_marketing": ["dashboard.view", "notifications.view"],
    "admin_ui": ["dashboard.view", "notifications.view", "ui.settings.view", "ui.settings.manage"],
    "admin_package_manager": ["labels.view", "labels.package"],
}

BUILTIN_ROLE_NAMES = {
    "super_admin": "Super Admin", "admin_release": "Admin Rilisan", "admin_finance": "Admin Finance",
    "admin_support": "Admin Support", "admin_content": "Admin Konten/CMS",
    "admin_marketing": "Admin Marketing", "admin_ui": "Admin UI", "admin_package_manager": "Pengelola Paket",
}

DEFAULT_NAV_ITEMS = [
    ("dashboard", "/admin/dashboard", "LayoutDashboard", "dashboard.view", "Dashboard", "Dashboard", None),
    ("analytics", "/admin/analytics", "BarChart3", "analytics.view", "Analitik Royalti", "Royalty Analytics", None),
    ("labels", "/admin/labels", "Building2", "labels.view", "Manajemen Label", "Label Management", None),
    ("rate_changes", "/admin/rate-changes", "Percent", "labels.rate.request.view", "Permintaan Rate/Fee", "Rate/Fee Requests", "labels"),
    ("kyc", "/admin/kyc", "ShieldCheck", "kyc.view", "Verifikasi Akun", "Account Verification", None),
    ("artists", "/admin/artists", "UserSquare", "artists.view", "Manajemen Artis", "Artist Management", None),
    ("releases", "/admin/releases", "Disc3", "releases.view", "Manajemen Rilisan", "Release Management", None),
    ("payments", "/admin/payments", "CreditCard", "payments.view", "Pembayaran", "Payments", None),
    ("royalty", "/admin/royalty", "FileSpreadsheet", "royalty.view", "Impor Royalti", "Royalty Import", None),
    ("royalty_adjustments", "/admin/royalty-adjustments", "Wallet", "royalty.manage", "Inject Saldo", "Royalty Adjustments", None),
    ("withdraw", "/admin/withdraw", "Banknote", "withdraw.view", "Penarikan Dana", "Withdrawals", None),
    ("wami", "/admin/wami", "Music", "wami.view", "Registrasi WAMI", "WAMI Registration", None),
    ("tickets", "/admin/tickets", "MessageSquare", "support.view", "Tiket Bantuan", "Support Tickets", None),
    ("cms", "/admin/cms", "LayoutTemplate", "cms.view", "Landing Page CMS", "Landing Page CMS", None),
    ("contracts", "/admin/contracts", "FileSignature", "contracts.view", "Kontrak", "Contracts", None),
    ("admin_users", "/admin/admin-users", "Users2", "access.users.view", "Pengguna Admin", "Admin Users", None),
    ("roles", "/admin/access", "KeyRound", "access.roles.view", "Role & Permission", "Roles & Permissions", "admin_users"),
    ("ui_settings", "/admin/ui-settings", "PanelLeft", "ui.settings.view", "Pengaturan UI", "UI Settings", "admin_users"),
    ("migrate", "/admin/migrate", "DatabaseZap", "migration.view", "Migrasi & Klaim", "Migration & Claims", None),
    ("activity", "/admin/activity-logs", "ScrollText", "activity.view", "Log Aktivitas", "Activity Logs", None),
]


def default_navigation() -> Dict[str, Any]:
    return {
        "key": "admin_navigation", "default_locale": "id",
        "items": [
            {"key": key, "route": route, "icon": icon, "permission": permission,
             "labels": {"id": label_id, "en": label_en}, "parent_key": parent,
             "visible": True, "order": index}
            for index, (key, route, icon, permission, label_id, label_en, parent) in enumerate(DEFAULT_NAV_ITEMS)
        ],
    }


async def ensure_admin_access_defaults(db) -> None:
    await db.admin_roles.create_index("id", unique=True)
    await db.admin_roles.create_index("key", unique=True)
    for key, permissions in BUILTIN_ROLE_DEFAULTS.items():
        await db.admin_roles.update_one(
            {"key": key},
            {"$setOnInsert": {"id": key, "key": key, "name": BUILTIN_ROLE_NAMES[key], "builtin": True,
                              "normalized_name": BUILTIN_ROLE_NAMES[key].casefold(),
                              "permissions": permissions, "active": True, "rbac_schema_version": 6}},
            upsert=True,
        )
        await db.admin_roles.update_one(
            {"key": key, "rbac_schema_version": {"$exists": False}},
            {"$set": {"permissions": permissions, "rbac_schema_version": 1}},
        )
        await db.admin_roles.update_one(
            {"key": key, "rbac_schema_version": {"$lt": 3}},
            {"$addToSet": {"permissions": "notifications.view"}, "$set": {"rbac_schema_version": 3}},
        )
    # v4: dedicated "labels.rate" permission for changing label royalty rate/fee.
    for key in ("super_admin", "admin_finance"):
        await db.admin_roles.update_one(
            {"key": key, "rbac_schema_version": {"$lt": 4}},
            {"$addToSet": {"permissions": "labels.rate"}, "$set": {"rbac_schema_version": 4}},
        )
    # v5: dedicated "migration.claims" permission for verifying label claim requests.
    for key in ("super_admin", "admin_support"):
        await db.admin_roles.update_one(
            {"key": key, "rbac_schema_version": {"$lt": 5}},
            {"$addToSet": {"permissions": "migration.claims"}, "$set": {"rbac_schema_version": 5}},
        )
    # One-time grant; subsequent boots preserve manual permission revocation and customization.
    for key in ("super_admin", "admin_finance"):
        await db.admin_roles.update_one(
            {"key": key, "rbac_schema_version": {"$lt": 6}},
            {"$addToSet": {"permissions": "labels.package"}, "$set": {"rbac_schema_version": 6}},
        )
    # v7: Sensitive Label Rate/Fee approval workflow. Finance loses DIRECT change and may
    # only REQUEST changes (Super Admin approves). $pull and $addToSet on the same field
    # must be separate updates; both are guarded by version < 7 so they run once.
    await db.admin_roles.update_one(
        {"key": "admin_finance", "rbac_schema_version": {"$lt": 7}},
        {"$pull": {"permissions": "labels.rate"}},
    )
    await db.admin_roles.update_one(
        {"key": "admin_finance", "rbac_schema_version": {"$lt": 7}},
        {"$addToSet": {"permissions": {"$each": ["labels.rate.request", "labels.rate.request.view"]}},
         "$set": {"rbac_schema_version": 7}},
    )
    await db.admin_roles.update_one(
        {"key": "super_admin", "rbac_schema_version": {"$lt": 7}},
        {"$addToSet": {"permissions": {"$each": ["labels.rate", "labels.rate.request", "labels.rate.request.view", "labels.rate.approve"]}},
         "$set": {"rbac_schema_version": 7}},
    )
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation"}, {"$setOnInsert": default_navigation()}, upsert=True,
    )
    nav = await db.admin_ui_settings.find_one({"key": "admin_navigation"}, {"_id": 0}) or default_navigation()
    existing_keys = {item.get("key") for item in nav.get("items", [])}
    missing = [item for item in default_navigation()["items"] if item["key"] not in existing_keys]
    if missing:
        await db.admin_ui_settings.update_one(
            {"key": "admin_navigation"},
            {"$push": {"items": {"$each": missing}}, "$set": {"navigation_schema_version": 2}},
        )
    # Idempotent rename of the KYC nav item to "Verifikasi Akun" (only if still on the old default label).
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation", "items": {"$elemMatch": {"key": "kyc", "labels.id": "Pemeriksaan KYC"}}},
        {"$set": {"items.$.labels.id": "Verifikasi Akun", "items.$.labels.en": "Account Verification"}},
    )
    # Action Center redesign: remove the standalone "Riwayat Notifikasi" nav item
    # (still reachable via the header notification bell's history link).
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation"},
        {"$pull": {"items": {"key": "notifications"}}},
    )


def is_admin_identity(user: Dict[str, Any]) -> bool:
    return user.get("role") in set(BUILTIN_ROLE_DEFAULTS) | {"admin_custom"} or bool(user.get("admin_role_id"))


async def enrich_admin_user(db, user: Dict[str, Any]) -> Dict[str, Any]:
    if not is_admin_identity(user):
        return user
    role_id = user.get("admin_role_id") or user.get("role")
    role = await db.admin_roles.find_one({"$or": [{"id": role_id}, {"key": role_id}]}, {"_id": 0})
    fallback = BUILTIN_ROLE_DEFAULTS.get(user.get("role"), [])
    permissions = role.get("permissions") if role and "permissions" in role else fallback
    enriched = {**user, "is_admin": True, "admin_role_id": (role or {}).get("id") or role_id,
                "role_name": (role or {}).get("name") or BUILTIN_ROLE_NAMES.get(user.get("role"), user.get("role")),
                "permissions": list(permissions or []),
                "admin_role_active": (role or {}).get("active", True)}
    return enriched


def has_permission(user: Dict[str, Any], permission: Optional[str]) -> bool:
    if not permission:
        return True
    if user.get("role") == "super_admin":
        return True
    permissions = set(user.get("permissions") or [])
    implied = {
        "access.users.manage": {"access.users.view"}, "access.roles.manage": {"access.roles.view"},
        "ui.settings.manage": {"ui.settings.view"}, "migration.claims": {"migration.view"},
        "labels.rate.approve": {"labels.rate.request.view"},
    }
    for source, targets in implied.items():
        if source in permissions:
            permissions.update(targets)
    return bool(user.get("admin_role_active", True)) and permission in permissions


def assert_admin_permission(user: Dict[str, Any], permission: str) -> None:
    if not has_permission(user, permission):
        raise HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED", "permission": permission, "message": "Anda tidak memiliki izin untuk tindakan ini"})


def legacy_role_for_permission(permission: Optional[str], current_role: str) -> str:
    """Bridge legacy in-route role checks while granular permissions become authoritative."""
    if current_role == "super_admin" or not permission:
        return current_role
    if permission.startswith(("analytics.", "payments.", "royalty.", "withdraw.")) or permission == "labels.bank":
        return "admin_finance"
    if permission.startswith(("releases.", "artists.", "wami.", "contracts.")):
        return "admin_release"
    if permission.startswith(("support.", "kyc.", "migration.")) or permission.startswith("labels."):
        return "admin_support"
    if permission.startswith("cms."):
        return "admin_content"
    if permission.startswith("ui."):
        return "admin_ui"
    return current_role


def permission_for_request(path: str, method: str) -> Optional[str]:
    method = method.upper(); mutate = method not in {"GET", "HEAD", "OPTIONS"}
    if "/admin/navigation" in path:
        return None
    if "/admin/access/roles" in path:
        return "access.roles.manage" if mutate else "access.roles.view"
    if "/admin/ui-settings" in path:
        return "ui.settings.manage" if mutate else "ui.settings.view"
    if "/admin/admin-users" in path:
        return "access.users.manage" if mutate else "access.users.view"
    if "/admin/admin/danger" in path:
        return "system.reset"
    if "/admin/analytics" in path:
        return "analytics.manage" if mutate else "analytics.view"
    if "/admin/dashboard/refresh-revenue" in path:
        return "analytics.manage"
    if "/admin/labels/rate-import" in path:
        return "royalty.import" if mutate else "royalty.view"
    if "/admin/balance-audit" in path:
        return "royalty.manage" if mutate else "royalty.view"
    if "/admin/rate-changes" in path:
        return "labels.rate.approve" if "/decision" in path else "labels.rate.request.view"
    if "/admin/labels/" in path and "/rate-change/" in path:
        return "labels.rate" if path.endswith("/direct") else "labels.rate.request"
    if "/admin/labels" in path:
        if path.endswith("/package"):
            return "labels.package"
        if any(token in path for token in ("bank-change", "bank-account")):
            return "labels.bank"
        if any(token in path for token in ("create-account", "revoke-account", "change-email")):
            return "labels.accounts"
        return "labels.manage" if mutate else "labels.view"
    if "/admin/kyc" in path:
        return "kyc.review" if mutate else "kyc.view"
    if "/admin/artists" in path:
        return "artists.manage" if mutate else "artists.view"
    if "/admin/releases" in path or ("/releases/" in path and "/admin/action" in path):
        return "releases.review" if mutate else "releases.view"
    if "/admin/payments" in path or "/payments/admin" in path:
        return "payments.manage" if mutate else "payments.view"
    if "/royalty/admin" in path:
        if "/royalty/admin/adjustments" in path:
            return "royalty.manage"
        if method == "DELETE": return "royalty.delete"
        if mutate and any(token in path for token in ("imports", "upload", "publish", "dana-received")): return "royalty.import"
        return "royalty.manage" if mutate else "royalty.view"
    if "/withdraw/admin" in path:
        return "withdraw.manage" if mutate else "withdraw.view"
    if "/tickets/admin" in path:
        return "support.manage" if mutate else "support.view"
    if "/contracts/admin" in path:
        return "contracts.manage" if mutate else "contracts.view"
    if "/wami/admin" in path:
        return "wami.manage" if mutate else "wami.view"
    if path.startswith("/api/cms/"):
        return "cms.manage" if mutate else "cms.view"
    if "/admin/migrate/claims" in path or "/admin/migrate/labels/unclaimed" in path:
        return "migration.claims"
    if "/admin/migrate" in path:
        return "migration.manage" if mutate else "migration.view"
    if "/admin/activity-logs" in path:
        return "activity.view"
    if "/notifications/admin/log" in path:
        return "notifications.view"
    if "/admin/cron" in path:
        return "automation.manage"
    if "/admin/dashboard" in path:
        return "dashboard.view"
    return None


def permission_catalog() -> List[Dict[str, Any]]:
    result = []
    for module in deepcopy(PERMISSION_MODULES):
        actions = []
        for key, label_id, label_en in module["actions"]:
            meta = permission_meta(key)
            actions.append({
                "key": key, "label_id": label_id, "label_en": label_en,
                "type": meta["type"], "sensitive": meta["sensitive"],
                "requires_approval": meta["requires_approval"], "lifecycle": meta["lifecycle"],
                "depends_on": resolve_deps(key),
                "description_id": meta["desc_id"], "description_en": meta["desc_en"],
                "boundary_id": meta["boundary_id"], "boundary_en": meta["boundary_en"],
            })
        result.append({**module, "actions": actions})
    return result


def compute_permission_warnings(permissions: List[str]) -> List[Dict[str, Any]]:
    """Configuration validation: derive determinable warnings from actual permission model."""
    selected = list(dict.fromkeys(permissions or []))
    sel = set(selected)
    engine = set(sel)
    implied = {
        "access.users.manage": {"access.users.view"}, "access.roles.manage": {"access.roles.view"},
        "ui.settings.manage": {"ui.settings.view"}, "migration.claims": {"migration.view"},
        "labels.rate.approve": {"labels.rate.request.view"},
    }
    for source, targets in implied.items():
        if source in engine:
            engine |= targets

    def nm(key: str):
        return PERMISSION_NAMES.get(key, (key, key))

    warnings: List[Dict[str, Any]] = []
    for key in selected:
        meta = permission_meta(key)
        for dep in resolve_deps(key):
            if dep not in engine:
                warnings.append({"code": "missing_prerequisite", "permission": key, "severity": "warning",
                    "message_id": f"Izin “{nm(key)[0]}” sebaiknya disertai “{nm(dep)[0]}”.",
                    "message_en": f"Permission “{nm(key)[1]}” should also include “{nm(dep)[1]}”."})
        if meta["lifecycle"] == "deprecated":
            warnings.append({"code": "deprecated_permission", "permission": key, "severity": "warning",
                "message_id": f"Izin “{nm(key)[0]}” sudah tidak digunakan (deprecated).",
                "message_en": f"Permission “{nm(key)[1]}” is deprecated."})
    if "labels.rate" in sel and "labels.rate.request" in sel:
        warnings.append({"code": "redundant_request", "permission": "labels.rate.request", "severity": "info",
            "message_id": "Izin ubah langsung sudah aktif; izin “Ajukan Perubahan Rate/Fee” menjadi tidak berpengaruh.",
            "message_en": "Direct change is granted, so the request permission has no effect."})
    if "labels.rate.approve" in sel and "labels.rate.request.view" not in engine:
        warnings.append({"code": "approver_no_queue", "permission": "labels.rate.approve", "severity": "warning",
            "message_id": "Penyetuju perlu izin “Lihat Permintaan Rate/Fee” untuk melihat antrean.",
            "message_en": "Approver needs “View Rate/Fee Requests” to see the queue."})
    return warnings


_STATE_LABELS = {
    "view": ("Dapat Melihat", "Can view"),
    "standard": ("Dapat Mengubah", "Can edit"),
    "sensitive": ("Perlu Persetujuan", "Requires approval"),
    "approval": ("Dapat Menyetujui", "Can approve"),
    "direct": ("Ubah Langsung", "Direct change"),
    "unavailable": ("Tidak Tersedia", "Unavailable"),
}


def preview_access(permissions: List[str], active: bool = True) -> Dict[str, Any]:
    """Behavioral role preview using the SAME production authorization engine (has_permission)."""
    user = {"role": "__preview__", "permissions": list(permissions or []), "admin_role_active": bool(active)}
    modules = []
    for module in PERMISSION_MODULES:
        actions = []
        module_allowed = False
        has_write = False
        for key, label_id, label_en in module["actions"]:
            allowed = has_permission(user, key)
            meta = permission_meta(key)
            if allowed:
                module_allowed = True
                state = meta["type"]
                if state != "view":
                    has_write = True
            else:
                state = "unavailable"
            sid, sen = _STATE_LABELS.get(state, _STATE_LABELS["standard"])
            entry = {"key": key, "label_id": label_id, "label_en": label_en,
                     "allowed": allowed, "state": state, "state_label_id": sid, "state_label_en": sen}
            if not allowed:
                entry["reason_id"] = f"Perlu izin “{label_id}”."
                entry["reason_en"] = f"Requires “{label_en}”."
            actions.append(entry)
        modules.append({"key": module["key"], "label_id": module["label_id"], "label_en": module["label_en"],
                        "accessible": module_allowed, "read_only": module_allowed and not has_write,
                        "actions": actions})
    return {"modules": modules, "active": bool(active)}