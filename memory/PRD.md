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
- Seluruh label, termasuk akun legacy, wajib menyelesaikan KYC sebelum memakai fitur inti. Dashboard, Profil/KYC, Kontrak, dan Notifikasi tetap dapat diakses selama proses aktivasi.
- Checklist KYC mencakup PIC, nama/logo label, email aktif terverifikasi, WhatsApp, kontrak aktif, rekening lengkap, alamat, kota, dan foto KTP.
- Halaman inti yang belum terbuka tetap dirender dalam keadaan blur dengan overlay tindakan menuju Profil/KYC; backend tetap menolak akses data memakai kode `KYC_REQUIRED`.
- Logo menerima JPG/PNG maksimal 5 MB. KTP menerima JPG/PNG maksimal 10 MB, disimpan privat, dan hanya dapat dibaca pemilik label, Super Admin, atau Admin Support melalui endpoint terautentikasi.
- Super Admin/Admin Support memiliki antrean KYC, preview KTP privat, approve, dan reject dengan alasan wajib. Perubahan identitas setelah verifikasi membatalkan aktivasi sampai review ulang.
- Saldo selalu diturunkan dari `royalty_lines` pending/available non-legacy, bukan lifetime rollup.
- Rekening awal diverifikasi admin; perubahan rekening berjalan melalui approval dua arah.
- Admin Label Management menampilkan saldo available per label dalam Rupiah, tidak termasuk dana withdrawn/legacy-settled atau dana yang sedang direservasi untuk withdraw aktif.
- Logo label ditampilkan pada kolom khusus di Label Management serta pada header Profil dan Dashboard label; akun tanpa logo memakai fallback inisial nama label.
- Label Management menampilkan kolom Status KYC terpisah dengan badge Indonesia: Belum Lengkap, Menunggu Review, Terverifikasi, Perlu Diperbarui, atau Ditolak; alasan penolakan tersedia sebagai tooltip.
- Saldo daftar label dibaca cepat dari snapshot materialized; worker background menghitung ulang snapshot secara bulk dari `royalty_lines` dengan aturan identik ke detail/withdrawable, sehingga request daftar tidak pernah menjalankan agregasi berat.
- Daftar label default diurutkan berdasarkan saldo available terbesar, mendukung urutan label/email dua arah, serta menampilkan bulan laporan withdraw terakhir atau `Belum pernah WD`.

### 3.4 Release Management
- Draft release + multi-track audio/cover upload ke R2.
- Metadata track: producer, arranger, preview timestamp, title language, lyric language, Original/Cover/Live, featuring existing/new, Spotify Artist ID, YouTube Artist ID, dan lyrics.
- Submission membuat notifikasi in-app admin dan email best-effort.
- Upload Rilisan tampil sebelum Rilisan pada navigasi label.
- Release Management default diurutkan berdasarkan prioritas operasional: Submitted, Awaiting Payment, Paid, Under Review, Need Revision, Approved, Delivered, Draft, lalu Live; dalam status yang sama pembaruan terbaru tampil lebih dahulu.
- Label submit memakai wizard empat tahap: informasi rilisan, unlimited artist/featuring dengan URL Spotify opsional, metadata/kredit per track, lalu validasi file dan review.
- Setiap kredit artis wajib memiliki minimal satu tautan sosial aktif. Platform mendukung Instagram, TikTok, Facebook, YouTube, X/Twitter, Spotify, Situs Web, dan Lainnya hingga 10 tautan.
- Artis tersimpan dipanggil dari Manajemen Artis dalam mode read-only pada wizard; artis legacy tanpa sosial memblokir submit sampai profil diperbaiki.
- Artis baru pada wizard wajib nama + tautan sosial; submit berhasil otomatis membuat profil artis reusable/profile-only serta menyimpan snapshot artist_id, nama, dan semua tautan pada rilisan.
- Release wajib memuat judul, genre/subgenre, label/PIC snapshot akun, SINGLE/EP/ALBUM, C Line/P Line, tahun produksi, tanggal rilis minimal 7 hari, URL web/original YouTube channel, cover JPG/PNG tepat 3000×3000, dan WAV per track pada 44,1/48 kHz.
- Metadata per track memuat ISRC opsional sampai Live, vocal/instrumental, Writer, Composer, Arranger, Producer, explicit, preview seconds, bahasa judul/lirik, dan lirik. Instrumental otomatis memakai nilai `Instrumental` tanpa input lirik.
- Need Revision tetap menjadi status backend dan membuka editor seperti Draft; track ID/audio yang sudah valid dipertahankan saat edit, lalu resubmit kembali ke Submitted dengan status history.
- Annual/VIP workflow: Submitted → Under Review → Approved → Delivered to Believe → Live. PPR: Submitted → Under Review → Awaiting Payment → Paid → Approved → Delivered to Believe → Live.
- Setelah metadata PPR valid, Admin Release mengirim satu invoice gabungan biaya dasar+addons. Label menerima notifikasi in-app/email; pembayaran Xendit mengubah status ke Paid dan tetap memerlukan approval Admin Release.
- Status Live mensyaratkan UPC rilisan dan ISRC pada setiap track; Reject tersedia sebelum Live dan Takedown hanya dari Live dengan alasan wajib.
- Detail release Admin dan Label menampilkan metadata penuh, seluruh artist/featuring, kredit/lyrics/audio per track, cover, addon, serta invoice sepanjang lifecycle.
- Detail rilisan admin menampilkan tautan sosial seluruh artis dan tombol Hubungi Label via WhatsApp dengan template judul, status, serta catatan workflow Bahasa Indonesia tanpa pengiriman otomatis.
- Label status dan tindakan workflow di UI memakai Bahasa Indonesia; enum backend tetap stabil agar data lama dan integrasi tidak rusak.

### 3.5 Admin Access & UI Configuration
- Dynamic RBAC menggantikan hard-coded role checks: Super Admin dapat membuat role bernama khusus serta mengubah nama, status, dan permission role bawaan/kustom.
- Permission dikatalogkan per modul menjadi Tab → Subtab → Fungsi/Aksi. Backend tetap menjadi sumber kebenaran dan frontend menyembunyikan/menonaktifkan kontrol yang tidak diizinkan.
- Perubahan permission role berlaku pada access token aktif di request berikutnya; perubahan assignment role user menaikkan `token_version` dan memutus sesi lama.
- Role bawaan `Admin UI` mengelola label navigasi Indonesia/Inggris, visibilitas, urutan drag-and-drop, serta parent/subtab satu tingkat menuju route internal yang immutable.
- Pengguna admin dapat diubah nama, role, status, dan password. Role nonaktif menolak request sesi aktif serta login baru; Super Admin efektif selalu full access dan role bawaan tidak dapat dihapus.
- Sidebar admin desktop dapat diciutkan menjadi icon rail dengan preferensi persisten; mobile memakai drawer geser dengan backdrop.
- Lonceng notifikasi admin berada hanya di sticky header kanan atas pada desktop/mobile dan tidak muncul di sidebar maupun drawer.
- Dropdown lonceng memakai latar solid penuh tanpa transparansi atau backdrop blur agar isi tetap jelas di atas halaman.
- Halaman `/admin/notifications` menyediakan log in-app dengan pencarian, filter status baca/jenis/rentang tanggal, pagination, tandai baca, dan tautan tujuan internal.
- Super Admin dapat mengaudit notifikasi seluruh admin dalam mode baca-saja untuk milik admin lain; admin berizin `notifications.view` hanya dapat melihat dan mengubah status baca notifikasinya sendiri.
- Log Aktivitas menampilkan nama asli/nama akun pelaku dari koleksi user; bila akun tidak lagi tersedia, ID user tetap ditampilkan sebagai fallback audit.

### 3.6 Pay-Per-Release & Xendit
- Submit PPR tidak membuat invoice.
- Admin approval membuat satu payment document gabungan: biaya dasar + seluruh add-on terpilih.
- Payment creation idempoten dengan deterministic `reference_id`; parallel approval tetap satu invoice.
- Xendit Payment Session baru dibuat ketika label membuka checkout invoice.
- Provider polling backend adalah sumber kebenaran pembayaran; return URL hanya untuk navigasi.
- Release berstatus approved setelah payment PPR yang sebelumnya sudah disetujui admin terkonfirmasi.
- Admin Payments memakai istilah Indonesia `Dibayar`, `Menunggu Pembayaran`, dan `Kedaluwarsa`, serta menampilkan modal invoice lengkap dengan label, layanan, metode provider, nominal, dan waktu pembayaran.
- Pembayaran sukses menghasilkan notifikasi in-app serta email idempoten untuk label dan admin terkait; kegagalan email tidak membatalkan fulfillment pembayaran.
- PPR yang dibayar mengarahkan Admin Release ke rilisan untuk melanjutkan distribusi, layanan custom memiliki status `Sedang Dikerjakan`/`Selesai`, dan langganan aktif otomatis tanpa tindakan manual.
- Admin Dashboard menampilkan jumlah pembayaran dibayar yang masih membutuhkan tindakan operasional dan mengarah ke daftar terfilter.
- Admin Payments menampilkan pemasukan Xendit bulanan secara prominen berdasarkan seluruh invoice `paid.paid_at` dan nominal IDR, dengan pilihan bulan/tahun serta jejak 12 bulan.

### 3.7 Royalty & Large Data
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
- Import royalti berstatus published/dana_received dapat diganti berdasarkan file yang dipilih melalui staging R2 terpisah, parsing background, dan preview wajib sebelum commit.
- Commit penggantian hanya untuk Super Admin: data lama dihapus permanen setelah file baru siap, pembayaran paid/legacy tidak diubah, selisih historis menjadi penyesuaian saldo, dan pengajuan requested/approved dihitung ulang pada dokumen yang sama.
- File pengganti tidak masuk analytics/saldo selama staging; commit menjaga cutoff per label, memulihkan match status, memperbarui transaksi, snapshot, cache, serta menyimpan audit replacement permanen.
- Label dengan withdraw aktif atau riwayat paid tanpa `period_to` diblokir dari pemulihan otomatis agar tidak terjadi pembayaran ganda.
- Pekerjaan hitung ulang persentase yang tidak memperbarui perkembangan selama lebih dari empat jam ditutup otomatis agar tidak memblokir koreksi saldo selamanya; proses yang masih aktif tetap dilindungi.
- Admin Finance/Super Admin dapat membuat riwayat legacy manual berdasarkan label, rentang bulan, tanggal pengajuan, dan tanggal pencairan; nominal dihitung otomatis dan proses settlement berjalan di background.
- Admin Finance/Super Admin dapat mengedit hanya `period_to` pada riwayat withdrawal legacy paid, wajib melihat preview cutoff/saldo/baris sebelum commit background. Withdrawal web tidak dapat diedit dan tetap menjadi batas minimum agar dana yang sudah dibayar tidak terbuka kembali.
- Penurunan cutoff legacy memulihkan status berdasarkan status induk import (`dana_received` → available, `published` → pending); kenaikan cutoff menandai rentang tambahan sebagai legacy settled. Saldo tersimpan, snapshot, cache, revision history, dan activity log diperbarui setelah commit.
- Admin Withdraw menampilkan Dana Tertunda bulanan (`requested + approved` berdasarkan `request_date`) dan Dana Keluar bulanan (`paid` berdasarkan `paid_date`) secara prominen; pilihan bulan/tahun juga memfilter daftar withdrawal.
- Pencarian nama label pada Admin Withdraw menelusuri seluruh riwayat lintas periode dan mengabaikan filter bulan untuk daftar selama pencarian aktif; filter status tetap berlaku.
- Detail Label menyediakan audit/rekonsiliasi scoped reusable: cutoff efektif berasal dari label + histori withdrawal paid, baris setelah cutoff diproyeksikan per line memakai persentase aktif dan kurs line/import, parent import `dana_received` diarahkan ke available, lalu preview wajib sebelum commit background.
- Scoped reconciliation tidak mengubah withdrawal web maupun baris sebelum/equal cutoff; data legacy tanpa EUR/kurs dipertahankan, sementara kurs line yang hilang dapat dibackfill dari import sebelum recalculation.
- Picker label pada flow manual memakai server-side search dan tidak memfilter label berdasarkan status withdraw.
- Admin Dashboard membagi Total Bagian Label menjadi Sudah Withdraw (modern + legacy) dan Belum Withdraw dengan invariant jumlah keduanya sama dengan total.

### 3.8 Support, Contracts & Documents
- Tiket Content ID claim memerlukan URL YouTube valid dan deklarasi originalitas.
- CMS dapat mengunggah tanda tangan/stempel JPG/PNG/WEBP ke R2.
- Release approved/delivered/live dapat menghasilkan Surat Pernyataan Hak Cipta PDF berisi penanggung jawab, artist, label, judul track, legal entity, signature, dan stamp.

### 3.9 Scheduled Automation
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
- Dropdown native menggunakan `color-scheme: dark` serta warna `option` eksplisit agar teks tetap terbaca pada Windows dan macOS.

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
- `admin_roles`: stable id/key, editable name/description, built-in/custom flag, active state, permission keys, RBAC schema version.
- `admin_ui_settings`: locale bawaan dan ordered navigation items berisi label ID/EN, immutable internal route, icon, visibility, dan parent/subtab.
- `labels`: id, user_id, payment/subscription state, account status, balances, profile/logo, KYC status/review metadata.
- `kyc_documents`: id, label_id, private storage key, checksum, content metadata, current/review status, reviewer, rejection reason.
- `artists`: profile account/profile-only, label_id, optional user_id, status, dan multi `social_links`.
- `releases`: metadata, tracks, status, payment status, selected add-ons, label/WhatsApp snapshot, serta primary/featured artist social snapshots.
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
- Phase 60 menyediakan penggantian import selected-file end-to-end sesuai keputusan pengguna: hard delete lama, paid tetap, adjustment saldo, active withdrawal dihitung ulang, dan mandatory preview.
- RCA production menemukan pekerjaan hitung ulang global lama `3a8a7130-7646-46ef-a1eb-444f89bc8565` masih berstatus processing sejak 23 Agustus 2026 meski tidak ada perkembangan. Watchdog dan commit guard yang baru menutup pekerjaan kedaluwarsa otomatis.
- Preview Hostinger SMTP authentication and one real internal delivery have been verified with the official mailbox.
- Phase 61 Admin Payments localization, invoice detail modal, payment action workflow, provider payment-method lookup, idempotent Admin/Label notifications, and Admin Dashboard action badge are implemented and verified.
- Native dropdown contrast pada Windows telah diperbaiki secara global; select, opsi aktif, dan opsi nonaktif terverifikasi berlatar gelap dengan teks putih.
- Phase 62 guarded legacy withdrawal edit sudah diimplementasikan: preview sebelum/sesudah, commit background, direct-web immutability, Finance/Super RBAC, dan deterministic completion UI terverifikasi.
- Phase 63 operational finance overview dan release queue ordering sudah diimplementasikan serta terverifikasi di desktop/mobile.
- Phase 64 scoped label balance reconciliation sudah diimplementasikan. Simulasi deterministik 24migo memverifikasi Rp3.311.210 → Rp5.117.660 pada cutoff 2026-05, 35%, Juni–Juli, tanpa mengubah paid web withdrawal.
- Phase 65 complete label release submission dan admin workflow sudah diimplementasikan serta terverifikasi, termasuk UI read-only untuk role admin non-release.
- Phase 66 mandatory label KYC sudah diimplementasikan: checklist profil, logo/KTP R2 privat, reviewer RBAC, approve/reject, backend gating, serta blur overlay untuk route label terlarang. Targeted backend 5/5, release regression 6/6, build frontend, dan browser label/admin lulus.
- Phase 67 menambahkan pencarian withdraw berdasarkan nama label lintas seluruh periode serta logo/fallback label pada Label Management, Profil, dan Dashboard. Gate akhir 9/9 dan browser desktop/mobile lulus.
- Phase 68 menambahkan multi-link sosial wajib untuk artis, selector artis reusable pada wizard, persistence artis baru saat submit, snapshot sosial admin, follow-up WhatsApp berbasis status, serta lokalisasi workflow. Gate akhir 10/10 dan testing agent 9/9 lulus.
- Phase 69 menambahkan dynamic admin RBAC, role/user editor, Admin UI bilingual navigation builder, nested subtab, desktop icon rail, dan mobile drawer. Gate akhir 17/17; testing agent backend 7/7; overflow Royalty mobile diperbaiki dan terukur 390/390px.
- Phase 71 memindahkan lonceng notifikasi admin ke sticky header kanan atas dan menambahkan log notifikasi terfilter dengan scope Super Admin/admin biasa. Targeted backend 6/6, frontend production build, desktop/mobile browser, RBAC, dan overflow check 390/390px lulus.
- Phase 72 membuat dropdown lonceng sepenuhnya solid dan memperkaya Log Aktivitas dengan nama pelaku serta fallback ID untuk user yang sudah tidak tersedia. API, frontend production build, dan browser visual lulus.
- Phase 73 (Verifikasi Akun) menyederhanakan aktivasi label: (1) checklist tidak lagi mensyaratkan `email_verified_at` — akun non-klaim otomatis lolos langkah email (selama email ada & aktif), akun klaim otomatis terverifikasi email saat admin menghubungkan label; efeknya tombol upload KTP kembali dapat ditekan setelah prasyarat lengkap. (2) Seluruh istilah "KYC" pada UI (label & admin, termasuk nav sidebar & heading) diganti "Verifikasi Akun"; route/testid/permission internal tetap. (3) Tombol "Klaim Label Lama" ditambahkan di tab Profil & Rekening (`POST /api/label/claim-request`) untuk akun yang sudah terlanjur daftar tanpa klaim → masuk antrean Admin Migrasi → Claims. (4) `link_claim_to_legacy_label` kini menghapus label kosong auto-buatan (beserta kontrak MDA/rekening/dokumen) sebelum memindahkan akun ke label legacy, hanya bila label lama belum punya rilisan/royalti, serta menandai `email_verified_at`. Terverifikasi via curl siklus penuh (register→claim→link) + screenshot label/admin.
- Phase 74 menambahkan empat penyempurnaan: (1) Email notifikasi klaim — `send_claim_approved_email`/`send_claim_rejected_email` dikirim best-effort saat admin link/reject klaim (terverifikasi terkirim via live SMTP). (2) Tautan YouTube Content ID kini tampil sebagai link yang dapat diklik pada detail tiket admin & label (`youtube_url` sudah tersimpan/tervalidasi https youtube). (3) Panduan aktivasi bernomor `KycStepsGuide` pada banner Verifikasi Akun menampilkan 3 langkah berurutan (lengkapi profil → unggah KTP → review admin) dengan indikator aktif/terkunci dan daftar item yang masih kurang. (4) Preview menu sidebar (`RoleNavPreview`) pada editor role admin — menampilkan menu yang akan tampil untuk role sesuai izin terpilih secara live sebelum disimpan; `/admin/access/catalog` kini menyertakan `navigation`. Semua terverifikasi via curl + screenshot.
- Phase 75 menambahkan tiga penyempurnaan alur rilisan: (1) Koreksi/mundurkan status oleh Admin Release/Super Admin — action `override_status` (+`target_status`) pada `POST /releases/{id}/admin/action` dengan whitelist status (tanpa awaiting_payment/paid), wajib alasan, tanpa efek samping pembayaran/pengiriman; UI "Koreksi / Mundurkan Status" pada panel workflow. (2) Hapus rilisan draft/ditolak untuk label — `DELETE /releases/{id}` (require_label, hanya status draft/rejected, membersihkan tracks + file R2 cover/audio); tombol hapus pada daftar Rilisan label untuk baris draft/rejected. (3) Pelabelan wajib/opsional pada form submit — kolom opsional ditandai "(opsional)" (ISRC, Arranger, Produser, Detik Preview, Featuring, URL Spotify), sisanya wajib; backend `validate_release_submission` sudah menegakkan aturan ini. Terverifikasi via curl (override live↔under_review + target invalid ditolak; draft dibuat→dihapus→404) dan screenshot UI workflow.
- Phase 76 menambahkan fitur Chat realtime (polling ~3s) berbasis widget popup mengambang di layout label & admin (`routes/chat.py`, koleksi `chat_conversations`/`chat_messages`/`chat_presence`). (1) Label ↔ Support: satu inbox support per label; semua staff Support + Super Admin melihat & membalas; Super Admin dapat membalas namun read-only jika tanpa izin support. (2) Admin ↔ Admin: chat internal 1:1 antar admin mana pun via direktori admin. (3) Presence heartbeat 20s; online = aktif <35s; indikator online tampil untuk label (melihat Support online) dan admin (melihat label & admin online). (4) Badge belum-dibaca via `GET /chat/unread`, toast + bunyi (Web Audio) saat pesan baru & popup tertutup. Otorisasi: support inbox hanya support/super admin (finance dsb ditolak 403 namun tetap bisa chat internal). Terverifikasi end-to-end via curl (label↔support, admin↔admin, unread, 403 non-support) + screenshot popup label & admin.
- Phase 77 memperkaya Chat dengan empat enhancement: (1) Riwayat/Arsip — support bisa "Selesai"-kan percakapan (`POST /chat/admin/thread/{id}/resolve`) → pindah ke tab Arsip; kirim pesan baru dari label otomatis membuka kembali (reopen) ke Aktif; filter `status=active|resolved` pada inbox. (2) Notifikasi Bell — setiap pesan baru membuat notifikasi `chat_message` untuk penerima (throttle 1 per percakapan) yang muncul di lonceng admin/label walau widget tertutup, dan otomatis ditandai terbaca saat thread dibuka. (3) Lampiran — `POST /chat/upload` ke R2 (`chat/` prefix, gambar/PDF/dok ≤15MB) dengan tombol klip; gambar tampil sebagai thumbnail, berkas sebagai tautan. (4) Indikator "sedang mengetik" — `POST /chat/typing/{id}` (window 6s) + animasi titik di thread lawan bicara. Semua terverifikasi via curl (upload+kirim lampiran, typing terlihat lawan, resolve→arsip→reopen, notifikasi bell dibuat & auto-read) dan screenshot popup admin.
- Phase 78 mengubah Admin Dashboard menjadi **Command Center / Action Center** sesuai PRD "Admin Dashboard & Action Center": (1) Endpoint baru `GET /admin/action-center` mengagregasi item operasional belum-selesai (penarikan, pembayaran, review rilisan, Verifikasi Akun, tiket, klaim label) dengan `priority` (critical/high/normal/low), `count`, `oldest_at`, `permission`, dan `link` deep-link ke modul/record tepat; diurutkan prioritas lalu tertua. (2) Dashboard baru: "Perlu Perhatian Anda" (hierarki terkuat, difilter per-permission via `hasPermission`, dengan state loading/empty "Semua beres"/error+retry), "Aksi Cepat" (shortcut proaktif), KPI "Ringkasan Platform" (sekunder), kartu Royalti, dan "Aktivitas Terbaru" (feed dari `/admin/activity-logs` dengan deep-link per record). (3) Menu "Riwayat Notifikasi" dihapus dari sidebar (idempotent `$pull` pada `admin_navigation` + dihapus dari default nav) — halaman tetap dapat diakses via link "Lihat Riwayat Notifikasi" di dropdown lonceng. (4) Lonceng notifikasi header DIPERTAHANKAN untuk notifikasi personal/chat (keputusan user opsi a, karena Chat fase 77 menyalurkan notif ke lonceng). Tidak ada perubahan business logic/modul lain. Terverifikasi via curl (action-center prioritas + nav item terhapus) & screenshot dashboard (Action Center, Quick Actions, Recent Activity, sidebar tanpa Riwayat Notifikasi, lonceng tetap ada).
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
- Import replacement regressions: `backend/tests/test_phase60_royalty_import_replacement.py`, `backend/tests/test_iter50_royalty_import_replacement_guards.py`; full browser R2 upload→preview→commit verified in preview.
- Payment operations regressions: `backend/tests/test_phase61_admin_payments.py`; final targeted result 12/12 with frontend production build and desktop/mobile browser verification.
- Legacy withdrawal edit regressions: `backend/tests/test_iter52_legacy_withdraw_edit.py`; final combined result 9/9 dengan frontend production build, desktop/mobile preview, route guard, dan completion-state browser verification.
- Finance/release reporting regressions: `backend/tests/test_iter53_finance_release_reporting.py`; final combined result 11/11, frontend production build, dan desktop/mobile month-switch verification.
- Scoped 24migo reconciliation: `backend/tests/test_iter54_phase64_scoped_24migo.py`; final combined gate 14/14 dengan exact line-level rounding, commit, clean re-preview, global audit regressions, legacy withdrawal regressions, dan frontend production build.
- Release submission/workflow: `backend/tests/test_phase65_release_submission_workflow.py`, `backend/tests/test_iter55_release_rbac_revision.py`, dan updated Phase43; final combined gate 16/16 dengan frontend production build serta desktop/mobile browser QA.
- Admin notification log: `backend/tests/test_iter60_admin_notifications_log.py`; final targeted result 6/6 dengan report `/app/test_reports/iteration_60.json`, frontend production build, serta desktop/mobile browser QA.