# RILIS MUSIK — Product Requirements (living doc)

Modern music release & royalty management platform. Stack: FastAPI + React + MongoDB, Cloudflare R2 storage, Hostinger SMTP, Xendit payments, Emergent Google Auth. Language: Indonesian primary, EN via runtime i18n catalog. Dynamic RBAC via `assert_admin_permission(user, "perm.key")`; Super Admin bypasses granular checks. WIB (Asia/Jakarta) for all attendance/cron/period logic.

## Core modules (implemented)
- Labels/KYC/Bank verification, Releases + go-live, Royalty import/analytics, Withdrawals, Add-ons, WAMI, Support tickets + Chat, Contracts, CMS, Migration/claims.
- Work Responsibility & Tracking (PRD-02): `work_service.py` projects OPEN/COMPLETED work from real business state; "Pekerjaan Saya" vs "Team Monitor".
- Staff Management & Attendance (PRD-04): `staff.py` — staff = admin accounts excluding super_admin; attendance from first-login evidence (WIB); leave requests; salary history; daily 00:30 WIB finalize cron.
- KPI & Performance (PRD-05): `performance_service.py` — see below.

## PRD-05 KPI/Performance + Chat correction (2026-06) — DONE
### Part A — Performance (derived measurement layer)
- New permission module `performance` (view_own, view_team, view_details, config.manage, period.manage). Default Super-Admin-only (rbac v12); grant others via Role & Permission.
- Engine `compute_staff_performance`: counts COMPLETED work_items attributed to staff in-period (completed_by, WIB month; excludes completed_by_super). Metrics: Completed count, Weighted Output (× Work Type Weight), Timeliness (on-time vs late via opened_at+SLA), Achievement (Actual/Target when configured), Overall Score 0–100 normalized over AVAILABLE components (achievement/timeliness/complexity/quality), Confidence (sample-size thresholds), Category.
- Per PRD & user decisions: Queue/Processing Time = "Tidak Tersedia" (no started_at tracked); Resolution Time shown. Quality = "Tidak Tersedia" (no reliable per-staff evidence). Targets default EMPTY (Not Applicable). Business config (weights/scoring/categories/confidence) = reasonable editable defaults, effective-dated, audited (`performance_config_audit`).
- Period Open/Finalized (`performance_periods`): finalize snapshots config so finalized results never silently change; reopen supported.
- Endpoints: `/api/admin/performance/{config,me,overview,staff/{id},periods,periods/action}`.
- Frontend: `/admin/performance` (Team), `/admin/my-performance` (self, super admin sees "not staff"), `/admin/performance/configuration`. Bilingual via catalog additions.
### Part B — Chat correction
- Renamed "Pusat Chat" → "Chat". Conversation-state filters (Semua/Belum Dibaca/Aktif/Arsip) replace presence filters. Presence (online/offline) NEVER triggers sound — only new incoming messages do (removed the online-arrival sound). Dock attaches to viewport bottom (bottom-0), panel opens upward. Desktop shows list + detail two-pane; mobile swaps list→detail. Backend `/chat/admin/labels` accepts status all|active|resolved.

## Recent fixes (2026-06)
- Work Monitor scoping: Team Monitor hides work types owned ONLY by Super Admin (via role-id `super_admin`); such tasks appear only in "Pekerjaan Saya". `withdraw_verification` moved to Super-Admin-only (migration `withdraw_super_admin_v1`).

## Backlog (P1/P2)
- P1: Upload size limits (~300MB) for Add-on delivery results.
- P1: Duplicate CSV upload prevention via file checksum at R2 upload.
- P2: Custom per-admin roles (decouple from builtin Finance/Release roles).
- P2: Smart links (Spotify/Apple/YouTube) in Live Today banner + go-live email.
- P2: Monthly royalty emails; national holiday API for chat hours; estimated withdrawal date; export trend chart; automated artist Excel report scheduling.
- P2 (paused): AI Assistant for admin work queues.

## Test credentials
See `/app/memory/test_credentials.md`. Super Admin: superadmin@rilismusik.com / SuperAdmin#2026.
