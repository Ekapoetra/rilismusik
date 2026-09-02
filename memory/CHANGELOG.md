# RILIS MUSIK — Changelog

## 2026-09-02 — Phase 56: Post-cutoff paid-marker recovery
- Dua CSV F - Audio diverifikasi dengan parser produksi: 7.611 baris, €137,540487659793, dan hasil tepat **Rp1.253.286** setelah bagian label 50% serta kurs per bulan.
- Menemukan penyebab saldo tetap Rp914.491 setelah Phase 55: audit hanya mendeteksi status `withdrawn`, sementara baris draft/pending/available yang keliru bertanda `legacy_settled=true` dilewati.
- Preview kini menghitung seluruh data pasca-batas tarik yang salah bertanda sudah dibayar dan memasukkannya ke pending atau available sesuai status aslinya.
- Commit menghapus penanda pembayaran lama, hanya mengubah `withdrawn` menjadi available, mempertahankan draft/pending/available, lalu menghitung ulang persentase label dan saldo.
- Terverifikasi 11/11 backend, frontend build, dan alur audit UI melalui independent testing iteration 47; tidak ada API yang di-MOCKED.

## 2026-09-02 — Phase 55: Global orphan-withdrawn recovery
- Memperbaiki kebuntuan production akibat pekerjaan `recalculate_all_unwithdrawn` lama yang tetap `processing` pada 70/1.720 label sejak 23 Agustus tanpa perkembangan.
- Commit audit kini menutup otomatis pekerjaan hitung ulang yang tidak bergerak lebih dari empat jam, tetapi tetap memblokir bila proses baru masih benar-benar aktif.
- Menambahkan pemeriksaan otomatis setiap 15 menit dan endpoint manual Admin Finance/Super Admin untuk menutup pekerjaan hitung ulang kedaluwarsa.
- Seluruh istilah teknis audit pada UI diganti bahasa Indonesia sederhana: `Royalti salah status`, `Nilai belum masuk saldo`, dan `Batas tarik`.
- Perbaikan kebuntuan terverifikasi 10/10 backend serta frontend build/UI melalui independent testing iteration 46.
- Audit read-only production F - Audio mencocokkan enam import Feb–Jul sebesar €137,54048766, bagian label 50%, dan kurs per import; estimasi awal kemudian dikoreksi dengan perhitungan per baris menjadi Rp1.253.286 sementara saldo aktif production Rp914.491.
- Riwayat paid F - Audio berakhir Januari 2026, tetapi data aktif Feb–Jul tidak mencakup seluruh source dan stored pending tercatat negatif Rp1.083.323.
- Balance audit kini memakai cutoff efektif maksimum dari cutoff label dan seluruh `paid.period_to`.
- Preview global mendeteksi withdrawn orphan setelah cutoff, nominalnya, range bulan, cutoff mismatch, dan riwayat paid tanpa periode.
- Commit guarded memulihkan hanya withdrawn orphan setelah cutoff, menjaga withdrawn historis, menghitung ulang persentase label terkini, merekonsiliasi pending/available, dan menyegarkan cache/snapshot.
- Label dengan withdraw aktif atau paid withdrawal tanpa `period_to` dilewati untuk mencegah double payment.
- Admin UI menampilkan summary orphan, nominal, cutoff efektif, status riwayat belum lengkap, dan hasil pemulihan.
- Terverifikasi 6/6 regresi backend, frontend build, smoke test Playwright, dan independent testing iteration 45. Tidak ada API yang di-MOCKED.
- Memperbaiki typo class Tailwind amber pada Withdraw, Label Dashboard, Release Detail, dan Royalty Import.

## 2026-09-01 — Phase 54: Nonblocking Label Balance Snapshot
- Production RCA: `/api/admin/labels` returned Cloudflare 524 after ~1 minute because live royalty aggregation ran inside the list request; frontend then misleadingly showed an empty list.
- Label list endpoint is fast again and reads `balance_available_idr` materialized on label documents.
- Source-of-truth reconciliation moved to a nonblocking background snapshot worker with status endpoint, hourly scheduler, startup trigger, and royalty-recalculation trigger.
- Label Management immediately renders rows, shows loading/API errors explicitly, shows background sync status, and reloads when reconciliation completes.
- Deterministic stale `59,557,995 → 13,149,228` materialization and list/detail parity remain covered.
- Independent iteration 44: 5/5 backend passed, build passed, normal list/error UI passed; no application API MOCKED.

## 2026-09-01 — Phase 53: Label List/Detail Balance Parity
- RCA: Label Management displayed stale `labels.balance_available_idr`, while Label Detail computed the live withdrawable amount from `royalty_lines`.
- Admin label list now performs one bulk royalty aggregation and one active-withdraw aggregation for all candidate labels—no per-label N+1 queries.
- Displayed `balance_available_idr` now follows the exact detail rules: status available, non-legacy, after cutoff, minus requested/approved withdrawal reservations, floored at zero.
- Stale stored balance remains only as `stored_balance_available_idr` for admin audit and is no longer shown as the available amount.
- Default balance sorting now uses the computed source-of-truth value.
- Deterministic reproduction `stored 59,557,995 → computed 13,149,228` passed and list/detail equality passed.
- Independent iteration 43: backend 5/5, frontend build and Playwright parity checks passed; no MOCKED flows.

## 2026-09-01 — Phase 52: Password Reset, Google Label Login & R2 Production CORS
- Confirmed and hardened forgot-password email flow: non-enumerating response, trusted-origin link, hidden query token UI, single-use reset, password update, and global session revocation.
- Added Emergent-managed Google Auth buttons on Login and Register for existing label accounts only; no Google auto-registration.
- Added backend Google session exchange, active-label checks, hashed provider-session audit, single-use replay guard, and issuance of the existing JWT cookie pair.
- Fixed production royalty-upload Network Error by merging R2 bucket CORS origins instead of overwriting them; apex, `www`, and preview origins now coexist.
- Shared R2 bucket was repaired immediately; actual OPTIONS preflight from production apex/`www` returns 204 with matching allow-origin.
- Hostinger password-reset email was sent successfully in a live self-test; reset and token-version revocation completed.
- Independent iteration 42: backend 12/12 passed and preview auth UI passed. Full external Google human-session success remains **MOCKED in tests only** because no human Google session was provided.
- Production still serves the older auth frontend until redeploy.

## 2026-08-31 — Phase 51: Admin Dashboard Withdraw Breakdown
- Admin Dashboard now keeps Total Bagian Label and shows `Sudah Withdraw` plus `Belum Withdraw` directly below it.
- Withdrawn includes modern `status=withdrawn` and `legacy_settled=true` through one condition, preventing double-counting.
- Unwithdrawn is calculated as total label share minus withdrawn, preserving the accounting invariant exactly.
- Cache persistence/warm-up now includes both breakdown values and automatically upgrades old cache documents.
- Removed obsolete warning banners that incorrectly claimed R2 and email were not live.
- Independent iteration 41: 14 passed, 1 skipped; API, UI, cache compatibility, Rupiah rendering, and responsive layout all passed.

## 2026-08-31 — Phase 50: Label Sorting & Last Withdrawal
- Added backend sorting for label name, email, and available balance with asc/desc direction.
- Default Label Management ordering is available balance highest-to-lowest.
- Added `Withdraw Terakhir` column sourced from `last_withdrawn_period`; empty values display `Belum pernah WD`.
- Alphabetical sorting is case-insensitive and balance sorting has a stable label-name tie-breaker.
- Regression 3/3 passed, frontend build passed, and desktop/mobile layout checks passed.

## 2026-08-31 — Phase 49: Available Balance in Label Management
- Added `Saldo Available` column to Admin → Label Management for every label.
- Values are formatted in Indonesian Rupiah and use the reconciled `balance_available_idr`, representing funds not withdrawn/legacy-settled and net of active withdrawal reservations.
- API normalizes missing/negative stored values to zero for safe display.
- Regression API 2/2 passed, frontend production build passed, and desktop/mobile overflow checks passed.

## 2026-08-31 — Phase 48: Complete Label Search in Manual Withdraw
- Klarifikasi: picker manual legacy withdraw menampilkan semua dokumen label, tidak memfilter berdasarkan pernah/belum withdraw.
- Fixed initial-list limitation: input sekarang menjalankan server-side search ke `/api/admin/labels?q=...`, sehingga label lama di luar 1.000 hasil awal tetap dapat ditemukan.
- Backend search meng-escape input sebagai literal regex agar nama dengan karakter khusus tetap aman dan dapat dicari.
- Regression search + manual legacy flow 2/2 lulus; browser membuktikan request server-side dan hasil dropdown tampil; frontend build lulus.

## 2026-08-31 — Phase 47: Manual Legacy Withdraw
- Admin Finance/Super Admin kini dapat menambah riwayat withdraw legacy dari Admin → Withdraw.
- Input mencakup searchable label picker, bulan awal, bulan pencairan terbaru, tanggal pengajuan, tanggal pencairan, dan catatan.
- Nominal serta jumlah baris dihitung otomatis dari `royalty_lines` aktif pada rentang yang dipilih.
- Commit berjalan di background, menandai baris sebagai `withdrawn + legacy_settled`, memperbarui cutoff, merekonsiliasi saldo dari source of truth, dan membuat history/transaksi audit.
- History manual tetap admin-only; endpoint label dan analytics hanya menampilkan royalti yang belum withdraw/pasca-cutoff.
- Validasi formal iteration 40: backend 100% lulus; issue searchable picker ditemukan lalu diperbaiki dan self-tested. Build frontend lulus.

## 2026-08-31 — Phase 46: Production apex/`www` login CORS
- RCA dari Console pengguna: halaman `https://www.rilismusik.com` memanggil endpoint absolut `https://rilismusik.com/api/auth/*`, sehingga browser memblokir credentialed request karena origin berbeda.
- Frontend browser sekarang selalu memakai URL relatif `/api` dan path file relatif, sehingga request mengikuti hostname aktif (apex maupun `www`).
- Backend CORS dan bootstrap R2 otomatis menambahkan pasangan apex/`www` untuk custom domain eksplisit, tanpa memperluas preview subdomain.
- Verifikasi independen iteration 39: 12/12 auth/CORS regressions lulus, Playwright login same-origin lulus, dan frontend production build lulus; tidak ada API MOCKED.

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

### SMTP credential remediation (2026-08-31)
- Preview SMTP dipindahkan ke mailbox resmi `official@rilismusik.com` melalui `smtp.hostinger.com:465` dengan SSL/TLS.
- Auth-only verification berhasil dan satu email verifikasi internal berhasil dikirim melalui pipeline `email_service.send_email`.
- Password tetap hanya berada di environment backend dan tidak dicatat di source code atau dokumentasi.

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