# PRD — Audit & Fix Konsistensi Analytics Royalti (2026-06)

## Root cause (level kode, terbukti)
Tiga definisi "baris layak Analytics" yang BERBEDA menyebabkan angka tak konsisten:
- Cache recompute (`admin_analytics._stream_dim_aggregate`): dulu hanya `period exists` → menghitung SEMUA baris (unmatched + staging).
- Live/filtered (`admin_monthly_analytics`): `match_status ∈ [matched, manually_matched]`.
- Label (`label_analytics`): `status ∈ [pending,available,withdrawn]` & `legacy_settled≠true`.
Akibat: dashboard tanpa filter (cache) > angka terfilter/impor → gejala "grafik Juni jauh lebih besar".

Periode SUDAH benar: `royalty_lines.period` ← `row_period` ← CSV "Bulan laporan"; kode menolak "Bulan Penjualan". Tidak ada period berbasis nama file.

## Keputusan bisnis (dikonfirmasi user)
Definisi KANONIK Analytics = `match_status ∈ [matched, manually_matched]` DAN `status ∈ [pending, available, withdrawn]` (published→withdrawn, kecualikan draft) DAN `replacement_stage ≠ true`.

## Perubahan
- `routes/analytics_eligibility.py` (BARU): `analytics_eligible_filter()` + konstanta. Satu-satunya sumber kebenaran.
- `admin_analytics.py`: cache recompute + live path pakai helper (cache==live dijamin).
- `revenue_rollup.py`: live fallback pakai helper.
- Endpoint BARU read-only `GET /api/admin/analytics/audit?period_from&period_to&dup_limit` (gate `analytics.manage`): per periode → raw vs eligible vs cache + diff, import kontributor (import_id+filename+status), overlap (>1 import/periode), dugaan duplikat (fingerprint baris identik lintas import). TIDAK mengubah data.
- Frontend: `pages/admin/AnalyticsAudit.jsx` + route `/admin/analytics/audit` (`analytics.manage`) + nav item `analytics_audit` ("Audit Konsistensi", icon ShieldCheck).

## Verifikasi (preview, 8 baris demo)
- Sebelum recompute: 2024-01 cache=Rp71.400 tapi eligible=Rp0 (import pending_review, baris draft) → membuktikan bug.
- Setelah recompute: cache=Rp0=eligible → diff 0 (DoD cache==live==eligible tercapai). monthly cache & live sama-sama 0.

## PENTING / belum selesai
- DB preview hanya 8 baris demo. Reconciliation angka asli Apr–Jul 2026 & deteksi duplikat 74rb baris HARUS dijalankan di PRODUKSI setelah deploy, via halaman "Audit Konsistensi".
- TIDAK ada dedup/hapus/migrasi destruktif yang dilakukan (sesuai PRD: buktikan dulu). Jika audit produksi menemukan duplikat nyata, butuh persetujuan terpisah + safe flow (report→snapshot→cleanup→rebuild balances→rebuild analytics→reconcile) dan cek dampak withdrawal.
- Legacy `legacy_settled` saat ini TETAP dihitung di admin analytics (status withdrawn masuk). Bila perlu dikecualikan, ubah satu tempat di `analytics_eligibility.py`.
