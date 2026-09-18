# RILIS MUSIK — Product Requirements (PRD)

## Original Problem Statement
Full-stack music-label distribution & royalty platform (FastAPI + React + MongoDB) with:
- Dynamic RBAC, Multi-Label capabilities (one account owning multiple labels).
- Full-scale Compensation & Payroll engine (tiered/flat bonus schemas, PDF payslips).
- Consolidated Royalty Analytics with a canonical eligibility filter (cache = live).
- Grouped, compact sidebar navigation with an Admin UI Settings drag-and-drop editor.
- KTP/KYC account verification workflow with image lightbox.

## User & Language
- Primary language: **Indonesian** (respond in Indonesian).
- Personas: Super Admin, sub-admins (Support/Finance/Release/Marketing/Content), Labels, Artists.

## Core Requirements (stable)
- RBAC-driven navigation & permissions.
- Multi-Label entitlement resolution & account-level wallet.
- Compensation: base salary history, automated tiered bonus (% of total paid Xendit revenue), immutable payroll snapshots, PDF payslips.
- Analytics: only published/available royalty imports count (staged/unpublished ignored) via `analytics_eligibility.py`.
- KYC: admin review of KTP with approve/reject; **KTP photo opens in a zoom/pan lightbox** (done 2026-06).

## Recent Work (this session, 2026-06)
- **Dashboard polish (DONE, verified screenshot):** Kartu KPI kini render dengan fallback (Rp0/0) saat `/admin/dashboard/metrics` gagal (mencegah panel kosong; penyebab di prod = endpoint belum ter-deploy → perlu redeploy). Panel "Sedang Dikerjakan" & "Aktivitas Terbaru" dibatasi 4 item + `Pager` (slide titik/panah). "Ringkasan Kerja" jadi self-fetch dgn dropdown periode di kanan-atas (hari/minggu/bulan). Donat 4 kategori eksklusif.
- **Dashboard UI fase-2 (DONE):** `pages/admin/Dashboard.jsx` mengacu 2 gambar; beda peran super/admin; step-% (open=0%).
- **Dashboard fase-2 backend (DONE):** `routes/dashboard_metrics.py` — `/metrics`, `/in-progress`, `/work-summary` (period + tren nyata).
  - `GET /metrics?period=today|week|month` — KPI dengan tren nyata dari timestamp: `sales_revenue` (murni Xendit paid by paid_at), `total_labels/artists/releases` (total + added-in-period + tren vs periode sebelumnya), `active_members` (labels `kyc_status==verified`). Finance-gated (butuh `payments.view`/`withdraw.view`/super_admin): `requested_withdrawal` (withdraw_requests leaf pending+paid), `royalty_income_eur` (total kanonik). Field `finance_visible`.
  - `GET /in-progress` — daftar entitas mid-pipeline dgn **% berbasis step** (release/tiket/withdraw/addon; mis. 4 step → 25/50/75/100). Difilter per izin modul (super admin lihat semua).
  - `GET /work-summary?period=` — donut jujur: completed (work_items completed di periode) + in_progress + open + overdue (open lewat SLA) + total.
  - Catatan: UI (fase berikut) belum dikerjakan — user minta backend dulu.
- **Follow-up ke Believe + pisah hitungan Add-on (DONE):** tugas `believe_followup` (≥3 hari kerja) + notifikasi + tombol recheck; `service_orders` dikeluarkan dari "Proses Add-on".
  - Work type baru `believe_followup` (`work_service.py`): tiket berstatus `submitted_to_believe` muncul sebagai tugas "Follow-up ke Believe" HANYA setelah ≥3 HARI KERJA (exclude Sabtu-Minggu + hari libur nasional & cuti bersama 2026 via `working_days.py`). Sebelum ambang, tiket ini dikeluarkan dari tugas "Tiket Bantuan" biasa (tidak jadi tugas aktif).
  - Notifikasi lonceng: cron harian `believe_followup_reminder_job` (02:00 UTC, `cron_jobs.py`) memberi tahu admin pemegang `support.view` sekali per siklus. Trigger manual: `POST /api/admin/cron/believe-followup-check`.
  - Tombol defer: `POST /api/tickets/admin/{id}/believe-recheck` ("Sudah dicek — masih diproses Believe") menunda follow-up 3 hari kerja lagi (berulang), set `believe_last_checked_at`, `believe_check_count`. UI di `TicketDetail.jsx`. Setelah selesai, admin set status `done`.
  - **Anomali Add-on dipisah:** `addon_processing` kini HANYA menghitung `addon_orders` (Layanan Tambahan). `service_orders` (pembelian layanan mandiri, tanpa alur fulfillment) DIHAPUS dari hitungan kerja — inilah "phantom 1" yang sebelumnya menggembungkan "Proses Add-on". WAMI tetap terpisah ("Registrasi WAMI").
- **Fix anomali gate pembayaran PPR (DONE):** keputusan PPR dari langganan label saat ini.
- **Content ID: tiga lampiran bertanda tangan di tiket support (DONE):** 3 PDF per pencipta.
- **Bukti Pembayaran PPR di panel Tindakan Rilisan (DONE):** panel "Bukti Pembayaran" khusus PPR.
- **Kolom Paket di Manajemen Rilisan (DONE):** kolom "Paket" (Multi Label/VIP/Annual/PPR) di `/admin/releases`.
- **Fix: Link pembayaran hilang setelah revisi/koreksi status (DONE):** dua akar masalah PPR:
  1. `routes/releases.py` — aksi `override_status` (Koreksi/Mundurkan Status) yang memundurkan rilisan PPR ke status pra-bayar (`draft`/`submitted`/`under_review`/`need_revision`) tidak mereset `payment_status` maupun membatalkan invoice lama, sehingga tombol "Kirim Tautan Pembayaran" gagal dengan 409. Sekarang invoice lama dibatalkan & `payment_status`→`not_generated`, `payment_id`→None.
  2. `payment_service.py::create_payment_document` — cabang `DuplicateKeyError` (reuse by `reference_id`) mengembalikan invoice `cancelled` apa adanya, sehingga link yang di-regenerate menunjuk invoice mati. Sekarang invoice `cancelled/expired/failed` dihidupkan kembali (`pending`, sesi Xendit lama dibersihkan, nominal/line-items diperbarui).
- **KTP Lightbox (DONE):** klik foto KTP di Verifikasi Akun → modal gelap full-size dengan zoom (scroll/+/−, 100%–500%), pan drag, reset. File `components/admin/KycReviewDetail.jsx`.
- Prior in session: PDF payslips, bonus schema engine (flat/tiered), analytics canonical filter + audit tool, UI Settings grouped nav editor.

## Backlog (prioritized)
### P1
- Upload size limits (e.g. 300MB) for Add-on delivery results (R2 abuse prevention).
- Duplicate CSV upload prevention via file fingerprint (checksum/hash) on R2 upload.
- UI Settings menu-name input text contrast in dark mode (`UiSettings.jsx`).
### P2
- Smart Links & platform buttons (Spotify/Apple/YouTube) in "Live Today" banner + go-live email.
- Monthly royalty emails.
- National Holiday API for chat operational hours.
- Estimated withdrawal date in Label Wallet card.
- Export trend chart for stream trends.
- Automated artist report scheduling via Excel.
- Recharts console warnings cleanup.

## Blocked
- GitHub push/staged-files sync issue → escalated to Emergent Support (no code action needed).
- AI Assistant (GPT-5.4 via Emergent LLM Key) — paused by user.
- Xendit bank account validation (Iluma API) — pending `ILUMA_API_KEY` from user.

## Key Files
- Frontend: `/app/frontend/src/` (React, Tailwind, Shadcn). KYC review: `components/admin/KycReviewDetail.jsx`; page: `pages/admin/KycReviews.jsx` (route `/admin/kyc`).
- Backend: `/app/backend/routes/` (kyc.py, compensation_admin.py, compensation_payslip.py, analytics_eligibility.py).
- Storage: Cloudflare R2 (`storage_service.py`). DB: MongoDB.

## Integrations
- Emergent-managed Google Auth, Cloudflare R2, Hostinger SMTP, Xendit.
