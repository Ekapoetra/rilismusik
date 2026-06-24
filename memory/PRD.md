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

## What's Been Implemented (Phase 1 MVP + Phase 2 Royalty & Finance) — 2026-06-24
### Phase 1 (initial release)
- **Landing page** — full iOS-inspired glassmorphism (floating navbar, hero floating cards, royalty simulator, pricing, FAQ accordion), 100% CMS-driven.
- **Auth** — register/login/logout/refresh/me, email verification (dev token), forgot/reset, brute-force lockout (X-Forwarded-For aware), httpOnly cookies + JWT + bcrypt.
- **Label** — dashboard stats, releases (list + 3-step upload wizard with WAV / 3000×3000 / date ≥7d validation + audio player + edit), artist sub-accounts, profile + bank, invoices + subscription (MOCK Xendit).
- **Admin** — multi-role console (5 roles, role-filtered sidebar): 12 metrics, label management (status + royalty %), release review (approve/need_revision/reject/deliver/mark_live/takedown + ISRC/UPC + payment guard), artists, payments, CMS (7 tabs), admin users (super admin only), activity logs.

### Phase 2 (Royalty & Finance) — newly added
- **CSV royalty import** — admin uploads Believe CSV (EUR), auto-detect headers (ISRC, UPC, Title, Artist, Platform, Country, Quantity, Revenue), tries ISRC → UPC matching, calculates per-line distributor fee (5%) and label share with **history-aware percentage** (royalty_percentage_history per period).
- **Manual exchange rate** EUR→IDR per period (no auto-fetch).
- **Status flow**: `pending_review` → `published` (kredit ke `balance_pending_idr` semua label) → `dana_received` (pindah ke `balance_available_idr`). Setiap transaksi dicatat di `balance_transactions` ledger.
- **Withdraw window**: Asia/Jakarta `withdraw_window_state()` — request open 1–14, payment window 15–20, closed 21+ (button disabled). Min Rp 1.000.000. Bank account required (admin verify bank).
- **Withdraw admin actions**: approve / reject (refund) / mark_paid (upload bukti pembayaran PDF/JPG + payment reference).
- **Label royalty report** — period selector, summary cards (total IDR, streams, lines), breakdown per platform & country, top tracks list, filterable line table (platform, country), **CSV export** endpoint streaming.
- **Bank verification** — admin can verify bank account (sets `bank_verified=True`).

## Prioritized Backlog
### P0 (next session — Phase 3: Support & Legal)
- Support ticketing (8 categories incl. takedown, edit metadata/audio/cover, Content ID).
- Contracts upload + status (Contract Active/Expired/Pending/Terminated).
- Blacklist management UI.
- Email notifications (Resend/SendGrid integration).
- Dashboard in-app notifications.
- Subscription expiry transition + reminder.

### P1 (Polish / Production-ready)
- Real Xendit live integration (key gathering + webhook signature verification).
- Real email provider (replace dev token returns).
- Google OAuth login (Emergent managed).
- PDF export of royalty report (currently CSV only).
- Bulk admin actions (import old labels CSV).
- Tax/PPN automation, multi-artist royalty splits per track.

### P2 (Phase 4+ — Growth)
- Public artist profile pages, royalty forecasting.
- Referral program (1 month subscription credit per onboarding).
- Mobile native app.

## Next Tasks
1. Implement Phase 2 (Royalty + Withdraw) when user confirms.
2. Gather Xendit live keys + email provider key when ready to move out of MOCK.
3. Add export PDF/Excel reports.
4. Future: Google login + WhatsApp notifications.

## Files of Reference (entry points)
- Backend: `/app/backend/server.py`, `/app/backend/auth_utils.py`, `/app/backend/models.py`.
- Frontend: `/app/frontend/src/App.js`, `/app/frontend/src/api/AuthContext.jsx`, `/app/frontend/src/pages/Landing.jsx`, `/app/frontend/src/pages/auth/Login.jsx`, `/app/frontend/src/pages/label/UploadRelease.jsx`, `/app/frontend/src/pages/admin/Dashboard.jsx`, `/app/frontend/src/pages/admin/CMS.jsx`.
