# Multi Label (Rp1.500.000/tahun) + Existing Account Merge Wizard — Program Tracker

Source of truth: two PRDs supplied by user (2026-06). Implemented in 6 phases, each tested before next.

## Definisi
- Paket tahunan tertinggi: 1 akun mengelola banyak label, unlimited release, benefit VIP (free WAMI + free layanan tambahan), kuota **7 submission/hari/ACCOUNT**.
- Setiap label mempertahankan histori royalti/withdrawal/cutoff sendiri; hanya kepemilikan account, saldo, analytics, withdraw, dan entitlement yang diagregasi.

## Keputusan yang sudah dikonfirmasi user
- Urutan fase 1→6 berurutan.
- Model akun: `user_id` semua child label di-set ke akun utama; akun lama diarsipkan (status `merged`, login nonaktif).
- Shared settlement period (Fase 5): ditentukan dari **data import royalti terbaru** (bukan koleksi published khusus).
- Testing pakai akun demo (demo_vip, demo_ppr), buat data uji sementara & dibersihkan.

## Status Fase
- **FASE 1 — Fondasi Entitlement & Paket — SELESAI (2026-06)**
  - `routes/entitlements.py`: `resolve_label_entitlements(label)` → {package, active, unlimited_release, vip_benefits, free_wami, free_addons, multi_label, daily_release_limit=7}. Helpers has_* .
  - `multi_label` tier didukung di `label_package_service.py` (aktivasi manual Super Admin, guard `labels.multi_label.manage`; finance→403).
  - RBAC: perms baru `labels.multi_label.view` / `labels.multi_label.manage` (labels module), PERMISSION_META, migrasi v13 (super_admin only), SYSTEM_ROLE rbac_schema_version=13. Muncul di capability review banner.
  - Harga: `payment_service.DEFAULT_PRICES["multi_label"]=1_500_000` + key_map `multi_label_price`.
  - Landing: kartu ke-4 "MULTI LABEL — Layanan Baru" Rp1.500.000/tahun, CTA "Ajukan Multi Label" (grid lg:grid-cols-4). testid `landing-pricing-multi-label`.
  - `GET /api/label/me` kini menyertakan `entitlements`.
  - Verifikasi curl: aktivasi multi_label pada Demo Label VIP → tier=multi_label, entitlements semua true; finance 403; direvert ke annual_vip (data bersih).

- **FASE 2 — Kepemilikan banyak label + Active Label switcher + Agregasi saldo dashboard — SELESAI (2026-06)**
  - `deps.py`: `get_labels_for_user()`, `get_label_by_user()` kini kembalikan **active label** (backward compatible untuk single-label), `account_entitlements()`, `_account_authority()` (label authority = tier multi_label, fallback primary/first).
  - `GET /api/label/account`: ringkasan akun (is_multi_label, labels[], primary/active id, entitlements, `account_available_idr` = Σ saldo child via `compute_labels_available_balances`). `POST /api/label/active-label`: switch active label (validasi ownership → 404 jika bukan milik akun).
  - `/api/label/account` & `/api/label/active-label` ditambahkan ke `KYC_ALLOWED_LABEL_PREFIXES` (viewable seperti /dashboard; saldo tetap diblur saat locked).
  - Frontend `pages/label/Dashboard.jsx`: `MultiLabelBar` (badge "MULTI LABEL", N label dikelola, aktif s/d tgl, Total Saldo Tersedia teragregasi, dropdown switcher `label-active-switcher`) — hanya muncul bila is_multi_label.
  - Diuji (testing_agent iter92 + curl + screenshot): acct_avail=Σ children, switch + /me follow active, forged label 404, single-label tanpa regresi.

- **FASE 3 — Unlimited release, kuota 7/hari/account, free WAMI, free layanan tambahan — SELESAI (2026-06)**
  - `payments.create_wami_invoice` kini pakai `account_entitlements().free_wami` → Multi Label & VIP dapat WAMI Rp0 (no invoice, status pending, `benefit_source`). Diverifikasi E2E: amount=0, benefit=multi_label.
  - `release_submission_quota.py`: `resolve_quota_scope(label)` → multi-label pakai scope `acct:{user_id}` mencakup semua owned label_ids (kuota **7/hari/ACCOUNT**); single-label tetap `label_id` (backward compatible). daily_record/submission_slot/submission_quota kini terima label doc + scope. Historical backfill & reservation repair query pakai `label_id $in label_ids`.
  - `releases.py` submit: `is_subscribed` & `free_addons` diambil dari `account_entitlements` (unlimited release account-level). Add-on saat submit: jika `free_addons` → dibuat `addon_orders` Rp0 (source `subscription_free`) via `addon_orders.sync_free_addon_orders`; annual_normal tetap diblok.
  - Catatan: enforcement 8th-submission 429 lintas label & free-addon-at-submit belum di-e2e (butuh fixture rilisan submittable); logic sudah terpasang & quota endpoint mengembalikan limit=7 account-scope.
  - Fixture QA: `scripts/seed_multilabel_fixture.py` (seed|cleanup), akun `multilabel-qa@example.com`.
- **FASE 4 — Analytics agregat + filter per-label + audit redaksi fee & legacy — SELESAI (2026-06)**
  - `label_analytics.py`: endpoint `/label/analytics` kini account-aware. Multi Label default `scope=all` (agregasi semua owned label via `label_id $in`), param opsional `label_id` (validasi ownership → 404) untuk filter per-label. `top_tracks` kini membawa `label_id`+`label_name`. Response menambah `labels[]`, `scope`, `selected_label_id`.
  - Redaksi fee: analytics hanya mengembalikan `label_idr` (nilai final label) — tidak ada gross/fee/EUR/exchange. Endpoint royalti label pakai `strip_sensitive` + `LABEL_HIDDEN_FIELDS`. Multi Label mewarisi redaksi yang sama (legacy `legacy_settled` selalu dikecualikan).
  - Frontend: `useLabelAnalytics` menerima `labelId`/`setLabelId`; dashboard `MultiLabelBar` punya dropdown "Filter Analitik" (Semua Label / per label) yang mem-filter grafik & overview.
  - Diuji curl: scope=all total_rev=5.000.000, filter B=3.000.000, forged 404.
- **Global Switcher — SELESAI**: `components/shared/LabelSwitcher.jsx` di header `LabelLayout` (semua halaman label), muncul hanya untuk akun Multi Label; switch → POST /active-label + reload.
- **FASE 5 — Withdrawal Batch — SELESAI (backend + tombol dashboard) (2026-06)**
  - `withdraw.py`: `POST /api/withdraw/label/batch` (Multi Label only) — hitung withdrawable per child (dari history eligible masing-masing), minimum dievaluasi pada TOTAL agregat, buat satu child `withdraw_request` per label (di bawah `label_financial_lock` per label) + parent `multi_label_withdraw_batches`. Atomic recovery: jika salah satu child gagal → hapus child yang sudah dibuat + refund. Payout bank = rekening label authority (primary).
  - Shared settlement: child menyimpan `shared_period_to` = max period_to lintas label; `mark_paid` menyetel `last_withdrawn_period` semua child ke `shared_period_to` (cutoff tersinkron). `_recompute_withdraw_batch` update status parent (requested→processing→paid) tiap aksi child.
  - `GET /api/withdraw/label/batches`: history batch + breakdown child (label_name, amount, status, period).
  - Frontend: tombol "Cairkan Saldo Gabungan" di MultiLabelBar dashboard (muncul bila account_available_idr>0 & tidak locked).
  - Diuji E2E (script, window dibuka via patch): batch total Rp5.000.000, period_to=2026-06, approve+mark_paid tiap child → batch=paid, kedua label last_withdrawn_period=2026-06 (tersinkron), saldo 0. Σ child = total batch.
  - Catatan: enforcement window request (tgl 1-14) tetap berlaku; testing memakai patch tanggal. Admin melihat child sebagai withdraw individual (punya batch_id) di list withdraw admin.
- **FASE 6 — Merge Wizard — SELESAI (2026-06)**
  - `routes/multi_label_merge.py`: `GET /admin/multi-label/candidates`, `POST /merge/validate`, `POST /merge/commit`, `GET /accounts`, `GET /requests`, `POST /requests/{id}/handle`, publik `POST /multi-label/request`.
  - Commit: reassign `user_id` semua label ke primary, aktifkan multi_label pada label authority, payout bank → account-level (`users.payout_bank_account_id`; bank baru → verified_status pending masuk work verify), set PIC account-level (responsible_name/email/whatsapp), arsipkan akun lama (status `merged`, merged_into_user_id/at/by, login 403 di auth.py). State machine draft→committing→completed/failed, idempotent. Validasi: label/akun exist, no label di multi_label account lain, no merge aktif lain, bank valid, dsb — NO PARTIAL MERGE.
  - History utuh: label tidak digabung, cutoff per-label dipertahankan (sync hanya saat withdrawal batch pertama paid), package history lama disimpan, legacy dikecualikan dari saldo. Quota jadi 7/hari/akun (bukan 21).
  - Frontend: `pages/admin/MultiLabelMerge.jsx` (tab Akun/Wizard 5 langkah/Permintaan), nav "Multi Label" di bawah Manajemen Label.
  - Diuji testing_agent iter93 (10/10 backend, 4/4 UI) + curl: combined 9jt (legacy excluded), cutoff A/B/C=2026-04/06/02 dipertahankan, old accounts 403, idempotent, finance 403.
- **Registrasi "Ajukan Multi Label" — SELESAI**: publik `POST /multi-label/request` + `pages/MultiLabelRequest.jsx` (route `/ajukan-multi-label`, CTA landing), masuk antrean admin (tab Permintaan) + notify super admin.
- **Admin Batch View — SELESAI**: `GET /withdraw/admin/batches` + `components/admin/MultiLabelBatchPanel.jsx` (baris induk batch + rincian child) di halaman Penarikan admin.
- **Enforcement kuota E2E — SELESAI**: diverifikasi script — 7 reservasi lintas label A+B OK, ke-8 → HTTP 429 (scope `acct:{user_id}`).

## Arsitektur relevan (existing)
- 1 user = 1 label via `labels.user_id`; `get_label_by_user()` di `routes/deps.py` mengembalikan satu label.
- Balance: `routes/balance_utils.py` (compute_labels_available_balances / compute_label_balance_snapshot), cutoff per-label `last_withdrawn_period`, exclude `legacy_settled`.
- Quota: `routes/release_submission_quota.py` ledger `label_daily_submissions` per `label_id:day` (perlu jadi account-level di Fase 3).
- Withdraw: `routes/withdraw.py` (~510 baris), FIFO force-full, MIN_WITHDRAW_IDR.
- RBAC engine: `routes/admin_permission_service.py` (PERMISSION_MODULES, migrasi bertingkat, capability review).
