# RILIS MUSIK — Product Requirement Document (PRD)

## Original Problem Statement
Web platform for Indonesian indie music distribution to 150+ DSPs via Believe. Three main parts:
1. **Landing Page** with iOS glassmorphism + CMS-editable content.
2. **Label Dashboard** (mobile-first): upload releases (WAV + 3000×3000 cover + metadata + release date ≥7 days), manage artists, royalty, withdraw, invoice, support, contracts, **WAMI registration**.
3. **Admin Dashboard** (desktop-first) with multi-role: Super Admin, Release, Finance, Support, Content/CMS.

Pricing (3-tier):
- **Pay Per Release**: Rp 35.000 per submission.
- **Annual Normal**: Rp 350.000 / year — unlimited release submit.
- **Annual VIP**: Rp 500.000 / year — unlimited release + **FREE WAMI** + GRATIS konten promosi.
- **WAMI Add-on**: Rp 100.000 / track (free for ACTIVE VIP subscribers).

Distributor fee 5% (visible to label for transparency), default label share 60% (HIDDEN from label).
Withdraw window 1–14 (request), 15–20 (payment), 21–end disabled. Min withdraw Rp 1.000.000.
Believe CSV (EUR) uploaded monthly by admin → IDR via manual exchange rate.

**Legal Entity (added 2026-06-24)**:
- **PT. Jeeres Group Indonesia** — Jl. Sintang Pontianak RT 12 / RW 5, Kec. Sintang, Sintang 78614, Indonesia.
- **NIB**: 2202260059749 · **WA/HP**: 085864137150.
- Displayed on Landing footer + Invoices page + editable via Admin CMS Legal Entity tab.

## Tech Stack
- **Backend**: FastAPI (Python 3.11), Motor (async MongoDB), JWT auth (httpOnly cookies), bcrypt, Pillow for image validation, APScheduler for background cron.
- **Frontend**: React 19 + React Router 7, Tailwind 3, axios with `withCredentials`, Plus Jakarta Sans + Manrope fonts.
- **Storage**: MongoDB (collections: users, labels, artists, releases, tracks, payments, royalty_imports, royalty_lines, withdraw_requests, bank_accounts, support_tickets, ticket_comments, contracts, landing_settings, activity_logs, email_verification_tokens, password_reset_tokens, login_attempts, royalty_percentage_history, notifications, wami_orders). Local filesystem for uploads under `/api/files`.
- **Payments**: Mock Xendit (real webhook handler ready at `/api/payments/webhook/xendit`).

## Architecture (Refactored 2026-06-24)
**Backend** — modular routers under `/app/backend/routes/`:
- `deps.py` — shared db connection, auth dependencies, notify helpers, log_activity.
- `cms_defaults.py` — `DEFAULT_LANDING_SETTINGS` dict (~95 lines).
- `seed.py` — `seed_indexes_and_admins()` (indexes + super-admin + sub-admins + CMS migration).
- `cron_jobs.py` — `check_subscription_expiry_job`, `check_contract_expiry_job`, manual trigger endpoints + scheduler lifecycle.
- One router per domain: `auth.py`, `labels.py`, `releases.py`, `artists.py`, `payments.py`, `wami.py`, `cms.py`, `admin.py`, `royalty.py`, `withdraw.py`, `tickets.py`, `notifications.py`, `contracts.py`.
- `server.py` = slim 101-line entry point (was 3228 lines): app factory + CORS + StaticFiles + router includes + startup/shutdown.

**Frontend** — AuthContext + ProtectedRoute. Three layouts: public landing, `LabelLayout` (mobile-first sidebar + bottom nav), `AdminLayout` (dark desktop-first sidebar). Pages under `/app/frontend/src/pages/{label,admin,auth}` + `Landing.jsx`.

## User Personas
1. **Label** — Indonesian indie label or independent artist. One main account per label.
2. **Artist Sub-Account** — created by a label. Sees only linked tracks + royalty.
3. **Admin** — internal operator with one of: Super Admin / Admin Release / Admin Finance / Admin Support / Admin Content / Admin Marketing.

## What's Been Implemented (Phase 1 → 6 + Refactor) — 2026-06-24

### Phase 1 — Landing + Auth + Label/Admin MVP (DONE)
Landing page (iOS glassmorphism, CMS-driven), full auth (register/login/refresh/me/verify/forgot/reset, brute-force lockout, httpOnly cookies + JWT + bcrypt), Label dashboard, 3-step release upload wizard (WAV / 3000×3000 / date ≥7d / audio player / edit), artist sub-accounts, profile + bank, invoices + subscription (MOCK Xendit), Admin multi-role console with 12 metrics, label/release/artist/payment/CMS/admin-user management + activity logs.

### Phase 2 — Royalty CSV & Withdraw (DONE)
CSV royalty import (Believe EUR), manual exchange rate, status flow pending_review → published → dana_received, withdraw window enforcement, label royalty report.

### Phase 3 — Support Ticketing (DONE)
8 categories, 8 statuses, chat-style comment thread with attachments, label create/view/cancel, admin list+filter+status update, cross-label isolation, 22/22 pytest.

### Phase 4 — Real Believe CSV + Contracts + Notifications + Blacklist (DONE)
Real Believe CSV parser (Indonesian headers + European decimals), label-name fallback match, all EUR + SENSITIVE fields hidden from label, contracts module (PDF upload, status badges, days_left), in-app notifications (bell icon + 30s poll), blacklist management UI, idempotent sub-admin seeding.

### Phase 5 — Royalty redaction + Cron (DONE)
All royalty percentage info hidden from label/artist surfaces (`royalty_percentage_default`, `royalty_percentage_history`, `default_royalty_share`, `label_percentage_applied`, `distributor_idr`, `exchange_rate`). Subscription expiry cron (hourly + T-7/T-3/T-1 reminders). Contract expiry cron (daily + T-30/T-7/T-1 reminders). Manual admin trigger endpoints.

### Phase 6 — 3-tier subscription + WAMI Add-on + Legal Entity (DONE 2026-06-24)
- **3-tier pricing**: Rp 35K PPR / Rp 350K Annual Normal / Rp 500K Annual VIP.
- **WAMI Add-on**: Rp 100.000/track via Xendit (mock) — FREE for active VIP subscribers. Admin manages via `/admin/wami`. Label requests via `/label/wami`.
- **VIP active-subscription guard**: expired-VIP labels pay normal Rp 100K (not auto-free).
- **Legal Entity** info (PT. Jeeres Group Indonesia, NIB, address, WhatsApp) on Landing footer, Invoices page banner, editable in Admin CMS Legal Entity tab (8 fields with data-testids).
- **CMS migration**: idempotent backfill of new sub-keys (`pricing.annual_normal_price`, `pricing.wami_addon_price`, `legal_entity.*`) without overwriting admin edits.

### Refactor — Modular Routers (DONE 2026-06-24)
`server.py` reduced 3228 → 101 lines. 14 modular routers + `deps.py` + `cms_defaults.py` + `seed.py` + `cron_jobs.py`. **114/115 pytest PASS, zero regression**.

### Phase 7 — Master Distribution Agreement (MDA) Auto-generation (DONE 2026-06-24)
- **MDA generated automatically at label registration** via reportlab PDF builder (`/app/backend/routes/mda_generator.py`).
- **Tier-agnostic**: same MDA covers Pay Per Release, Annual Normal, Annual VIP, and WAMI add-on — listed as "Schedule A" inside the contract. Label can switch tiers without invalidating MDA.
- **Lifetime contract** (no expiry) — `end_date=null`, `is_lifetime=true`. Either party can terminate via support ticket / admin termination.
- **Legal basis**: UU ITE No. 11/2008 jo. UU No. 19/2016 (electronic signature via checkbox + timestamp + accepted_by_name).
- **9-pasal Indonesian-language template**: Definisi, Lisensi Distribusi, Skema Pembayaran (Schedule A), Royalti & Biaya Distributor, Jadwal Withdraw, Kepatuhan & Takedown, Jangka Waktu & Pengakhiran, Hukum yang Berlaku (Pengadilan Negeri Sintang), Persetujuan Elektronik.
- **CMS-driven**: PT. Jeeres Group Indonesia + NIB 2202260059749 + WA 085864137150 merged dynamically from `landing_settings.legal_entity`.
- **Public preview** at `GET /api/cms/mda/preview` (no auth) — renders sample PDF with placeholder label data so prospects can review before registering. Does NOT mutate DB.
- **UI**: Register page (`/register`) has MDA checkbox + link to preview PDF; submit button disabled until ticked. Label `/label/contract` shows "Tanpa Batas Waktu" + violet UU-ITE banner for the auto-generated MDA.
- **Tests**: `test_phase7_mda.py` 5/5 PASS.

### Phase 8 — Bulk Migration & Account Claim (DONE 2026-06-24)
**For post-deploy migration of 15K legacy songs + 5-6K legacy labels + multi-year withdraw history + Believe royalty CSVs.**

- **Multi-period royalty CSV**: `POST /api/royalty/admin/imports` now accepts CSVs containing multiple months in one upload. When `period` form field is omitted, parser uses each row's `Bulan Laporan` column. Import doc gets `is_multi_period=true`, `period_start`, `period_end`, `period_breakdown={"2024-01": N, ...}`. Each line tagged with its own `period`. Publish/dana_received use period range "2024-01 s/d 2024-03" in transaction descriptions. After initial migration, monthly CSVs continue working with single `period`.
- **Bulk Labels CSV** (`POST /api/admin/migrate/labels`): 13 columns (label_name, pic_name, whatsapp, address, city, country, label_type, payment_type, subscription_tier, subscription_expires_at, account_status, royalty_percentage_default, notes). Idempotent by (label_name + city) composite key. `user_id=null`, `account_status='legacy_unclaimed'`, `legacy_import=true`. Returns per-row report (OK/SKIPPED/ERROR).
- **Bulk Releases CSV**: lookup label by legacy_id or name, `imported_legacy=true`, audio_url optional, ISRC/UPC dedupe.
- **Bulk Tracks CSV**: lookup release by legacy_id or release_isrc, ISRC dedupe.
- **Bulk Withdraws CSV**: inserts withdraw_requests + balance_transactions silently (NO notifications, NO balance mutation — pure historical record).
- **Account Claim flow**: label registers with `claim_existing=true` + `legacy_label_name='X'` → does NOT create label doc; user gets `claim_status='pending_link'`. Admin sees pending claims at `/admin/migrate` → Claims tab → searches legacy labels by name → clicks Link → existing legacy label's `user_id` is set + `account_status='active'` + auto-generated MDA PDF.
- **Admin UI** at `/admin/migrate` (Super Admin only): 5 tabs (Labels/Releases/Tracks/Withdraws/Claims). Each tab has Download Template + File picker + Dry-run toggle + Submit + per-row error report CSV download.
- **Dry-run mode**: All 4 CSV imports support `dry_run=true` to preview without DB mutation.
- **File size cap**: 30 MB per upload (chunked inserts at 1000 rows per batch).
- **Permissions**: only `super_admin` can run bulk migrations; super_admin + admin_release + admin_support can resolve claims.
- **Tests**: `test_phase8_migrate.py` 9/9 + `test_phase8_extras.py` 10/10 = 19/19 PASS.

### Phase 9 — Auto-create from CSV + Admin "Buatkan Akun" (DONE 2026-06-25)
- **Auto-create legacy entities from Believe CSV**: when admin uploads royalty CSV, any new `label_name` / new ISRC / new UPC automatically creates placeholder Label (account_status='legacy_unclaimed', user_id=null), Release (imported_legacy=true, status='live'), and Track (imported_legacy=true, audio_url=null). Import doc reports `auto_created_labels/releases/tracks` counts. Royalty line matches the new entities → no more `unmatched_lines` cluttering admin queue.
- **Fuzzy match**: `_norm_name()` helper (lowercase + trim + collapse whitespace) matches "NADA Records" to "nada records  " — prevents duplicate labels from case/spacing variations.
- **Admin "Buatkan Akun"**: `POST /api/admin/labels/{label_id}/create-account` (super_admin / admin_release / admin_support only) creates a user account for a legacy unclaimed label. Auto-generates 12-char unambiguous password if not supplied, returns it ONCE in JSON, generates MDA PDF, links user_id to label, sets account_status='active'.
- **UI**: `/admin/labels` filter dropdown now includes 'Legacy / Unclaimed'. Each unclaimed row shows amber `Unclaimed` badge + violet `From CSV` badge (if auto-created) + 'Buatkan Akun' button → modal with email/pic_name/whatsapp/password fields → credentials modal showing plaintext password with Copy button.
- **2 demo accounts** seeded via `python3 -m scripts.seed_demo_labels`:
  - PPR: `demo_ppr@rilismusik.com / DemoPPR#2026` — Pay Per Release, Rp 5jt balance, 2 releases.
  - VIP: `demo_vip@rilismusik.com / DemoVIP#2026` — Annual VIP active (expires 2027-04-21), Rp 15jt balance + Rp 3.2jt pending, 3 releases, 1 historical paid withdraw, 1 free WAMI registration.
- **Tests**: `test_phase9_autocreate.py` 10/10 + 42/42 regression = 52/52 PASS, zero regression.

### Phase 10 — Background CSV Import Recovery (DONE 2026-06-25)
**Solves: 80MB+ Believe CSV imports surviving container restart / uvicorn --reload.**

- **Auto-resume on startup**: `resume_interrupted_imports()` runs in `server.py` startup. Scans for `royalty_imports` with `status='processing'`. For each stuck doc:
  - If CSV file is still on disk → wipe partial inserts (`royalty_lines` + auto-created labels/releases/tracks for that `import_id`) and re-spawn the background task.
  - If file is gone (container restart wiped tmpfs) → mark `status='error'` with descriptive `error_message`.
- **Manual retry endpoint**: `POST /api/royalty/admin/imports/{id}/retry` (super_admin / admin_finance) — same idempotent reset-then-rerun flow for cases where auto-resume failed or admin wants to retry a previously-errored import. Returns 400 if status is not `processing`/`error` or if file is missing.
- **New status `error`**: import_doc now has 5 statuses (`processing`, `pending_review`, `published`, `dana_received`, `error`) with `error_message` field surfaced to admin UI.
- **Bug fix**: removed duplicate `GET /admin/imports/{id}` endpoint that was shadowing the rich `{import, lines, per_label}` response — RoyaltyDetail page was broken before this fix.
- **UI**: Admin `/admin/royalty` page now polls every 4s while any import is processing. Each row shows live progress bar + matched lines counter. Status badge supports new `Processing` (animated spinner icon) and `Error` (red X) states. Retry button (`data-testid="royalty-import-retry-{id}"`) appears for both states. RoyaltyDetail page polls every 3s and shows a hero progress card (sky→violet gradient) with `processed_lines / matched_lines / auto_created_labels / auto_created_tracks` plus an error banner.
- **Tests**: `test_phase10_csv_recovery.py` 5/5 PASS + 24/24 regression = 29/29 PASS.

### Phase 11 — SMTP Email Notifications LIVE (Hostinger, DONE 2026-06-28)
**Replaces console-only mock emails with real transactional sending via Hostinger SMTP.**

- **email_service module** (`/app/backend/email_service.py`): Standard-library `smtplib.SMTP_SSL` (port 465) wrapped with `asyncio.to_thread` for non-blocking FastAPI. No 3rd-party SDK needed — robust, portable, and works with any SMTP provider (Hostinger, Gmail Workspace, Mailgun, etc.) by just swapping env vars. 7 typed helpers covering all transactional flows.
- **Env vars in `/app/backend/.env`**: `SMTP_HOST=smtp.hostinger.com`, `SMTP_PORT=465`, `SMTP_USER=support@rilismusik.com`, `SMTP_PASSWORD`, `SENDER_EMAIL=support@rilismusik.com`, `SENDER_NAME=RILIS MUSIK`.
- **Production-ready**: Unlike Resend test mode, Hostinger SMTP delivers to ANY recipient from day 1 — full custom domain (`@rilismusik.com`) auto-aligns SPF/DKIM/DMARC (Hostinger handles DNS).
- **Tests**: `test_phase11_email.py` 3/3 PASS.

### Phase 12 — Cloudflare R2 Object Storage LIVE (DONE 2026-06-28)
**Replaces ephemeral local-disk uploads with Cloudflare R2 (S3-compatible) — files survive container restarts and pod evictions.**

- **storage_service module** (`/app/backend/storage_service.py`): boto3 client pointed at R2 endpoint with `region_name='auto'` + `signature_version='s3v4'` (Cloudflare R2 requirements). Async helpers via `asyncio.to_thread`: `upload_bytes`, `upload_fileobj` (multipart-aware for large WAV), `generate_presigned_url`, `delete_object`, `head_object`, plus FastAPI convenience `upload_upload_file`.
- **Smart `/api/files/{path}` handler** (`server.py` L47-72): R2-first lookup with disk fallback for legacy files. R2 hit → 302-redirect to presigned URL (TTL 7d for `cover/`+`landing/`, 1h for everything else). Path-traversal guard for the disk-fallback branch.
- **8 upload sites migrated to R2**: releases (cover+audio), contracts (PDF), CMS landing image, tickets attachment, withdraw proof, auto-MDA PDF at register/admin/migrate, cms/mda/preview (in-memory).
- **MDA generator refactor**: added `generate_mda_pdf_bytes(label, legal_entity) -> bytes` for the bytes-first path; old disk-based `generate_mda_pdf()` retained for backward compat.
- **Env vars**: `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET=rilismusik`, `R2_PUBLIC_BASE_URL` (reserved for future custom domain).
- **Tests**: 32/32 PASS (5/5 unit + 7/7 E2E + 20/20 regression).

### Phase 13 — Full Data Reset (Super Admin Danger Zone, DONE 2026-06-28)
**Lets the super admin wipe ALL business data with one click to test the platform end-to-end with real data on a clean slate.**

- **Endpoint**: `POST /api/admin/admin/danger/reset-all-data` (form-data) — Super Admin only.
- **Preserves**: admin users (5 sub-admins + super_admin) + CMS landing settings + DB indexes.
- **Wipes** 22 collections + R2 bucket files (paginated batches of 1000).
- **Re-seeds admins** idempotently after wipe.
- **UI**: super-admin-only "Danger Zone" card on `/admin/admin-users` with double-confirm modal.
- **Bug fixes during testing**: synced `admin_marketing` (was orphan in seed) and `admin_content` (was orphan in ADMIN_ROLES set).
- **Tests**: 14/14 PASS (3 back-to-back idempotent resets confirmed).

### Phase 14 — Direct-to-R2 Large CSV Upload (DONE 2026-06-28)
**Solves: Believe royalty CSV uploads >100 MB failing in production due to Kubernetes ingress body cap.**

- **3-step flow** bypasses the ~100 MB ingress limit. Frontend uploads DIRECTLY to Cloudflare R2 — supports up to 5 GB.
  1. `POST /api/royalty/admin/imports/initiate` → returns `{import_id, presigned_put_url, r2_key, content_type, expires_in:7200}`.
  2. Browser `PUT` directly to presigned URL with XHR `upload.onprogress` for real-time bar.
  3. `POST /api/royalty/admin/imports/{id}/finalize` → backend `head_object` → `download_to_file` → kicks off existing `_process_csv_import_bg`.
- **R2 CORS auto-config**: `storage_service.ensure_cors()` runs at startup with `AllowedOrigins=[FRONTEND_URL, preview, production]`.
- **Resume/retry hardened**: `_ensure_local_csv()` re-downloads from R2 if staging file missing.
- **Frontend UI**: 3-stage progress card (`Meminta URL → Upload ke R2 X% → Memulai processing`).
- **Tests**: 10/10 PASS — auth gates, RBAC, validation, happy path, CORS preflight, backward-compat.

### Phase 15 — SQL Snake_case Header Support (DONE 2026-06-28)
**Solves: User uploaded one-off SQL-export CSV with snake_case headers — parser returned all-unmatched.**

- **1-line core fix** in `royalty_utils.normalize_header()`: replace `_` and `-` with spaces + collapse whitespace. Now matches Believe `Bulan Laporan`, SQL `bulan_laporan`, kebab-case, etc. — same alias list.
- **18 canonical fields** auto-detected from 23-col SQL header set. Non-canonical (e.g. `release_catalog_nb`) silently ignored.
- **Robust value parsing**: SQL YYYY-MM-DD periods + US dot-decimals work alongside European comma-decimals.
- **Tests**: 33/33 PASS — full E2E upload of user's `/tmp/sql_revenues.csv` → 10/10 matched.

### Phase 16 — Background Publish (Idempotent & Restart-Safe, DONE 2026-06-28)
**Solves: Publishing 219,800-row royalty CSV in production triggered Kubernetes ingress 60s timeout.**

- **Refactored** publish endpoint to return immediately (status=`publishing`) and spawn `_publish_bg()`. Frontend auto-polls every 3-4s.
- **New statuses**: `publishing` + `publish_error`. Idempotency via `balance_transactions` lookup before crediting.
- **Restart-safe**: `resume_interrupted_imports()` handles both `processing` and `publishing` on startup.
- **Tests**: 15/15 PASS — happy path, race re-publish, restart-resume, auth gates.

### Phase 16.1 — Defensive Publish Wrapper (DONE 2026-06-28)
**Surfaces actual root cause of any future publish failure instead of generic 500.**

- Wrapped `admin_publish_import` in try/except → catches non-HTTPException, logs full stack trace, writes `error_message` to import doc, returns descriptive HTTP 500 with `{type(e).__name__}: {str(e)[:200]}`.
- Defensive `imp.get("status", "pending_review")` handles legacy docs missing the `status` field.
- Frontend now distinguishes 4 publish response branches: publishing / published / HTTP 500 (with deploy hint) / other.
- **Tests**: 9/9 PASS (frozen status, missing status, auth gates, retry).
- **Critical diagnostic value**: this wrapper is what exposed the Phase 16.2 root cause in production.

### Phase 16.2 — Chunked Update Fix for MongoDB Atlas maxTimeMS (DONE 2026-06-28)
**Solves: After Phase 16+16.1 deployed to production, user retried publish for 219,800-row import — wrapper surfaced the real error: MongoDB `MaxTimeMSExpired` (code 50) writeConcernError on the single huge update_many. Atlas serverless/shared clusters enforce a per-operation maxTimeMS that a 219K-doc update_many can exceed.**

- **Chunked the line-status flip** into batches of 2000 docs using Mongo native `_id` pagination (always indexed → guaranteed IXSCAN, no custom index needed):
  ```python
  CHUNK_SIZE = 2000
  last_oid = None
  while True:
      q = {**base_filter, **({"_id": {"$gt": last_oid}} if last_oid else {})}
      batch = await db.royalty_lines.find(q, {"_id": 1}).sort("_id", 1).limit(CHUNK_SIZE).to_list(CHUNK_SIZE)
      if not batch: break
      oids = [d["_id"] for d in batch]
      last_oid = oids[-1]
      await db.royalty_lines.update_many({"_id": {"$in": oids}}, {"$set": {"status": "pending"}})
      # progress 75 → 95%
  ```
- **Each chunk completes in ~1s** — well within any Atlas maxTimeMS limit. Self-test: 220K rows published in 10 seconds total (preview environment).
- **`allowDiskUse=True`** added to the per-label aggregate pipeline for safety on very large datasets.
- **Idempotency preserved**: chunk filter `status: {$ne: "pending"}` naturally skips already-flipped lines. balance_transactions lookup still gates per-label crediting (no double-credit).
- **Tests**: `test_phase16_2_chunked_publish.py` 10/10 PASS + 15/15 Phase 16 regression + 9/9 Phase 16.1 regression = **34/34 PASS**. Scale test seeds 50,000 royalty_lines directly into Mongo and confirms publish completes in <2s wall-clock.

## Test credentials
See `/app/memory/test_credentials.md`.

## Prioritized Backlog

### P0 (next session)
- **Optimize CSV processing with `insert_many` batched** — `royalty_lines` are inserted one-by-one via streaming. Refactor to batch insert ~5,000 documents per round trip → drop 1M-row import wall-time from ~10 min to ~1–2 min.
- **Xendit LIVE integration** — replace mock-pay with real Xendit invoice/webhook for PPR + Subscription tiers + WAMI add-on. Webhook already locked behind `XENDIT_CALLBACK_TOKEN` (Phase 17 SEC-001). Need API keys + dashboard webhook URL.

### P1 (Production polish)
- CMS Landing Page dynamic linkage (Admin CMS already drives 12 keys — verify all are referenced live).
- PATCH /api/admin/labels/{id} should accept `subscription_tier` (admins currently can't change tier via API).
- Google OAuth login (Emergent managed).
- PDF export of royalty report (currently CSV only).
- Contract MIME magic-byte check (currently extension-only).
- Re-seed demo labels so Phase 2/3/4/6/9 tests pass again post-Phase-13 reset.

### P2 (Phase 7+ — Growth)
- Public artist profile pages, royalty forecasting.
- Referral program (1 month subscription credit per onboarding).
- Mobile native app.
- Multi-artist royalty splits per track.

## Changelog

### Phase 29 — Full Auto-Sync on Upload + Legacy Tool Removal (2026-06-30)
**User request**: "Saat saya upload ulang laporan bulanan, langsung sinkronkan otomatis data artis, riwayat royalti, katalog lagu, dan label dari CSV Believe. Settingan lama hapus saja."

- **Auto-sync dashboards after upload** (`routes/royalty.py`): new `_trigger_dashboard_recompute()` helper fires `_recompute_revenue_cache()` + `recompute_monthly_analytics()` as fire-and-forget tasks. Called from:
  1. `_process_csv_import_inline` — right after the final status flip to `pending_review` (covers both direct upload and R2 large-upload background paths).
  2. `admin_force_finalize_import` — after a successful force-finalize.
  Previously the analytics cache was only rebuilt after Publish/Delete → Artist Management / Katalog / Analytics stayed empty until publish. Now they populate immediately after upload completes. **Publish remains manual** (admin sets kurs EUR→IDR first) per user choice — label balances & label-visible royalty history still only appear after Publish.
- **Legacy migration tools REMOVED from UI** (`pages/admin/Migrate.jsx` rewritten 1028 → ~170 lines): tabs Labels / Releases / Tracks / Withdraws (old) / Withdraws FIFO / Backfill Bulan Laporan / Materialize Artists all deleted. Page renamed **"Klaim Akun"** — only the ClaimsPanel remains (still needed for legacy-label account claiming) + an emerald info banner explaining the new auto-sync. Sidebar nav label updated (`AdminLayout.jsx`).
- **Backend migrate endpoints kept intact** (super_admin-only, harmless) so existing test suites and emergency API access still work — only the frontend surface was removed.
- **E2E verified (curl)**: uploaded 2-row Believe CSV → `auto_created_labels=1, auto_created_releases=1, auto_created_tracks=2, auto_created_artists=1`, status `pending_review`; within 5s `/admin/analytics/status` showed fresh rebuild, `/admin/artists` returned new artist WITH revenue rollup (18.75 EUR / 181,687 IDR), `/admin/analytics/monthly` served `source=cache` with correct KPI — all WITHOUT publish. Test import deleted afterwards (cascade removed auto-created entities).
- **Regression**: `test_phase28_autocreate_artists.py` + `test_phase16_5_batched_csv_import.py` = 13/13 PASS. Screenshot confirmed new Klaim Akun page renders, old tabs gone.

### Phase 28 — Auto-create Artists during CSV Ingestion (2026-06-30)
**User insight**: "Data artis dan rilis sudah lengkap di CSV royalti bulanan (kolom artist, label, track, UPC, ISRC). Kenapa harus migrasi lagi? Kenapa tidak otomatis?"

**Root cause**: Phase 9 already auto-created Label/Release/Track during CSV ingestion, but **artists were never auto-created** — admin had to run "Materialize Artists" tool manually after every upload. Artist Management page stayed empty until that secondary step ran.

- **`/app/backend/royalty_utils.py`** — new `slug_artist(name)` helper (lowercased + alphanumeric-only). Returns `""` for blank or `"Unknown"` so those rows skip auto-create.
- **`/app/backend/routes/royalty.py` `_process_csv_import_inline`** — added inline artist auto-create:
  - At startup, pre-loads `all_artists_by_key: Dict[(label_id, name_slug), artist_doc]` via `db_bg.artists.find` (CSOT-safe).
  - Per row, when `label_id` is resolved AND `raw["artist_name"]` is non-blank/non-Unknown: looks up `(label_id, slug)` in the map. If found → reuses `artist_id`. If not → creates new artist doc (status=active, user_id=null, imported_legacy=true, auto_created_from_lines=true, auto_created_from=import_id) and appends to `new_artist_batch`.
  - The `artist_id` is set on `royalty_lines.artist_id` directly at ingestion (not None anymore).
  - Newly auto-created tracks are mutated to also carry the resolved `artist_id` before flush.
- **Counters**: new `auto_artists` field in `counters` dict, surfaced as `auto_created_artists` in the import doc and the API response.
- **Cleanup**: `_reset_import_for_retry()` and `_delete_import_bg()` now also delete `artists` with matching `auto_created_from=import_id` (so retry/delete is symmetric with insert).
- **Tests** `/app/backend/tests/test_phase28_autocreate_artists.py` (7/7 PASS):
  1. `auto_created_artists` counter appears in the import response.
  2. New artist appears in `GET /admin/artists` with revenue rollup hydrated (revenue_eur, royalty_lines_count, last_active_period).
  3. `royalty_lines.artist_id` is populated at ingestion (not null).
  4. 2nd CSV with same `(label, artist)` combo does NOT create duplicate artist (idempotent).
  5. "Unknown" and blank artist names are skipped (not auto-created).
  6. Multiple distinct artists in one CSV all get created.
  7. Deleting the import also deletes the auto-created artists (cleanup).
- **Test update**: `test_phase16_5_batched_csv_import.py` expectation changed from 4 → 5 insert_many calls (added `artists`) inside `_process_csv_import_inline`; `test_source_inserts_use_db_bg` now also asserts `db_bg.artists.insert_many(`.
- **Combined regression (Phase 9 + 16.2 + 16.4 + 16.5 + 18 + 23.2 + 23 force + 24 + 26 + 27 + 28)**: **94/94 PASS**.
- **UX impact**: "Materialize Artists" tool stays available for legacy data that was ingested before Phase 28 was deployed (run once after redeploy to backfill historical royalty_lines with `artist_id`), but is **no longer needed after every CSV upload**. New uploads populate Artist Management + analytics rollups end-to-end automatically.

### Phase 27 — Async All Migration Tools + Critical Indexes (2026-06-29)
User report (production after Phase 26 redeploy): Withdraw FIFO dry-run hit `timeout of 110000ms exceeded` (frontend axios timeout). Analytics Royalti & Artist Management still empty. Root cause analysis:
- (a) `royalty_lines` missing the compound index `(label_id, period, status)` → per-label aggregations in Withdraw FIFO dry-run do full collection scans, slow on 3M+ rows.
- (b) Materialize Artists was still sync — full DB scan over 3M+ rows easily exceeds 120s ingress proxy timeout.
- (c) Analytics is empty for the user's selected period range (Mei 2025 – Apr 2026) because no published data exists yet — 2025-05 and 2026-04 were still processing when reported. User needs to widen filter (e.g. "Semua" / "12 Bulan Terakhir" reaching back into 2024 data).

- **Backend `routes/seed.py`** — added 6 critical indexes to `ensure_indexes()`:
  - `royalty_lines (label_id, period, status)` compound — fixes Withdraw FIFO dry-run aggregation
  - `royalty_lines (label_id, artist_name_raw)` compound — fixes Materialize Artists scan
  - `royalty_lines artist_name_raw` solo, `royalty_lines row_period` solo, `royalty_lines release_id`, `royalty_lines track_id`
  - `migrate_jobs id` unique, `migrate_jobs (status, submitted_at desc)`, `migrate_jobs kind`
  - All use `db_bg` (CSOT-uncapped) + `create_index` is idempotent + non-blocking (MongoDB background-builds).
- **Backend `routes/migrate.py`** — new endpoint `POST /api/admin/migrate/ensure-indexes` (super_admin):
  - Manually re-runs `seed_indexes_and_admins()` for production scenarios where the deploy already happened but new indexes from code haven't been built yet.
- **Backend `routes/migrate.py`** — Materialize Artists converted to async job pattern:
  - Endpoint returns HTTP 200 + `job_id` immediately (no longer blocks until completion).
  - Heavy aggregation + bulk_write moved into `_materialize_artists_bg()` with progress writes per phase (`aggregating`, `diffing`, `inserting_artists`, `backfilling_lines_and_tracks`).
  - Frontend polls `GET /admin/migrate/jobs/{id}` every 3s.
- **Frontend `pages/admin/Migrate.jsx`**:
  - `MaterializeArtistsPanel` updated to handle async pattern — submit returns job_id immediately, indigo status card displays live progress (phase, combos_found, lines_updated), result panel renders when status='done'.
  - WithdrawFifoPanel timeout bumped from 110s → 115s (matches ingress 120s ceiling — buys time for first dry-run before indexes finish building on production).
- **Tests** `/app/backend/tests/test_phase27_indexes_and_async.py` (4/4 PASS):
  - `ensure-indexes` endpoint returns ok + duration
  - RBAC super_admin only (admin_finance 403)
  - 5 critical compound indexes present on `royalty_lines` after ensure
  - 3 indexes present on `migrate_jobs`
- **Test updates**: Phase 26 materialize tests rewritten to use `_wait_for_job` helper (polls until `status` in `{done, error}`).
- Combined Phase 22 → 27 regression: **48/48 PASS**.

### Phase 26 — Materialize Artists + Async Withdraw FIFO (2026-06-29)
Production multi-bug report: (1) Artist Management still empty after upload even though royalty_lines have artist names, (2) Withdraw FIFO migration consistently hit 120s ingress timeout on the COMMIT path, (3) Analytics + Releases pages depend on cache rebuild that admin must trigger manually.

- **Backend `routes/migrate.py`** — new endpoint `POST /api/admin/migrate/materialize-artists` (super_admin only):
  - Aggregates `royalty_lines` by (label_id, artist_name_raw) for matched rows, excluding `None`/`""`/`"Unknown"`/`"unknown"`. Filter uses single `$nin` (MongoDB rejects co-existing `$ne` + `$nin` on the same field).
  - Dry-run returns preview with combo counts + top-20 by `total_label_idr`.
  - Commit: `insert_many` new artist docs in 1k batches, then `bulk_write` `UpdateMany` ops in 500-batch chunks to backfill `royalty_lines.artist_id` and `tracks.artist_id`. Idempotent — only NEW (label_id, name_slug) combos get inserted.
  - Auto-triggers `recompute_monthly_analytics()` after commit so Artist Management page shows data immediately.
- **Backend `routes/migrate.py`** — Phase 22 commit converted to background pattern:
  - When `dry_run=false`, response has `commit.queued=true` + `job_id` + dry-run preview totals (no 120s timeout risk).
  - New helper `_commit_legacy_period_bg(job_id, ...)` runs the heavy chunked writes (chunk-flip royalty_lines, balance adjust, history docs insert) via `db_bg`. Writes progress to `migrate_jobs` collection every 10 labels.
  - Auto-triggers `recompute_monthly_analytics()` after job completion.
- **Backend `routes/migrate.py`** — new endpoint `GET /api/admin/migrate/jobs/{job_id}`:
  - Returns the polling-friendly job doc (status, progress counters, result, error_message).
  - Used by both Withdraw FIFO frontend polling and potentially future background migrations.
- **Frontend `pages/admin/Migrate.jsx`**:
  - New tab "Materialize Artists" (data-testid `admin-migrate-tab-materialize-artists`) with `Sparkles` icon — 6th tab in the strip.
  - `MaterializeArtistsPanel` component: scope-by-limit input, dry-run toggle, 4-card stats grid, top-20 preview table with label_id/lines/revenue_eur/label_idr columns.
  - `WithdrawFifoPanel` updated to handle async commit: polls `/admin/migrate/jobs/{job_id}` every 3s after submit, renders progress UI (status, labels processed, lines flipped, history inserted, final result on done, error on fail). Polling interval cleared on unmount.
- **Tests** `/app/backend/tests/test_phase26_materialize_artists_and_async_fifo.py` (7/7 PASS):
  - Dry-run no-mutation + correct preview shape
  - Commit creates artists + backfills lines/tracks; excludes "Unknown"
  - Idempotent re-run finds 0 new artists
  - RBAC super_admin only
  - Withdraw FIFO commit returns job_id + bg task flips/inserts correctly; balances decremented
  - Dry-run withdraw still synchronous (no job_id)
  - GET /jobs/{id} returns 404 on unknown
- **Test updates**: Phase 22 `test_commit_idempotent` + `test_b_label_only_advances_not_regresses` updated to use new `_commit_and_wait` helper (polls job to completion before asserting).
- Combined Phase 22 → 26 regression: **44/44 PASS**.

### Phase 25 — Label Account Lifecycle + Fast Dashboard (2026-06-29)
User report: (1) needed ability to revoke a label PIC user account without losing label/royalty data (e.g. for PIC change-over), (2) ability to change a label's email, and (3) label dashboard was loading slowly with saldo/withdraw button not visible.

- **Backend `routes/admin.py`** — 2 new endpoints (super_admin / admin_support / admin_release):
  - `POST /api/admin/labels/{id}/revoke-account` (Form: `cascade_artists`, `reason`)
    - Disables the PIC user account (`status=disabled`, bumps `token_version` → all existing JWTs invalidated instantly)
    - Clears `labels.user_id`, sets `account_status="no_account"`, stores `previous_account_email` for audit
    - If `cascade_artists=true`, all artist sub-account users under the label are also disabled + token-bumped
    - Label, releases, royalty_lines, contracts — all preserved untouched. Admin can immediately create a new account via the existing `create-account` endpoint.
  - `POST /api/admin/labels/{id}/change-email` (Form: `new_email`, `notify`)
    - Validates email format + uniqueness
    - Updates `users.email`, `labels.email`, bumps `token_version` so old sessions are invalidated
    - If `notify=true`, sends Indonesian-language notification emails to BOTH old (security warning) and new (welcome) addresses via Hostinger SMTP. Email failures don't block the change (best-effort with warning logs).
- **Backend `routes/labels.py`** — fast dashboard:
  - `label_dashboard` `last_month_revenue` now reads from `monthly_analytics` cache (dim=label, key=label_id, sorted by period desc, limit 1) → sub-second.
  - Falls back to live aggregate via `db_bg` (CSOT-uncapped) only if cache miss — was using CSOT-capped `db` which timed out for labels with massive history.
- **Frontend `pages/admin/LabelDetail.jsx`**:
  - New "Akun Login" section in the Aksi card with current email + 2 buttons (data-testid `admin-label-change-email`, `admin-label-revoke-account`)
  - Modal "Cabut Akses Akun" (amber theme) with reason input + cascade-to-artists checkbox showing actual artist count
  - Modal "Ganti Email Akun" (sky theme) with old/new email fields + notify toggle (default on)
  - When `user_id` is null but `previous_account_email` exists, shows breadcrumb directing admin to "Buat Akun" for re-creation
- **Tests** `/app/backend/tests/test_phase25_label_account_lifecycle.py` (10/10 PASS):
  - Revoke clears user_id + disables user + bumps token_version (artists untouched without cascade)
  - Revoke cascade disables N artists
  - Revoke 400 if label has no user
  - Revoke 403 for admin_finance
  - Change email updates both rows + bumps token_version
  - Change email 409 on duplicate, 400 on invalid format, 400 on same email
  - Change email 403 for admin_finance
  - Label dashboard reads `last_month_revenue` from `monthly_analytics` cache (sub-second)
- Combined Phase 22+23+23.1+23.2+24+25 regression: **37/37 PASS**.

### Phase 24 — Materialized Rollups Everywhere (2026-06-29)
User report (production): after Phase 23.2 backfill, Analytics dashboard was empty (no chart/Top-10), Artist Management showed no data even with period filter, and Release Management took 30-60s to load each page. Root cause: Artist/Release endpoints aggregated against `royalty_lines` (1M+ rows) on every page load → CSOT timeouts + slowness. Analytics cache (`monthly_analytics`) wasn't always rebuilt after a backfill because the auto-trigger was fire-and-forget.

- **Backend `routes/admin_analytics.py`**:
  - Added `release` to `DIMENSIONS` — rebuild now produces `dim='release'` docs with hydrated `release_title`, `release_artist`, `upc`, `release_date`.
  - New compound index `(dim, key, period)` on `monthly_analytics` for sub-second entity-id lookups (Artist/Release/Label Management list endpoints).
  - Persisted `rollup_health` doc (id='monthly_analytics') with last finished_at, duration_sec, doc_count, per_dim_counts, last_error/last_error_at — survives pod restart.
  - `recompute_monthly_analytics()` now writes failure state to `rollup_health` so admin UI can see if a previous rebuild crashed.
  - `/admin/analytics/status` falls back to `rollup_health` when this pod's in-memory `_last_recompute_meta` is empty (fresh restart scenario).
- **Backend `routes/revenue_rollup.py`** (rewritten):
  - `rollup_revenue_by_id` now reads from `monthly_analytics` cache via `_rollup_from_cache` (sub-second, indexed on `(dim, key, period)`).
  - Graceful degradation: if cache is empty for that dim (post-deploy / post-backfill before async recompute finishes), falls back to live aggregate over `royalty_lines` AND triggers an async cache rebuild for next time.
  - Used by Artist Management (`artists.py`), Release Management (`releases.py`), and Label dashboard — all three pages now load in <500ms regardless of `royalty_lines` row count.
- **Frontend `pages/admin/Analytics.jsx`**:
  - Status Cache panel now shows per-dim counts (total/platform/country/label/artist/track/release) with formatted numbers.
  - Surfaces `last_error` in a red callout box if the most recent rebuild failed.
  - Updated help text to mention backfill is also an auto-trigger.
- **Tests** `/app/backend/tests/test_phase24_materialized_rollups.py` (4/4 PASS):
  - Cache hit returns sentinel value (proving cache path wins over live).
  - Cache miss → live fallback returns correct aggregated value.
  - Rebuild endpoint emits `dim='release'` docs with hydrated title.
  - `rollup_health` persisted across pod restarts; `/status` returns per_dim_counts.
- Combined Phase 22+23+23.1+23.2+24 regression: **27/27 PASS**.

### Phase 23.2 — Backfill `royalty_lines.period` from `row_period` (2026-06-29)
User uploaded yearly Believe CSVs (2020-2024 yearly + 2025 + 2026 Q1) BEFORE Phase 23.1 was deployed, so all rows got tagged with the form's `period` field instead of CSV's `Bulan Laporan` column. Artist/Release/Label/Analytics dashboards consequently could not show proper monthly grouping. Lucky break: every `royalty_lines` document already stores `row_period` (raw CSV column value) untouched alongside `period`, so a derived backfill is sufficient — no need to re-upload CSV.

- **Backend** `/app/backend/routes/migrate.py`:
  - New endpoint `POST /api/admin/migrate/royalty/backfill-period-from-row` (super_admin only). Form fields: `dry_run` (bool, default true) and optional `import_id` (scope to one import; omit for full DB).
  - Dry-run aggregates per-import preview: rows_to_fix, old_periods_in_lines, new_periods_will_be, current vs new period_breakdown.
  - Commit phase: chunked `_id`-paginated `update_many` via `db_bg` (10k rows/batch) using MongoDB aggregation pipeline syntax `[{$set: {period: "$row_period"}}]` for server-side field-to-field copy (zero Python round-trip). Loop guard against infinite iteration on silent server-side failures.
  - After commit, calls `_recompute_import_period_metadata()` for each affected import to refresh `period_breakdown`, `period_start`, `period_end`, `is_multi_period`, `period` (display label). Invalidates `metrics_cache` + monthly analytics cache.
  - Idempotent — re-running finds 0 rows-to-fix.
- **Frontend** `/app/frontend/src/pages/admin/Migrate.jsx`:
  - New tab `backfill-period` (data-testid `admin-migrate-tab-backfill-period`) with `RotateCw` icon — 6th in the Migrate page tab strip.
  - `BackfillPeriodPanel` component: amber warning explaining when to use, scope dropdown (loaded from `/royalty/admin/imports`), dry-run toggle (default true), submit button. After response: preview/commit banner, 3-card stats grid, per-import table (filename, status, total/will-fix counts, old→new periods), recomputed-imports table (display period, range, distinct months).
- **Tests**: `/app/backend/tests/test_phase23_2_backfill_period.py` (6/6 PASS): dry-run no-mutation; full commit + recompute (yearly 24-row import → 12 month breakdown after, with month-1 idempotent skip); RBAC (super_admin only); 404 on unknown import_id; full-DB backfill only touches mismatched rows; no-changes-needed returns zero counts. Combined Phase 23 regression: **34/34 PASS**.

### Phase 23.1 — CSV `Bulan Laporan` priority + async Delete (2026-06-29)
Two production bugs reported back-to-back: (1) royalty imports were tagging ALL rows with the form's `period` field, overwriting the actual CSV `Bulan Laporan` column values — breaking multi-period imports for analytics, FIFO withdraw, and rollups. (2) The "Hapus" button on stuck imports did nothing because the synchronous `delete_many` over 600K-1M `royalty_lines` exceeded the request timeout.

- **Fix #1 — CSV column wins** (`routes/royalty.py`):
  - Line 546: `line_period = raw.get("row_period") or period` (was `period or raw.get("row_period")`). CSV's `Bulan Laporan` column is now ALWAYS the source of truth. Form's `period` only kicks in if a row has no `Bulan Laporan` value (true legacy CSVs).
  - `display_period` derivation also reordered to derive strictly from `sorted_periods`; form period is only a last-resort default when the CSV had zero valid rows.
- **Fix #2 — Async background delete** (`routes/royalty.py`):
  - `admin_delete_import` now flips status to `deleting` immediately + returns **HTTP 202** + spawns `_delete_import_bg`. No more silent timeout on 600K-1M row imports.
  - `_delete_import_bg` chunks the royalty_lines wipe via `db_bg` + `_id`-paginated 5,000-row batches, writes `deletion_progress_lines` for live progress, then cleans auto-created entities + R2 + local CSV + the import doc itself. On exception, surfaces `error_message` on the import doc.
  - New status `deleting` whitelisted in `DELETABLE_STATUSES` so re-clicking Hapus on an already-deleting row is a no-op (returns 202 again).
  - `admin_list_imports` exposes `progress_pct` derived from `deletion_progress_lines / total_lines` so the UI can render a live bar.
- **Frontend `RoyaltyImport.jsx`**:
  - `remove()` now treats 202 as success, shows toast "Penghapusan dijadwalkan — baris akan hilang setelah cleanup selesai".
  - Auto-poll trigger extended to include `deleting` status.
  - New rose-colored `deleting` status badge with spinner.
- **Tests**:
  - `/app/backend/tests/test_phase23_1_bulan_laporan_priority.py` (2/2 PASS) — multi-period CSV preserves true row periods; legacy CSV without column falls back to form period.
  - `/app/backend/tests/test_phase16_4_delete_import_and_dashboard_cache.py` updated: delete now expects 202 + polls for 404. (11/11 still PASS.)
  - Combined regression: **34/34 PASS** (Phase 16.4 + 16.5 + 22 + 23 + 23.1).

### Phase 23 — Stuck Royalty Import Recovery (2026-06-29)
User reported in production: 2 large CSV imports (600K + 750K rows) stuck at "Processing 99%" for >1 hour. Root cause was twofold — (1) the UI caps display at 99% while status='processing', and (2) the final `update_one` to flip status to `pending_review` used the CSOT-capped `db` client, so Atlas slowness silently aborted the transition. **Retry was also non-responsive** because `_reset_import_for_retry` ran `delete_many` over 600K+ rows through `db` and timed out.

- **Backend** `/app/backend/routes/royalty.py`:
  - Final status-flip in `_process_csv_import_inline` now uses `db_bg` (CSOT-uncapped).
  - Error-state update in `_process_csv_import_bg` tries `db_bg` first, falls back to `db` so failures always surface.
  - `_reset_import_for_retry` migrated to `db_bg` + chunked `_id`-paginated `delete_many` (5,000 rows/batch) — Retry can now wipe a 1M+ row partial import without timing out.
  - **New endpoint** `POST /api/royalty/admin/imports/{id}/force-finalize` (super_admin + admin_finance) — recomputes counters from actual `royalty_lines` rows (matched/unmatched/total_revenue_eur/total_label_idr/period_breakdown) and force-flips status to `pending_review`. If 0 rows exist in MongoDB → marks `error` instead. Pure derived recompute, idempotent, no row inserts. Reusable helper `_recompute_import_stats_from_lines()`.
- **Backend** `/app/backend/routes/cron_jobs.py`:
  - New `watchdog_stuck_royalty_imports()` cron — every 15 minutes (60s first-run delay), finds imports `status='processing'` with `updated_at` older than `STUCK_IMPORT_AFTER_MINUTES=30` → calls the same `_recompute_import_stats_from_lines` helper. Auto-flips to `pending_review` (with `watchdog_recovered=true` flag) if rows exist, else `error` with descriptive Indonesian message.
  - Manual trigger endpoint `POST /api/admin/cron/stuck-imports-check` (super_admin + admin_finance) for impatient admins.
- **Frontend** `/app/frontend/src/pages/admin/RoyaltyImport.jsx`:
  - New amber "Force Finalize" button (`data-testid='royalty-import-force-finalize-{id}'`) visible for `processing`/`error` rows. Confirms via `window.confirm` and surfaces matched/total row counts on success.
- **Tests**: `/app/backend/tests/test_phase23_force_finalize.py` (8 tests, **8/8 PASS**) covering: recompute correctness with multi-period rows, 0-row → error transition, status guard (rejects published/dana_received), RBAC (finance allowed, support/release blocked), watchdog manual trigger + recovery E2E. Combined regression with Phase 16.2 / 16.3 / 16.4 / 16.5 = **40/40 PASS**.

### Phase 22 — Legacy Withdraw CSV → Period-end FIFO Migration (2026-06-29)
User uploaded `music_withdrawals.csv` (legacy columns: nama_label, period_start, period_end, amount, exchange_rate, status, …) and needed it mapped into the modern FIFO system from Phase 20.

- **Backend** `/app/backend/routes/migrate.py` (lines 767-1113):
  - `POST /api/admin/migrate/withdraws-legacy-period` (super_admin only) — multipart upload, 4 toggle flags: `dry_run`, `create_history_docs`, `flip_royalty_lines`, `adjust_balances`.
  - Fuzzy label matcher `_normalize_label_name()` strips `PT ` / `PT, ` / `PT. ` prefix, lowercases, drops `.,;:!?()[]{}\"'` punctuation and `-_`, collapses whitespace. Verified against punctuation/casing/prefix variants.
  - Per label: `last_withdrawn_period = MAX(period_end)` (advance-only, idempotent), flips `royalty_lines.status pending|available → withdrawn` for period in `(old_last_withdrawn_period, new_last_withdrawn_period]` via chunked `_id` paginated update_many through `db_bg` (CSOT-safe).
  - Decrements `labels.balance_pending_idr` / `balance_available_idr` by summed `label_idr` of flipped lines (computed BEFORE flip).
  - Inserts one `withdraw_requests` doc per CSV row (`status='paid'`, `legacy_import=true`, `legacy_trx_id`), deduped by `(label_id, legacy_trx_id)`.
  - Returns rich preview/commit payload: `dry_run, total_csv_rows, matched_labels, unmatched_label_names, totals_preview, label_summaries, commit`.
- **Frontend** `/app/frontend/src/pages/admin/Migrate.jsx` — new `WithdrawFifoPanel` (lines 356-528) added as 5th tab "Withdraws (Period FIFO)" (data-testid `admin-migrate-tab-withdraws-fifo`). Renders amber spec banner, file picker, submit button, 4 flag toggles, dry-run/commit banners, stats grid (5 cards), Balance Adjustment Preview, Period Update Preview, Unmatched Labels collapsible list, Per-Label Summary table.
- **Route guard tightened** `/app/frontend/src/App.js` — `/admin/migrate` now wrapped in `<ProtectedRoute roles={["super_admin"]}>` so sub-admins are redirected to `/admin/dashboard` client-side (backend RBAC was already 403, this closes the UX gap flagged by iteration 25).
- **Tests**: `/app/backend/tests/test_phase22_legacy_withdraw_migration.py` (7) + `/app/backend/tests/test_phase22_extras.py` (5 new: finance/release RBAC + flag isolation) = **12/12 PASS**. Frontend E2E confirmed via iteration 25 testing agent (panel render, dry-run upload, stats grid, dry-run banner, error toast all PASS).

### Phase 20 + 21 — Withdraw FIFO & Artist/Release Rollup (2026-06-29)
Per user spec: every withdraw consumes ALL `available` royalty_lines whose `period` > the label's last_withdrawn_period (force-full, no partial). Artist/Release management lists now show total revenue + last active bulan laporan from royalty_lines.

- **Phase 20 backend** (`/app/backend/routes/withdraw.py`):
  - `_compute_withdrawable(label_id)` helper aggregates `royalty_lines` where `label_id=X AND status='available' AND period > last_withdrawn_period` (strict `$gt` to prevent double-spend). Returns `{withdrawable_idr, period_from, period_to, lines_count, last_withdrawn_period}`.
  - `GET /api/withdraw/label/computed` — exposes the FIFO sum + range to the UI so labels see what's about to be withdrawn before clicking submit.
  - `POST /api/withdraw/label/request` — REFACTORED. No longer accepts `amount_idr` from body. Auto-computes via the helper. Rejects if computed < `MIN_WITHDRAW_IDR` (1M IDR). Stores `period_from`, `period_to`, `lines_count` on the withdraw doc so admin can audit + mark_paid can flip the correct line range.
  - `mark_paid` action — after marking the request paid: chunked `update_many` (via `db_bg`, CSOT-safe, 5,000-row batches paginated by `_id`) flips matching royalty_lines from `available → withdrawn`, then bumps `labels.last_withdrawn_period = wd.period_to` so the next withdraw starts strictly after.
  - Reject path unchanged — refunds balance, leaves royalty_lines untouched.

- **Phase 21 backend** (`/app/backend/routes/revenue_rollup.py` + admin/artists/releases routes):
  - Shared helper `rollup_revenue_by_id(field, ids, period_from?, period_to?)` aggregates royalty_lines by `artist_id` / `release_id` / `label_id` / `track_id` with optional period window. Excludes unmatched rows (FK to label/artist unreliable).
  - Patched 4 endpoints to enrich responses with `revenue_eur`, `revenue_idr`, `royalty_lines_count`, `first_active_period`, `last_active_period`:
    - `GET /api/admin/artists`, `GET /api/admin/releases` — accept `?period_from=&period_to=`
    - `GET /api/artists/` (label), `GET /api/releases/` (label) — same shape

- **Phase 20 frontend** (`/app/frontend/src/pages/label/Withdraw.jsx` — REWRITTEN):
  - Removed manual amount input. Replaced with read-only FIFO range card: "Range Bulan Laporan: {fmtPeriod(from)} → {fmtPeriod(to)}" + total amount + line count + last_withdrawn_period.
  - "Tarik Semua: Rp X" button (`data-testid='withdraw-submit-button'`) disabled when window closed / no eligible balance. `window.confirm` before POST.
  - Riwayat withdraw rows now show the period chip ("Jan 2025 - Apr 2026").

- **Phase 21 frontend**:
  - `/app/frontend/src/pages/admin/Artists.jsx` — REWRITTEN. Table with 5 columns: Artist | Label | Revenue (default sort desc) | Aktif Terakhir | Baris/Status. Period dropdown filters (populated from `/api/admin/analytics/periods`). Totals card.
  - `/app/frontend/src/pages/admin/Releases.jsx` — REWRITTEN. 6 columns: Rilisan | Label | Release Date | Revenue | Aktif Terakhir | Status. Status filter, period filter, sort selector (revenue/date).
  - `/app/frontend/src/pages/label/Artists.jsx` — adds emerald "Royalti Aktif" block to each artist card.

- **Tests**: `/app/backend/tests/test_phase20_21_withdraw_fifo_rollup.py` (21 tests, 20 PASS + 1 environmental skip). Combined regression: 60+/61 PASS.

### Phase 18 + 19 — Monthly Analytics dashboard (2026-06-29)
User uploaded ~1M royalty lines (Believe CSV 2020-2026-04). Requested admin dashboard with charts driven by "bulan laporan" (royalty_lines.period). Period axis = YYYY-MM. Filterable by label/platform/country/artist/track.

- **Backend `/app/backend/routes/admin_analytics.py`** — pre-computed `monthly_analytics` collection (~7 dimensions × periods × keys). Atomic staging-collection swap (insert → drop → rename) avoids half-recomputed window. `asyncio.Lock` guards concurrent rebuilds.
  - `POST /api/admin/analytics/recompute` — super_admin only. Rebuild from `royalty_lines`. Routed via `db_bg` (no CSOT cap).
  - `GET /api/admin/analytics/monthly?period_from=&period_to=&label_id=&platform=&country=&artist_id=&track_id=&top_n=` — admin role. Returns `{source: cache|live, kpi: 8 fields, monthly: [...], top_platforms, top_countries, top_labels, top_artists, top_tracks}`. Cache path ~50ms; falls back to live aggregate (db_bg) when any dimension filter is set. Hydrates label/artist/track ids to names in one batched `$in` per collection.
  - `GET /api/admin/analytics/periods` — list of available YYYY-MM (sorted asc) with min/max for UI range picker. Falls back to `royalty_lines.distinct("period")` if cache cold.
  - `GET /api/admin/analytics/status` — last recompute meta (running, finished_at, duration_sec, doc_count).
  - **Auto-trigger** post-publish (`_publish_bg` step 5) + post-delete-import (`admin_delete_import`).
- **Frontend `/app/frontend/src/pages/admin/Analytics.jsx`** — full dashboard via `recharts 3.6.0`:
  - 6 KPI tiles: Revenue IDR / EUR / Total Streams / Distinct Platforms / Negara / Track.
  - Line chart **Pendapatan per Bulan Laporan** dengan dual Y-axis (IDR kiri / EUR kanan, gradient stroke).
  - 5 top-10 panels: Platform, Negara, Label, Artist, Track. Click row to apply as filter.
  - Filter row: 5 dropdowns (multi-select-style) + "Clear semua" + indicator "filter aktif (slow path)".
  - Period range pickers (from/to YYYY-MM dropdowns) + quick range buttons (12 Bulan Terakhir, Tahun Ini, Semua).
  - "Rebuild Cache" button → POST recompute, spinner, refetch.
  - Status Cache card: source (cache/live), last-update timestamp, doc_count, durasi.
- **Routing & access**:
  - `/admin/analytics` route wrapped in a granular `<ProtectedRoute roles=["super_admin", "admin_finance"]>` — direct URL access by `admin_release`/`admin_support`/`admin_content` redirects back to `/admin/dashboard`.
  - Sidebar `BarChart3` icon nav entry hidden from non-super/non-finance roles.
- **Tests**: `/app/backend/tests/test_phase18_analytics.py` (20 PASS + 1 skip). Combined regression: **60/60 PASS**.

### Phase 16.5 — Batched CSV ingestion (2026-06-29)
Optimized the `_process_csv_import_inline` hot path so 1M-row CSV imports drop from ~10 minutes to ~2-3 minutes on Atlas.

- **BATCH_SIZE 2,000 → 5,000** (≈4-8 MB per insert_many round trip, well under 16 MB BSON cap & 100k bulk-op limit, 2.5× fewer round trips).
- **`ordered=False` on every insert_many** (lines/labels/releases/tracks) → MongoDB parallelizes within each batch + skips duplicate-key errors instead of aborting.
- **All bulk writes route through `db_bg`** (CSOT-uncapped client) → production Atlas no longer kills a slow insert at 10s.
- **Throttled progress writes** — `PROGRESS_EVERY_N_FLUSHES = 10` reduces `royalty_imports` doc updates from ~500 (per 1M-row import) to ~20, eliminating write contention. Final flush forces a progress write so the UI sees exact totals.
- **Pre-flight cursor reads** (labels / tracks / releases / pct_history maps) also routed through `db_bg` — at ~100k tracks in production, the full collection scan was already brushing against CSOT.
- **Missing indexes added** in `seed_indexes_and_admins()`:
  - `tracks.isrc` and `tracks.label_id` — CSV matcher's hot lookup
  - `releases.upc` — fallback matcher
  - Compound `royalty_lines (import_id, match_status, status)` — used by `_publish_bg` chunked pagination
  - Compound `royalty_lines (import_id, label_id)` — used by per-label aggregate in admin import detail
  - `seed_indexes_and_admins()` itself migrated to `db_bg` (creating an index on a 1M-row collection itself exceeds CSOT cap on first run).
- **Local benchmark**: 10,000 synthetic rows → ingestion in 1.2s = ~8,700 rows/s. Projected 1M-row Atlas wall-time ≈ 2-3 min (vs prior ~10 min).
- **Tests**: `tests/test_phase16_5_batched_csv_import.py` (6 — source asserts + end-to-end perf bench). Combined regression: 40/40 PASS.

### Phase 16.4 — Delete failed royalty imports + dashboard revenue cache (2026-06-29)
User-reported: failed periods can't be deleted, and the admin dashboard is "sangat lama dibuka" since the 1M-row CSV import.

- **`DELETE /api/royalty/admin/imports/{id}`** (super_admin only). Allowed statuses: `awaiting_upload`, `processing`, `error`, `publish_error`, `pending_review`. Refused for `published` / `publishing` / `dana_received` because those have `balance_transactions` tied to label balances (HTTP 400 with Indonesian explainer). Cascading delete cleans `royalty_lines` (via `db_bg` — chunked), labels/releases/tracks created from this import (`auto_created_from` match), the uploaded R2 object (best-effort), the local CSV file, then the import doc itself. Returns row counts.
- **Dashboard revenue cache (stale-while-revalidate)**: `_dashboard_revenue_cache` module-local dict + Mongo `metrics_cache.dashboard_revenue` persistence. First load after pod boot warms from Mongo; if both empty, sync recompute. Subsequent loads serve from cache; if older than 60s, fire-and-forget background refresh runs while the cached value is returned immediately. Cache invalidation on publish-complete + delete-import (lazy import to avoid cycle).
- **`POST /api/admin/dashboard/refresh-revenue`** (super_admin + admin_finance only — 403 for other admin roles). Forces a sync recompute for impatient admins after fresh imports.
- **UI**:
  - `/admin/royalty` list — every deletable row gets a red Trash2 "Hapus" button (`data-testid=royalty-import-delete-{id}`). Confirms via `window.confirm`, then refreshes the list.
  - `/admin/royalty/{id}` detail — "Hapus Import" button (`data-testid=admin-royalty-delete`). On success, redirects back to `/admin/royalty` after 1.5s.
- **Tests**: `tests/test_phase16_4_delete_import_and_dashboard_cache.py` (11 new) + `tests/test_phase16_3_csot_uncapped_client.py` (5 updated to be refactor-tolerant) — 34/34 PASS in combined suite.

### Phase 16.3 — CSOT-uncapped Mongo client `db_bg` (2026-06-29, hotfix)
Production user reported repeated publish failures + 500s on `/api/admin/dashboard` and `/api/royalty/admin/imports/{id}` after redeploy:
> Publish gagal: customer-apps-shard-00-01.fpzjgt.mongodb.net:27017:
> The read operation timed out (configured timeouts: timeoutMS: 10000.0ms)

Root cause: Emergent's production `MONGO_URL` includes `timeoutMS=10000` (PyMongo CSOT — Client-Side Operation Timeout). Every heavy aggregate / `update_many` over the 1M-row `royalty_lines` collection blows through that 10s cap.

- Added a second Motor client `client_bg` / `db_bg` in `/app/backend/routes/deps.py` with `timeoutMS=None`, `socketTimeoutMS=None`. Production-Atlas connections still apply server-side `maxTimeMS` where set, but client-side ceiling is lifted.
- Switched every heavy `royalty_lines` op to `db_bg`:
  - `_publish_bg` (background publish — already chunked; all aggregate + chunked find/update_many now via `db_bg`).
  - `/api/admin/dashboard` revenue aggregate (entire collection sum).
  - `/api/royalty/admin/imports/{id}` top-500 sample + per-label breakdown aggregate.
  - `/api/royalty/admin/imports/{id}/mark-dana-received` — also migrated to chunked `_id` update_many (was a single huge update_many that would hit `maxTimeMS=50` on Atlas).
- Belt-and-suspenders fallback added in `_publish_bg`: if writing `publish_error` via `db_bg` fails, the foreground `db` is tried as last-ditch.
- New regression suite `/app/backend/tests/test_phase16_3_csot_uncapped_client.py` (5 tests, all PASS) statically guards against future agents reverting any of these calls back to `db`.

### Phase 17 — Security Hardening (2026-06-29)
Four critical/medium audit findings remediated. 18/18 security + regression tests PASS.

- **SEC-001 — Token leak fixed.** `/api/auth/forgot-password`, `/api/auth/register`, `/api/auth/resend-verification` no longer return `reset_token` / `verification_token` in HTTP bodies. Tokens are persisted in MongoDB (`password_reset_tokens` / `email_verification_tokens`) and delivered only via Hostinger SMTP.
- **SEC-001 — Xendit webhook locked.** `/api/payments/webhook/xendit` now requires the `x-callback-token` header (constant-time compared to `XENDIT_CALLBACK_TOKEN` env). Fails closed (HTTP 503) when env var is unset → no unauthenticated payment-confirmation bypass possible until live Xendit is wired.
- **SEC-002 — Per-email brute-force lockout.** Login lockout is now tracked at two levels (`email:<addr>` + `<ip>:<addr>`). Attackers rotating `X-Forwarded-For` headers can no longer bypass the 5-attempt threshold. xfail marker removed from `test_brute_force_lockout_after_5`.
- **SEC-003 — Session invalidation on password reset.** JWT access + refresh tokens now carry a `tv` (token_version) claim. `make_get_current_user` enforces `tok_tv == user.token_version`. `reset-password` increments `token_version` → all prior access & refresh tokens immediately rejected with 401. Outstanding (other) reset tokens for the same user are also marked `used=true` to prevent re-use. Login attempts counter is cleared so the user isn't locked out after a successful reset. Legacy tokens (without `tv`) decode to `tv=0` and match legacy users with missing `token_version` field → backwards-compatible.
- **SEC-004 — HTML escape in email bodies.** Added `email_service.h()` (built on `html.escape(..., quote=True)`); every user-controlled interpolation in transactional emails (`pic_name`, `label_name`, `description`, `bank_name`, `account_number`) is now escaped.
- **Tests:** `/app/backend/tests/test_phase17_security.py` (7) + `/app/backend/tests/test_phase17_regression.py` (11) — both at 100%.

## Files of Reference (entry points)
- Backend: `/app/backend/server.py` (slim 101-line entry), `/app/backend/routes/` (modular routers), `/app/backend/models.py`, `/app/backend/auth_utils.py`, `/app/backend/royalty_utils.py`.
- Frontend: `/app/frontend/src/App.js`, `/app/frontend/src/api/AuthContext.jsx`, `/app/frontend/src/pages/Landing.jsx`, `/app/frontend/src/pages/label/*.jsx`, `/app/frontend/src/pages/admin/*.jsx`.
- Tests: `/app/backend/tests/test_phase{2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17}_*.py` + `test_refactor_smoke.py` + `test_rilismusik_api.py`.
