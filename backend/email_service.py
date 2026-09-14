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
from datetime import datetime
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


EMAIL_LOGO_URL = f"{FRONTEND_URL}/brand/email-logo.png"
EMAIL_CLOCK_URL = f"{FRONTEND_URL}/brand/email-clock.png"


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


# ---------- Shared HTML wrapper (light theme) ----------
def _wrap(title: str, body_html: str, cta_label: Optional[str] = None, cta_url: Optional[str] = None,
          badge_html: Optional[str] = None) -> str:
    year = datetime.now().year
    badge_block = f'<div style="margin:0 0 16px 0;">{badge_html}</div>' if badge_html else ""
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <tr><td style="padding:8px 36px 4px 36px;">
          <a href="{cta_url}" style="display:block;text-align:center;padding:17px 24px;background:#a855f7;background-image:linear-gradient(90deg,#7c3aed,#ec4899);color:#ffffff;font-weight:800;text-decoration:none;border-radius:16px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;letter-spacing:0.2px;">{cta_label}</a>
        </td></tr>
        """
    return f"""
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#eef0f3;font-family:'Helvetica Neue',Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#eef0f3;padding:28px 14px;">
        <tr><td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:28px;overflow:hidden;border:1px solid #e6e7eb;">
            <!-- Header -->
            <tr><td style="padding:30px 36px 20px 36px;border-bottom:1px solid #edeef1;">
              <table width="100%" cellpadding="0" cellspacing="0"><tr>
                <td valign="middle" style="white-space:nowrap;">
                  <img src="{EMAIL_LOGO_URL}" alt="RM" width="44" height="44" style="width:44px;height:44px;border-radius:12px;vertical-align:middle;display:inline-block;border:0;" />
                  <span style="display:inline-block;vertical-align:middle;margin-left:12px;color:#111114;font-size:21px;font-weight:800;letter-spacing:1px;">RILIS MUSIK</span>
                </td>
                <td valign="middle" align="right" style="color:#a1a1aa;font-size:14px;white-space:nowrap;">
                  <span style="color:#d4d4d8;">|</span>&nbsp;&nbsp;Musik Tanpa Batas
                </td>
              </tr></table>
            </td></tr>
            <!-- Title + body -->
            <tr><td style="padding:30px 36px 8px 36px;">
              {badge_block}
              <h1 style="margin:0;color:#0f1012;font-size:34px;font-weight:800;line-height:1.15;letter-spacing:-0.8px;">{title}</h1>
            </td></tr>
            <tr><td style="padding:16px 36px 8px 36px;color:#3f3f46;font-size:16px;line-height:1.65;">
              {body_html}
            </td></tr>
            {cta_block}
            <!-- Footer -->
            <tr><td style="padding:26px 36px 30px 36px;border-top:1px solid #edeef1;color:#a1a1aa;font-size:12px;line-height:1.6;">
              <div style="color:#52525b;font-weight:700;font-size:13px;">PT. Jeeres Group Indonesia</div>
              <div style="margin-top:2px;color:#a1a1aa;">&copy; {year} RILIS MUSIK</div>
              <div style="margin-top:12px;color:#c4c4cc;font-size:11px;">
                Jl. Sintang Pontianak RT 12 / RW 5, Kec. Sintang, Sintang 78614 &middot; NIB 2202260059749 &middot; WA 085864137150<br/>
                Email otomatis &mdash; jangan balas. Hubungi support via dashboard untuk bantuan.
              </div>
            </td></tr>
          </table>
        </td></tr>
      </table>
    </body></html>
    """


def _badge(label: str, dot_color: str = "#059669", bg: str = "#e7f6ee", text: str = "#047857") -> str:
    return (
        f'<span style="display:inline-block;padding:8px 16px;background:{bg};border-radius:999px;'
        f'color:{text};font-size:12px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:999px;background:{dot_color};'
        f'vertical-align:middle;margin-right:8px;"></span>{h(label)}</span>'
    )


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
    <p style="margin:0 0 14px 0;">Halo <strong>{h(pic_name)}</strong>,</p>
    <p style="margin:0 0 14px 0;">Terima kasih sudah mendaftar di RILIS MUSIK. Untuk mengaktifkan akun Anda, klik tombol di bawah:</p>
    <p style="margin:0;color:#71717a;font-size:13px;">Link verifikasi berlaku 24 jam. Jika Anda tidak mendaftar, abaikan email ini.</p>
    """
    html = _wrap("Verifikasi email Anda", body, "Verifikasi Email", verify_url)
    return await send_email(to=to, subject="Verifikasi email RILIS MUSIK", html=html)


async def send_password_reset_email(*, to: str, token: str, base_url: Optional[str] = None) -> Optional[str]:
    reset_url = f"{(base_url or FRONTEND_URL).rstrip('/')}/reset-password?token={token}"
    body = (
        '<p style="margin:0 0 14px 0;">Halo,</p>'
        '<p style="margin:0 0 14px 0;">Kami menerima permintaan reset password untuk akun ini. Klik tombol berikut untuk mengatur password baru:</p>'
        '<p style="margin:0;color:#71717a;font-size:13px;">Link berlaku 1 jam. Jika Anda tidak meminta reset, abaikan email ini — password lama tetap aman.</p>'
    )
    html = _wrap("Reset Password", body, "Reset Password", reset_url)
    return await send_email(to=to, subject="Reset password RILIS MUSIK", html=html)


async def send_claim_approved_email(*, to: str, pic_name: str, label_name: str) -> Optional[str]:
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(pic_name)}</strong>,</p>
    <p style="margin:0 0 14px 0;">Kabar baik! Permintaan klaim akun lama Anda telah <strong style="color:#059669;">disetujui</strong>. Akun Anda kini terhubung dengan label <strong>{h(label_name)}</strong> beserta seluruh riwayat data (royalti, penarikan, dan rilisan).</p>
    <p style="margin:0;color:#71717a;font-size:13px;">Akun Anda juga otomatis terverifikasi. Silakan buka dashboard untuk melihat data Anda.</p>
    """
    html = _wrap("Klaim akun disetujui", body, "Buka Dashboard", f"{FRONTEND_URL}/label/dashboard")
    return await send_email(to=to, subject=f"Klaim akun disetujui — {h(label_name)}", html=html)


async def send_claim_rejected_email(*, to: str, pic_name: str, legacy_label_name: str, reason: str) -> Optional[str]:
    reason_text = (reason or "").strip() or "Tidak ada keterangan."
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(pic_name)}</strong>,</p>
    <p style="margin:0 0 14px 0;">Mohon maaf, permintaan klaim akun lama Anda untuk label <strong>{h(legacy_label_name)}</strong> <strong style="color:#dc2626;">belum dapat kami setujui</strong> saat ini.</p>
    <p style="margin:0 0 14px 0;background:#fef3f2;padding:14px 18px;border-radius:14px;color:#b45309;"><strong>Alasan:</strong> {h(reason_text)}</p>
    <p style="margin:0;color:#71717a;font-size:13px;">Anda dapat mengajukan ulang dengan nama label yang benar melalui menu Profil &amp; Rekening, atau hubungi support untuk bantuan lebih lanjut.</p>
    """
    html = _wrap("Klaim akun ditolak", body, "Hubungi Support", f"{FRONTEND_URL}/label/support")
    return await send_email(to=to, subject="Permintaan klaim akun ditolak", html=html)


async def send_artist_royalty_report_email(*, to: str, artist_name: str, label_name: str, period: Optional[str], xlsx_bytes: bytes, filename: str) -> Optional[str]:
    periode_txt = period or "semua periode"
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(artist_name)}</strong>,</p>
    <p style="margin:0 0 14px 0;">Berikut laporan royalti Anda dari label <strong>{h(label_name)}</strong> untuk <strong>{h(periode_txt)}</strong>, terlampir dalam berkas Excel.</p>
    <p style="margin:0 0 6px 0;color:#71717a;font-size:13px;">Laporan berisi rincian per platform, negara, dan track. Royalti legacy tidak termasuk dalam laporan ini.</p>
    <p style="margin:0;color:#71717a;font-size:13px;">Jika ada pertanyaan, silakan hubungi label Anda.</p>
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
    <p style="margin:0 0 14px 0;">Halo <strong>{h(label_name)}</strong>,</p>
    <p style="margin:0 0 14px 0;">Kontrak distribusi Anda akan berakhir dalam <strong style="color:#d97706;">{int(days_left)} hari</strong> (tanggal <strong>{h(end_date)}</strong>).</p>
    <p style="margin:0;">Silakan hubungi admin via support ticket untuk perpanjangan kontrak agar distribusi tidak terhenti.</p>
    """
    html = _wrap(
        f"Kontrak berakhir dalam {int(days_left)} hari", body,
        "Buka Dashboard Kontrak", f"{FRONTEND_URL}/label/contract",
    )
    return await send_email(to=to, subject=f"⏰ Kontrak distribusi berakhir {int(days_left)} hari lagi", html=html)


async def send_subscription_expiry_email(*, to: str, label_name: str, days_left: int) -> Optional[str]:
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(label_name)}</strong>,</p>
    <p style="margin:0;">Subscription tahunan Anda akan berakhir dalam <strong style="color:#d97706;">{int(days_left)} hari</strong>. Perpanjang sekarang untuk tetap upload rilisan tanpa biaya per release.</p>
    """
    html = _wrap(
        f"Subscription berakhir dalam {int(days_left)} hari", body,
        "Perpanjang Sekarang", f"{FRONTEND_URL}/label/invoices",
    )
    return await send_email(to=to, subject=f"⏰ Subscription berakhir {int(days_left)} hari lagi", html=html)


def _kv_table(rows: list[tuple[str, str, str]]) -> str:
    """rows: list of (label, value_html, value_style_extra)."""
    trs = ""
    last = len(rows) - 1
    for i, (label, value, extra) in enumerate(rows):
        border = "border-top:1px solid #edeef1;" if i == last and len(rows) > 1 else ""
        trs += (
            f'<tr><td style="padding:9px 0;color:#71717a;font-size:14px;{border}">{label}</td>'
            f'<td style="padding:9px 0;text-align:right;color:#18181b;{extra}{border}">{value}</td></tr>'
        )
    return f'<table style="margin-top:16px;width:100%;border-collapse:collapse;">{trs}</table>'


def build_payment_receipt_email(*, label_name: str, description: str, amount_idr: int, invoice_id: str) -> tuple[str, str]:
    amt = f"Rp {amount_idr:,}".replace(",", ".")
    table = _kv_table([
        ("Invoice ID", f'<span style="font-family:monospace;font-size:12px;">{h(invoice_id)}</span>', ""),
        ("Deskripsi", h(description), ""),
        ("Total", amt, "color:#059669;font-weight:800;font-size:18px;"),
    ])
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(label_name)}</strong>,</p>
    <p style="margin:0;">Pembayaran Anda telah <strong style="color:#059669;">berhasil diterima</strong>.</p>
    {table}
    """
    html = _wrap("Pembayaran berhasil", body, "Lihat Invoice", f"{FRONTEND_URL}/label/invoices")
    return f"Pembayaran diterima — {h(description)}", html


def build_admin_paid_payment_email(
    *, label_name: str, description: str, amount_idr: int, invoice_id: str,
    payment_type: str, paid_at: str, instruction: str,
) -> tuple[str, str]:
    amt = f"Rp {amount_idr:,}".replace(",", ".")
    table = _kv_table([
        ("Invoice", f'<span style="font-family:monospace;font-size:12px;">{h(invoice_id)}</span>', ""),
        ("Layanan", h(description), ""),
        ("Tipe", h(payment_type), ""),
        ("Waktu bayar", h(paid_at), ""),
        ("Total", amt, "color:#059669;font-weight:800;font-size:18px;"),
    ])
    body = f"""
    <p style="margin:0;">Pembayaran baru dari <strong>{h(label_name)}</strong> telah dikonfirmasi.</p>
    {table}
    <p style="margin:20px 0 0 0;background:#f5f3ff;padding:14px 18px;border-radius:14px;color:#6d28d9;"><strong>Tindakan admin:</strong> {h(instruction)}</p>
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
    <p style="margin:0 0 14px 0;">Halo <strong>{h(label_name)}</strong>,</p>
    <p style="margin:0 0 14px 0;">Penarikan dana Anda sebesar <strong style="color:#059669;">{amt}</strong> sudah <strong>ditransfer</strong> ke rekening:</p>
    <p style="margin:0 0 14px 0;background:#f4f4f6;padding:14px 18px;border-radius:14px;color:#3f3f46;font-family:monospace;font-size:13px;">{h(bank_name)} · {h(account_number)}</p>
    <p style="margin:0;color:#71717a;font-size:13px;">Dana biasanya masuk dalam 1×24 jam. Hubungi support jika belum diterima.</p>
    """
    html = _wrap("Penarikan berhasil ditransfer", body, "Lihat Riwayat", f"{FRONTEND_URL}/label/withdraw")
    return await send_email(to=to, subject=f"Penarikan {amt} ditransfer", html=html)


async def send_release_submission_email(*, to: str, label_name: str, release_title: str, release_id: str) -> Optional[str]:
    table = _kv_table([
        ("Judul", h(release_title), "font-weight:700;"),
        ("Release ID", f'<span style="font-family:monospace;font-size:12px;">{h(release_id)}</span>', ""),
    ])
    body = f"""
    <p style="margin:0;">Rilisan baru dari <strong>{h(label_name)}</strong> telah masuk untuk ditinjau.</p>
    {table}
    """
    html = _wrap("Rilisan baru menunggu review", body, "Buka Release Management", f"{FRONTEND_URL}/admin/releases/{release_id}")
    return await send_email(to=to, subject=f"Rilisan baru — {h(release_title)}", html=html)


async def send_release_invoice_email(
    *, to: str, label_name: str, release_title: str, amount_idr: int,
    payment_id: str, release_id: str,
) -> Optional[str]:
    amount = f"Rp {int(amount_idr):,}".replace(",", ".")
    table = _kv_table([
        ("Invoice", f'<span style="font-family:monospace;">{h(payment_id)}</span>', ""),
        ("Total", amount, "color:#059669;font-size:18px;font-weight:800;"),
    ])
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(label_name)}</strong>,</p>
    <p style="margin:0;">Metadata rilisan <strong>{h(release_title)}</strong> telah valid. Invoice Pay Per Release sudah tersedia.</p>
    {table}
    <p style="margin:16px 0 0 0;color:#71717a;font-size:13px;">Buka detail rilisan untuk melihat rincian layanan dan melanjutkan pembayaran melalui Xendit.</p>
    """
    html = _wrap("Invoice rilisan tersedia", body, "Buka Rilisan", f"{FRONTEND_URL}/label/releases/{release_id}")
    return await send_email(to=to, subject=f"Invoice tersedia — {h(release_title)}", html=html)


async def send_monthly_royalty_summary_email(
    *, to: str, label_name: str, period: str, total_idr: int, streams: int, top_tracks: list[dict],
) -> Optional[str]:
    amount = f"Rp {int(total_idr):,}".replace(",", ".")
    stream_text = f"{int(streams):,}".replace(",", ".")
    track_rows = "".join(
        f'<tr><td style="padding:8px 0;color:#3f3f46;border-top:1px solid #edeef1;">{h(item.get("title") or "Unknown")}</td>'
        f'<td style="padding:8px 0;text-align:right;color:#71717a;border-top:1px solid #edeef1;">{int(item.get("streams") or 0):,} stream</td></tr>'
        for item in top_tracks
    ) or '<tr><td style="padding:8px 0;color:#71717a;">Belum ada data track.</td></tr>'
    body = f"""
    <p style="margin:0 0 14px 0;">Halo <strong>{h(label_name)}</strong>,</p>
    <p style="margin:0;">Berikut ringkasan royalti untuk periode <strong>{h(period)}</strong>.</p>
    <table style="margin:16px 0;width:100%;border-collapse:collapse;">
      <tr><td style="padding:12px 14px;background:#f4f4f6;color:#71717a;border-radius:10px 0 0 10px;">Pendapatan</td><td style="padding:12px 14px;background:#f4f4f6;text-align:right;color:#059669;font-weight:800;border-radius:0 10px 10px 0;">{amount}</td></tr>
      <tr><td colspan="2" style="height:8px;"></td></tr>
      <tr><td style="padding:12px 14px;background:#f4f4f6;color:#71717a;border-radius:10px 0 0 10px;">Total Stream</td><td style="padding:12px 14px;background:#f4f4f6;text-align:right;color:#18181b;font-weight:800;border-radius:0 10px 10px 0;">{stream_text}</td></tr>
    </table>
    <p style="margin:0 0 4px 0;font-weight:700;color:#18181b;">Top Track</p><table style="width:100%;border-collapse:collapse;">{track_rows}</table>
    """
    html = _wrap("Ringkasan Royalti Bulanan", body, "Buka Analytics", f"{FRONTEND_URL}/label/royalty")
    return await send_email(to=to, subject=f"Ringkasan royalti {period} — {h(label_name)}", html=html)


def _abs_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{FRONTEND_URL}{url if url.startswith('/') else '/' + url}"


_ID_MONTHS = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


def _fmt_date_id(value: Optional[str]) -> Optional[str]:
    """Format an ISO date/datetime string to 'DD Month YYYY' (Indonesian)."""
    if not value:
        return None
    try:
        s = str(value).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
    except Exception:
        try:
            dt = datetime.strptime(str(value)[:10], "%Y-%m-%d")
        except Exception:
            return None
    return f"{dt.day} {_ID_MONTHS[dt.month]} {dt.year}"


async def send_release_live_email(
    *, to: str, label_name: str, release_title: str, artist_name: Optional[str],
    release_id: str, cover_url: Optional[str], release_date: Optional[str] = None,
) -> Optional[str]:
    """Celebratory 'your release is now live' email — light theme with clear hierarchy."""
    cover = _abs_url(cover_url)
    artist_txt = h(artist_name) if artist_name else "—"
    date_txt = _fmt_date_id(release_date)

    cover_cell = (
        f'<td width="92" valign="top" style="width:92px;">'
        f'<img src="{cover}" alt="{h(release_title)}" width="80" height="80" '
        f'style="width:80px;height:80px;border-radius:14px;object-fit:cover;display:block;border:1px solid #e6e7eb;" />'
        f'</td>'
    ) if cover else ""

    date_line = (
        f'<div style="color:#a1a1aa;font-size:14px;margin-top:3px;">{h(date_txt)}</div>' if date_txt else ""
    )

    body = f"""
    <p style="margin:0 0 22px 0;font-size:17px;line-height:1.55;color:#3f3f46;">
      Halo, <strong style="color:#18181b;">{h(label_name)}</strong>! Rilisan terbaru
      {('<strong style="color:#18181b;">' + artist_txt + '</strong>') if artist_name else ''} kini mulai tersedia di platform digital.
    </p>

    <!-- Release card -->
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f7;border-radius:20px;margin:0 0 8px 0;">
      <tr><td style="padding:18px 20px;">
        <table cellpadding="0" cellspacing="0"><tr>
          {cover_cell}
          <td valign="middle" style="padding-left:{'16' if cover else '0'}px;">
            <div style="color:#0f1012;font-size:19px;font-weight:800;line-height:1.25;">{h(release_title)}</div>
            <div style="color:#52525b;font-size:15px;margin-top:3px;">{artist_txt}</div>
            {date_line}
          </td>
        </tr></table>
      </td></tr>
    </table>
    """

    # CTA button, then info box + report link (order matches the reference design).
    detail_url = f"{FRONTEND_URL}/label/releases/{release_id}"
    body += f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:22px 0 4px 0;"><tr><td>
      <a href="{detail_url}" style="display:block;text-align:center;padding:17px 24px;background:#a855f7;background-image:linear-gradient(90deg,#7c3aed,#ec4899);color:#ffffff;font-weight:800;text-decoration:none;border-radius:16px;font-family:'Helvetica Neue',Arial,sans-serif;font-size:16px;letter-spacing:0.2px;">Buka Detail Rilisan</a>
    </td></tr></table>

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f3ff;border-radius:18px;margin:18px 0 4px 0;">
      <tr><td style="padding:16px 18px;">
        <table cellpadding="0" cellspacing="0"><tr>
          <td width="40" valign="middle" style="width:40px;">
            <img src="{EMAIL_CLOCK_URL}" alt="" width="28" height="28" style="width:28px;height:28px;display:block;border:0;" />
          </td>
          <td valign="middle" style="padding-left:12px;color:#5b21b6;font-size:15px;line-height:1.5;">
            Ketersediaan dapat muncul secara bertahap di setiap platform.
          </td>
        </tr></table>
      </td></tr>
    </table>
    <p style="margin:16px 0 0 0;">
      <a href="{FRONTEND_URL}/label/support" style="color:#7c3aed;font-weight:700;text-decoration:none;font-size:15px;">Laporkan kendala melalui dashboard &rarr;</a>
    </p>
    """

    badge = _badge("Rilisan Sudah Tayang")
    title = f"{h(release_title)} sudah resmi dirilis."
    html = _wrap(title, body, badge_html=badge)
    return await send_email(to=to, subject=f"🎉 {h(release_title)} sudah tayang di platform!", html=html)
