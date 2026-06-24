"""Withdraw helpers: Asia/Jakarta date windows + ledger updates."""
from datetime import datetime, timezone, timedelta
from typing import Tuple

JAKARTA_OFFSET = timedelta(hours=7)  # UTC+7, no DST


def jakarta_now() -> datetime:
    return datetime.now(timezone.utc) + JAKARTA_OFFSET


def withdraw_window_state() -> dict:
    """Return current withdraw window status based on Asia/Jakarta day-of-month."""
    now = jakarta_now()
    day = now.day
    if 1 <= day <= 14:
        phase = "request_open"
        message = "Periode request withdraw terbuka (tanggal 1-14)."
    elif 15 <= day <= 20:
        phase = "payment_window"
        message = "Periode pembayaran withdraw (admin proses tanggal 15-20). Request baru ditutup."
    else:
        phase = "closed"
        message = f"Tombol withdraw nonaktif (tanggal {day}). Buka kembali tanggal 1."
    return {
        "phase": phase,
        "day": day,
        "month": now.strftime("%Y-%m"),
        "request_open": phase == "request_open",
        "payment_window": phase == "payment_window",
        "message": message,
    }


MIN_WITHDRAW_IDR = 1_000_000
