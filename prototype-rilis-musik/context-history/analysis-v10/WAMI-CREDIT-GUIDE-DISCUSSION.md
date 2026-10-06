# Pembahasan WAMI dan panduan kredit — 28 September 2026

Status: pembahasan, bukan izin implementasi/rilis. Pengguna menyetujui struktur pengajuan WAMI dan meminta panduan penggunaan kredit untuk semua akun serta konfigurasi khusus. Belum dapat menghubungi staf; gunakan repo sebagai baseline sementara dan ingatkan pertanyaan saat pembahasan WAMI dilanjutkan atau sebelum persyaratan/rilis WAMI difinalkan. Tidak ada jadwal pengingat berbasis waktu yang diminta.

## Temuan yang sudah diperiksa

- Prototype V10.9: WAMI masih outline melalui v4.js; katalog v106.js mempunyai filter, bukan alur pendaftaran terhubung.
- Repo aplikasi lama (read-only): backend/routes/wami.py, backend/routes/payments.py, backend/models.py, frontend/src/pages/label/Wami.jsx sudah mempunyai daftar/pengajuan per track, pembayaran, update petugas, referensi WAMI, notifikasi, dan impor pencocokan XLSX.
- CreateWamiOrderIn hanya membutuhkan track_id; metadata berasal dari katalog. TrackIn mencakup judul, artis, composer, lyricist, performer dan ISRC (sebagian opsional pada model lama). Tidak ditemukan formulir khusus yang menetapkan dokumen wajib WAMI lengkap. Jangan menyebut data model ini persyaratan resmi WAMI.
- Baseline lama hanya menerima rilisan live, memeriksa kepemilikan, mencegah order aktif ganda, membuat unpaid untuk layanan berbayar dan pending jika benefit free_wami tersedia. Benefit ditentukan resolver akun termasuk multi-label, bukan semata nama paket.
- Impor WAMI mengenal title, ISWC, contributors, original publishers, performers, BMAT ID, internal ID. Itu data hasil/impor, bukan seluruhnya kolom wajib label saat mengajukan.
- Status lama rejected/cancelled tidak otomatis diadopsi; dialog terbaru meminta jalur perbaikan. Koreksi/kebutuhan WAMI tidak otomatis mengubah metadata distribusi.
- Hindari klaim bahwa seluruh repo belum memiliki WAMI; yang belum adalah alur pada prototype terbaru.

## Baseline WAMI sementara yang diusulkan

Pilih lagu dari katalog tayang; untuk EP/Album tayang sebagian perlu mendukung eligibilitas per lagu yang sudah dikonfirmasi tayang, jangan membatasi hanya status keseluruhan rilisan. Periksa kepemilikan/cakupan master dan pengajuan yang sudah ada. Tampilkan judul, artis, asal rilisan, ISRC, pencipta/penulis lirik/performer bila tersedia. Jangan mewajibkan identitas/dokumen baru tanpa dasar. Persyaratan dokumen, pembagian hak dan kelengkapan lain belum final.

## Pertanyaan staf yang wajib dibawa kembali

1. Contoh formulir kosong atau daftar kolom dan dokumen yang benar-benar dibutuhkan untuk satu lagu.
2. Data apa dari katalog yang dapat langsung dipakai, apa yang sering kurang, dan siapa menyediakan/menandatangani dokumen.
3. Bagaimana hasil penerimaan/perbaikan diterima; referensi apa yang dicatat sebagai bukti penyelesaian.
4. Apakah syarat lagu harus sudah tayang memang kebutuhan operasi saat ini, termasuk EP/Album tayang sebagian dan lagu lama.

## Panduan dan konfigurasi kredit (usulan untuk dinilai pengguna)

- Semua akun: Standar & Penanda → Penggunaan Kredit, hanya baca. Label hanya melihat panduan yang relevan baginya, tanpa membuka standar pekerjaan internal atau data akun lain. Tautan kontekstual dari saldo/beli kredit dan pengajuan rilisan menuju panduan yang sama.
- Super Admin: perluas menu Paket & Kredit yang sudah ada dengan tab Aturan Penggunaan. Jangan membuat sidebar konfigurasi kredit duplikat. Admin tidak mengubah kebijakan atau saldo melalui panduan.
- Panduan menjelaskan satuan, sumber kredit, prioritas pemakaian, biaya layanan, alokasi/terpakai/pengembalian, kedaluwarsa, bonus dan contoh EP/Album tayang sebagian. Saldo tersedia dibedakan dari alokasi.
- Satu sumber aturan untuk kalkulasi, ringkasan sebelum submit, dan isi panduan; jangan sekadar teks petunjuk terpisah dari mesin perhitungan.
- Konfigurasi draft → preview dampak dan panduan → terbitkan versi bertanggal. Pengajuan berjalan mempertahankan aturan saat diterima; jangan mengubah kredit permanen menjadi kedaluwarsa atau menilai ulang pengajuan berjalan tanpa kebijakan migrasi yang dibahas. Sertakan riwayat pelaku/perubahan.
- Baseline prototype, bukan penetapan harga baru: Standard 1 / Express 2 / MAX 3 kredit per lagu (v105-model.js); paket memenuhi syarat mendapat 5 kredit harian dengan pergantian hari WIB (v10-model.js); kredit pembelian tidak kedaluwarsa; dialokasikan pada pengajuan dan diselesaikan per lagu ketika konfirmasi tayang; sumber paling cepat kedaluwarsa didahulukan pada Flow105.
- Pengembalian pada Flow105: sumber yang masih berlaku kembali ke lot asal; kredit harian kedaluwarsa kembali sebagai sementara 48 jam; sumber sementara yang kedaluwarsa dikembalikan terbatas sisa masa saat dialokasikan, maksimal 48 jam. Detail harus ditulis sesuai jalur aktif, bukan disamaratakan menjadi semua pengembalian mendapat 48 jam baru. Wajib audit kesesuaian kebijakan saat implementasi.
- Harga kredit dan penawaran sudah dapat diatur melalui v104-commerce.js, tetapi jumlah harian, biaya Standard/Express/MAX dan pengembalian masih tertanam pada model. Ini celah penghubung konfigurasi yang harus diselesaikan jika fitur disetujui.
- WAMI belum memakai kredit di repo lama (rupiah atau benefit paket). Jangan otomatis mengonversi biaya WAMI menjadi kredit karena penambahan menu panduan.

Tidak ada perubahan kode, harga, saldo atau rilis pada pembahasan ini.

## Keputusan lanjutan yang disetujui pengguna — 28 September 2026

Pengguna menyetujui alur petugas dan aturan pengingat berikut. Ini persetujuan rancangan, belum perintah eksekusi atau rilis.

### Antrean dan penanganan WAMI

- Admin dan Super Admin memakai halaman pekerjaan yang sama, dengan hak konfigurasi harga/benefit/kebijakan khusus Super Admin.
- Tab: Semua, Antrean, Penanganan Saya, Menunggu WAMI, Selesai. Perlu perbaikan dan Menunggu pembayaran tersedia sebagai filter. Pengajuan belum dibayar tidak masuk antrean kerja.
- Satu baris per lagu: cover/judul/artis, label, tanggal pengajuan, perkembangan, petugas, detail panel kanan. Detail memuat data pengajuan, proses pendaftaran, riwayat; tombol salin untuk data kerja. Jangan menampilkan rekening/KTP/dokumen lain yang tidak dibutuhkan.
- Tindakan mengikuti tahap: Mulai pemeriksaan; Minta perbaikan; Lanjutkan pendaftaran; Tandai pendaftaran dikirim; Tandai dokumen dikirim. Setelah dua langkah pengiriman lengkap, otomatis Menunggu WAMI.
- Catat respons WAMI: Diterima (referensi bila tersedia, catat hasil, Selesai) atau Perlu perbaikan (jelaskan bagian dan penanggung jawab Label/Petugas). Catat tindak lanjut tidak menandai selesai.
- Koreksi pencatatan pengiriman memerlukan alasan dan riwayat tetap tersimpan; tidak otomatis menyuruh pengiriman ulang.
- Perbaikan melanjutkan pengajuan yang sama, menyimpan pembayaran dan riwayat; tidak menagih ulang otomatis. Benefit paket dikunci ketika pengajuan sah diterima, tidak berubah menjadi berbayar karena paket kemudian berakhir.

### Pengingat WAMI

- Siap tetapi belum ditangani: pengingat setelah 2 jam kerja; pada 4 jam kerja muncul atensi Admin dan Super Admin untuk penugasan.
- Sedang ditangani tanpa perkembangan: pengingat setelah 2 jam kerja; pada 4 jam kerja petugas perlu melanjutkan atau mencatat kendala.
- Perbaikan label: pengingat 4 jam lalu 24 jam; setelah 48 jam tandai Perbaikan tertunda dan buat kebutuhan tindak lanjut petugas. Pengajuan tetap dapat dilanjutkan, tidak batal dan tidak ditagih ulang otomatis.
- Menunggu WAMI: pemeriksaan/tindak lanjut internal setelah 2 hari kerja sejak pengiriman lengkap. Ini bukan SLA atau janji waktu respons WAMI. Setelah tindak lanjut, simpan hasil komunikasi dan tanggal pemeriksaan berikutnya; estimasi dari WAMI boleh menjadi acuan tanggal.
- Jam kerja mengacu konfigurasi operasional, bukan menghitung malam/akhir pekan sebagai keterlambatan internal. Jadwal kerja aktual perlu dibaca dari konfigurasi yang berlaku ketika implementasi.
- Membuka halaman tidak mengulang waktu. Perubahan nyata dicatat; catatan kendala tidak menyelesaikan pekerjaan atau menghapus riwayat keterlambatan.
- Notifikasi tidak berulang untuk kondisi/tingkat perhatian yang sama; atensi tetap terlihat sampai ditangani. Tindakan selesai oleh satu petugas harus menghentikan pengingat yang sudah tidak relevan.
- Tempat konfigurasi: Sistem → Prosedur & Pengingat → WAMI. Terpisah dari panduan Penggunaan Kredit (Standar & Penanda) dan konfigurasi kredit (Paket & Kredit).

### Konfigurasi kredit

Simpan menyimpan rancangan aturan; Terapkan perubahan menampilkan ringkasan dampak dan waktu berlaku. Panduan dan kalkulasi berasal dari aturan yang sama. Tidak mengubah pengajuan berjalan secara surut.

### Tetap menunggu verifikasi staf

Persyaratan kolom/dokumen WAMI, penggunaan ulang metadata, bukti penerimaan, dan syarat lagu tayang belum dikonfirmasi. Dasar repo bersifat sementara, bukan pernyataan persyaratan resmi WAMI. Ingatkan kembali sebelum finalisasi. Jangan menganggap persetujuan alur/pengingat ini sebagai konfirmasi persyaratan dokumen atau izin merilis.

## Implementasi V11.0 — 29 September 2026

Pengguna telah mengizinkan rilis. Alur yang disepakati dan panduan/konfigurasi kredit tersedia dalam prototype-v11.0; lihat README-V11.0.md dan SCOPE-V11.0.md. Empat pertanyaan staf di atas tetap belum terjawab dan wajib dibawa kembali sebelum finalisasi. Rilis prototype bukan penetapan persyaratan resmi WAMI.
