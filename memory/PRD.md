# RILIS MUSIK — Product Requirement Document (PRD)

## Original Problem Statement
Web platform for Indonesian indie music distribution to 150+ DSPs via Believe. Three main parts:
1. **Landing Page** with iOS glassmorphism + CMS-editable content.
2. **Label Dashboard** (mobile-first): upload releases (WAV + 3000×3000 cover + metadata + release date ≥7 days), manage artists, royalty, withdraw, invoice, support, contracts.
3. **Admin Dashboard** (desktop-first) with multi-role: Super Admin, Release, Finance, Support, Content/CMS.

Pricing: Pay Per Release Rp35.000 / Annual Subscription Rp500.000. Distributor fee 5%, default label share 60% (editable per label with history).
Withdraw window 1–14 (request), 15–20 (payment), 21–end disabled. Min withdraw Rp1.000.000.
Believe CSV (EUR) uploaded monthly by admin → IDR via manual exchange rate.

## Tech Stack
- **Backend**: FastAPI (Python 3.11), Motor (async MongoDB), JWT auth (httpOnly cookies), bcrypt, Pillow for image validation.
- **Frontend**: React 19 + React Router 7, Tailwind 3, axios with `withCredentials`, Plus Jakarta Sans + Manrope fonts.
- **Storage**: MongoDB (collections: users, labels, artists, releases, tracks, payments, royalty_imports, royalty_lines, withdraw_requests, bank_accounts, support_tickets, ticket_comments, contracts, landing_settings, activity_logs, email_verification_tokens, password_reset_tokens, login_attempts, royalty_percentage_history). Local filesystem for uploads under `/api/files`.
- **Payments**: Mock Xendit (real webhook handler ready at `/api/payments/webhook/xendit`).

## Architecture
- **Single FastAPI app** with routers: `/api/auth`, `/api/label`, `/api/releases`, `/api/artists`, `/api/payments`, `/api/cms`, `/api/admin`.
- **AuthContext** in React, JWT in httpOnly cookies (`access_token` + `refresh_token`).
- Three layouts: public landing, `LabelLayout` (mobile-first sidebar + bottom nav), `AdminLayout` (dark desktop-first sidebar).
- Role-gated routes via `ProtectedRoute`.

## User Personas
1. **Label** — Indonesian indie label or independent artist. One main account per label. Submits releases, manages artists, monitors royalty + balance, withdraws.
2. **Artist Sub-Account** — created by a label. Sees only linked tracks + royalty (visibility controlled by label).
3. **Admin** — internal operator with one of: Super Admin / Admin Release / Admin Finance / Admin Support / Admin Content. Reviews releases, manages royalty, withdraw, tickets, CMS.

## Core Requirements (Static)
- Email verification on register (token simulated in MVP).
- Release upload validation: WAV audio, square 3000×3000 cover (Pillow check), release_date ≥ today+7.
- Pay-per-release: release status `awaiting_payment` until invoice paid → `under_review`.
- Annual subscription: active subscription bypasses per-release invoice.
- Admin actions on release: approve / need_revision / reject / deliver / mark_live / takedown.
- Admin update label: account_status (active/suspended/blacklisted), royalty %_default (with history).
- CMS: editable hero, benefits, pricing, FAQ, SEO, footer (key/value `landing_settings`).
- Admin user creation (super_admin only). Multi-role sidebar filtering.
- Activity logs on every important admin action.

## What's Been Implemented (Phase 1 MVP + Phase 2 Royalty & Finance + Phase 3 Support) — 2026-06-24
### Phase 1 (initial release)
- **Landing page** — full iOS-inspired glassmorphism (floating navbar, hero floating cards, royalty simulator, pricing, FAQ accordion), 100% CMS-driven.
- **Auth** — register/login/logout/refresh/me, email verification (dev token), forgot/reset, brute-force lockout (X-Forwarded-For aware), httpOnly cookies + JWT + bcrypt.
- **Label** — dashboard stats, releases (list + 3-step upload wizard with WAV / 3000×3000 / date ≥7d validation + audio player + edit), artist sub-accounts, profile + bank, invoices + subscription (MOCK Xendit).
- **Admin** — multi-role console (5 roles, role-filtered sidebar): 12 metrics, label management (status + royalty %), release review (approve/need_revision/reject/deliver/mark_live/takedown + ISRC/UPC + payment guard), artists, payments, CMS (7 tabs), admin users (super admin only), activity logs.

### Phase 2 (Royalty & Finance) — added
- **CSV royalty import** — admin uploads Believe CSV (EUR), auto-detect headers, ISRC→UPC matching, distributor fee (5%) + history-aware label %.
- **Manual exchange rate** EUR→IDR per period.
- **Status flow**: `pending_review` → `published` → `dana_received` with balance ledger.
- **Withdraw window** (1–14 request / 15–20 payment / 21+ closed), min Rp 1.000.000, bank verification.
- **Label royalty report** with breakdown per platform/country + CSV export.

### Phase 4 (Real Believe CSV + Sensitive-field redaction) — added 2026-06-24
- **Real Believe CSV parser** — full Indonesian header support (Bulan Penjualan, Negara, Judul track, Nama Artis, Judul rilis, Kuantias [misspelled], Pendapatan Bersih, Pendapatan Kotor, Harga Unit, Biaya Mekanis, Tingkat pembagian klien). Auto-detects semicolon delimiter and parses European decimals correctly (`0,000407547753` → `0.000407547753`).
- **Label name fallback match** — when ISRC/UPC don't match a release in DB, try matching CSV `Nama Label` to existing label name (case-insensitive). 4712/5000 (94.2%) rows matched on the real Believe sample.
- **Sensitive fields hidden from label/artist responses**: `Harga Unit`, `Biaya Mekanis`, `Pendapatan Kotor`, `Tingkat pembagian klien` are STORED for admin audit but stripped via `strip_sensitive()` before returning to label/artist users.
- **Reset Demo Data** endpoint (`POST /api/royalty/admin/reset-demo-data` with `confirm=RESET`, super_admin only) — wipes royalty imports + lines + transactions, resets all label balances to 0, deletes uploaded CSV files. UI: red danger-zone button + RESET-gated confirmation modal.
- **31/31 pytest passing** at `/app/backend/tests/test_believe_royalty.py`.
- Demo data: 1 import for 2025-05, 4712 matched lines across 4 demo labels (Khizanah Kreasi Gontor, Mustafa Kamal, WANWE RECORDS, Manawa Music).

### Phase 3 (Support & Legal) — added 2026-06-24
- **Support Ticketing System** — 8 categories (takedown, edit_metadata, edit_audio, edit_cover, content_id_claim, content_id_release, royalty_issue, other), 8 statuses (open, waiting_admin, waiting_label, in_progress, submitted_to_believe, done, rejected, cancelled).
- **Chat-style comment thread** with attachments (WAV / 3000×3000 cover / JPG/PNG/PDF/TXT/DOCX); auto status flip when label/admin comments; system messages for status changes.
- **Label** can create/view/cancel own tickets at `/label/support`. Strict cross-label isolation (403).
- **Admin** can list (filter by status/category/search), view detail, comment, change status + add internal notes at `/admin/tickets`.
- **22/22 pytest passing** at `/app/backend/tests/test_phase3_tickets.py`.

### Landing & UI polish — 2026-06-24
- New **Platforms section** showing all major DSP logos (Spotify, Apple Music, Deezer, YouTube Music, TikTok, Facebook/Instagram Music, Amazon Music, SoundCloud, Tidal, Shazam, iHeart Radio).
- Removed "60% default bagian label" from hero stats and pricing footer (replaced with "150+ platform digital").
- "Made with Emergent" badge hidden.

## Prioritized Backlog
### P0 (next session)
- **Xendit live integration** (Pay Per Release Rp35.000 + Annual Subscription Rp500.000) — needs API keys.
- **Contracts module** — upload kontrak, set masa berlaku, perpanjangan, status (Active/Expired/Pending/Terminated).
- **Blacklist management UI** (backend `account_status='blacklisted'` already wired; UI still pending).
- **Email notifications** (Resend/SendGrid) for verification, password reset, invoice, ticket updates.
- **In-app notifications** dashboard (bell icon).
- **Subscription expiry** transition + reminder cron.

### P1 (Polish / Production-ready)
- Real email provider (replace dev token returns).
- Google OAuth login (Emergent managed).
- PDF export of royalty report (currently CSV only).
- Bulk admin actions (import old labels CSV).
- Cloud Storage (S3/Cloudinary) for WAV + cover.
- Tax/PPN automation, multi-artist royalty splits per track.
- Phase-3-tester suggestions: MIME-type validation on uploads, `.strip()` on ticket subject/description, formal status-transition rules.

### P2 (Phase 4+ — Growth)
- Public artist profile pages, royalty forecasting.
- Referral program (1 month subscription credit per onboarding).
- Mobile native app.

## Next Tasks
1. **Xendit Payment integration** (block release submission until invoice paid).
2. **Contracts module** + **Blacklist UI** + **Email/in-app notifications**.
3. PDF export (currently CSV only).
4. Multi-artist royalty splits per track (currently 100% to label, artist views via track linkage).

## Files of Reference (entry points)
- Backend: `/app/backend/server.py`, `/app/backend/auth_utils.py`, `/app/backend/models.py`.
- Frontend: `/app/frontend/src/App.js`, `/app/frontend/src/api/AuthContext.jsx`, `/app/frontend/src/pages/Landing.jsx`, `/app/frontend/src/pages/auth/Login.jsx`, `/app/frontend/src/pages/label/UploadRelease.jsx`, `/app/frontend/src/pages/admin/Dashboard.jsx`, `/app/frontend/src/pages/admin/CMS.jsx`.
