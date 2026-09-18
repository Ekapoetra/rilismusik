"""Dynamic admin roles, permissions, and navigation configuration."""
import hashlib
from copy import deepcopy
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from models import now_iso, new_id

SYSTEM_ROLE = "super_admin"  # the ONLY permanent/system role


PERMISSION_MODULES = [
    {"key": "dashboard", "label_id": "Dashboard", "label_en": "Dashboard", "actions": [("dashboard.view", "Lihat dashboard", "View dashboard")]},
    {"key": "work", "label_id": "Pekerjaan", "label_en": "Work", "actions": [("work.view", "Lihat Pekerjaan", "View Work queue"), ("work.manage", "Kelola Tanggung Jawab & SLA", "Manage Responsibility & SLA")]},
    {"key": "analytics", "label_id": "Analitik", "label_en": "Analytics", "actions": [("analytics.view", "Lihat analitik", "View analytics"), ("analytics.manage", "Hitung ulang analitik", "Recompute analytics")]},
    {"key": "labels", "label_id": "Label", "label_en": "Labels", "actions": [("labels.view", "Lihat label", "View labels"), ("labels.manage", "Edit label", "Edit labels"), ("labels.package", "Ubah Langsung Paket", "Direct Package Change"), ("labels.package.request", "Ajukan Perubahan Paket", "Request Package Change"), ("labels.package.request.view", "Lihat Permintaan Paket", "View Package Requests"), ("labels.package.approve", "Setujui/Tolak Paket", "Approve/Reject Package"), ("labels.rate", "Ubah Langsung Rate/Fee", "Direct Rate/Fee Change"), ("labels.rate.request", "Ajukan Perubahan Rate/Fee", "Request Rate/Fee Change"), ("labels.rate.request.view", "Lihat Permintaan Rate/Fee", "View Rate/Fee Requests"), ("labels.rate.approve", "Setujui/Tolak Rate/Fee", "Approve/Reject Rate/Fee"), ("labels.blacklist", "Blacklist Langsung", "Direct Blacklist"), ("labels.blacklist.request", "Ajukan Blacklist", "Request Blacklist"), ("labels.blacklist.request.view", "Lihat Permintaan Blacklist", "View Blacklist Requests"), ("labels.blacklist.approve", "Setujui/Tolak Blacklist", "Approve/Reject Blacklist"), ("labels.accounts", "Kelola akun label", "Manage label accounts"), ("labels.bank", "Kelola rekening", "Manage bank accounts"), ("labels.bank.verify", "Verifikasi Rekening", "Verify Bank Accounts"), ("labels.multi_label.view", "Lihat Multi Label", "View Multi Label"), ("labels.multi_label.manage", "Kelola Multi Label", "Manage Multi Label")]},
    {"key": "kyc", "label_id": "Verifikasi Akun", "label_en": "Account Verification", "actions": [("kyc.view", "Lihat Verifikasi Akun", "View account verification"), ("kyc.review", "Setujui/tolak Verifikasi Akun", "Approve/reject account verification")]},
    {"key": "artists", "label_id": "Artis", "label_en": "Artists", "actions": [("artists.view", "Lihat artis", "View artists"), ("artists.manage", "Edit artis", "Edit artists")]},
    {"key": "releases", "label_id": "Rilisan", "label_en": "Releases", "actions": [("releases.view", "Lihat rilisan", "View releases"), ("releases.review", "Review dan ubah status", "Review and update status"), ("releases.go_live", "Finalisasi Tayang (UPC/ISRC)", "Finalize Go-Live (UPC/ISRC)"), ("releases.takedown", "Turunkan Rilisan", "Take Down Release"), ("releases.delete", "Hapus Rilisan", "Delete Release")]},
    {"key": "payments", "label_id": "Pembayaran", "label_en": "Payments", "actions": [("payments.view", "Lihat pembayaran", "View payments"), ("payments.manage", "Kelola pembayaran/produk", "Manage payments/products"), ("payments.refund", "Refund pembayaran (tandai sudah direfund)", "Refund payments (mark refunded)")]},
    {"key": "royalty", "label_id": "Royalti", "label_en": "Royalty", "actions": [("royalty.view", "Lihat royalti", "View royalty"), ("royalty.import", "Impor royalti", "Import royalty"), ("royalty.publish", "Publish/rilis royalti ke saldo", "Publish royalty to balances"), ("royalty.manage", "Audit dan rekonsiliasi", "Audit and reconcile"), ("royalty.delete", "Hapus import", "Delete import")]},
    {"key": "withdraw", "label_id": "Penarikan Dana", "label_en": "Withdrawals", "actions": [("withdraw.view", "Lihat penarikan", "View withdrawals"), ("withdraw.manage", "Kelola/edit penarikan", "Manage/edit withdrawals"), ("withdraw.approve", "Setujui/tolak penarikan", "Approve/reject withdrawals"), ("withdraw.pay", "Bayar penarikan (tandai dibayar)", "Pay withdrawals (mark paid)")]},
    {"key": "wami", "label_id": "WAMI", "label_en": "WAMI", "actions": [("wami.view", "Lihat WAMI", "View WAMI"), ("wami.manage", "Ubah status WAMI", "Update WAMI status")]},
    {"key": "addon", "label_id": "Layanan Tambahan", "label_en": "Add-on Services", "actions": [("addon.view", "Lihat layanan tambahan", "View add-on services"), ("addon.manage", "Kelola katalog & proses order", "Manage catalog & process orders")]},
    {"key": "support", "label_id": "Tiket Bantuan", "label_en": "Support Tickets", "actions": [("support.view", "Lihat tiket", "View tickets"), ("support.manage", "Balas/ubah status", "Reply/update status")]},
    {"key": "cms", "label_id": "CMS", "label_en": "CMS", "actions": [("cms.view", "Lihat CMS", "View CMS"), ("cms.manage", "Edit konten/aset", "Edit content/assets")]},
    {"key": "contracts", "label_id": "Kontrak", "label_en": "Contracts", "actions": [("contracts.view", "Lihat kontrak", "View contracts"), ("contracts.manage", "Buat/perpanjang/akhiri", "Create/extend/terminate")]},
    {"key": "access", "label_id": "Kontrol Akses", "label_en": "Access Control", "actions": [("access.users.view", "Lihat pengguna admin", "View admin users"), ("access.users.manage", "Buat/edit pengguna admin", "Create/edit admin users"), ("access.roles.view", "Lihat role", "View roles"), ("access.roles.manage", "Buat/edit role", "Create/edit roles")]},
    {"key": "ui", "label_id": "Pengaturan UI", "label_en": "UI Settings", "actions": [("ui.settings.view", "Lihat pengaturan UI", "View UI settings"), ("ui.settings.manage", "Edit bahasa/navigasi", "Edit language/navigation")]},
    {"key": "migration", "label_id": "Migrasi", "label_en": "Migration", "actions": [("migration.view", "Lihat migrasi/klaim", "View migration/claims"), ("migration.manage", "Jalankan migrasi/klaim", "Run migration/claims"), ("migration.claims", "Verifikasi klaim label", "Verify label claims")]},
    {"key": "activity", "label_id": "Log Aktivitas", "label_en": "Activity Logs", "actions": [("activity.view", "Lihat log aktivitas", "View activity logs")]},
    {"key": "notifications", "label_id": "Notifikasi", "label_en": "Notifications", "actions": [("notifications.view", "Lihat riwayat notifikasi", "View notification history")]},
    {"key": "automation", "label_id": "Otomasi", "label_en": "Automation", "actions": [("automation.manage", "Jalankan tugas terjadwal", "Trigger scheduled jobs")]},
    {"key": "staff", "label_id": "Manajemen Staf", "label_en": "Staff Management", "actions": [("staff.view", "Lihat staf", "View staff"), ("staff.manage", "Kelola staf (status kerja & gaji)", "Manage staff (employment & salary)"), ("staff.attendance.view", "Lihat absensi tim", "View team attendance"), ("staff.attendance.correct", "Koreksi absensi", "Correct attendance"), ("staff.leave.approve", "Setujui/tolak cuti", "Approve/reject leave"), ("staff.config.manage", "Kelola konfigurasi absensi", "Manage attendance configuration")]},
    {"key": "performance", "label_id": "Performa & KPI", "label_en": "Performance & KPI", "actions": [("performance.view_own", "Lihat performa sendiri", "View own performance"), ("performance.view_team", "Lihat performa tim", "View team performance"), ("performance.view_details", "Lihat detail performa", "View performance details"), ("performance.config.manage", "Kelola konfigurasi KPI", "Manage KPI configuration"), ("performance.period.manage", "Finalisasi/buka periode kinerja", "Finalize/reopen performance period")]},
    {"key": "compensation", "label_id": "Kompensasi & Payroll", "label_en": "Compensation & Payroll", "actions": [("compensation.view", "Lihat kompensasi", "View compensation"), ("compensation.view_own", "Lihat kompensasi sendiri", "View own compensation"), ("compensation.view_team", "Lihat kompensasi tim", "View team compensation"), ("compensation.salary.manage", "Kelola gaji", "Manage salary"), ("compensation.allowance.manage", "Kelola tunjangan", "Manage allowances"), ("compensation.bonus.view", "Lihat bonus", "View bonus"), ("compensation.bonus.transactions.view", "Lihat transaksi bonus", "View bonus transactions"), ("compensation.bonus.rules.manage", "Kelola aturan bonus", "Manage bonus rules"), ("compensation.adjustment.create", "Buat penyesuaian", "Create adjustment"), ("compensation.adjustment.approve", "Setujui penyesuaian", "Approve adjustment"), ("compensation.payroll.view", "Lihat payroll", "View payroll"), ("compensation.payroll.manage", "Kelola payroll", "Manage payroll"), ("compensation.payroll.approve", "Setujui payroll", "Approve payroll"), ("compensation.payroll.mark_paid", "Tandai payroll dibayar", "Mark payroll paid"), ("compensation.payroll.finalize", "Finalisasi payroll", "Finalize payroll")]},
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
    "labels.package": {"type": "direct", "sensitive": True, "depends_on": ["labels.view"],
        "desc_id": "Mengubah paket/langganan label secara LANGSUNG tanpa persetujuan.",
        "desc_en": "Change a label package/subscription DIRECTLY without approval.",
        "boundary_id": "Hanya pemegang izin tepercaya; setiap perubahan diaudit.",
        "boundary_en": "Trusted holders only; every change is audited."},
    "labels.package.request": {"type": "sensitive", "sensitive": True, "requires_approval": True, "depends_on": ["labels.view"],
        "desc_id": "Mengajukan perubahan paket label untuk disetujui Super Admin.",
        "desc_en": "Submit a label package change for Super Admin approval.",
        "boundary_id": "Paket live tidak berubah sampai disetujui.",
        "boundary_en": "The live package stays unchanged until approved."},
    "labels.package.request.view": {"type": "view", "depends_on": ["labels.view"],
        "desc_id": "Melihat antrean permintaan perubahan paket.",
        "desc_en": "View the package change request queue."},
    "labels.package.approve": {"type": "approval", "sensitive": True, "depends_on": ["labels.package.request.view"],
        "desc_id": "Menyetujui atau menolak permintaan perubahan paket (efektif hanya Super Admin).",
        "desc_en": "Approve or reject package change requests (effectively Super Admin only)."},
    "labels.blacklist": {"type": "direct", "sensitive": True, "depends_on": ["labels.view"],
        "desc_id": "Blacklist / lepas blacklist label secara LANGSUNG tanpa persetujuan.",
        "desc_en": "Blacklist / un-blacklist a label DIRECTLY without approval.",
        "boundary_id": "Hanya pemegang izin tepercaya; setiap perubahan diaudit.",
        "boundary_en": "Trusted holders only; every change is audited."},
    "labels.blacklist.request": {"type": "sensitive", "sensitive": True, "requires_approval": True, "depends_on": ["labels.view"],
        "desc_id": "Mengajukan blacklist / lepas blacklist label untuk disetujui Super Admin.",
        "desc_en": "Submit a label blacklist / un-blacklist for Super Admin approval.",
        "boundary_id": "Status live tidak berubah sampai disetujui.",
        "boundary_en": "The live status stays unchanged until approved."},
    "labels.blacklist.request.view": {"type": "view", "depends_on": ["labels.view"],
        "desc_id": "Melihat antrean permintaan blacklist.",
        "desc_en": "View the blacklist request queue."},
    "labels.blacklist.approve": {"type": "approval", "sensitive": True, "depends_on": ["labels.blacklist.request.view"],
        "desc_id": "Menyetujui atau menolak permintaan blacklist (efektif hanya Super Admin).",
        "desc_en": "Approve or reject blacklist requests (effectively Super Admin only)."},
    # --- Granular high-risk actions (Phase C) ---
    "releases.go_live": {"type": "sensitive", "sensitive": True, "depends_on": ["releases.review"],
        "desc_id": "Menandai rilisan TAYANG (mengunci UPC/ISRC). Aksi final yang tampil di DSP.",
        "desc_en": "Mark a release LIVE (locks UPC/ISRC). Final action visible on DSPs."},
    "releases.takedown": {"type": "sensitive", "sensitive": True, "depends_on": ["releases.review"],
        "desc_id": "Menurunkan rilisan yang sudah tayang dari platform.",
        "desc_en": "Take a live release down from platforms."},
    "releases.delete": {"type": "sensitive", "sensitive": True, "destructive": True, "depends_on": ["releases.view"],
        "desc_id": "Menghapus permanen data rilisan. Tidak dapat dibatalkan.",
        "desc_en": "Permanently delete a release record. Cannot be undone."},
    "withdraw.approve": {"type": "approval", "sensitive": True, "depends_on": ["withdraw.view"],
        "desc_id": "Menyetujui atau menolak permintaan penarikan dana label.",
        "desc_en": "Approve or reject a label withdrawal request."},
    "withdraw.pay": {"type": "sensitive", "sensitive": True, "depends_on": ["withdraw.view"],
        "desc_id": "Menandai penarikan sudah DIBAYAR — mengunci saldo & periode royalti (aksi finansial).",
        "desc_en": "Mark a withdrawal PAID — locks balance & royalty period (financial action)."},
    "royalty.publish": {"type": "sensitive", "sensitive": True, "depends_on": ["royalty.view"],
        "desc_id": "Publish/rilis hasil import royalti ke saldo label (mempengaruhi uang label).",
        "desc_en": "Publish an import to label balances (affects label money)."},
    "labels.bank.verify": {"type": "approval", "sensitive": True, "depends_on": ["labels.bank"],
        "desc_id": "Memverifikasi/menyetujui perubahan & input rekening bank label (dulu khusus Super Admin, kini dapat didelegasikan).",
        "desc_en": "Verify/approve label bank account changes & first-time inputs (was Super Admin only, now delegatable)."},
    "labels.multi_label.view": {"type": "view", "depends_on": ["labels.view"],
        "desc_id": "Melihat akun & pengaturan Multi Label.",
        "desc_en": "View Multi Label accounts & settings."},
    "labels.multi_label.manage": {"type": "sensitive", "sensitive": True, "depends_on": ["labels.multi_label.view"],
        "desc_id": "Mengaktifkan/mengelola paket Multi Label di level account (gabung banyak label, benefit VIP, kuota 7/hari/akun).",
        "desc_en": "Activate/manage the account-level Multi Label package (multi-label ownership, VIP benefits, 7/day/account quota).",
        "boundary_id": "Efektif hanya Super Admin sampai didelegasikan.",
        "boundary_en": "Effectively Super Admin only until delegated."},
    "compensation.view_own": {"type": "view", "depends_on": ["compensation.view"],
        "desc_id": "Melihat kompensasi (gaji & payroll) milik sendiri.", "desc_en": "View own compensation (salary & payroll)."},
    "compensation.view_team": {"type": "view", "depends_on": ["compensation.view"],
        "desc_id": "Melihat kompensasi seluruh staf.", "desc_en": "View all staff compensation."},
    "compensation.salary.manage": {"type": "sensitive", "sensitive": True, "depends_on": ["compensation.view"],
        "desc_id": "Mengubah gaji staf (effective-dated).", "desc_en": "Change staff salary (effective-dated)."},
    "compensation.allowance.manage": {"type": "sensitive", "sensitive": True, "depends_on": ["compensation.view"],
        "desc_id": "Mengelola tunjangan staf.", "desc_en": "Manage staff allowances."},
    "compensation.bonus.rules.manage": {"type": "sensitive", "sensitive": True, "depends_on": ["compensation.bonus.view"],
        "desc_id": "Membuat/mengubah skema bonus (persentase dari total pendapatan).", "desc_en": "Create/edit bonus schemes (percentage of total revenue)."},
    "compensation.adjustment.approve": {"type": "approval", "sensitive": True, "depends_on": ["compensation.adjustment.create"],
        "desc_id": "Menyetujui penyesuaian kompensasi.", "desc_en": "Approve compensation adjustments."},
    "compensation.payroll.approve": {"type": "approval", "sensitive": True, "depends_on": ["compensation.payroll.view"],
        "desc_id": "Menyetujui periode payroll.", "desc_en": "Approve payroll periods."},
    "compensation.payroll.mark_paid": {"type": "sensitive", "sensitive": True, "depends_on": ["compensation.payroll.view"],
        "desc_id": "Menandai payroll telah dibayar.", "desc_en": "Mark payroll as paid."},
    "compensation.payroll.finalize": {"type": "sensitive", "sensitive": True, "depends_on": ["compensation.payroll.view"],
        "desc_id": "Finalisasi payroll (snapshot menjadi immutable).", "desc_en": "Finalize payroll (snapshots become immutable)."},
}

_META_DEFAULT = {"type": "standard", "sensitive": False, "requires_approval": False,
                 "destructive": False, "depends_on": None, "lifecycle": "active",
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
    "admin_release": ["dashboard.view", "notifications.view", "labels.view", "labels.manage", "labels.accounts", "artists.view", "artists.manage", "releases.view", "releases.review", "addon.view", "addon.manage", "wami.view", "wami.manage", "contracts.view", "contracts.manage", "activity.view", "automation.manage"],
    "admin_finance": ["dashboard.view", "notifications.view", "analytics.view", "analytics.manage", "labels.view", "labels.manage", "labels.package.request", "labels.package.request.view", "labels.rate.request", "labels.rate.request.view", "labels.bank", "artists.view", "releases.view", "payments.view", "payments.manage", "addon.view", "addon.manage", "royalty.view", "royalty.import", "royalty.manage", "withdraw.view", "withdraw.manage", "activity.view", "automation.manage"],
    "admin_support": ["dashboard.view", "notifications.view", "labels.view", "labels.manage", "labels.accounts", "labels.bank", "labels.blacklist.request", "labels.blacklist.request.view", "kyc.view", "kyc.review", "artists.view", "payments.view", "payments.manage", "support.view", "support.manage", "migration.view", "migration.manage", "migration.claims"],
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
    ("work", "/admin/work", "ClipboardList", "work.view", "Pekerjaan", "Work", None),
    ("analytics", "/admin/analytics", "BarChart3", "analytics.view", "Analitik Royalti", "Royalty Analytics", None),
    ("analytics_audit", "/admin/analytics/audit", "ShieldCheck", "analytics.manage", "Audit Konsistensi", "Consistency Audit", None),
    ("labels", "/admin/labels", "Building2", "labels.view", "Manajemen Label", "Label Management", None),
    ("rate_changes", "/admin/rate-changes", "ShieldCheck", "labels.rate.request.view", "Persetujuan Sensitif", "Sensitive Approvals", "labels"),
    ("multi_label", "/admin/multi-label", "Layers", "labels.multi_label.view", "Multi Label", "Multi Label", "labels"),
    ("kyc", "/admin/kyc", "ShieldCheck", "kyc.view", "Verifikasi Akun", "Account Verification", None),
    ("artists", "/admin/artists", "UserSquare", "artists.view", "Manajemen Artis", "Artist Management", None),
    ("releases", "/admin/releases", "Disc3", "releases.view", "Manajemen Rilisan", "Release Management", None),
    ("payments", "/admin/payments", "CreditCard", "payments.view", "Pembayaran", "Payments", None),
    ("addon_orders", "/admin/addon-orders", "Sparkles", "addon.view", "Layanan Tambahan", "Add-on Services", None),
    ("royalty", "/admin/royalty", "FileSpreadsheet", "royalty.view", "Impor Royalti", "Royalty Import", None),
    ("royalty_adjustments", "/admin/royalty-adjustments", "Wallet", "royalty.manage", "Inject Saldo", "Royalty Adjustments", None),
    ("withdraw", "/admin/withdraw", "Banknote", "withdraw.view", "Penarikan Dana", "Withdrawals", None),
    ("xendit_recon", "/admin/xendit-reconciliation", "Scale", "payments.view", "Rekonsiliasi Xendit", "Xendit Reconciliation", "payments"),
    ("refunds", "/admin/refunds", "RotateCcw", "payments.refund", "Refund Pembayaran", "Payment Refunds", "payments"),
    ("wami", "/admin/wami", "Music", "wami.view", "Registrasi WAMI", "WAMI Registration", None),
    ("tickets", "/admin/tickets", "MessageSquare", "support.view", "Tiket Bantuan", "Support Tickets", None),
    ("cms", "/admin/cms", "LayoutTemplate", "cms.view", "Landing Page CMS", "Landing Page CMS", None),
    ("contracts", "/admin/contracts", "FileSignature", "contracts.view", "Kontrak", "Contracts", None),
    ("admin_users", "/admin/admin-users", "Users2", "access.users.view", "Pengguna Admin", "Admin Users", None),
    ("roles", "/admin/access", "KeyRound", "access.roles.view", "Role & Permission", "Roles & Permissions", "admin_users"),
    ("ui_settings", "/admin/ui-settings", "PanelLeft", "ui.settings.view", "Pengaturan UI", "UI Settings", None),
    ("migrate", "/admin/migrate", "DatabaseZap", "migration.view", "Migrasi & Klaim", "Migration & Claims", None),
    ("activity", "/admin/activity-logs", "ScrollText", "activity.view", "Log Aktivitas", "Activity Logs", None),
    ("status", "/admin/status", "Activity", "dashboard.view", "Status", "Status", None),
    ("staff", "/admin/staff", "UsersRound", "staff.view", "Manajemen Staf", "Staff Management", None),
    ("attendance", "/admin/attendance", "CalendarCheck", "staff.attendance.view", "Absensi", "Attendance", "staff"),
    ("staff_config", "/admin/staff/configuration", "SlidersHorizontal", "staff.config.manage", "Konfigurasi", "Configuration", "staff"),
    ("performance", "/admin/performance", "Gauge", "performance.view_team", "Performa Tim", "Team Performance", None),
    ("my_performance", "/admin/my-performance", "TrendingUp", "performance.view_own", "Performa Saya", "My Performance", None),
    ("performance_config", "/admin/performance/configuration", "SlidersHorizontal", "performance.config.manage", "Konfigurasi KPI", "KPI Configuration", "performance"),
    ("compensation_me", "/admin/compensation/me", "Wallet", "compensation.view_own", "Kompensasi Saya", "My Compensation", None),
    ("compensation_payroll", "/admin/compensation/payroll", "Receipt", "compensation.payroll.view", "Payroll", "Payroll", "compensation_me"),
    ("compensation_staff", "/admin/compensation/staff", "UsersRound", "compensation.view_team", "Kompensasi Staf", "Staff Compensation", "compensation_me"),
    ("compensation_bonus", "/admin/compensation/bonus", "Coins", "compensation.bonus.view", "Bonus", "Bonus", "compensation_me"),
    ("compensation_bonus_rules", "/admin/compensation/bonus-rules", "Percent", "compensation.bonus.rules.manage", "Aturan Bonus", "Bonus Rules", "compensation_me"),
    ("compensation_adjustments", "/admin/compensation/adjustments", "PlusCircle", "compensation.adjustment.create", "Penyesuaian", "Adjustments", "compensation_me"),
]

# Sidebar section groups (PRD §21). Order here = default vertical order.
DEFAULT_NAV_GROUPS = [
    ("work_center", "Pusat Kerja", "Work Center"),
    ("distribution_ops", "Operasional Distribusi", "Distribution Operations"),
    ("royalty_finance", "Royalti & Keuangan", "Royalty & Finance"),
    ("services_support", "Layanan & Dukungan", "Services & Support"),
    ("team_access", "Tim & Akses", "Team & Access"),
    ("personal", "Personal", "Personal"),
    ("system", "Sistem", "System"),
]

# nav item key → default group id
NAV_GROUP_MAP = {
    "dashboard": "work_center", "work": "work_center", "status": "work_center",
    "labels": "distribution_ops", "rate_changes": "distribution_ops", "multi_label": "distribution_ops",
    "kyc": "distribution_ops", "releases": "distribution_ops", "migrate": "distribution_ops", "contracts": "distribution_ops",
    "analytics": "royalty_finance", "analytics_audit": "royalty_finance", "artists": "royalty_finance",
    "royalty": "royalty_finance", "royalty_adjustments": "royalty_finance", "withdraw": "royalty_finance",
    "payments": "royalty_finance", "xendit_recon": "royalty_finance", "refunds": "royalty_finance",
    "addon_orders": "services_support", "wami": "services_support", "tickets": "services_support",
    "admin_users": "team_access", "roles": "team_access", "staff": "team_access", "attendance": "team_access",
    "staff_config": "team_access", "performance": "team_access", "performance_config": "team_access",
    "my_performance": "personal", "compensation_me": "personal", "compensation_payroll": "personal",
    "compensation_staff": "personal", "compensation_bonus": "personal", "compensation_bonus_rules": "personal",
    "compensation_adjustments": "personal",
    "cms": "system", "activity": "system", "ui_settings": "system",
}


def default_navigation() -> Dict[str, Any]:
    return {
        "key": "admin_navigation", "default_locale": "id",
        "groups": [
            {"id": gid, "labels": {"id": lid, "en": len_}, "order": i}
            for i, (gid, lid, len_) in enumerate(DEFAULT_NAV_GROUPS)
        ],
        "items": [
            {"key": key, "route": route, "icon": icon, "permission": permission,
             "labels": {"id": label_id, "en": label_en}, "parent_key": parent,
             "group_id": NAV_GROUP_MAP.get(key, DEFAULT_NAV_GROUPS[0][0]),
             "visible": True, "order": index}
            for index, (key, route, icon, permission, label_id, label_en, parent) in enumerate(DEFAULT_NAV_ITEMS)
        ],
    }


async def ensure_admin_access_defaults(db) -> None:
    await db.admin_roles.create_index("id", unique=True)
    await db.admin_roles.create_index("key", unique=True)
    # Super Admin is the ONLY permanent/system role. It is guaranteed to exist and
    # implicitly holds every permission (see has_permission short-circuit). Its stored
    # permission array is kept only for display; new permissions are auto-covered.
    await db.admin_roles.update_one(
        {"key": SYSTEM_ROLE},
        {"$setOnInsert": {"id": SYSTEM_ROLE, "key": SYSTEM_ROLE, "name": BUILTIN_ROLE_NAMES[SYSTEM_ROLE],
                          "normalized_name": BUILTIN_ROLE_NAMES[SYSTEM_ROLE].casefold(),
                          "permissions": ALL_PERMISSIONS, "active": True, "system": True, "builtin": True,
                          "rbac_schema_version": 14}},
        upsert=True,
    )
    await db.admin_roles.update_one({"key": SYSTEM_ROLE}, {"$set": {"system": True, "builtin": True, "active": True}})
    # One-time (flag rbac_unified_v1): convert every legacy builtin role into an ordinary
    # dynamic role and backfill admin_role_id on legacy admin users. After this migration a
    # deleted role is NEVER recreated on restart, and no builtin role is auto-seeded.
    await unify_roles_and_users(db)
    await migrate_granular_permissions(db)
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
    # v8: Extend request→approval to Blacklist and Package changes. Finance loses DIRECT package
    # and may only REQUEST; Support may REQUEST blacklist; Super Admin gets direct+approve for both.
    await db.admin_roles.update_one(
        {"key": "super_admin", "rbac_schema_version": {"$lt": 8}},
        {"$addToSet": {"permissions": {"$each": ["labels.blacklist", "labels.blacklist.request", "labels.blacklist.request.view", "labels.blacklist.approve", "labels.package.request", "labels.package.request.view", "labels.package.approve"]}},
         "$set": {"rbac_schema_version": 8}},
    )
    await db.admin_roles.update_one(
        {"key": "admin_support", "rbac_schema_version": {"$lt": 8}},
        {"$addToSet": {"permissions": {"$each": ["labels.blacklist.request", "labels.blacklist.request.view"]}},
         "$set": {"rbac_schema_version": 8}},
    )
    await db.admin_roles.update_one(
        {"key": "admin_finance", "rbac_schema_version": {"$lt": 8}},
        {"$pull": {"permissions": "labels.package"}},
    )
    await db.admin_roles.update_one(
        {"key": "admin_finance", "rbac_schema_version": {"$lt": 8}},
        {"$addToSet": {"permissions": {"$each": ["labels.package.request", "labels.package.request.view"]}},
         "$set": {"rbac_schema_version": 8}},
    )
    # v9: Work Responsibility layer (PRD-02). Grant work.view to all admin roles, work.manage to Super Admin.
    await db.admin_roles.update_many(
        {"rbac_schema_version": {"$lt": 9}},
        {"$addToSet": {"permissions": "work.view"}, "$set": {"rbac_schema_version": 9}},
    )
    await db.admin_roles.update_one(
        {"key": "super_admin"},
        {"$addToSet": {"permissions": {"$each": ["work.view", "work.manage"]}}},
    )
    # v10: Add-on Services module (direct action, no approval). Release + Finance can process & manage catalog.
    await db.admin_roles.update_one(
        {"key": "super_admin"},
        {"$addToSet": {"permissions": {"$each": ["addon.view", "addon.manage"]}}},
    )
    for key in ("admin_release", "admin_finance"):
        await db.admin_roles.update_one(
            {"key": key, "rbac_schema_version": {"$lt": 10}},
            {"$addToSet": {"permissions": {"$each": ["addon.view", "addon.manage"]}}, "$set": {"rbac_schema_version": 10}},
        )
    # v11: Staff Management & Attendance (PRD-04). Super Admin only by default.
    await db.admin_roles.update_one(
        {"key": "super_admin"},
        {"$addToSet": {"permissions": {"$each": ["staff.view", "staff.manage", "staff.attendance.view", "staff.attendance.correct", "staff.leave.approve", "staff.config.manage"]}}},
    )
    # v12: Performance & KPI (PRD-05). Super Admin only by default; grant others via Role & Permission.
    await db.admin_roles.update_one(
        {"key": "super_admin"},
        {"$addToSet": {"permissions": {"$each": ["performance.view_own", "performance.view_team", "performance.view_details", "performance.config.manage", "performance.period.manage"]}}},
    )
    # v13: Multi Label package (account-level entitlement). Super Admin only by default;
    # grant labels.multi_label.view/manage to other roles via Role & Permission for future delegation.
    await db.admin_roles.update_one(
        {"key": "super_admin"},
        {"$addToSet": {"permissions": {"$each": ["labels.multi_label.view", "labels.multi_label.manage"]}}},
    )
    # v14: Compensation & Payroll module (Super Admin only by default; delegate via Role & Permission).
    await db.admin_roles.update_one(
        {"key": "super_admin"},
        {"$addToSet": {"permissions": {"$each": [a[0] for m in PERMISSION_MODULES if m["key"] == "compensation" for a in m["actions"]]}}},
    )
    # Every staff (all admin roles) can view their OWN compensation (self-service).
    await db.admin_roles.update_many(
        {"key": {"$ne": "super_admin"}},
        {"$addToSet": {"permissions": {"$each": ["compensation.view", "compensation.view_own"]}}},
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
    # Bonus model v2: attribution removed (bonus is now a % of total revenue). Drop the stored nav item.
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation"},
        {"$pull": {"items": {"key": "compensation_attribution"}}},
    )
    # Idempotent rename of the KYC nav item to "Verifikasi Akun" (only if still on the old default label).
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation", "items": {"$elemMatch": {"key": "kyc", "labels.id": "Pemeriksaan KYC"}}},
        {"$set": {"items.$.labels.id": "Verifikasi Akun", "items.$.labels.en": "Account Verification"}},
    )
    # Rename the sensitive approvals nav item if still on the old default label.
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation", "items": {"$elemMatch": {"key": "rate_changes", "labels.id": "Permintaan Rate/Fee"}}},
        {"$set": {"items.$.labels.id": "Persetujuan Sensitif", "items.$.labels.en": "Sensitive Approvals", "items.$.icon": "ShieldCheck"}},
    )
    # Add-on Services nav item now gated by its own permission (was releases.review).
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation", "items": {"$elemMatch": {"key": "addon_orders", "permission": "releases.review"}}},
        {"$set": {"items.$.permission": "addon.view"}},
    )
    # Action Center redesign: remove the standalone "Riwayat Notifikasi" nav item
    # (still reachable via the header notification bell's history link).
    await db.admin_ui_settings.update_one(
        {"key": "admin_navigation"},
        {"$pull": {"items": {"key": "notifications"}}},
    )
    # Configuration Required: detect newly-registered permissions for Super Admin review.
    await sync_capability_review(db)
    # PRD "Work Scope not Responsibility": purge the retired Responsibility mapping so no
    # deployment ever reads it again (work ownership now follows permissions / super_admin_only).
    await db.admin_ui_settings.delete_one({"key": "work_responsibility"})


def is_admin_identity(user: Dict[str, Any]) -> bool:
    return user.get("role") in set(BUILTIN_ROLE_DEFAULTS) | {"admin_custom"} or bool(user.get("admin_role_id"))


async def unify_roles_and_users(db) -> Dict[str, Any]:
    """One-time RBAC unification. Super Admin stays the sole system role; every other role
    becomes a dynamic role; legacy admin users get an explicit admin_role_id. Idempotent flag."""
    flag = await db.admin_ui_settings.find_one({"key": "rbac_unified_v1"})
    if flag:
        return {"skipped": True}
    res = await db.admin_roles.update_many(
        {"key": {"$ne": SYSTEM_ROLE}}, {"$set": {"builtin": False, "system": False}},
    )
    migrated = 0
    async for u in db.users.find(
        {"role": {"$nin": ["label", "artist", SYSTEM_ROLE]}, "admin_role_id": {"$in": [None, ""]}},
        {"_id": 0, "id": 1, "role": 1},
    ):
        role = await db.admin_roles.find_one({"$or": [{"id": u.get("role")}, {"key": u.get("role")}]}, {"_id": 0, "id": 1})
        if role:
            await db.users.update_one({"id": u["id"]}, {"$set": {"admin_role_id": role["id"]}})
            migrated += 1
    await db.admin_ui_settings.update_one(
        {"key": "rbac_unified_v1"},
        {"$set": {"key": "rbac_unified_v1", "roles_dynamic": res.modified_count,
                  "users_migrated": migrated, "done_at": now_iso()}}, upsert=True,
    )
    return {"roles_dynamic": res.modified_count, "users_migrated": migrated}


# Phase C: new granular permissions are granted to any dynamic role that already holds the
# broader parent permission, so nobody loses an ability. New capabilities NEVER auto-grant
# beyond this preserve-effective-access rule; Super Admin is implicit and needs no entry.
GRANULAR_GRANTS = [
    ("releases.review", ["releases.go_live", "releases.takedown", "releases.delete"]),
    ("withdraw.manage", ["withdraw.approve", "withdraw.pay"]),
    ("royalty.import", ["royalty.publish"]),
]


async def migrate_granular_permissions(db) -> Dict[str, Any]:
    """One-time (flag rbac_granular_v1): preserve effective access when splitting broad
    permissions into granular high-risk ones."""
    flag = await db.admin_ui_settings.find_one({"key": "rbac_granular_v1"})
    if flag:
        return {"skipped": True}
    touched = 0
    for parent, children in GRANULAR_GRANTS:
        r = await db.admin_roles.update_many(
            {"key": {"$ne": SYSTEM_ROLE}, "permissions": parent},
            {"$addToSet": {"permissions": {"$each": children}}},
        )
        touched += r.modified_count
    # Keep Super Admin's display array complete too (implicit access already covers it).
    await db.admin_roles.update_one(
        {"key": SYSTEM_ROLE},
        {"$addToSet": {"permissions": {"$each": [c for _, ch in GRANULAR_GRANTS for c in ch]}}},
    )
    await db.admin_ui_settings.update_one(
        {"key": "rbac_granular_v1"},
        {"$set": {"key": "rbac_granular_v1", "roles_touched": touched, "done_at": now_iso()}}, upsert=True,
    )
    return {"roles_touched": touched}


async def bump_token_version(db, user_ids: List[str]) -> int:
    """Invalidate existing sessions/JWTs for the given users (token_version is checked in
    get_current_user). Called whenever a user's effective permissions may have changed."""
    ids = [i for i in dict.fromkeys(user_ids or []) if i]
    if ids:
        await db.users.update_many({"id": {"$in": ids}}, {"$inc": {"token_version": 1}})
    return len(ids)


async def bump_role_members(db, role_id: str) -> int:
    """Invalidate sessions for every admin currently holding this role (by id or legacy key)."""
    ids = await db.users.distinct("id", {"$or": [{"admin_role_id": role_id}, {"role": role_id}]})
    return await bump_token_version(db, ids)


# ---------------------------------------------------------------------------
# Capability review ("Configuration Required"): new permissions are auto-added to
# the catalog by developers, implicitly held by Super Admin, and DEFAULT-DENY to
# dynamic roles. When the catalog gains permissions the Super Admin has not yet
# reviewed, we raise a Configuration Required marker + one idempotent notification.
# ---------------------------------------------------------------------------
def _perm_fingerprint(perms: List[str]) -> str:
    return hashlib.sha1("|".join(sorted(set(perms))).encode()).hexdigest()[:16]


async def _super_admin_ids(db) -> List[str]:
    return await db.users.distinct("id", {"role": SYSTEM_ROLE, "status": {"$nin": ["suspended", "disabled"]}})


async def sync_capability_review(db) -> Dict[str, Any]:
    """Detect newly-registered permissions and (idempotently) flag them for Super Admin review."""
    current = set(ALL_PERMISSIONS)
    state = await db.admin_ui_settings.find_one({"key": "permission_catalog_state"}, {"_id": 0})
    if not state:
        # First boot on this build: baseline everything as already-configured (existing roles
        # were set up before this mechanism). Future additions will trigger a review.
        await db.admin_ui_settings.update_one(
            {"key": "permission_catalog_state"},
            {"$set": {"key": "permission_catalog_state", "reviewed_permissions": sorted(current),
                      "reviewed_at": now_iso()}}, upsert=True,
        )
        return {"baselined": len(current)}
    reviewed = set(state.get("reviewed_permissions") or [])
    new_perms = sorted(current - reviewed)
    if not new_perms:
        return {"new": 0}
    fp = _perm_fingerprint(new_perms)
    # One idempotent in-app notification per Super Admin per fingerprint.
    names = [PERMISSION_NAMES.get(k, (k, k))[0] for k in new_perms]
    body = f"{len(new_perms)} izin baru perlu ditinjau: {', '.join(names[:6])}{'…' if len(names) > 6 else ''}. Belum ada role yang dikonfigurasi untuk izin ini."
    for uid in await _super_admin_ids(db):
        await db.notifications.update_one(
            {"event_key": f"perm_review_{fp}_{uid}"},
            {"$setOnInsert": {
                "id": new_id(), "user_id": uid, "type": "permission_review_required",
                "title": "Izin baru perlu ditinjau", "body": body,
                "link": "/admin/access", "meta": {"fingerprint": fp, "new_permissions": new_perms},
                "event_key": f"perm_review_{fp}_{uid}", "read_at": None, "created_at": now_iso(),
            }}, upsert=True,
        )
    return {"new": len(new_perms), "fingerprint": fp, "permissions": new_perms}


async def pending_capability_review(db) -> Dict[str, Any]:
    state = await db.admin_ui_settings.find_one({"key": "permission_catalog_state"}, {"_id": 0})
    reviewed = set((state or {}).get("reviewed_permissions") or [])
    new_perms = sorted(set(ALL_PERMISSIONS) - reviewed)
    meta = permission_meta
    items = [{"key": k, "label_id": PERMISSION_NAMES.get(k, (k, k))[0],
              "label_en": PERMISSION_NAMES.get(k, (k, k))[1],
              "sensitive": meta(k)["sensitive"], "destructive": meta(k)["destructive"]}
             for k in new_perms]
    return {"pending": items, "count": len(items)}


async def complete_capability_review(db, actor_id: str) -> Dict[str, Any]:
    current = sorted(set(ALL_PERMISSIONS))
    await db.admin_ui_settings.update_one(
        {"key": "permission_catalog_state"},
        {"$set": {"key": "permission_catalog_state", "reviewed_permissions": current,
                  "reviewed_at": now_iso(), "reviewed_by": actor_id}}, upsert=True,
    )
    return {"reviewed": len(current)}


async def enrich_admin_user(db, user: Dict[str, Any]) -> Dict[str, Any]:
    if not is_admin_identity(user):
        return user
    is_super = user.get("role") == SYSTEM_ROLE
    role_id = user.get("admin_role_id") or user.get("role")
    role = await db.admin_roles.find_one({"$or": [{"id": role_id}, {"key": role_id}]}, {"_id": 0})
    if is_super:
        # Implicit full access: no dependency on a stored permission array.
        permissions = ALL_PERMISSIONS
        active = True
        role_name = (role or {}).get("name") or BUILTIN_ROLE_NAMES.get(SYSTEM_ROLE, "Super Admin")
        resolved_id = (role or {}).get("id") or SYSTEM_ROLE
    else:
        # Default deny: a missing OR inactive role grants NO permissions and no admin access.
        permissions = list(role.get("permissions") or []) if role else []
        active = bool(role.get("active", True)) if role else False
        role_name = (role or {}).get("name") or "—"
        resolved_id = (role or {}).get("id") or role_id
    return {**user, "is_admin": True, "admin_role_id": resolved_id, "role_name": role_name,
            "permissions": permissions, "admin_role_active": active}


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
        "labels.package.approve": {"labels.package.request.view"},
        "labels.blacklist.approve": {"labels.blacklist.request.view"},
    }
    for source, targets in implied.items():
        if source in permissions:
            permissions.update(targets)
    return bool(user.get("admin_role_active", True)) and permission in permissions


def assert_admin_permission(user: Dict[str, Any], permission: str) -> None:
    if not has_permission(user, permission):
        raise HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED", "permission": permission, "message": "Anda tidak memiliki izin untuk tindakan ini"})


def permission_for_request(path: str, method: str) -> Optional[str]:
    method = method.upper(); mutate = method not in {"GET", "HEAD", "OPTIONS"}
    if "/admin/navigation" in path:
        return None
    if "/admin/work" in path:
        return None
    if "/admin/performance" in path:
        return None
    if "/admin/refunds" in path:
        return None
    if "/admin/access/roles" in path:
        return "access.roles.manage" if mutate else "access.roles.view"
    if "/admin/ui-settings" in path:
        return "ui.settings.manage" if mutate else "ui.settings.view"
    if "/admin/admin-users" in path:
        return "access.users.manage" if mutate else "access.users.view"
    if "/admin/bank-verifications" in path or "/admin/bank-account-change-requests" in path:
        return "labels.bank.verify"
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
    if "/admin/sensitive-requests" in path:
        return None
    if "/admin/labels/" in path and "/rate-change/" in path:
        return "labels.rate" if path.endswith("/direct") else "labels.rate.request"
    if "/admin/labels/" in path and path.endswith("/blacklist-request"):
        return "labels.blacklist.request"
    if "/admin/labels/" in path and path.endswith("/package-request"):
        return "labels.package.request"
    if "/admin/labels/" in path and (path.endswith("/blacklist") or path.endswith("/unblacklist")):
        return "labels.blacklist"
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
    if "/admin/staff/config" in path:
        return "staff.config.manage" if mutate else "staff.view"
    if "/admin/staff" in path and mutate:
        return "staff.manage"
    if "/admin/staff" in path:
        return "staff.view"
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
                "type": meta["type"], "sensitive": meta["sensitive"], "destructive": meta["destructive"],
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
    families = [
        ("labels.rate", "labels.rate.request", "labels.rate.request.view", "labels.rate.approve", "rate/fee"),
        ("labels.package", "labels.package.request", "labels.package.request.view", "labels.package.approve", "paket"),
        ("labels.blacklist", "labels.blacklist.request", "labels.blacklist.request.view", "labels.blacklist.approve", "blacklist"),
    ]
    for direct, request, view, approve, _label in families:
        if direct in sel and request in sel:
            warnings.append({"code": "redundant_request", "permission": request, "severity": "info",
                "message_id": f"Izin ubah langsung “{nm(direct)[0]}” sudah aktif; izin “{nm(request)[0]}” menjadi tidak berpengaruh.",
                "message_en": f"Direct change “{nm(direct)[1]}” is granted, so “{nm(request)[1]}” has no effect."})
        if approve in sel and view not in engine:
            warnings.append({"code": "approver_no_queue", "permission": approve, "severity": "warning",
                "message_id": f"Penyetuju perlu izin “{nm(view)[0]}” untuk melihat antrean.",
                "message_en": f"Approver needs “{nm(view)[1]}” to see the queue."})
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