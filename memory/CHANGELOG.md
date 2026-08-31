# RILIS MUSIK — Changelog

## 2026-08-31 — Phases 41–45: P0–P2 Completion

### Phase 41 — Multi-device authentication
- Fixed refresh token regression for users with `token_version > 0`; refresh now validates and preserves the current token version.
- Added unique JWT `sid` per device session while preserving global revocation.
- Disabled/suspended users cannot login, use access tokens, or refresh.
- Added password visibility toggle to Login.
- Added `admin_marketing` post-login redirect and visible Admin Dashboard navigation.

### Phase 42 — Account administration
- Added bidirectional bank-change approval workflow:
  - Label request → Admin Finance/Super Admin approval.
  - Admin proposal → Label approval.
  - Current payout destination remains unchanged before approval.
- Added safe admin deletion as soft-disable with immediate token revocation.
- Protected self-deletion and the final active Super Admin.
- Disabled admin email can be restored safely through Admin Users.

### Phase 43 — Release metadata, PPR invoicing, tickets, add-ons
- Added track producer, arranger, preview seconds, title/lyric language, track type, featuring existing/new, Spotify/YT IDs, and lyrics.
- Moved Upload Rilisan above Rilisan in label navigation.
- New PPR sequence: submit → admin review → one combined invoice → Xendit checkout → payment confirmation.
- Added deterministic/idempotent payment references and parallel approval protection.
- Added release submission in-app notifications and best-effort admin email.
- Added required YouTube URL for Content ID claim tickets.
- Added full edit/delete/archive controls for paid-service add-ons.

### Phase 44 — Copyright PDF
- Added CMS Documents tab for responsible person, title, signature, and stamp.
- Signature/stamp assets upload to Cloudflare R2.
- Added authenticated copyright PDF generator and label download action.
- PDF embeds legal entity, label, artist, release/track title, copyright lines, signature, and optional stamp.

### Phase 45 — Scheduled automation
- Added monthly royalty summary aggregation and idempotent email delivery records.
- Added retry-safe SMTP failure behavior and manual admin endpoints.
- Added completion notifications for migration jobs and royalty-import terminal states.
- Registered monthly and completion-monitor jobs in APScheduler.

### Verification
- Self-tests: 13/13 targeted regressions passed.
- Independent testing iteration 38: 18/18 backend/auth tests passed.
- Desktop/mobile responsive checks passed on Login, Upload wizard, Profile bank panel, Admin Users, Admin Payments, and CMS Documents.
- Frontend production build passed.
- Independent HIGH issue (`admin_marketing` redirect) fixed and self-verified.
- No application API is mocked. Historical Xendit provider unit tests may mock the external provider only to avoid creating real production transactions.

### Known external issue
- Hostinger SMTP currently returns `535 authentication failed` in preview. Email features correctly record failure/retry and never block core flows, but live delivery requires valid SMTP credentials.

## 2026-08-23—2026-08-30 — Phases 35–40: Production data integrity
- Enforced strict `Bulan laporan` parsing and rejected invalid/missing periods.
- Moved legacy withdrawal imports and heavy corrections to background jobs.
- Added R2 CSV replacement and resumable analytics rebuild.
- Added XLSX/CSV label-rate synchronization and unsettled recalculation.
- Rebuilt balances from unwithdrawn `royalty_lines` and added global reconciliation.
- Simplified label analytics and added admin financial summaries.
- Removed withdrawn/legacy revenue from label Artist views.

## 2026-08-22—2026-08-23 — Phases 32–34: Royalty formula, Xendit, refactor
- Removed separate distributor fee; label share is applied directly to Believe net revenue.
- Added legacy settlement cutoff and withdrawal-aware recalculation guards.
- Integrated production Xendit Payment Sessions with secure backend polling.
- Split oversized backend/frontend modules into domain services and components.
- Added explicit same-origin credentialed auth paths and improved test cleanup.

## Earlier foundation
- Built React/FastAPI/MongoDB product with Label/Admin dashboards.
- Added registration, MDA generation, contracts, support tickets, WAMI, notifications, withdrawal, CMS, analytics, and massive royalty import architecture.
- Migrated persistent uploads to Cloudflare R2.
- Added security hardening: no auth token leakage, brute-force protection, token-version revocation, email HTML escaping, CORS hardening, and payment reconciliation checks.