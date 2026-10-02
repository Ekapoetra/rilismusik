"""Presentation contract for V7; no database access or business mutations."""
from collections import Counter
from urllib.parse import quote


SOURCES = (
    {"source": "releases", "permission": "releases.view", "category": "Rilisan", "route": "/admin/releases/{id}",
     "titles": ("release_title", "title"), "statuses": ("submitted", "under_review", "need_revision", "awaiting_payment", "paid", "approved", "delivered"),
     "new": ("submitted",), "waiting": ("need_revision", "awaiting_payment", "delivered"),
     "progress": {"submitted": 0, "under_review": 25, "paid": 50, "approved": 50, "delivered": 75}},
    {"source": "support_tickets", "permission": "support.view", "category": "Tiket bantuan", "route": "/admin/tickets/{id}",
     "titles": ("subject", "category"), "statuses": ("open", "waiting_admin", "waiting_label", "in_progress", "submitted_to_believe"),
     "new": ("open",), "waiting": ("waiting_label", "submitted_to_believe"), "progress": {"open": 0, "in_progress": 33, "submitted_to_believe": 67}},
    {"source": "withdraw_requests", "permission": "withdraw.view", "category": "Penarikan", "route": "/admin/withdraw",
     "titles": ("label_name",), "statuses": ("requested", "approved", "processing"), "new": ("requested",), "waiting": (),
     "progress": {"requested": 0, "approved": 50, "processing": 50}, "match": {"child_withdraw_ids": {"$exists": False}, "legacy_import": {"$ne": True}}},
    {"source": "addon_orders", "permission": "addon.view", "category": "Layanan tambahan", "route": "/admin/addon-orders",
     "titles": ("product_name", "label_name"), "statuses": ("pending", "in_progress", "delivered"), "new": ("pending",), "waiting": (),
     "progress": {"pending": 0, "in_progress": 33, "delivered": 67}},
    {"source": "wami_orders", "permission": "wami.view", "category": "Registrasi WAMI", "route": "/admin/wami",
     "titles": ("label_name",), "statuses": ("pending", "in_progress"), "new": ("pending",), "waiting": (), "progress": {}},
    {"source": "kyc_documents", "permission": "kyc.view", "category": "Verifikasi akun", "route": "/admin/kyc",
     "titles": ("label_name",), "statuses": ("pending_review",), "new": ("pending_review",), "waiting": (), "progress": {}, "match": {"is_current": True}},
    {"source": "users", "permission": "migration.view", "category": "Klaim akun", "route": "/admin/migrate?tab=claims",
     "titles": ("name",), "status_field": "claim_status", "statuses": ("pending_link",), "new": ("pending_link",), "waiting": (), "progress": {}, "match": {"role": "label"}},
    {"source": "label_rate_change_requests", "super_only": True, "category": "Persetujuan rate", "route": "/admin/rate-changes",
     "titles": ("label_name",), "statuses": ("pending",), "new": ("pending",), "waiting": (), "progress": {}},
    {"source": "sensitive_action_requests", "super_only": True, "category": "Persetujuan sensitif", "route": "/admin/rate-changes",
     "titles": ("summary", "label_name"), "statuses": ("pending",), "new": ("pending",), "waiting": (), "progress": {}},
    {"source": "bank_account_change_requests", "super_only": True, "category": "Verifikasi rekening", "route": "/admin/bank-verifications",
     "titles": ("label_name",), "statuses": ("pending_admin_approval",), "new": ("pending_admin_approval",), "waiting": (), "progress": {}},
    {"source": "bank_accounts", "super_only": True, "category": "Verifikasi rekening", "route": "/admin/bank-verifications",
     "titles": ("label_name",), "status_field": "verified_status", "statuses": ("pending",), "new": ("pending",), "waiting": (), "progress": {}},
)

STATUS_LABELS = {
    "submitted": "Diajukan", "under_review": "Dalam pemeriksaan", "need_revision": "Menunggu revisi label",
    "awaiting_payment": "Menunggu pembayaran", "paid": "Pembayaran diterima", "approved": "Disetujui",
    "delivered": "Dikirim", "open": "Baru", "in_progress": "Dalam penanganan", "processing": "Diproses",
    "submitted_to_believe": "Menunggu Believe", "requested": "Diajukan", "pending": "Menunggu pemeriksaan",
    "pending_review": "Menunggu pemeriksaan", "pending_link": "Menunggu pencocokan", "pending_admin_approval": "Menunggu persetujuan",
    "waiting_admin": "Menunggu admin", "waiting_label": "Menunggu label",
}


def may_read_source(spec, user, has_permission):
    if spec.get("super_only"):
        return user.get("role") == "super_admin"
    return has_permission(user, spec["permission"])


def presentation_row(spec, doc):
    identifier = str(doc.get("id") or "")
    status = doc.get(spec.get("status_field", "status"))
    if not identifier or status not in spec["statuses"]:
        return None
    is_new = status in spec["new"]
    return {
        "key": f"{spec['source']}:{identifier}", "id": identifier, "source": spec["source"],
        "category": spec["category"], "title": next((str(doc[k]) for k in spec["titles"] if doc.get(k)), spec["category"]),
        "label_name": doc.get("label_name"), "status": status, "status_label": STATUS_LABELS.get(status, status),
        "bucket": "new" if is_new else "in_progress", "waiting": not is_new and status in spec["waiting"],
        "percent": spec["progress"].get(status), "link": spec["route"].replace("{id}", quote(identifier, safe="")),
        "updated_at": doc.get("updated_at") or doc.get("created_at"),
    }


def summarize(rows, completed_today=None):
    # A business record can appear in more than one work projection. Count it once.
    unique = {r["key"]: r for r in rows if r}
    items = sorted(unique.values(), key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    queued = sum(r["bucket"] == "new" for r in items)
    categories = Counter(r["category"] for r in items)
    return items, {
        "total": len(items), "new": queued, "in_progress": len(items) - queued,
        "waiting": sum(r["waiting"] for r in items), "completed_today": completed_today,
    }, [{"category": name, "count": count} for name, count in categories.items()]


def page_rows(items, bucket, page, page_size):
    selected = [r for r in items if bucket == "all" or (bucket == "waiting" and r["waiting"]) or r["bucket"] == bucket]
    start = (page - 1) * page_size
    return {"items": selected[start:start + page_size], "total": len(selected), "page": page, "page_size": page_size,
            "pages": max(1, (len(selected) + page_size - 1) // page_size)}
