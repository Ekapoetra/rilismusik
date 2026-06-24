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

## What's Been Implemented (Phase 1 MVP) — 2026-06-24
- **Landing page** — full iOS-inspired glassmorphism: floating pill navbar, hero with floating cards, 8 benefit cards, how-it-works timeline, pricing 2-column (PPR + Subscription), interactive royalty simulator, testimonials, FAQ accordion, footer, all CMS-driven.
- **Auth** — register/login/logout/refresh/me, email verification (dev token), forgot/reset password (dev token), brute force protection (5 attempts → 15 min lockout), httpOnly cookies, bcrypt, JWT.
- **Label dashboard** — overview metrics, status pills (subscription/contract/bank), recent releases.
- **Releases** — list (filter + search), 3-step upload wizard (metadata → tracks → cover+audio), validation (WAV / 3000×3000 / date ≥7d), submit flow with pay-per-release MOCK invoice OR subscription bypass, detail view with audio player, edit (draft / need_revision only).
- **Artists** — label can create artist sub-accounts (with password + visibility settings); artist dashboard with linked releases + visibility flags.
- **Profile + Bank** — edit profile, submit bank account (one-time only, requires admin verification).
- **Invoices** — label can buy Annual Subscription, see invoice list, mock-pay invoices.
- **Admin dashboard** — 12 metrics + royalty + last CSV info.
- **Admin Labels** — list/search/filter, detail page with status actions (activate/suspend/blacklist) + royalty %_default update (saves history).
- **Admin Releases** — list with status filter, detail page with approve/need_revision/reject/deliver/mark_live/takedown actions + ISRC/UPC entry, payment-blocked workflow.
- **Admin Artists** — list with label name.
- **Admin Payments** — invoice list with filters + MOCK mark-paid.
- **Admin CMS** — tabs for General/Hero/Benefits/Pricing/FAQ/SEO/Footer; live updates to landing page.
- **Admin Users** — super_admin creates other admins with role.
- **Activity Logs** — read-only log of all admin/label important actions.

## Prioritized Backlog
### P0 (next session — Phase 2: Royalty & Finance)
- CSV royalty import (Believe format), kurs EUR/IDR per period, matching by ISRC/UPC, auto-create unknown lines with admin review.
- Royalty calculation engine (fee 5%, label %, history-aware).
- Balance ledger (`royalty_pending` → `royalty_available` when admin marks `dana_received`).
- Withdraw system with date window (1–14 request, 15–20 payment, 21+ disabled), min Rp1.000.000.
- Royalty report page for label (filter month/artist/song/release/platform/country) + PDF/Excel export.

### P1 (Phase 3: Support, Legal, Notifications)
- Support ticketing (8 categories incl. takedown, edit metadata/audio/cover, Content ID).
- Contracts upload + status (Contract Active/Expired/Pending/Terminated).
- Blacklist management UI.
- Email notifications (Resend/SendGrid integration).
- Dashboard in-app notifications.
- Subscription expiry transition + reminder.

### P2 (Phase 4+ — Polish)
- Real Xendit live integration (key gathering + webhook signature verification).
- Google OAuth login (Emergent managed).
- Bulk admin actions (import old labels CSV).
- Tax/PPN automation, multi-artist royalty splits.
- Public artist profile pages, royalty forecasting, mobile native app.

## Next Tasks
1. Implement Phase 2 (Royalty + Withdraw) when user confirms.
2. Gather Xendit live keys + email provider key when ready to move out of MOCK.
3. Add export PDF/Excel reports.
4. Future: Google login + WhatsApp notifications.

## Files of Reference (entry points)
- Backend: `/app/backend/server.py`, `/app/backend/auth_utils.py`, `/app/backend/models.py`.
- Frontend: `/app/frontend/src/App.js`, `/app/frontend/src/api/AuthContext.jsx`, `/app/frontend/src/pages/Landing.jsx`, `/app/frontend/src/pages/auth/Login.jsx`, `/app/frontend/src/pages/label/UploadRelease.jsx`, `/app/frontend/src/pages/admin/Dashboard.jsx`, `/app/frontend/src/pages/admin/CMS.jsx`.
