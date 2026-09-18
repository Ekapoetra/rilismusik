# PRD 06 — Compensation, Sales Bonus & Payroll — Program Tracker

Repo-aligned. Staff = Admin user (excl. Super Admin). Reuse staff_profiles.salary_current_idr,
staff_salary_history, canonical payments, dynamic RBAC, permission-based Work. NO parallel salary
master / staff user type / second auth. Royalty NEVER a bonus source.

## Keputusan user (dikonfirmasi 2026-06)
- Fase A→D berurutan.
- Proration v1: **TANPA proration** — bayar penuh sesuai gaji efektif pada tanggal pembayaran.
- Absensi (ABSENT/LATE/LEAVE) TIDAK auto-potong gaji; hanya via adjustment manual.
- Fixture uji prefiks `compqa-`, dibersihkan setelah tes.

## Status
- **FASE A — Fondasi & RBAC + My Compensation — SELESAI (2026-06)**
  - RBAC: modul `compensation` di PERMISSION_MODULES (view/view_own/view_team/salary.manage/allowance.manage/bonus.view/bonus.transactions.view/bonus.attribution.manage/bonus.rules.manage/adjustment.create/adjustment.approve/payroll.view/manage/approve/mark_paid/finalize) + PERMISSION_META (dependency+sensitive) + migrasi v14 (super_admin only) + rbac_schema_version=14.
  - Nav: item `compensation_me` + submenu (payroll/staff/bonus/attribution/bonus-rules/adjustments) di DEFAULT_NAV_ITEMS (auto-tambah saat restart).
  - `routes/compensation_service.py`: `resolve_salary(user_id, as_of_date)` effective-dated (history effective_date<=date, ambil terbaru; fallback salary_current_idr + needs_review bila ada history future); `is_staff_user()`; `GET /api/compensation/me` (compensation.view_own), `GET /api/compensation/staff/{id}` (compensation.view_team).
  - Frontend: `pages/admin/MyCompensation.jsx` (tab Gaji/Bonus/Riwayat Payroll) + route guard compensation.view_own.
  - Diuji: resolver (2026-05→5jt Jan-rate, 2026-09→7jt Aug-rate, sebelum history→fallback flagged), catalog perms, superadmin 200, finance 403, screenshot page.
- **FASE B — Sales Bonus Engine — SELESAI (2026-06)**
  - `routes/compensation_admin.py`: bonus source = payments `status=paid` SAJA (bukan royalti). Atribusi eksplisit (`sales_attributions`, 1 payment→1 staf). Bonus Rules effective-dated (payment_type/*, basis total/base/addon, percent/flat). Bonus Ledger idempotent per payment (re-atribusi → reverse lama). Antrean Unattributed. Endpoint: bonus/rules (GET/POST/PATCH), bonus/unattributed, bonus/attribute (POST/DELETE), bonus/ledger.
  - Anti double-count: satu payment memakai SATU rule paling spesifik (exact type > "*", effective terbaru).
  - Diuji: rule 10% × Rp500k → bonus Rp50k; reverse; block reverse jika sudah paid_out (409).
- **FASE C — Payroll + Allowance + Adjustment — SELESAI (2026-06)**
  - Payroll Period (draft→review→approved→paid→finalized) + Payroll Item snapshot (salary via resolver di tanggal akhir periode [tanpa proration], allowance effective-dated, bonus earned bulan itu, adjustment approved). Finalisasi immutable + bonus ledger → paid_out (tak bisa dipakai ulang / dibatalkan).
  - Allowances (`compensation_allowances`, effective-dated) + Adjustments (`compensation_adjustments`, +/- , pending→approved). Salary manage (reuse staff_salary_history + sync salary_current_idr bila efektif ≤ hari ini).
  - Diuji E2E: item compqa = 8jt+1jt+50k−500k = 8.55jt; transisi lifecycle; generate setelah finalized → 409; self-view menampilkan payroll final.
- **FASE D — UI Admin — SELESAI (2026-06)**
  - `pages/admin/CompensationAdmin.jsx` (tab Payroll/Staf/Bonus/Atribusi/Aturan Bonus/Penyesuaian) + `MyCompensation.jsx`. 6 route nav → satu halaman (tab dari pathname), tiap route di-guard permission. Tunjangan Cepat form (transport/makan) effective-dated.
  - Audit: `log_activity` pada salary_change, bonus_attribute, bonus_rule_create, allowance_create, payroll_*.
  - Self-service: semua admin role otomatis dapat `compensation.view/view_own` (migrasi v14) → staf lihat kompensasi sendiri saja (team → 403).
  - **Work Queue integration — BELUM di-wire ke work_service** (antrean Unattributed & Payroll pending sudah tersedia via halaman Compensation; integrasi ke Work Dashboard menyusul).

## Slip Gaji PDF — SELESAI (2026-06)
- `routes/compensation_payslip.py`: `generate_payslip_pdf(staff, period, item)` (reportlab, A4) dengan kop logo `frontend/public/brand/logo-full.png` + "RILIS MUSIK", info staf, rincian (Gaji Pokok + breakdown Tunjangan + Bonus + breakdown Penyesuaian), band "TOTAL DITERIMA". Membaca SNAPSHOT payroll_item saja (tanpa hitung ulang).
- `GET /api/compensation/payslip/{period_id}?staff_user_id=` di `compensation_service.py`: hanya periode `finalized` (else 409); self → `compensation.view_own`, staf lain → `compensation.view_team` (404 bila item tak ada). Response attachment PDF.
- `_own_compensation` kini menandai setiap payroll_history dgn `period_status`.
- Frontend: helper `api/payslip.js` (blob download + unwrap error), tombol "Slip" di MyCompensation (Riwayat Payroll, hanya baris final) & CompensationAdmin (detail payroll per staf, hanya saat periode final).
- Diuji E2E (super admin): buat periode→set gaji→generate→finalized→unduh slip finance1 (PDF valid, 394KB), periode non-final → 409. Fixture QA (`reason=PAYSLIP_QA`, periode 2098-11/12) dibersihkan total.

## Bonus Engine v2 — Persentase Total Pendapatan (2026-06, redesign)
- **Perubahan besar**: model atribusi per-pembayaran DIGANTI. Bonus kini = persentase × TOTAL pendapatan Xendit bulan periode payroll (pay_per_release/annual_subscription/wami_addon/custom_service, status paid, by paid_at). Royalti tetap dikecualikan.
- **Skema** (`bonus_schemes`): {name, scope: all|role|staff, role_key/staff_user_id, percent 0-100, effective_from/to (null=lifetime), active}. Tiap staf yang cocok menerima persentase PENUH (tidak dibagi). Jika cocok >1 skema aktif → DIJUMLAHKAN.
- **Menu Atribusi DIHAPUS** (nav item `compensation_attribution` di-pull, route & tab dihapus, permission `compensation.bonus.attribution.manage` dihapus dari registry).
- Endpoint: `GET/POST/PATCH/DELETE /api/compensation/bonus/schemes`, `GET /api/compensation/bonus/preview?period_key=`. Payroll generate memakai `_bonus_for_staff` (snapshot `bonus_idr` + `bonus_breakdown` + `bonus_revenue_idr` di payroll_item). Finalisasi TIDAK lagi freeze ledger (bonus sudah ter-snapshot).
- Koleksi lama `bonus_rules`, `sales_attributions`, `bonus_ledger` DIHAPUS. `_own_compensation` kini mengembalikan `bonus_history` (dari payroll snapshot), bukan `bonus_ledger`.
- Frontend: tab "Aturan Bonus" → form Skema (cakupan/persen/lifetime|tanggal), tab "Bonus" → kalkulator preview (pendapatan + bonus per staf per periode). MyCompensation tab Bonus pakai `bonus_history`.
- Diuji E2E: 2 payment paid (6jt+4jt=10jt, 1 pending dikecualikan); skema all 5% + role admin_finance 3% → finance 800k (dijumlah), non-finance 500k; validasi percent 0 → 400; payroll snapshot cocok; nav tanpa atribusi; UI create/list/nonaktifkan skema OK. Semua fixture dibersihkan.

## Arsitektur existing relevan
- staff_profiles: {user_id, salary_current_idr, employment_status, join_date}. staff_salary_history: {user_id, previous_idr, new_idr, effective_date, changed_at}. Set via `routes/staff.py`.
- payments: {id, type(payment_type), amount, status(paid), paid_at, base_amount, addon_amount, line_items}. payment_service.py.
- RBAC engine: admin_permission_service.py (PERMISSION_MODULES, PERMISSION_META, migrasi bertingkat, DEFAULT_NAV_ITEMS, capability review).
- Work permission-based fallback ke Super Admin (pola Multi Label Fase 5).
- Koleksi baru direncanakan: compensation_allowances, sales_attributions, bonus_rules, bonus_ledger, compensation_adjustments, payroll_periods, payroll_items.
