# RILIS MUSIK — Product Requirements Document

## 1. Product Summary
RILIS MUSIK adalah aplikasi web modern untuk distribusi musik, pengelolaan rilisan, royalti, pembayaran, kontrak, WAMI, support, dan administrasi label. Produk menggunakan desain premium gelap dan harus responsif di desktop/mobile.

## 2. User Personas
- **Label:** mengelola profil, rekening, artist, rilisan, invoice, royalti, withdraw, kontrak, WAMI, support, dan notifikasi.
- **Artist:** melihat rilisan dan royalti yang memang terhubung ke akun artist tersebut.
- **Super Admin:** mengelola seluruh data, akun admin, CMS, migrasi, dan audit.
- **Admin Release:** review rilisan, kontrak, dan WAMI.
- **Admin Finance:** pembayaran, rekening, royalti, withdraw, rate, dan audit saldo.
- **Admin Support:** tiket support dan label/artist context.
- **Admin Content/CMS:** konten landing dan aset dokumen.
- **Admin Marketing:** dashboard admin untuk kebutuhan operasional marketing.

## 3. Core Requirements

### 3.1 Public Landing & CMS
- Landing modern, mobile-responsive, dan dikelola dari Admin CMS.
- CMS mencakup general, hero, benefits, pricing, FAQ, SEO, footer, legal entity, serta aset dokumen.
- Gambar dan file persisten menggunakan Cloudflare R2.

### 3.2 Authentication & Account Security
- JWT access/refresh melalui HttpOnly Secure cookies dengan Bearer fallback untuk pengujian/API.
- Login multi-perangkat: login baru tidak membatalkan perangkat lain.
- Setiap sesi memiliki `sid`; `token_version` hanya digunakan untuk global revocation.
- Password reset, perubahan email, disable/suspend, dan penghapusan akses admin mengakhiri semua sesi lama.
- Brute-force protection dan email verification tetap aktif.
- Forgot-password mengirim link email berbasis trusted active origin; reset bersifat single-use dan mencabut seluruh sesi lama.
- Google Login tersedia pada Login/Register hanya untuk akun label existing dengan email Google yang sama; Google tidak membuat akun baru otomatis.

### 3.3 Label Dashboard
- Dashboard, artist, release, analytics, royalty, withdraw, WAMI, support, contracts, invoices, profile, notifications.
- Saldo selalu diturunkan dari `royalty_lines` pending/available non-legacy, bukan lifetime rollup.
- Rekening awal diverifikasi admin; perubahan rekening berjalan melalui approval dua arah.
- Admin Label Management menampilkan saldo available per label dalam Rupiah, tidak termasuk dana withdrawn/legacy-settled atau dana yang sedang direservasi untuk withdraw aktif.
- Saldo daftar label dibaca cepat dari snapshot materialized; worker background menghitung ulang snapshot secara bulk dari `royalty_lines` dengan aturan identik ke detail/withdrawable, sehingga request daftar tidak pernah menjalankan agregasi berat.
- Daftar label default diurutkan berdasarkan saldo available terbesar, mendukung urutan label/email dua arah, serta menampilkan bulan laporan withdraw terakhir atau `Belum pernah WD`.

### 3.4 Release Management
- Draft release + multi-track audio/cover upload ke R2.
- Metadata track: producer, arranger, preview timestamp, title language, lyric language, Original/Cover/Live, featuring existing/new, Spotify Artist ID, YouTube Artist ID, dan lyrics.
- Submission membuat notifikasi in-app admin dan email best-effort.
- Upload Rilisan tampil sebelum Rilisan pada navigasi label.

### 3.5 Pay-Per-Release & Xendit
- Submit PPR tidak membuat invoice.
- Admin approval membuat satu payment document gabungan: biaya dasar + seluruh add-on terpilih.
- Payment creation idempoten dengan deterministic `reference_id`; parallel approval tetap satu invoice.
- Xendit Payment Session baru dibuat ketika label membuka checkout invoice.
- Provider polling backend adalah sumber kebenaran pembayaran; return URL hanya untuk navigasi.
- Release berstatus approved setelah payment PPR yang sebelumnya sudah disetujui admin terkonfirmasi.

### 3.6 Royalty & Large Data
- Massive Believe CSV (80MB+) memakai direct upload R2 dan background workers.
- R2 bucket CORS merge-safe mengizinkan origin production apex/`www` dan preview secara bersamaan untuk direct PUT upload.
- Periode hanya berasal dari kolom `Bulan laporan`; baris tanpa periode valid ditolak.
- Import publish, mark dana received, rate sync, audit/reconciliation, dan legacy withdrawals bersifat background + resumable.
- Label rate mass update mendukung XLSX/CSV.
- Legacy-settled/withdrawn data tidak tampil sebagai saldo label aktif.
- Audit saldo global memakai cutoff efektif paling akhir antara `labels.last_withdrawn_period` dan seluruh riwayat withdraw `paid.period_to`.
- Baris `withdrawn` setelah cutoff efektif dideteksi sebagai orphan; commit eksplisit memulihkannya ke available, menghitung ulang persentase label terkini, dan menyegarkan snapshot.
- Baris pasca-cutoff yang statusnya masih draft/pending/available tetapi keliru bertanda `legacy_settled=true` juga dideteksi dan dipulihkan tanpa mengubah status aslinya.
- Status induk laporan menjadi sumber kebenaran: baris draft/pending pada laporan `dana_received` harus available, sedangkan baris draft pada laporan `published` harus pending. Audit mendeteksi dan commit menyelaraskan status secara bertahap.
- Admin Finance memiliki endpoint diagnosis read-only per label yang mengelompokkan seluruh royalty lines berdasarkan status, jenis/nilai periode, penanda pembayaran, status pencocokan, dan status induk import tanpa mengubah saldo.
- Admin Finance memiliki audit file ganda read-only di Royalty Import; audit membandingkan fingerprint file, jumlah/nilai per periode, dampak per label, saldo aktif, dan risiko riwayat pembayaran tanpa fungsi hapus.
- Label dengan withdraw aktif atau riwayat paid tanpa `period_to` diblokir dari pemulihan otomatis agar tidak terjadi pembayaran ganda.
- Pekerjaan hitung ulang persentase yang tidak memperbarui perkembangan selama lebih dari empat jam ditutup otomatis agar tidak memblokir koreksi saldo selamanya; proses yang masih aktif tetap dilindungi.
- Admin Finance/Super Admin dapat membuat riwayat legacy manual berdasarkan label, rentang bulan, tanggal pengajuan, dan tanggal pencairan; nominal dihitung otomatis dan proses settlement berjalan di background.
- Picker label pada flow manual memakai server-side search dan tidak memfilter label berdasarkan status withdraw.
- Admin Dashboard membagi Total Bagian Label menjadi Sudah Withdraw (modern + legacy) dan Belum Withdraw dengan invariant jumlah keduanya sama dengan total.

### 3.7 Support, Contracts & Documents
- Tiket Content ID claim memerlukan URL YouTube valid dan deklarasi originalitas.
- CMS dapat mengunggah tanda tangan/stempel JPG/PNG/WEBP ke R2.
- Release approved/delivered/live dapat menghasilkan Surat Pernyataan Hak Cipta PDF berisi penanggung jawab, artist, label, judul track, legal entity, signature, dan stamp.

### 3.8 Scheduled Automation
- Ringkasan royalti bulan sebelumnya dikirim pada tanggal 3, 02:00 UTC.
- Pengiriman idempoten per `(label_id, period)`; SMTP failure tersimpan sebagai retryable `failed`, bukan `sent`.
- Background `migrate_jobs` dan `royalty_imports` terminal menghasilkan notifikasi in-app satu kali per status.

## 4. Architecture

### Frontend
- React + React Router + Tailwind CSS + Recharts.
- API client memakai `process.env.REACT_APP_BACKEND_URL`/same-origin `/api` dan `withCredentials`.
- Browser selalu memakai path API relatif agar alias domain apex/`www` tidak berubah menjadi credentialed cross-origin request.
- UI primitives berada di `/app/frontend/src/components/ui/`.
- Semua elemen interaktif/kritis menggunakan `data-testid`.

### Backend
- FastAPI + Motor/PyMongo + APScheduler.
- Semua endpoint berada di prefix `/api`.
- MongoDB hanya memakai `MONGO_URL` dan `DB_NAME` dari environment.
- Domain routes berada di `/app/backend/routes/`; shared auth di `/app/backend/auth_utils.py`.

### Storage & Integrations
- Cloudflare R2 melalui `backend/storage_service.py`.
- Xendit Payment Sessions production dengan backend polling.
- Hostinger SMTP melalui `backend/email_service.py`.
- Custom JWT authentication.

## 5. Primary Data Models
- `users`: id, email, password_hash, role, status, token_version.
- `labels`: id, user_id, payment/subscription state, account status, balances.
- `releases`: metadata, tracks, status, payment status, selected add-ons.
- `tracks`: artist metadata, audio, ISRC, preview/language/type/lyrics fields.
- `payments`: release_id, reference_id, amount, line_items, provider state.
- `royalty_lines`: import_id, label_id, period, quantity, label_idr, status.
- `bank_account_change_requests`: snapshots, proposed bank, approval target/status, audit metadata.
- `monthly_email_deliveries`: label_id, period, status, attempts, summary.

## 6. Non-Functional Requirements
- No ObjectId leakage; Mongo projections exclude `_id` for API responses.
- Datetimes use timezone-aware ISO values.
- Sensitive mutations are audited and revoke sessions where appropriate.
- Heavy operations must never block the request lifecycle.
- Layouts must not horizontally overflow at mobile or desktop widths.

## 7. Current Status
- P0 multi-device authentication is implemented and independently verified.
- P1 account, release/PPR, support/add-on, and copyright PDF scope is implemented.
- P2 monthly summary scheduling and background completion notifications are implemented.
- Audit production read-only F - Audio menemukan enam import Feb–Jul 2026 sebesar €137,54048766; saldo aktif Rp914.491 tidak berasal dari kesalahan formula 50%, melainkan royalty lines pasca-cutoff yang tidak aktif serta saldo pending tersimpan negatif.
- Phase 55 global orphan-withdrawn audit/recovery sudah diimplementasikan dan terverifikasi di preview; production masih memerlukan redeploy, preview audit global, review admin, lalu commit eksplisit.
- Phase 56 menutup blind spot Phase 55: audit sebelumnya melewati baris pasca-cutoff yang bukan `withdrawn` tetapi masih bertanda sudah dibayar. Dua CSV F - Audio membuktikan nilai tepat Rp1.253.286, sedangkan production tetap Rp914.491 setelah rekonsiliasi lama.
- Verifikasi production pasca-Phase 56 tetap menunjukkan nol koreksi. RCA Phase 57 menemukan blind spot lanjutan: baris biasa berstatus draft/pending pada laporan yang induknya sudah `published`/`dana_received` dilewati audit dan seluruh kartu saldo.
- Setelah verifikasi Phase 57 production tetap nol, pendekatan koreksi dihentikan. Phase 58 menambahkan diagnosis read-only agar kategori aktual Rp338.795 dapat dibaca langsung sebelum perubahan saldo berikutnya.
- Production memiliki satu pasangan duplikat pasti: `MEI 2026.csv` dan `Mei 2022.csv`, masing-masing 162.836 baris dan €8.296,7551 dengan breakdown periode identik tetapi kurs Rp18.000 vs Rp15.500. Phase 59 menyediakan audit dampak lengkap sebelum keputusan arsip.
- RCA production menemukan pekerjaan hitung ulang global lama `3a8a7130-7646-46ef-a1eb-444f89bc8565` masih berstatus processing sejak 23 Agustus 2026 meski tidak ada perkembangan. Watchdog dan commit guard yang baru menutup pekerjaan kedaluwarsa otomatis.
- Preview Hostinger SMTP authentication and one real internal delivery have been verified with the official mailbox.
- Full implementation history: `/app/memory/CHANGELOG.md`.
- Remaining priorities/blockers: `/app/memory/ROADMAP.md`.
- Test credentials: `/app/memory/test_credentials.md`.

## 8. Key References
- Auth: `backend/routes/auth.py`, `backend/auth_utils.py`.
- Release/PPR: `backend/routes/releases.py`, `backend/payment_service.py`.
- Bank approval: `backend/routes/bank_change_service.py`, `backend/routes/labels.py`, `backend/routes/admin.py`.
- Documents: `backend/routes/cms.py`, `backend/routes/copyright_generator.py`.
- Automation: `backend/routes/monthly_royalty_email.py`, `backend/routes/background_job_notifications.py`, `backend/routes/cron_jobs.py`.
- Balance integrity: `backend/routes/balance_audit.py`, `frontend/src/pages/admin/BalanceAuditPanel.jsx`.
- New regression suites: `backend/tests/test_phase41_multidevice_auth.py` through `test_phase45_scheduled_notifications.py`.
- Orphan recovery regression: `backend/tests/test_phase55_orphan_withdrawn_recovery.py`; independent report `/app/test_reports/iteration_45.json`.
- Stale-job watchdog regression: `backend/tests/test_iter46_stale_recalculation_watchdog.py`; independent report `/app/test_reports/iteration_46.json`.
- Legacy marker recovery regression: `backend/tests/test_iter47_balance_audit_draft_legacy_marker.py`; independent report `/app/test_reports/iteration_47.json`.
- Import-line status recovery regression: `backend/tests/test_phase57_import_line_status_recovery.py`; independent report `/app/test_reports/iteration_48.json`.