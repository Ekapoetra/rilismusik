# RILIS MUSIK — Prioritized Roadmap

## P0 — Production rollout
- Redeploy current preview code so production mendapat perbaikan login apex/`www` dan konfigurasi official Hostinger mailbox.
- Redeploy juga membawa fitur Admin Withdraw → Tambah Riwayat Manual Legacy.
- Redeploy juga membawa kolom Rupiah `Saldo Available` pada daftar Label Management.
- Redeploy membawa default sort saldo terbesar, pilihan sort label/email/saldo, dan kolom bulan withdraw terakhir.
- Redeploy membawa pencarian label server-side agar seluruh label production dapat ditemukan, termasuk label lama di luar 1.000 hasil awal.
- Setelah redeploy, smoke test login/me/refresh pada `https://rilismusik.com` dan `https://www.rilismusik.com` dari Windows dan macOS.
- Run one controlled production release-submission email and one manually triggered monthly summary, then confirm Hostinger delivery logs.
- Run a controlled user acceptance pass for multi-device auth, bank approval, PPR invoice, and PDF download.

## P1 — Product follow-up
- Add Admin Finance UI for monthly email delivery status/retry (backend status endpoint already exists).
- Add explicit bank-change history timeline and cancellation before approval.
- Add bulk download/archive for generated copyright letters.
- Add migration/report for legacy PPR releases whose invoices were created before the new post-approval flow.

## P2 — Quality & operations
- Link remaining CMS settings dynamically across all landing sections.
- Move FastAPI deprecated `on_event` startup/shutdown hooks to lifespan handlers.
- Add background job notification deep-links by exact job kind instead of the generic migration page.
- Add an optional daily operations digest for failed imports, failed emails, and pending approvals.

## Completed in current cycle
- Manual legacy withdraw dengan amount otomatis, background settlement, rekonsiliasi saldo, dan label visibility guard.
- Multi-device JWT sessions and global revocation.
- Login password visibility.
- Safe admin deletion/restoration and `admin_marketing` access.
- Two-sided bank-account approval.
- Expanded release metadata and submission notifications.
- Post-approval combined PPR invoice.
- Content ID YouTube link.
- Add-on edit/delete/archive.
- Copyright PDF with CMS signature/stamp.
- Monthly royalty emails and background completion notifications.