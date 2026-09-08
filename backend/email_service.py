"""SMTP email service for RILIS MUSIK (Hostinger).

All transactional emails (verification, reset, contract warnings, invoices)
are routed through `send_email()`. Uses standard library `smtplib.SMTP_SSL`
on port 465, wrapped with `asyncio.to_thread` to keep FastAPI's event loop
non-blocking.

Sender mailbox and provider settings come exclusively from backend environment variables.
"""
import os
import ssl
import asyncio
import logging
import smtplib
from html import escape as _html_escape
from email.message import EmailMessage
from typing import Optional

logger = logging.getLogger("rilismusik")


def h(s) -> str:
    """SEC-004: HTML-escape user-controlled values before interpolating into the
    HTML email body. Always use this around `pic_name`, `label_name`, `description`,
    `bank_name`, `account_number`, etc.
    """
    return _html_escape("" if s is None else str(s), quote=True)


SMTP_HOST = os.environ["SMTP_HOST"]
SMTP_PORT = int(os.environ["SMTP_PORT"])
SMTP_USER = os.environ["SMTP_USER"]
SMTP_PASSWORD = os.environ["SMTP_PASSWORD"]
SENDER_EMAIL = os.environ["SENDER_EMAIL"]
SENDER_NAME = os.environ["SENDER_NAME"]
FRONTEND_URL = os.environ["FRONTEND_URL"].rstrip("/")


def _from_header() -> str:
    return f"{SENDER_NAME} <{SENDER_EMAIL}>"


def _smtp_send_sync(*, to: str, subject: str, html: str, attachments: Optional[list] = None) -> str:
    """Synchronous SMTP send. Called from a worker thread via asyncio.to_thread.
    Returns the SMTP message-id on success; raises on failure.
    `attachments`: list of dicts {filename, content(bytes), maintype, subtype}.
    """
    msg = EmailMessage()
    msg["From"] = _from_header()
    msg["To"] = to
    msg["Subject"] = subject
    # Plain-text fallback for clients that don't render HTML
    plain_fallback = "Email ini dirancang untuk klien HTML. Buka di browser modern atau Gmail/Outlook untuk tampilan terbaik."
    msg.set_content(plain_fallback)
    msg.add_alternative(html, subtype="html")

    for att in (attachments or []):
        msg.add_attachment(
            att["content"], maintype=att.get("maintype", "application"),
            subtype=att.get("subtype", "octet-stream"), filename=att["filename"],
        )

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30) as server:
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
    return msg["Message-ID"] or "sent"


# ---------- Shared HTML wrapper ----------
def _wrap(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None) -> str:
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <tr><td align="center" style="padding:24px 0;">
          <a href="{cta_url}" style="display:inline-block;padding:14px 28px;background:#a855f7;color:#fff;font-weight:700;text-decoration:none;border-radius:999px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:14px;">{cta_label}</a>
        </td></tr>
        """
    return f"""
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#0a0a0a;font-family:'Helvetica Neue',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:32px 16px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#141414;border-radius:24px;overflow:hidden;border:1px solid #262626;">
            <tr><td style="padding:32px 32px 0 32px;">
              <div style="font-family:'Helvetica Neue',Arial,sans-serif;font-size:13px;letter-spacing:3px;text-transform:uppercase;color:#a855f7;font-weight:800;">RILIS MUSIK</div>
              <h1 style="margin:8px 0 0 0;color:#fff;font-size:28px;font-weight:800;line-height:1.2;letter-spacing:-0.5px;">{title}</h1>
            </td></tr>
            <tr><td style="padding:24px 32px;color:#d4d4d8;font-size:15px;line-height:1.6;">
              {body_html}
            </td></tr>
            {cta_block}
            <tr><td style="padding:24px 32px;border-top:1px solid #262626;color:#71717a;font-size:11px;line-height:1.5;">
              <strong style="color:#a1a1aa;">PT. Jeeres Group Indonesia</strong><br/>
              Jl. Sintang Pontianak RT 12 / RW 5, Kec. Sintang, Sintang 78614, Indonesia<br/>
              NIB 2202260059749 · WA 085864137150
              <div style="margin-top:12px;color:#52525b;">Email otomatis — jangon balas. Hubungi support via dashboard untuk bantuan.</div>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """


# ---------- Low-level send ----------
async def send_email(*, to: str, subject: str, html: str, attachments: Optional[list] = None) -> Optional[str]:
    """Send an email via Hostinger SMTP. Returns the message-id on success,
    None on failure. Never raises — failure is logged and ignored so callers
    can treat email as best-effort (transactional flows continue to work).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("[EMAIL] SMTP credentials not set — skipping email to %s (%s)", to, subject)
        return None
    try:
        message_id = await asyncio.to_thread(_smtp_send_sync, to=to, subject=subject, html=html, attachments=attachments)
        logger.info("[EMAIL] sent to=%s subject=%r id=%s", to, subject, message_id)
        return message_id
    except Exception as e:
        logger.exception("[EMAIL] failed to=%s subject=%r err=%s", to, subject, e)
        return None


# ---------- Domain-specific helpers ----------
async def send_verification_email(*, to: str, pic_name: str, token: str, base_url: Optional[str] = None) -> Optional[str]:
    verify_url = f"{(base_url or FRONTEND_URL).rstrip('/')}/verify-email?token={token}"
    body = f"""
    <p>Halo <strong>{h(pic_name)}</strong>,</p>
    <p>Terima kasih sudah mendaftar di RILIS MUSIK. Untuk mengaktifkan akun Anda, klik tombol di bawah:</p>
    <p style="color:#a1a1aa;font-size:13px;">Link verifikasi berlaku 24 jam. Jika Anda tidak mendaftar, abaikan email ini.</p>
    """
    html = _wrap("Verifikasi email Anda", body, "Verifikasi Email", verify_url)
    return await send_email(to=to, subject="Verifikasi email RILIS MUSIK", html=html)


async def send_password_reset_email(*, to: str, token: str, base_url: Optional[str] = None) -> Optional[str]:
    reset_url = f"{(base_url or FRONTEND_URL).rstrip('/')}/reset-password?token={token}"
    body = (
        "<p>Halo,</p>"
        "<p>Kami menerima permintaan reset password untuk akun ini. Klik tombol berikut untuk mengatur password baru:</p>"
        "<p style=\"color:#a1a1aa;font-size:13px;\">Link berlaku 1 jam. Jika Anda tidak meminta reset, abaikan email ini — password lama tetap aman.</p>"
    )
    html = _wrap("Reset Password", body, "Reset Password", reset_url)
    return await send_email(to=to, subject="Reset password RILIS MUSIK", html=html)


async def send_claim_approved_email(*, to: str, pic_name: str, label_name: str) -> Optional[str]:
    body = f"""
    <p>Halo <strong>{h(pic_name)}</strong>,</p>
    <p>Kabar baik! Permintaan klaim akun lama Anda telah <strong style="color:#10b981;">disetujui</strong>. Akun Anda kini terhubung dengan label <strong>{h(label_name)}</strong> beserta seluruh riwayat data (royalti, penarikan, dan rilisan).</p>
    <p style="color:#a1a1aa;font-size:13px;">Akun Anda juga otomatis terverifikasi. Silakan buka dashboard untuk melihat data Anda.</p>
    """
    html = _wrap("Klaim akun disetujui", body, "Buka Dashboard", f"{FRONTEND_URL}/label/dashboard")
    return await send_email(to=to, subject=f"Klaim akun disetujui — {h(label_name)}", html=html)


async def send_claim_rejected_email(*, to: str, pic_name: str, legacy_label_name: str, reason: str) -> Optional[str]:
    reason_text = (reason or "").strip() or "Tidak ada keterangan."
    body = f"""
    <p>Halo <strong>{h(pic_name)}</strong>,</p>
    <p>Mohon maaf, permintaan klaim akun lama Anda untuk label <strong>{h(legacy_label_name)}</strong> <strong style="color:#f87171;">belum dapat kami setujui</strong> saat ini.</p>
    <p style="margin-top:12px;background:#0a0a0a;padding:12px 16px;border-radius:12px;color:#fbbf24;"><strong>Alasan:</strong> {h(reason_text)}</p>
    <p style="color:#a1a1aa;font-size:13px;">Anda dapat mengajukan ulang dengan nama label yang benar melalui menu Profil &amp; Rekening, atau hubungi support untuk bantuan lebih lanjut.</p>
    """
    html = _wrap("Klaim akun ditolak", body, "Hubungi Support", f"{FRONTEND_URL}/label/support")
    return await send_email(to=to, subject="Permintaan klaim akun ditolak", html=html)


async def send_artist_royalty_report_email(*, to: str, artist_name: str, label_name: str, period: Optional[str], xlsx_bytes: bytes, filename: str) -> Optional[str]:
    periode_txt = period or "semua periode"
    body = f"""
    <p>Halo <strong>{h(artist_name)}</strong>,</p>
    <p>Berikut laporan royalti Anda dari label <strong>{h(label_name)}</strong> untuk <strong>{h(periode_txt)}</strong>, terlampir dalam berkas Excel.</p>
    <p style="color:#a1a1aa;font-size:13px;">Laporan berisi rincian per platform, negara, dan track. Royalti legacy tidak termasuk dalam laporan ini.</p>
    <p style="color:#a1a1aa;font-size:13px;">Jika ada pertanyaan, silakan hubungi label Anda.</p>
    """
    html = _wrap(f"Laporan Royalti — {periode_txt}", body)
    return await send_email(
        to=to, subject=f"Laporan Royalti {h(artist_name)} — {periode_txt}", html=html,
        attachments=[{
            "filename": filename, "content": xlsx_bytes,
            "maintype": "application",
            "subtype": "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }],
    )


async def send_contract_expiry_email(*, to: str, label_name: str, days_left: int, end_date: str) -> Optional[str]:
    body = f"""
    <p>Halo <strong>{h(label_name)}</strong>,</p>
    <p>Kontrak distribusi Anda akan berakhir dalam <strong style="color:#f59e0b;">{int(days_left)} hari</strong> (tanggal <strong>{h(end_date)}</strong>).</p>
    <p>Silakan hubungi admin via support ticket untuk perpanjangan kontrak agar distribusi tidak terhenti.</p>
    """
    html = _wrap(
        f"Kontrak berakhir dalam {int(days_left)} hari", body,
        "Buka Dashboard Kontrak", f"{FRONTEND_URL}/label/contract",
    )
    return await send_email(to=to, subject=f"⏰ Kontrak distribusi berakhir {int(days_left)} hari lagi", html=html)


async def send_subscription_expiry_email(*, to: str, label_name: str, days_left: int) -> Optional[str]:
    body = f"""
    <p>Halo <strong>{h(label_name)}</strong>,</p>
    <p>Subscription tahunan Anda akan berakhir dalam <strong style="color:#f59e0b;">{int(days_left)} hari</strong>. Perpanjang sekarang untuk tetap upload rilisan tanpa biaya per release.</p>
    """
    html = _wrap(
        f"Subscription berakhir dalam {int(days_left)} hari", body,
        "Perpanjang Sekarang", f"{FRONTEND_URL}/label/invoices",
    )
    return await send_email(to=to, subject=f"⏰ Subscription berakhir {int(days_left)} hari lagi", html=html)


def build_payment_receipt_email(*, label_name: str, description: str, amount_idr: int, invoice_id: str) -> tuple[str, str]:
    amt = f"Rp {amount_idr:,}".replace(",", ".")
    body = f"""
    <p>Halo <strong>{h(label_name)}</strong>,</p>
    <p>Pembayaran Anda telah <strong style="color:#10b981;">berhasil diterima</strong>.</p>
    <table style="margin-top:16px;width:100%;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Invoice ID</td><td style="text-align:right;color:#fff;font-family:monospace;font-size:12px;">{h(invoice_id)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;font-size:13px;">Deskripsi</td><td style="text-align:right;color:#fff;">{h(description)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;font-size:13px;border-top:1px solid #262626;">Total</td><td style="text-align:right;color:#10b981;font-weight:800;font-size:18px;border-top:1px solid #262626;">{amt}</td></tr>
    </table>
    """
    html = _wrap(
        "Pembayaran berhasil", body,
        "Lihat Invoice", f"{FRONTEND_URL}/label/invoices",
    )
    return f"Pembayaran diterima — {h(description)}", html


def build_admin_paid_payment_email(
    *, label_name: str, description: str, amount_idr: int, invoice_id: str,
    payment_type: str, paid_at: str, instruction: str,
) -> tuple[str, str]:
    amt = f"Rp {amount_idr:,}".replace(",", ".")
    body = f"""
    <p>Pembayaran baru dari <strong>{h(label_name)}</strong> telah dikonfirmasi.</p>
    <table style="margin-top:16px;width:100%;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#a1a1aa;">Invoice</td><td style="text-align:right;color:#fff;font-family:monospace;font-size:12px;">{h(invoice_id)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;">Layanan</td><td style="text-align:right;color:#fff;">{h(description)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;">Tipe</td><td style="text-align:right;color:#fff;">{h(payment_type)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;">Waktu bayar</td><td style="text-align:right;color:#fff;">{h(paid_at)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;border-top:1px solid #262626;">Total</td><td style="text-align:right;color:#10b981;font-weight:800;font-size:18px;border-top:1px solid #262626;">{amt}</td></tr>
    </table>
    <p style="margin-top:20px;background:#0a0a0a;padding:12px 16px;border-radius:12px;color:#fbbf24;"><strong>Tindakan admin:</strong> {h(instruction)}</p>
    """
    html = _wrap("Pembayaran baru diterima", body, "Buka Pembayaran", f"{FRONTEND_URL}/admin/payments?payment_id={h(invoice_id)}")
    return f"Pembayaran baru — {h(label_name)} — {amt}", html


async def send_payment_receipt_email(*, to: str, label_name: str, description: str, amount_idr: int, invoice_id: str) -> Optional[str]:
    subject, html = build_payment_receipt_email(
        label_name=label_name, description=description, amount_idr=amount_idr, invoice_id=invoice_id,
    )
    return await send_email(to=to, subject=subject, html=html)


async def send_admin_paid_payment_email(
    *, to: str, label_name: str, description: str, amount_idr: int,
    invoice_id: str, payment_type: str, paid_at: str, instruction: str,
) -> Optional[str]:
    subject, html = build_admin_paid_payment_email(
        label_name=label_name, description=description, amount_idr=amount_idr,
        invoice_id=invoice_id, payment_type=payment_type, paid_at=paid_at,
        instruction=instruction,
    )
    return await send_email(to=to, subject=subject, html=html)


async def send_withdraw_paid_email(*, to: str, label_name: str, amount_idr: int, bank_name: str, account_number: str) -> Optional[str]:
    amt = f"Rp {amount_idr:,}".replace(",", ".")
    body = f"""
    <p>Halo <strong>{h(label_name)}</strong>,</p>
    <p>Penarikan dana Anda sebesar <strong style="color:#10b981;">{amt}</strong> sudah <strong>ditransfer</strong> ke rekening:</p>
    <p style="background:#0a0a0a;padding:12px 16px;border-radius:12px;color:#d4d4d8;font-family:monospace;font-size:13px;">{h(bank_name)} · {h(account_number)}</p>
    <p style="color:#a1a1aa;font-size:13px;">Dana biasanya masuk dalam 1×24 jam. Hubungi support jika belum diterima.</p>
    """
    html = _wrap(
        "Penarikan berhasil ditransfer", body,
        "Lihat Riwayat", f"{FRONTEND_URL}/label/withdraw",
    )
    return await send_email(to=to, subject=f"Penarikan {amt} ditransfer", html=html)


async def send_release_submission_email(*, to: str, label_name: str, release_title: str, release_id: str) -> Optional[str]:
    body = f"""
    <p>Rilisan baru dari <strong>{h(label_name)}</strong> telah masuk untuk ditinjau.</p>
    <table style="margin-top:16px;width:100%;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#a1a1aa;">Judul</td><td style="text-align:right;color:#fff;font-weight:700;">{h(release_title)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;">Release ID</td><td style="text-align:right;color:#fff;font-family:monospace;font-size:12px;">{h(release_id)}</td></tr>
    </table>
    """
    html = _wrap("Rilisan baru menunggu review", body, "Buka Release Management", f"{FRONTEND_URL}/admin/releases/{release_id}")
    return await send_email(to=to, subject=f"Rilisan baru — {h(release_title)}", html=html)


async def send_release_invoice_email(
    *, to: str, label_name: str, release_title: str, amount_idr: int,
    payment_id: str, release_id: str,
) -> Optional[str]:
    amount = f"Rp {int(amount_idr):,}".replace(",", ".")
    body = f"""
    <p>Halo <strong>{h(label_name)}</strong>,</p>
    <p>Metadata rilisan <strong>{h(release_title)}</strong> telah valid. Invoice Pay Per Release sudah tersedia.</p>
    <table style="margin-top:16px;width:100%;border-collapse:collapse;">
      <tr><td style="padding:8px 0;color:#a1a1aa;">Invoice</td><td style="text-align:right;color:#fff;font-family:monospace;">{h(payment_id)}</td></tr>
      <tr><td style="padding:8px 0;color:#a1a1aa;border-top:1px solid #262626;">Total</td><td style="text-align:right;color:#10b981;font-size:18px;font-weight:800;border-top:1px solid #262626;">{amount}</td></tr>
    </table>
    <p style="color:#a1a1aa;font-size:13px;">Buka detail rilisan untuk melihat rincian layanan dan melanjutkan pembayaran melalui Xendit.</p>
    """
    html = _wrap("Invoice rilisan tersedia", body, "Buka Rilisan", f"{FRONTEND_URL}/label/releases/{release_id}")
    return await send_email(to=to, subject=f"Invoice tersedia — {h(release_title)}", html=html)


async def send_monthly_royalty_summary_email(
    *, to: str, label_name: str, period: str, total_idr: int, streams: int, top_tracks: list[dict],
) -> Optional[str]:
    amount = f"Rp {int(total_idr):,}".replace(",", ".")
    stream_text = f"{int(streams):,}".replace(",", ".")
    track_rows = "".join(
        f'<tr><td style="padding:7px 0;color:#d4d4d8;">{h(item.get("title") or "Unknown")}</td>'
        f'<td style="padding:7px 0;text-align:right;color:#a1a1aa;">{int(item.get("streams") or 0):,} stream</td></tr>'
        for item in top_tracks
    ) or '<tr><td style="padding:7px 0;color:#a1a1aa;">Belum ada data track.</td></tr>'
    body = f"""
    <p>Halo <strong>{h(label_name)}</strong>,</p>
    <p>Berikut ringkasan royalti untuk periode <strong>{h(period)}</strong>.</p>
    <table style="margin:16px 0;width:100%;border-collapse:collapse;">
      <tr><td style="padding:10px;background:#0a0a0a;color:#a1a1aa;">Pendapatan</td><td style="padding:10px;background:#0a0a0a;text-align:right;color:#10b981;font-weight:800;">{amount}</td></tr>
      <tr><td style="padding:10px;background:#0a0a0a;color:#a1a1aa;">Total Stream</td><td style="padding:10px;background:#0a0a0a;text-align:right;color:#fff;font-weight:800;">{stream_text}</td></tr>
    </table>
    <p style="font-weight:700;color:#fff;">Top Track</p><table style="width:100%;border-collapse:collapse;">{track_rows}</table>
    """
    html = _wrap("Ringkasan Royalti Bulanan", body, "Buka Analytics", f"{FRONTEND_URL}/label/royalty")
    return await send_email(to=to, subject=f"Ringkasan royalti {period} — {h(label_name)}", html=html)
