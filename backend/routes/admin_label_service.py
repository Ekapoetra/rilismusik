"""Label administration business logic, independent from FastAPI routes."""
import asyncio
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

from auth_utils import hash_password
from email_service import h, send_email
from models import LabelStatusUpdate, new_id, now_iso
from .deps import db, logger, log_activity
from .royalty_recalculation import run_label_recalculation_job


FINANCE_ROLES = ("super_admin", "admin_finance")
ACCOUNT_ADMIN_ROLES = ("super_admin", "admin_support", "admin_release")


def _require_role(user: dict, allowed: tuple[str, ...], detail: str) -> None:
    if user.get("role") not in allowed:
        raise HTTPException(status_code=403, detail=detail)


async def _get_label(label_id: str) -> dict:
    label = await db.labels.find_one({"id": label_id})
    if not label:
        raise HTTPException(status_code=404, detail="Label tidak ditemukan")
    return label


def _parse_subscription_expiry(raw_value: str) -> datetime:
    try:
        if len(raw_value) == 10:
            return datetime.strptime(raw_value, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc,
            )
        parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Format masa berlaku tidak valid (pakai YYYY-MM-DD)") from exc


def _subscription_update(body: LabelStatusUpdate, label: dict, user: dict) -> Dict[str, Any]:
    touched = any(value is not None for value in (
        body.payment_type, body.subscription_tier,
        body.subscription_expires_at, body.subscription_status,
    ))
    if not touched:
        return {}
    _require_role(user, FINANCE_ROLES, "Hanya Admin Finance / Super Admin yang bisa mengubah paket langganan")
    update: Dict[str, Any] = {}
    if body.payment_type == "pay_per_release":
        update.update({
            "payment_type": "pay_per_release", "subscription_tier": None,
            "subscription_status": "inactive", "subscription_expires_at": None,
        })
    elif body.payment_type is not None:
        update["payment_type"] = body.payment_type
    if body.subscription_tier is not None:
        update.update({"subscription_tier": body.subscription_tier, "payment_type": "annual_subscription"})
    if body.subscription_expires_at is not None:
        raw = body.subscription_expires_at.strip()
        if not raw:
            update["subscription_expires_at"] = None
        else:
            expiry = _parse_subscription_expiry(raw)
            update["subscription_expires_at"] = expiry.isoformat()
            payment_type = update.get("payment_type", label.get("payment_type"))
            if body.subscription_status is None and payment_type == "annual_subscription":
                update["subscription_status"] = "active" if expiry > datetime.now(timezone.utc) else "expired"
    if body.subscription_status is not None:
        update["subscription_status"] = body.subscription_status
    return update


async def _queue_royalty_change(
    *, label_id: str, label: dict, body: LabelStatusUpdate, user: dict,
) -> Tuple[Dict[str, Any], Optional[str]]:
    if body.royalty_percentage_default is None:
        return {}, None
    _require_role(user, FINANCE_ROLES, "Hanya Admin Finance / Super Admin")
    active = await db.withdraw_requests.find_one({
        "label_id": label_id,
        "status": {"$in": ["requested", "approved"]},
        "legacy_import": {"$ne": True},
    }, {"_id": 0, "id": 1})
    if active:
        raise HTTPException(status_code=409, detail="Selesaikan atau tolak withdraw aktif sebelum mengubah persentase royalti.")
    percentage = float(body.royalty_percentage_default)
    await db.royalty_percentage_history.insert_one({
        "id": new_id(), "label_id": label_id, "percentage": percentage,
        "effective_month": datetime.now(timezone.utc).strftime("%Y-%m"),
        "changed_by": user["id"], "changed_at": now_iso(),
        "reason": body.royalty_change_reason,
    })
    update: Dict[str, Any] = {"royalty_percentage_default": percentage}
    current = float(label.get("royalty_percentage_default", 60) or 60)
    if current == percentage:
        return update, None
    job_id = new_id()
    update.update({"royalty_recalculation_status": "queued", "royalty_recalculation_job_id": job_id})
    await db.migrate_jobs.insert_one({
        "id": job_id, "kind": "recalculate_label_unwithdrawn", "status": "queued",
        "label_id": label_id, "percentage": percentage, "submitted_by": user["id"],
        "submitted_at": now_iso(), "updated_at": now_iso(),
        "progress_lines_done": 0, "progress_lines_total": 0,
    })
    return update, job_id


async def update_label(label_id: str, body: LabelStatusUpdate, user: dict) -> dict:
    label = await _get_label(label_id)
    update: Dict[str, Any] = {}
    if body.account_status is not None:
        update["account_status"] = body.account_status
        if body.account_status == "blacklisted":
            update["blacklisted"] = True
    royalty_update, job_id = await _queue_royalty_change(
        label_id=label_id, label=label, body=body, user=user,
    )
    update.update(royalty_update)
    update.update(_subscription_update(body, label, user))
    if update:
        update["updated_at"] = now_iso()
        await db.labels.update_one({"id": label_id}, {"$set": update})
        await log_activity(user["id"], "update_label", "label", label_id, before=label, after=update)
    if job_id:
        asyncio.create_task(run_label_recalculation_job(
            job_id=job_id, label_id=label_id,
            percentage=float(body.royalty_percentage_default),
        ))
    result = await db.labels.find_one({"id": label_id}, {"_id": 0})
    if job_id:
        result.update({"royalty_recalculation_job_id": job_id, "royalty_recalculation_status": "queued"})
    return result


def _normalize_email(value: str, *, field_name: str = "Email") -> str:
    normalized = (value or "").lower().strip()
    if not normalized or "@" not in normalized:
        raise HTTPException(status_code=400, detail=f"{field_name} tidak valid")
    return normalized


def _account_password(supplied: Optional[str]) -> str:
    if supplied and len(supplied) < 8:
        raise HTTPException(status_code=400, detail="Password minimal 8 karakter")
    if supplied:
        return supplied
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(12))


async def _create_mda_for_account(label: dict, linked: dict, user: dict, now: str) -> None:
    try:
        import storage_service
        from .mda_generator import generate_mda_pdf_bytes

        legal = await db.landing_settings.find_one({"key": "legal_entity"}, {"_id": 0, "value": 1})
        contract_id = new_id()
        pdf_bytes = generate_mda_pdf_bytes(linked, (legal or {}).get("value") or {})
        r2_key = f"contract/{contract_id}.pdf"
        await storage_service.upload_bytes(key=r2_key, data=pdf_bytes, content_type="application/pdf")
        await db.contracts.insert_one({
            "id": contract_id, "label_id": label["id"], "label_name": label.get("label_name"),
            "title": "Master Distribution Agreement", "kind": "mda",
            "file_url": f"/api/files/{r2_key}",
            "filename": f"MDA-{(label.get('label_name') or '')[:20]}.pdf",
            "start_date": now[:10], "end_date": None, "is_lifetime": True,
            "status": "active", "notes": f"Auto-generated saat admin {user.get('email')} membuat akun untuk legacy label.",
            "accepted_at": now, "accepted_by_name": linked["pic_name"],
            "accepted_by_email": linked["email"], "created_at": now,
            "updated_at": now, "created_by": user["id"],
        })
    except Exception as exc:
        logger.warning("MDA generation on admin create-account failed: %s", exc)


async def create_label_account(
    *, label_id: str, email: str, pic_name: Optional[str], whatsapp: Optional[str],
    password: Optional[str], user: dict,
) -> dict:
    _require_role(user, ACCOUNT_ADMIN_ROLES, "Hanya Super Admin / Release / Support")
    label = await _get_label(label_id)
    if label.get("user_id"):
        raise HTTPException(status_code=400, detail="Label ini sudah punya akun user")
    email_clean = _normalize_email(email)
    if await db.users.find_one({"email": email_clean}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")
    plaintext = _account_password(password)
    user_id = new_id()
    pic = (pic_name or label.get("pic_name") or label.get("label_name") or "").strip() or "Label PIC"
    wa = (whatsapp or label.get("whatsapp") or "").strip()
    now = now_iso()
    await db.users.insert_one({
        "id": user_id, "name": pic, "email": email_clean,
        "password_hash": hash_password(plaintext), "role": "label",
        "email_verified_at": now, "status": "active", "token_version": 0,
        "created_at": now, "updated_at": now, "created_by_admin": user["id"],
    })
    linked = {**label, "user_id": user_id, "email": email_clean, "pic_name": pic, "whatsapp": wa or label.get("whatsapp")}
    await db.labels.update_one({"id": label_id}, {"$set": {
        "user_id": user_id, "email": email_clean, "pic_name": pic,
        "whatsapp": linked["whatsapp"], "account_status": "active",
        "mda_accepted_at": now, "updated_at": now,
    }})
    await _create_mda_for_account(label, linked, user, now)
    await log_activity(user["id"], "create_label_account", "label", label_id, after={
        "user_id": user_id, "email": email_clean, "label_name": label.get("label_name"),
    })
    return {
        "ok": True, "user_id": user_id, "email": email_clean,
        "password": plaintext, "label_id": label_id,
        "label_name": label.get("label_name"),
        "warning": "Password ini hanya ditampilkan SEKALI. Salin sekarang untuk dibagikan ke label.",
    }


async def _disable_users(user_ids: list[str], admin_id: str, reason: str) -> int:
    if not user_ids:
        return 0
    result = await db.users.update_many(
        {"id": {"$in": user_ids}},
        {"$set": {
            "status": "disabled", "disabled_at": now_iso(),
            "disabled_by": admin_id, "disabled_reason": reason,
            "updated_at": now_iso(),
        }, "$inc": {"token_version": 1}},
    )
    return result.modified_count


async def revoke_label_account(
    *, label_id: str, cascade_artists: bool, reason: str, user: dict,
) -> dict:
    _require_role(user, ACCOUNT_ADMIN_ROLES, "Hanya Super Admin / Support / Release")
    label = await _get_label(label_id)
    current_user_id = label.get("user_id")
    if not current_user_id:
        raise HTTPException(status_code=400, detail="Label ini belum punya akun user — gunakan 'Buat Akun' untuk membuat.")
    target = await db.users.find_one({"id": current_user_id}, {"_id": 0})
    if not target:
        await db.labels.update_one({"id": label_id}, {"$set": {
            "user_id": None, "account_status": "no_account", "updated_at": now_iso(),
        }})
        return {"ok": True, "label_id": label_id, "warning": "User account stale-reference dibersihkan."}
    await _disable_users([current_user_id], user["id"], reason or "Akses dicabut oleh admin")
    await db.labels.update_one({"id": label_id}, {"$set": {
        "user_id": None, "account_status": "no_account",
        "previous_account_email": target.get("email"),
        "previous_account_revoked_at": now_iso(), "updated_at": now_iso(),
    }})
    cascade_count = 0
    if cascade_artists:
        artists = await db.artists.find({"label_id": label_id}, {"_id": 0, "user_id": 1}).to_list(2000)
        cascade_count = await _disable_users(
            [artist["user_id"] for artist in artists if artist.get("user_id")],
            user["id"], "Cascade dari label revoke",
        )
    await log_activity(
        user["id"], "revoke_label_account", "label", label_id,
        before={"user_id": current_user_id, "email": target.get("email")},
        after={"cascade_artists": cascade_artists, "artists_disabled": cascade_count, "reason": reason},
    )
    return {
        "ok": True, "label_id": label_id, "label_name": label.get("label_name"),
        "revoked_email": target.get("email"), "artists_disabled": cascade_count,
        "next_step": "Akun bisa dibuat ulang dengan email baru via 'Buat Akun' di Label Management.",
    }


async def _send_email_change_notifications(
    *, old_email: str, new_email: str, label_name: str,
) -> Dict[str, bool]:
    safe_label = h(label_name)
    safe_old = h(old_email)
    safe_new = h(new_email)
    messages = {
        "old": (
            old_email, "Pemberitahuan: Email akun RILIS MUSIK Anda telah diubah",
            f"<p>Hai Tim {safe_label},</p><p>Email akun login Anda di <b>RILIS MUSIK</b> baru saja diubah "
            f"dari <b>{safe_old}</b> menjadi <b>{safe_new}</b> oleh admin.</p>"
            "<p>Jika ini bukan Anda, segera hubungi tim support RILIS MUSIK.</p>",
        ),
        "new": (
            new_email, "Selamat datang — email baru terhubung ke akun RILIS MUSIK",
            f"<p>Hai Tim {safe_label},</p><p>Akun RILIS MUSIK Anda kini terhubung dengan email "
            f"<b>{safe_new}</b>.</p><p>Silakan login menggunakan email ini. Password tidak berubah.</p>",
        ),
    }
    sent = {"old": False, "new": False}
    for key, (recipient, subject, html) in messages.items():
        try:
            await send_email(to=recipient, subject=subject, html=html)
            sent[key] = True
        except Exception as exc:
            logger.warning("[CHANGE-EMAIL] notify %s failed: %s", key, exc)
    return sent


async def change_label_email(
    *, label_id: str, new_email: str, send_notification: bool, user: dict,
) -> dict:
    _require_role(user, ACCOUNT_ADMIN_ROLES, "Hanya Super Admin / Support / Release")
    label = await _get_label(label_id)
    current_user_id = label.get("user_id")
    if not current_user_id:
        raise HTTPException(status_code=400, detail="Label belum punya akun — gunakan 'Buat Akun' dulu.")
    normalized = _normalize_email(new_email, field_name="Email baru")
    existing = await db.users.find_one({"email": normalized}, {"_id": 0, "id": 1})
    if existing and existing.get("id") != current_user_id:
        raise HTTPException(status_code=409, detail="Email ini sudah dipakai akun lain")
    target = await db.users.find_one({"id": current_user_id}, {"_id": 0})
    if not target:
        raise HTTPException(status_code=404, detail="User account tidak ditemukan (stale ref)")
    old_email = target.get("email")
    if old_email == normalized:
        raise HTTPException(status_code=400, detail="Email baru sama dengan email lama")
    await db.users.update_one({"id": current_user_id}, {
        "$set": {"email": normalized, "email_changed_at": now_iso(), "email_changed_by": user["id"], "updated_at": now_iso()},
        "$inc": {"token_version": 1},
    })
    await db.labels.update_one({"id": label_id}, {"$set": {"email": normalized, "updated_at": now_iso()}})
    notifications = {"old": False, "new": False}
    if send_notification:
        notifications = await _send_email_change_notifications(
            old_email=old_email, new_email=normalized,
            label_name=label.get("label_name", "label Anda"),
        )
    await log_activity(
        user["id"], "change_label_email", "label", label_id,
        before={"email": old_email}, after={"email": normalized, "notify_sent": notifications},
    )
    return {
        "ok": True, "label_id": label_id, "old_email": old_email,
        "new_email": normalized, "notify_sent": notifications,
        "warning": "Semua sesi login lama akan terputus. Label harus login ulang.",
    }