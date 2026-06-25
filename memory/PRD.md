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

## Test credentials
See `/app/memory/test_credentials.md`.

## Prioritized Backlog

### P0 (next session)
- **Xendit LIVE integration** — replace mock-pay with real Xendit invoice/webhook for PPR + Subscription tiers + WAMI add-on. Needs API keys.
- **Email notifications LIVE** (Resend / SendGrid) — currently only in-app + console-logged.

### P1 (Production polish)
- Cloud Storage (S3 / Cloudinary) for WAV + cover + contract PDFs.
- PATCH /api/admin/labels/{id} should accept `subscription_tier` (admins currently can't change tier via API).
- CMS Landing Page dynamic linkage (Admin CMS already drives 12 keys — verify all are referenced live).
- Replace dev-mode token returns from auth endpoints with real email send.
- Google OAuth login (Emergent managed).
- PDF export of royalty report (currently CSV only).
- Contract MIME magic-byte check (currently extension-only).

### P2 (Phase 7+ — Growth)
- Public artist profile pages, royalty forecasting.
- Referral program (1 month subscription credit per onboarding).
- Mobile native app.
- Multi-artist royalty splits per track.

## Files of Reference (entry points)
- Backend: `/app/backend/server.py` (slim 101-line entry), `/app/backend/routes/` (modular routers), `/app/backend/models.py`, `/app/backend/auth_utils.py`, `/app/backend/royalty_utils.py`.
- Frontend: `/app/frontend/src/App.js`, `/app/frontend/src/api/AuthContext.jsx`, `/app/frontend/src/pages/Landing.jsx`, `/app/frontend/src/pages/label/*.jsx`, `/app/frontend/src/pages/admin/*.jsx`.
- Tests: `/app/backend/tests/test_phase{2,3,4,5,6}_*.py` + `test_refactor_smoke.py` (115 tests / 114 pass / 1 intentional skip).
