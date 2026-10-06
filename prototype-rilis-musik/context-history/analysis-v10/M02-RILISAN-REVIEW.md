# M02 · Rilisan — panduan pembahasan

Tanggal: 25 September 2026. Status: analisis repo dan usulan penerapan, belum implementasi atau rilis.

## Dasar pemeriksaan

Repo referensi: Ekapoetra/rilismusik, commit 6929bf25a56579d5ac81ed9def38a183665d7863. HEAD GitHub diperiksa melalui API pada 25 September dan cocok dengan salinan lokal; tanggal commit 18 September 2026. Pembacaan kode tidak membuktikan keadaan deployment atau data produksi. Tidak ada pengujian akun produksi, pengiriman rilisan, perubahan data server atau transaksi.

Prototype V10.4 adalah pengalaman visual terakhir. Formulir ringkas prototype belum mewakili kelengkapan empat langkah pada repo. Gunakan repo sebagai inventaris fungsi dan V10.4 beserta koreksi pengguna sebagai dasar UI. Jangan membangun ulang dashboard Admin/Super Admin di ruang Label.

## Rute pembahasan dan navigasi

| Kode | Layar label | Hubungan internal |
|---|---|---|
| M02.1 | Daftar Rilisan | Daftar Manajemen Rilisan; antrean pekerjaan merujuk rilisan yang sama |
| M02.2 | Buat/Edit Rilisan | Metadata, artis, kontributor dan berkas menjadi bahan pemeriksaan |
| M02.3 | Detail dan perbaikan | Admin memberi catatan pada bagian terkait; label memperbaiki versi pengajuan |
| M02.4 | Pengiriman dan tayang | Admin mengirim ke Believe, menyimpan kode, mengecek tautan, mengonfirmasi tayang |

Rute yang sudah ada: /label/releases, /label/releases/upload, /label/releases/:id, /label/releases/:id/edit; internal /admin/releases dan /admin/releases/:id. Hak akses internal tetap diperiksa sesuai peran/izin. Akun Business harus selalu menunjukkan label yang sedang diwakili; pergantian label tidak boleh memindahkan draft/kredit tanpa konteks yang jelas.

Usulan penggantian UI: formulir Buat/Edit menjadi halaman penuh di menu Rilisan, menggantikan popup ringkas Siapkan Rilisan. Alasan: empat tahap, banyak lagu/kontributor, unggahan dan perbaikan memerlukan ruang tetap. Tidak menambah menu sidebar baru. Detail ringkas bisa dibuka dari daftar, tetapi penyuntingan panjang tetap memiliki halaman sendiri. Usulan ini perlu dibahas sebelum implementasi.

## M02.1 — daftar sebagai titik awal

Repo sudah menyediakan pencarian, filter status, filter WAMI, judul/cover/artis, jenis rilisan, tanggal, status, detail dan tindakan draft. Endpoint daftar membatasi hasil 500; belum ada pagination pada pasangan layar/endpoint yang diperiksa.

Usulan tampilan: judul Rilisan dan tombol Buat Rilisan; tab Semua, Draft, Dalam Proses, Perlu Perbaikan, Tayang. Tab adalah kelompok tampilan dari status asli, bukan status baru. Filter tanggal/jenis/status yang tidak tercakup tab tetap tersedia; status Ditolak/Diturunkan tetap dapat ditemukan melalui Semua dan filter, bukan disembunyikan. Label melihat miliknya; Admin melihat cakupan izin; Super Admin melihat cakupan pengelolaan.

Baris memuat cover, judul dan artis; untuk EP/Album tampilkan jumlah lagu; tanggal lengkap; tahap pekerjaan; penanda tenggat hanya jika relevan; panah detail. Status kredit/pembayaran tidak dijadikan tahap pekerjaan. Kembali dari detail mempertahankan tab, filter dan scroll. Jangan menambah kartu ringkasan kosong hanya untuk mengisi halaman.

## M02.2 — inventaris formulir yang ada

Istilah penting: satu pengajuan dapat berisi beberapa lagu. Unit kredit yang disepakati adalah lagu. Nama tahap repo “Lagu & Kredit” berarti kredit kontributor; usulan baru **Lagu & Kontributor** agar tidak tertukar dengan kredit layanan.

| Tahap repo | Data | Kondisi saat ini |
|---|---|---|
| Informasi Rilisan | Judul; jenis Single/EP/Album; genre; subgenre; tahun produksi; tanggal rilis | Wajib saat pengajuan; Single 1, EP 2–6, Album 7–12 lagu |
| Informasi Rilisan | Nama label; penanggung jawab | Diambil dari profil, bukan diminta ulang |
| Informasi Rilisan | C Line / nama pemilik karya; P Line / nama pemilik master | Wajib; penjelasan singkat di indikator informasi perlu diperjelas, jangan menyamakan keduanya |
| Informasi Rilisan | Tautan web/kanal YouTube artis | Opsional; kanal YouTube memiliki validasi khusus di server |
| Artis | Artis utama; artis tamu tingkat rilisan | Utama minimal satu; tamu opsional; pilih artis tersimpan atau isi baru |
| Artis | Nama artis; tautan sosial; Spotify artist URL | Sosial minimal satu untuk artis yang dicantumkan; Spotify opsional jika belum punya profil |
| Lagu & Kredit | Judul tiap lagu; ISRC lama; vokal/instrumental; explicit | Judul wajib, ISRC opsional pada pengajuan; explicit tetap keputusan pengguna |
| Lagu & Kredit | Penulis lirik; komposer; arranger; produser | Repo mewajibkan penulis/komposer; arranger/produser opsional; bisa beberapa nama |
| Lagu & Kredit | Bahasa judul; bahasa lirik; lirik lengkap | Bahasa judul wajib; lirik dan bahasanya bergantung vokal/instrumental |
| Lagu & Kredit | Artis tamu per lagu; detik awal cuplikan | Tamu opsional; cuplikan 0–3600 detik dalam validasi sekarang |
| File & Pemeriksaan | Cover; WAV tiap lagu; pemutar pratinjau | Cover JPG/PNG tepat 3000×3000; WAV 44,1/48 kHz |
| File & Pemeriksaan | Layanan tambahan; estimasi biaya; pernyataan hak distribusi | Repo menampilkan pilihan layanan berbayar untuk PPR; pernyataan wajib sebelum kirim |

Pilihan sosial pada repo: Instagram, TikTok, Facebook, YouTube, X, Website, Other. Syarat sosial artis pada rilisan berbeda dari tautan opsional untuk kredibilitas/verifikasi label. Jangan memindahkan aturan salah satunya ke konteks lain.

### Susunan UI yang diusulkan

1. **Informasi Rilisan:** data utama ringkas. Nama label/penanggung jawab mengambil identitas operasional yang disetujui, tidak mengambil nama akun Google sebagai penanggung jawab. Tanggal dipilih di sini dan ditampilkan kembali pada ringkasan akhir yang memakai sumber data sama.
2. **Artis:** pilih tersimpan atau Tambah Artis dalam konteks formulir. Jangan memaksa keluar ke menu Artis dan kehilangan draft. Artis utama/tamu rilisan dipisahkan dari tamu pada lagu tertentu. Perubahan profil artis tidak diam-diam mengubah snapshot rilisan yang sudah diperiksa.
3. **Lagu & Kontributor:** daftar lagu dengan nomor urut dan panel buka/tutup. Buka satu lagu untuk fokus; ringkasan lagu lain tetap terlihat. Nama kontributor bisa dipakai ulang melalui pilihan eksplisit, bukan disalin ke semua lagu otomatis. Indikator kelengkapan menjelaskan bagian yang kurang.
4. **Berkas & Pengajuan:** cover, WAV dan pratinjau; ringkasan semua metadata dengan tombol kembali ke bagian terkait; pernyataan hak distribusi khusus rilisan; tanggal lengkap dengan penjelasan; layanan Standard/Express/MAX dan kredit.

Semua isian wajib bertanda bintang; aturan unggahan tampil dekat tempat unggah. Pemeriksaan gagal menjelaskan file/kolom yang perlu diperbaiki tanpa menghapus isian benar. Jangan mengubah audio/cover otomatis dengan cara yang mengubah karya.

### Draft dan bagian bawah formulir

- Pengunjung yang sudah login boleh membuat draft sebelum aktivasi atau pembayaran. Draft parsial boleh disimpan; syarat pengajuan tidak boleh menjadi syarat menyimpan draft. Hak data tetap milik akun/label yang tepat.
- Usulan simpan otomatis dengan indikator Tersimpan/Menyimpan/Gagal menyimpan; Simpan Draft tetap di kiri sesuai arahan pengguna. Jangan menampilkan berhasil sebelum penyimpanan berhasil. Perpindahan halaman tidak menghilangkan isian yang belum tersimpan.
- Area akhir: tanggal menonjol di tengah; kredit tersedia ringkas di kiri tombol layanan; layanan default Standard membuka slider kecil saat diklik; Ajukan Rilisan di kanan. Standard/Express netral, MAX memakai warna identitas. Kredit sementara muncul saat slider digerakkan seperti rancangan sebelumnya.
- Pengajuan memeriksa kelengkapan, aktivasi, kontrak, akses akun, sumber kredit dan tanggal. Rekening belum lengkap tidak menghalangi pengiriman rilisan. Kredit/langganan tidak menghapus pembatasan karena masalah akun.
- Jika belum siap, tindakan mengantar ke kebutuhan terkait dan kembali ke draft yang sama. Membeli atau menyelesaikan aktivasi tidak otomatis mengirim draft. Tombol pengajuan memerlukan tindakan pengguna tersendiri.

## M02.3–M02.4 — hubungan tiga akun

| Tahap | Label | Admin sesuai izin | Super Admin |
|---|---|---|---|
| Draft | Mengisi, menyimpan, mengganti berkas | Tidak menjadi antrean pemeriksaan | Tidak perlu persetujuan rutin |
| Diajukan | Melihat ringkasan pengajuan dan alokasi kredit | Menerima pekerjaan yang merujuk ID rilisan sama | Memantau beban/pengecualian |
| Pemeriksaan | Melihat progres | Memeriksa metadata, artis, berkas dan tanggal | Menangani pengecualian sensitif sesuai izin |
| Perlu perbaikan | Membuka bagian yang ditandai, memperbaiki, mengirim ulang | Melihat versi baru dan perubahan yang perlu diperiksa | Memantau sengketa atau koreksi khusus |
| Siap dikirim | Melihat tahap | Menyalin metadata dan mengunduh berkas; memasukkan manual ke Believe | Tidak perlu menjadi persetujuan kedua semua rilisan |
| Dikirim ke Believe | Melihat tanggal dan perkembangan | Mencatat pengiriman, menyimpan UPC/ISRC bila tersedia | Menangani koreksi status/kompensasi khusus dengan alasan dan jejak |
| Pemeriksaan tayang | Melihat hasil dan tindak lanjut | Mengecek tautan yang diberikan Believe: Konfirmasi Tayang atau Rilisan tidak ditemukan | Memantau masalah/tenggat |
| Tayang | Membuka tautan dan riwayat | Memfinalkan berdasarkan hasil pemeriksaan | Memantau hasil dan koreksi terkontrol |

Pemeriksaan petugas mencakup konfirmasi bahwa seluruh tautan yang tersedia telah dicek. Rilisan tidak ditemukan tetap dalam tindak lanjut Believe, bukan otomatis ditolak atau tayang. Tidak menambah opsi “Ditemukan, tapi bermasalah” yang telah dihapus pengguna. Identitas sensitif, rekening, saldo lintas label dan kompensasi tidak otomatis terbuka hanya karena petugas menangani rilisan.

Pengiriman manual ke Believe tidak dapat dibandingkan otomatis tanpa data dari Believe. Tampilkan tanggal permintaan dengan hari/bulan lengkap dan atensi kuat. Jika petugas mencatat tanggal konfirmasi/koreksi, simpan terpisah dari permintaan awal dan tampilkan perbedaannya. Kesalahan internal tidak boleh diubah menjadi kewajiban label mengajukan ulang atau membayar ulang.

## Kredit, layanan dan status: aturan penghubung

- Rancangan disepakati: kredit dialokasikan saat pengajuan, baru terpakai final ketika tayang dikonfirmasi. Tidak memotong dua kali pada klik ulang, pengiriman ulang revisi, atau konfirmasi tayang ulang.
- Kredit harian 5/hari merupakan rancangan baru, berbeda dari quota 7 pengajuan/hari pada repo. EP/Album memerlukan alokasi berdasarkan jumlah lagu. Kekurangan kredit harian dapat melibatkan kredit tambahan; urutan sumber dan persetujuan penggunaan kredit berbayar harus jelas sebelum pengajuan, tidak diam-diam.
- Aturan pengembalian yang sudah dibahas tetap dibedakan menurut sumber: harian ditolak hari sama kembali hari itu; beda hari menjadi kredit sementara 48 jam; pembelian kembali ke sumber kredit permanen. Kelanjutan revisi rilisan yang sama jangan sekaligus mengembalikan kredit dan mempertahankan hak alokasi lama.
- Standard 7 hari kerja, Express 5 dan MAX 3 mengikuti pembahasan; Jumat MAX sebelum 12.00 dengan target Minggu adalah pengecualian eksplisit. Perlu satu tabel kalender layanan agar angka 3 tidak diinterpretasikan berbeda oleh formulir/petugas. Tarif Express/MAX belum menjadi kebijakan harga final hanya karena memakai angka contoh.
- Tanggal jauh ke depan valid. Jangan menandai terlambat hanya karena lewat 7 hari dari pengajuan bila label memang memilih tanggal bulan depan.
- Simpan sumber kredit, jumlah, layanan dan versi aturan saat pengajuan. Masa langganan berakhir selama rilisan diproses tidak boleh mengganti tagihan secara diam-diam. Perubahan jumlah lagu/layanan saat revisi perlu hitung selisih dan persetujuan yang terlihat.
- Nama tahap pekerjaan, urgensi/tenggat, pembayaran dan kredit adalah makna berbeda. Guide indikator menjadi sumber bersama; badge “Prioritas”/“Lewat periode” tidak dibuat sendiri di komponen lama.

## Celah kode yang harus ditangani sebelum alur baru dianggap selesai

1. **Akses draft:** deps.py masih memaksa pemeriksaan KYC pada endpoint rilisan; create draft juga menolak kontrak kedaluwarsa. Ini bertentangan dengan eksplorasi draft untuk calon member. Perlu pisahkan izin draft dari izin pengajuan tanpa membuka akses data label lain.
2. **Draft belum benar-benar awal:** UploadRelease menyimpan setelah validasi tahap tiga; server memvalidasi tanggal sejak create draft. Belum ditemukan autosave pada formulir ini.
3. **Model lama:** quota 7 pengajuan per hari, tanggal 7 hari kalender, pembayaran PPR setelah pemeriksaan; belum mengikuti kredit per lagu serta layanan baru.
4. **Langganan saat proses:** keputusan approve/deliver menggunakan hak langganan SAAT INI. Perlu hak pengajuan tersimpan agar kedaluwarsa tidak mengubah biaya rilisan yang telah dialokasikan.
5. **Tayang:** individual sudah punya save_identifiers terpisah; mark_live masih hanya memeriksa kode. Modal tayang massal juga harus mengikuti pemeriksaan bukti, bukan melewati aturan baru.
6. **Koreksi status:** cabang override_status tidak terlihat memeriksa Super Admin secara khusus; gate go_live hanya untuk action mark_live. Tinjau dan tutup jalur alternatif pada server sebelum memakai transaksi kredit. Ini temuan pembacaan kode, bukan eksploitasi/pengujian produksi.
7. **Tanggal:** deliver/mark_live/reschedule dapat menimpa release_date. Pertahankan permintaan awal, koreksi, pelaku dan waktu.
8. **Instrumental:** repo masih mewajibkan penulis lirik meski instrumental. Usulan: komposer tetap wajib, penulis lirik tidak relevan untuk instrumental. Perlu persetujuan formulir, bukan mengisi nama palsu agar lolos.
9. **Data dan berkas:** nama penanggung jawab memprioritaskan user.name; revisi harus menunjuk snapshot yang jelas. Cover server melewati pemeriksaan dimensi bila Pillow tidak tersedia; validasi wajib tidak boleh hanya mengandalkan browser.
10. **Pertumbuhan katalog:** batas daftar 500 tanpa pagination perlu ditangani agar rilisan lama tidak terlihat hilang. Default array platform dalam model bukan bukti bahwa UI sudah menyediakan pemilihan DSP.

Tidak ada penolakan final pada aktivasi bukan otomatis aturan yang sama untuk rilisan. Repo memiliki Ditolak dan dapat diedit lagi; kita perlu membedakan revisi yang melanjutkan pengajuan dengan penolakan yang melepas alokasi sebelum menerapkan pengembalian kredit. Kebijakan ini dibahas di M02.3.

## Penggunaan DNA bersama dan batas cakupan

Gunakan komponen bersama untuk tombol, switch/slider, tab, badge, atensi, viewer dan dialog. Animasi per kelompok independen, arah mengikuti gerakan aktual, tidak berulang saat diam dan tidak mengubah scroll. Warna status tetap semantik; warna identitas bukan warna semua indikator. Ikon/tulisan dalam blok identitas menjaga kontras. Form memiliki hierarki, ruang rapat yang cukup, informasi bantuan kontekstual dan layout responsif.

Penggantian: halaman formulir menggantikan popup Siapkan Rilisan; Lagu & Kontributor menggantikan nama yang ambigu; pemeriksaan tayang menggantikan tindakan yang seolah cukup dengan kode. Penggabungan: antrean kerja dan Manajemen Rilisan memakai data/detail yang sama. Tidak menambah sidebar untuk tahapan, kredit, atau pengecekan tayang.

Ide belum final: pengubahan profil artis tanpa meninggalkan draft; aturan instrumental; hak cover/remix dan berkas izinnya (model/endpoint ada sebagian, wizard belum jelas); kredit selisih revisi; kebijakan penolakan rilisan. Jangan menyatakan sudah disetujui hanya karena tercatat di sini.

Urutan uji saat nanti membangun: calon member menyimpan draft parsial; Single dan EP/Album; artis tamu tiap lagu; instrumental; berkas tidak sesuai; kurang kredit; aktivasi/pembayaran lalu kembali draft; revisi tanpa biaya ganda; MAX Jumat; paket habis saat proses; salah tanggal internal; simpan kode tanpa tayang; tidak ditemukan lalu follow-up; konfirmasi tayang sekali; hak Admin vs Super Admin; isolasi label Business; kembali daftar mempertahankan scroll. Uji ini belum dijalankan pada pekerjaan analisis ini.

## Sumber kode utama

- frontend/src/App.js — rute label dan internal.
- frontend/src/pages/label/Releases.jsx — daftar dan filter.
- frontend/src/pages/label/UploadRelease.jsx; release-form/ReleaseInfoStep.jsx, ArtistCreditsStep.jsx, TracksStep.jsx, AssetsReviewStep.jsx, releaseFormState.js — wizard dan validasi.
- frontend/src/pages/label/ReleaseDetail.jsx — detail, revisi, pembayaran dan layanan tambahan.
- frontend/src/pages/admin/Releases.jsx, ReleaseDetail.jsx; komponen AdminReleaseWorkflow, GoLiveModal, MassGoLiveModal — pekerjaan petugas dan tayang.
- backend/routes/releases.py, release_workflow_service.py, deps.py, admin_permission_service.py, work_service.py; backend/models.py — akses, validasi, workflow dan model.
- analysis-v10/RELEASE-DATE-INCIDENT.md — kasus tanggal dan perlindungan alokasi.

Sumber di atas bersifat referensi, tidak diubah. Celah M01 diparkir di RANCANGAN-VERSI-BERIKUTNYA.md. Pembahasan praktis dimulai dari M02.1 Daftar Rilisan, lalu M02.2 formulir; tidak perlu memutuskan seluruh celah sekaligus.
