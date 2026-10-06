# Acuan repo untuk V10

Tanggal pemeriksaan: 22 September 2026.
Repo sumber: https://github.com/Ekapoetra/rilismusik
HEAD terverifikasi melalui git ls-remote: 6929bf25a56579d5ac81ed9def38a183665d7863.
Commit tersebut sama dengan sha pada analysis-v4/repo-tree.json. Repo sumber tetap hanya-baca; V9 merupakan prototype terpisah.

## Batas pemeriksaan

Peta ini berasal dari default navigasi backend, route frontend, dan komponen navigasi pada salinan referensi analysis-v4. Belum merupakan pengujian endpoint live, audit seluruh prosedur, atau bukti fungsi produksi berjalan.

Navigasi frontend memuat GET /admin/navigation. Susunan, visibilitas, label, grup dan izin dapat mengikuti konfigurasi tersimpan. Karena respons live belum dibaca, daftar berikut adalah acuan bawaan kode, bukan klaim sidebar situs pasti identik.

Sumber utama:
- backend/routes/admin_permission_service.py: DEFAULT_NAV_ITEMS, DEFAULT_NAV_GROUPS, NAV_GROUP_MAP.
- frontend/src/App.js: route dan penjagaan izin.
- frontend/src/contexts/AdminNavigationContext.jsx: pengambilan navigasi dinamis dan fallback.
- frontend/src/components/shared/AdminLayout.jsx: penyajian grup, induk/anak, dan sidebar.

## Inventaris bawaan repo

| Kelompok | Menu dan anak menu bawaan |
|---|---|
| Pusat Kerja | Dashboard; Pekerjaan; Status |
| Operasional Distribusi | Manajemen Label; Persetujuan Sensitif dan Multi Label sebagai anak Manajemen Label; Verifikasi Akun; Manajemen Rilisan; Migrasi & Klaim; Kontrak |
| Royalti & Keuangan | Analitik Royalti; Audit Konsistensi; Manajemen Artis; Impor Royalti; Inject Saldo; Penarikan Dana; Pembayaran; Rekonsiliasi Xendit dan Refund Pembayaran sebagai anak Pembayaran |
| Layanan & Dukungan | Layanan Tambahan; Registrasi WAMI; Tiket Bantuan |
| Tim & Akses | Pengguna Admin; Role & Permission sebagai anak Pengguna Admin; Manajemen Staf; Absensi dan Konfigurasi sebagai anak Manajemen Staf; Performa Tim; Konfigurasi KPI sebagai anak Performa Tim |
| Personal | Performa Saya; Kompensasi Saya; Payroll, Kompensasi Staf, Bonus, Aturan Bonus, Penyesuaian sebagai anak Kompensasi Saya |
| Sistem | Landing Page CMS; Log Aktivitas; Pengaturan UI |

Route tambahan yang harus tetap diperhitungkan meski tidak tercantum sebagai menu utama default:
- /admin/bank-verifications: verifikasi rekening, khusus Super Admin.
- /admin/notifications: notifikasi.
- Rincian label, rilisan, royalti dan tiket melalui route :id.
- /admin/labels/rate-import dialihkan ke /admin/labels; jangan menghidupkan kembali menu impor rate terpisah tanpa alasan.
- /label/... merupakan area pengguna label, terpisah dari area admin; hubungan alurnya perlu ditinjau saat membuka menu sumber, bukan dianggap otomatis tercakup oleh prototype admin.

## Pembedaan dengan prototype dan usulan

| Area | Acuan repo | Keputusan/usulan versi kita |
|---|---|---|
| Navigasi | Tujuh grup navigasi dinamis dalam area admin | Pemisahan mode Platform/Staff dan susunan sidebar prototype adalah rancangan kita |
| Pekerjaan | /admin/work, WorkQueue | Pekerjaan Saya menjadi penyajian lintas sumber; jangan menciptakan catatan pekerjaan ganda |
| Label | Label, KYC, persetujuan sensitif, multi-label, migrasi, kontrak | Paket Flex/Go/Pro/Business; verifikasi reputasi otomatis; emblem; status akses/aktivitas perlu dipetakan ke data yang tersedia |
| Verifikasi | Terdapat KycReviews dan route /admin/kyc | Centang pencapaian/verifikasi otomatis tidak otomatis menggantikan pemeriksaan identitas atau kepemilikan yang sudah ada |
| Royalti | Impor, rincian, analitik, audit, penyesuaian saldo, penarikan | Pemantauan Royalti nonoperasional dan pemisahan liabilitas pada V9 belum boleh dianggap sudah tersedia di repo |
| Panduan | Konfigurasi terkait tersebar dalam modul | Standar & Penanda adalah tambahan prototype V9; perlu sumber aturan dan pemetaan yang jelas |
| UI | Ada Pengaturan UI; konteks navigasi dan preferensi | Editor widget dalam halaman, spacing grid dan stok desain adalah usulan V10; keberadaan Pengaturan UI tidak membuktikan fitur tersebut tersedia |
| Staff | Terdapat absensi, performa, konfigurasi KPI dan kompensasi | Pengecualian Super Admin, tanpa lembur, izin sementara, rating dan aturan versi prototype perlu adu dengan implementasi repo sebelum integrasi |

## Standar pembahasan tiap versi kecil

Sebelum merancang menu, isi kartu pembanding berikut:
1. Nama/identitas menu sumber, route dan izin yang ada.
2. Halaman, endpoint, objek data, status dan tindakan yang benar-benar ditemukan; bedakan kontrak kode dari hasil API live.
3. Alur sekarang: pemicu, aktor, input, tindakan, hasil dan pengecualian.
4. Ide baru pengguna dan perbedaannya dengan alur sekarang.
5. Keputusan: pertahankan, ubah penyajian, ubah prosedur, atau tambahkan kemampuan baru.
6. Dampak pada menu lain, widget, penanda, notifikasi dan izin.
7. Skenario penerimaan dan kegagalan yang bisa dicoba, termasuk bukti bahwa perubahan terkait ikut diperbarui.
8. Celah yang diparkir, tanpa menyatakannya sebagai keputusan final.

Jangan menganggap nama menu yang sama berarti fungsi yang sama. Jangan menghapus suatu pekerjaan hanya karena tidak dipilih menjadi menu utama. Penamaan yang disetujui pengguna disimpan bersama identitas sumbernya.

## Koreksi urutan prioritas sebelumnya

Rencana V10.1 dan seterusnya masih usulan, bukan roadmap final yang sudah diaudit terhadap semua endpoint.

- Fondasi V10.1: koreksi navigasi, pemetaan sumber widget, foto dummy, dan pengaturan widget langsung di halaman sesuai kesepakatan.
- Sebelum memperdalam Rilisan: buka Label beserta hubungan KYC, persetujuan sensitif, multi-label, migrasi/klaim, dan kontrak. Masing-masing dapat memakai versi kecil sendiri.
- Pekerjaan Saya ditelusuri sejak menu sumber pertama, lalu dikembangkan mengikuti alur rilisan/tiket; tidak menunggu semua modul selesai dan tidak menjadi sumber data baru.
- Urutan finansial mengikuti sumber: laporan/impor → rincian dan analitik → audit/penyesuaian → saldo → penarikan/verifikasi rekening → pemantauan nonoperasional. Pembayaran layanan, refund dan rekonsiliasi merupakan alur berbeda yang harus tetap dipetakan.
- Staff dan KPI menunggu kecukupan bukti prosedur; menu yang sudah ada tetap menjadi acuan, bukan dianggap harus dibangun dari nol.

Periksa ulang HEAD sebelum pekerjaan repo berikutnya. Jika berubah, perbarui baseline dan catat selisihnya terlebih dahulu.
