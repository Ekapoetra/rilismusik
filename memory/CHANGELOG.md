# RILIS MUSIK — Changelog

## 2026-06 — Fix: Daftar Chat Internal Tampilkan Akun Terhapus
- `GET /api/chat/admin/admins` (`routes/chat.py`) sebelumnya hanya menyaring `status != "suspended"`, sehingga admin yang dihapus (soft-delete → `status: "disabled"`, `deleted_at`) tetap muncul di tab INTERNAL Pusat Chat.
- Filter diperbarui menjadi `status $nin ["suspended","disabled"]` + `deleted_at $in [None]` agar hanya akun admin aktif yang tampil.
- Verifikasi DB: menonaktifkan 1 akun → hilang dari daftar (25→24), dipulihkan → muncul lagi (24→25). Perubahan uji di-revert bersih.


## 2026-09-04 — Phase 72: Solid Notification Dropdown & Activity Actor Names
- Mengubah dropdown lonceng menjadi latar `#101010` yang sepenuhnya solid dan menghapus backdrop blur/transparansi.
- Endpoint Log Aktivitas kini mengambil nama asli/nama akun pelaku secara bulk dari koleksi `users`, tanpa query N+1.
- Log dari user yang sudah terhapus atau tidak ditemukan tetap menampilkan `user_id` sebagai fallback audit.
- Melokalkan judul/kolom Log Aktivitas dan menambahkan loading, error, serta test ID pada informasi penting.
- Verifikasi: API mengembalikan nama `Super Admin`, browser menampilkan nama akun serta fallback ID, computed dropdown `rgb(16, 16, 16)` dengan `backdropFilter=none`, dan frontend production build lulus. Tidak ada API **MOCKED**.

## 2026-09-04 — Phase 71: Admin Notification Header & Log
- Memindahkan lonceng notifikasi admin ke sticky header kanan atas pada desktop/mobile dan menghapusnya sepenuhnya dari sidebar serta drawer.
- Menambahkan halaman `/admin/notifications` dengan pencarian, filter status baca/jenis/rentang tanggal, pagination, tandai satu/semua dibaca, dan tautan tujuan internal.
- Menambahkan scope audit seluruh admin khusus Super Admin; admin biasa dengan `notifications.view` hanya dapat melihat serta mengubah notifikasi miliknya.
- Menambahkan endpoint `GET /api/notifications/admin/log` dengan permission dinamis, proyeksi MongoDB tanpa `_id`, metadata penerima, pagination, dan seluruh filter log.
- Memperbaiki overflow mobile 390px melalui grid `minmax(0,1fr)`, batas lebar kontrol, wrapping konten, dan pagination responsif.
- Verifikasi akhir: targeted backend 6/6, frontend production build, desktop browser, mobile 390px (`scrollWidth=390`), posisi header/drawer, filter pencarian, scope, serta RBAC lulus. Tidak ada API **MOCKED**.

## 2026-09-04 — Phase 70: Status KYC pada Manajemen Label
- Menambahkan kolom Status KYC terpisah di Admin Label Management.
- Badge status memakai istilah Indonesia dan warna semantik untuk Belum Lengkap, Menunggu Review, Terverifikasi, Perlu Diperbarui, dan Ditolak.
- Alasan penolakan KYC tersedia melalui tooltip badge saat datanya ada.
- Mengubah grid desktop menjadi kolom adaptif dan layout tablet/mobile menjadi summary rows agar tidak clipping atau horizontal overflow.
- Verifikasi: kontrak API/status 2/2, production build, desktop browser, serta mobile 390px lulus. Tidak ada API **MOCKED**.

## 2026-09-04 — Phase 69: Dynamic Admin RBAC & UI Navigation Builder
- Mengganti RBAC admin hard-coded menjadi katalog permission backend granular untuk tab, subtab, dan aksi seperti view/manage/review/import/delete.
- Menambahkan CRUD role kustom, rename/edit role bawaan, proteksi Super Admin, deaktivasi role, dan penerapan permission pada sesi aktif tanpa login ulang.
- Menambahkan edit pengguna admin: nama, role custom/bawaan, status, password opsional, serta revokasi sesi otomatis saat assignment role berubah.
- Menambahkan role bawaan Admin UI dengan pengaturan label Indonesia/Inggris, visibility, parent/subtab satu tingkat, route internal immutable, dan urutan drag-and-drop menggunakan `dnd-kit`.
- Sidebar admin desktop kini dapat diciutkan ke icon rail dan menyimpan preferensi; mobile memakai drawer geser. Navigasi difilter backend berdasarkan permission efektif.
- Menambahkan mode read-only pada Role, UI Settings, KYC, Rilisan, Pembayaran, Royalti, Withdraw, dan Label sesuai action permission.
- Mempertahankan kompatibilitas role lama melalui migrasi RBAC versioned serta bridge legacy endpoint checks.
- Memperbaiki overflow mobile Admin Royalty Import; viewport 390px kini memiliki document/body width 390px.
- Verifikasi akhir: 17/17 targeted/regression, testing agent RBAC 7/7, production build, desktop/mobile browser, drag-and-drop, active-token permission refresh, dan role deactivation lulus. Tidak ada API **MOCKED**.

## 2026-09-04 — Phase 68: Artist social identity & WhatsApp follow-up
- Menambahkan multi-link sosial wajib untuk tambah/edit artis: Instagram, TikTok, Facebook, YouTube, X/Twitter, Spotify, Situs Web, dan Lainnya.
- Menambahkan validasi backend URL/domain platform, batas 10 tautan, deduplikasi, dan kewajiban tautan Spotify menuju profil artis.
- Wizard rilisan kini dapat memanggil artis tersimpan dalam mode read-only; artis legacy tanpa sosial memblokir submit dan diarahkan ke Manajemen Artis.
- Artis baru pada wizard wajib nama + minimal satu tautan; saat submit berhasil sistem membuat profil artis reusable/profile-only dan menyimpan snapshot nama/artist_id/seluruh sosial pada rilisan.
- Detail submitted admin/label menampilkan tautan sosial artis utama dan featuring. Backend menggunakan data profil tersimpan yang authoritative sehingga snapshot klien tidak dapat memanipulasi identitas artis.
- Menambahkan tombol Hubungi Label via `wa.me` pada detail rilisan admin dengan nomor label, judul, status Indonesia, dan catatan workflow; pesan hanya dibuka sebagai draft, tidak dikirim otomatis.
- Melokalkan status, tombol aksi, stepper, dan navigasi rilisan/artis ke Bahasa Indonesia tanpa mengubah enum backend.
- Verifikasi akhir: 10/10 targeted/regression, testing agent 9/9, production build, browser desktop/mobile, multi-link, status-template WhatsApp, RBAC, dan KYC lulus. Tidak ada API **MOCKED**.

## 2026-09-04 — Phase 67: Global withdraw search & label identity
- Menambahkan pencarian nama label server-side pada Admin Withdraw; saat pencarian aktif, daftar mengambil seluruh riwayat lintas bulan sementara filter status tetap berlaku.
- Pencarian mendukung beberapa kata tanpa harus berurutan, sehingga nama seperti `Demo Label PPR` dapat ditemukan melalui `Demo PPR`.
- Menambahkan kontrak `logo_url` string/null yang stabil pada daftar admin, profil label, dan dashboard label.
- Menambahkan kolom Logo di samping Label pada Label Management serta logo besar pada header Profil dan Dashboard; logo kosong/rusak memakai fallback inisial.
- Memperbaiki tampilan error object pada analytics Dashboard menjadi pesan Indonesia yang dapat dibaca.
- Verifikasi akhir: 9/9 backend/regresi, Python compile, frontend production build, browser desktop/mobile, gambar R2 nyata, dan pencarian lintas 2024–2026 lulus. Tidak ada API **MOCKED**.

## 2026-09-03 — Phase 66: Mandatory label KYC
- Mewajibkan KYC untuk seluruh label termasuk legacy; hanya Dashboard, Profil/KYC, Kontrak, dan Notifikasi yang tetap terbuka sebelum verifikasi.
- Menambahkan checklist identitas lengkap, upload logo JPG/PNG maksimal 5 MB, dan KTP JPG/PNG maksimal 10 MB.
- KTP disimpan pada namespace R2 privat, diblokir dari endpoint file publik, dan hanya dilayani melalui endpoint terautentikasi untuk pemilik serta reviewer resmi.
- Menambahkan antrean review KYC untuk Super Admin/Admin Support dengan preview privat, approve, reject beralasan wajib, notifikasi, activity log, dan counter Admin Dashboard.
- Route inti memakai backend gate `KYC_REQUIRED`; frontend tetap merender halaman yang dipilih dalam keadaan blur dengan overlay tindakan ke Profil/KYC.
- Perubahan data identitas setelah verified otomatis mengunci ulang akun sampai KTP baru direview.
- Verifikasi akhir: targeted KYC 5/5, regresi release 6/6, Python compile, frontend production build, browser lockout/profile, serta browser admin preview/approve/reject lulus. Cloudflare R2 diuji nyata; tidak ada API **MOCKED**.

## 2026-09-03 — Phase 65: Complete release submission and Believe workflow
- Mengganti form submit Label menjadi wizard 4 tahap dengan metadata rilisan, artist/featuring unlimited, metadata per-track, file, addons, deklarasi, dan review.
- Menambahkan validasi client+server untuk cover JPG/PNG tepat 3000×3000 dan WAV valid dengan sample rate 44,1/48 kHz.
- Menambahkan URL Spotify per artist, validasi original YouTube `/channel/UC…`, snapshot Nama Label/PIC akun, C/P Line, tahun produksi, dan tanggal rilis minimal 7 hari.
- Setiap track kini menyimpan vocal/instrumental, Writer, Composer, Arranger, Producer, explicit, preview seconds, bahasa, lirik, audio sample rate, dan ISRC. Instrumental otomatis `Instrumental`.
- Need Revision mempertahankan track ID dan audio upload, menampilkan catatan admin di editor, serta resubmit kembali ke Submitted dengan revision/status history.
- Workflow Annual/VIP dan PPR dipisahkan; invoice PPR baru dibuat setelah metadata valid, idempoten, mencakup addon, dan mengirim notifikasi in-app/email.
- Konfirmasi payment mengubah release ke Paid, lalu Admin Release wajib Approve → Deliver to Believe → input UPC+ISRC semua track → Live.
- Menambahkan Reject sebelum Live dan Takedown hanya dari Live dengan alasan wajib; input ISRC divalidasi atomik agar request gagal tidak menulis sebagian track.
- Detail Admin/Label sekarang menampilkan seluruh metadata release dan track. Finance/Support mendapat tampilan read-only; hanya Super Admin/Admin Release melihat workflow controls.
- QA independen awal 11/11 menemukan URL YouTube custom lolos draft dan action controls terlihat pada Finance; keduanya diperbaiki. Gate akhir 16/16 lulus, frontend build dan browser desktop/mobile lulus.
- Cloudflare R2, SMTP, dan provider Xendit hanya **MOCKED pada tes transport terisolasi**; endpoint aplikasi dan state machine diuji nyata di preview.

## 2026-09-03 — Phase 64: Scoped label balance reconciliation
- Menambahkan `Audit & Sesuaikan Saldo` pada Detail Label untuk Super Admin/Admin Finance sehingga koreksi dapat dijalankan satu label dahulu, termasuk 24migo, lalu digunakan pada label lain.
- Preview scoped menghitung setiap royalty line setelah cutoff dengan persentase aktif label dan kurs line; jika kurs line kosong, memakai kurs parent import.
- Preview menampilkan saldo lama→benar, cutoff terverifikasi, periode terdampak, baris salah status, dan perhitungan lama→persentase aktif sebelum tombol commit tersedia.
- Commit memulihkan baris post-cutoff yang salah withdrawn/legacy, mengarahkan import `dana_received` ke available, menghitung ulang nilai IDR, menyegarkan saldo/cache, dan menjaga withdrawal web serta baris historis tetap utuh.
- Global audit tetap memakai pipeline ringan; proyeksi line-level yang lebih mahal hanya dijalankan untuk audit scoped.
- Data legacy tanpa revenue/kurs dipertahankan agar alur lama tidak terblokir; data lengkap tetap direkonsiliasi presisi.
- Simulasi exact 24migo: €452,044530864149 Juni + €326,12 Juli, rate 35%, kurs 19.000/18.500 menghasilkan Rp5.117.660 dari baseline Rp3.311.210; delta Rp1.806.450 dan paid web withdrawal tetap tidak berubah.
- Verifikasi akhir: 14/14 targeted/regression tests dan frontend production build lulus, tanpa API mocked. Fixture phase64 telah dibersihkan.

## 2026-09-03 — Phase 63: Release priority and monthly finance overview
- Release Management kini default pada urutan Submitted → Awaiting Payment → Paid → Under Review → Need Revision → Approved → Delivered → Draft → Live; status yang sama diurutkan dari pembaruan terbaru.
- Admin Payments menampilkan total pemasukan invoice paid berdasarkan `paid_at` dan field `amount`, dengan kartu angka utama, pilihan bulan/tahun, total tahunan, dan jejak 12 bulan.
- Admin Withdraw menampilkan Dana Keluar berdasarkan `paid_date` serta Dana Tertunda requested+approved berdasarkan `request_date`.
- Filter bulan/tahun Withdraw mengubah kartu ringkasan dan daftar; paid difilter dari bulan pencairan, status lain dari bulan pengajuan.
- Menambahkan indeks tanggal/status untuk payment dan withdrawal reporting serta validasi pasangan year/month.
- Menambahkan loading cue deterministik pada daftar Withdraw saat filter periode/status berubah.
- Verifikasi: targeted testing agent 4/4 dan regresi akhir gabungan 11/11 lulus, frontend production build lulus, desktop/mobile lulus, tanpa API mocked.

## 2026-09-03 — Phase 62: Guarded legacy withdrawal period edit
- Menambahkan tombol edit hanya pada withdrawal `paid` dengan `legacy_import=true`; withdrawal yang berasal dari web tidak dapat diedit di UI maupun API.
- Admin Finance/Super Admin dapat mengubah hanya bulan laporan terakhir setelah melihat preview cutoff, saldo pending/available, dan jumlah royalty lines terdampak.
- Commit berjalan di background, single-use preview, stale/concurrent guards, serta memblokir active web withdrawal dan paid history tanpa `period_to`.
- Penurunan cutoff memulihkan status royalty line sesuai status induk import; kenaikan cutoff kembali menandai rentang sebagai legacy settled tanpa mengubah withdrawal web.
- Label cutoff, stored balances, snapshot/cache, revision history, activity log, dan deskripsi transaksi legacy disegarkan setelah commit.
- Menutup akses langsung Admin Support ke halaman/API Withdraw dan menstabilkan modal agar status selesai selalu terlihat tanpa spinner tersisa.
- Verifikasi: 9/9 backend/regression lulus, frontend production build lulus, serta browser desktop/mobile, redirect RBAC, preview, commit, dan completion state lulus. Tidak ada API yang di-mock.

## 2026-09-03 — Windows native dropdown contrast fix
- Menambahkan `color-scheme: dark` pada root dan seluruh native select.
- Menetapkan background gelap serta teks putih secara eksplisit untuk `option`/`optgroup`, termasuk opsi terpilih.
- Frontend production build lulus dan computed browser styles memverifikasi select serta opsi aktif/nonaktif memiliki kontras gelap-terang yang benar.

## 2026-09-03 — Phase 61: Admin payment operations
- Melokalkan Admin Payments dengan status `Dibayar`, `Menunggu Pembayaran`, `Kedaluwarsa`, `Gagal`, dan `Dibatalkan`.
- Menambahkan modal detail invoice berisi label, email, jenis layanan, deskripsi, metode pembayaran Xendit, nominal, status tindakan, waktu, dan rincian line item.
- Menambahkan workflow PPR ke Release, WAMI ke halaman proses, layanan custom `Sedang Dikerjakan`/`Selesai`, dan langganan otomatis tanpa aksi manual.
- Pembayaran sukses kini membuat notifikasi in-app serta email idempoten untuk label dan admin yang relevan; SMTP tetap best-effort dan tidak menggagalkan fulfillment.
- Metode pembayaran diambil dari payload provider atau Payment Request/Payment Xendit, bukan input browser.
- Admin Dashboard kini menampilkan kartu pembayaran yang perlu ditindaklanjuti dan membuka daftar terfilter.
- Memperbaiki bootstrap index lama agar seluruh index notifikasi baru tetap dibuat, serta membuat test ID lonceng desktop/mobile unik.
- Verifikasi akhir: 12/12 backend/regresi lulus, frontend production build lulus, UI desktop/mobile serta modal/aksi lulus. Xendit/SMTP hanya di-MOCKED pada tes provider terisolasi; API aplikasi tidak di-mock.

## 2026-09-02 — Phase 60: Guarded royalty import replacement
- Menambahkan tombol `Ganti File Import` untuk import published/dana_received pada Royalty Detail.
- File pengganti diunggah ke R2 path terpisah, divalidasi ukuran/header, diproses background, dan disembunyikan dari Analytics/saldo sampai commit.
- Preview wajib menampilkan baris/EUR lama→baru, perubahan saldo aktif, penyesuaian pembayaran lama, dampak per label, dan nominal pengajuan aktif sebelum→sesudah.
- Commit hanya Super Admin dengan frasa `GANTI DATA`; data import/lines lama dihapus permanen setelah pengganti siap.
- Nominal paid/legacy withdrawal dipertahankan; selisih historis dibuat sebagai adjustment current balance yang idempotent.
- Pengajuan requested/approved tetap pada dokumen/status yang sama tetapi amount, line count, transaction, dan revision history dihitung ulang.
- Menambahkan guard perubahan setelah preview, guard active withdrawal tanpa period range, cancel staging, startup resume, R2 cleanup, dan audit record replacement permanen.
- Mark Dana Received tetap memproses draft+pending untuk mencegah line tertinggal.
- Terverifikasi 24/24 backend, frontend build, panel screenshot, serta browser E2E nyata upload R2→preview→commit→database verification; tidak ada API yang di-MOCKED.

## 2026-09-02 — Phase 59: Read-only duplicate import audit
- Menemukan pasangan duplikat production yang pasti: `MEI 2026.csv` dan `Mei 2022.csv`, masing-masing 162.836 baris, €8.296,7551, periode Apr 2025–Mei 2026, dan jumlah baris per bulan identik; kursnya berbeda Rp18.000 vs Rp15.500.
- Menambahkan audit background hanya-baca yang membandingkan isi per periode serta menghitung dampak EUR/IDR, saldo aktif, riwayat, label terdampak, dan kebutuhan review pembayaran.
- Menambahkan panel Audit File Ganda pada Royalty Import tanpa tombol hapus/arsip.
- Riwayat import kini menampilkan nama file, rentang periode, dan label `Total File EUR (Semua Bulan)` agar tidak tertukar dengan Analytics bulanan.
- Polling UI langsung menampilkan status, bertahan dari gangguan koneksi sementara, dan memberi batas tunggu 15 menit.
- Terverifikasi 8/8 backend, build frontend, dan Playwright progres audit; tidak ada API yang di-MOCKED.

## 2026-09-02 — Phase 58: Read-only production balance diagnostics
- Setelah Phase 57 production tetap menunjukkan nol koreksi, seluruh perubahan saldo tambahan dihentikan sampai bukti data tersedia.
- Menambahkan `GET /api/admin/balance-audit/labels/{label_id}/diagnostic` untuk mengelompokkan seluruh baris label berdasarkan status, periode dan jenis datanya, penanda pembayaran, status pencocokan, serta status induk laporan.
- Endpoint hanya baca, tidak menjalankan audit, tidak mengubah status baris, dan tidak mengubah saldo.
- Terverifikasi dengan simulasi received/published/draft dan 10/10 regresi backend.

## 2026-09-02 — Phase 57: Parent-import status recovery
- Verifikasi production setelah Phase 56 tetap menunjukkan F - Audio Rp914.491, nol koreksi, dan nol penanda pembayaran salah.
- RCA menemukan baris draft/pending dapat tertinggal ketika proses publish/Dana Diterima terputus, walaupun induk laporan sudah berstatus `published` atau `dana_received`.
- Audit kini mengelompokkan per import dan membandingkan status baris dengan status induk laporan; selisih ikut dihitung pada Royalti Salah Status dan perkiraan saldo.
- Commit mengubah draft/pending menjadi available untuk laporan yang sudah diterima dan draft menjadi pending untuk laporan yang sudah diterbitkan; draft pada laporan belum terbit tetap tidak diubah.
- Alur Dana Diterima dan pemulihan saat startup kini memeriksa draft serta pending agar masalah tidak berulang.
- Terverifikasi 22/22 backend setelah satu retry timeout jaringan, frontend build/UI lulus, dan tidak ada API yang di-MOCKED (iteration 48).

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