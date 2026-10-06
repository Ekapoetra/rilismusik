# Rancangan setelah V10.3 — pembahasan, belum implementasi

Catatan 24 September 2026. Tidak mengubah V10.3 atau menandai versi berikutnya selesai. Dua puluh catatan visual/UX pengguna setelah V10.3 tetap menjadi cakupan pembahasan; catatan berikut memperjelasnya.

## Ketentuan dari pengguna

- Rilis prototipe WAJIB meminta izin pengguna terlebih dahulu. Mengerjakan dan menguji berkas kerja tidak berarti izin membangun/membagikan HTML standalone, ZIP, atau merilis versi. Siapkan perubahan dan hasil pemeriksaan dahulu; jangan merilis otomatis.
- Revisi kerja berikutnya: banner perubahan identitas ringkas dengan warna identitas dan aset putih, pulse gradasi halus; rincian perubahan dan persetujuan petugas memakai hierarki bersama; rekening penerima ditampilkan sebagai kartu bergaya kartu bank. Belum dirilis sampai pengguna mengizinkan.

- Editor tata letak hanya dimiliki Super Admin. Tombol melayang hanya penempatan sementara.
- Super Admin dapat beralih pratinjau Super Admin, Admin, dan Label untuk menata tampilan masing-masing.
- Tata letak yang disimpan berlaku untuk seluruh pengguna pada peran tujuan; mereka menerima perubahan setelah memuat ulang halaman. Ini bukan preferensi pribadi.
- Manajemen Label membutuhkan filter. Pembahasan batas khusus Admin ditunda atas instruksi pengguna; tidak menjadi pertanyaan terbuka yang menghambat versi ini. Batas kewenangan yang sudah ada tetap berlaku.
- Pencapaian diusulkan pengguna menjadi lebih banyak tingkat dengan nominal lebih rendah, termasuk sublevel I/II/III, dan hadiah kredit tambahan pada setiap tingkat.
- Label yang memperoleh pencapaian menerima ucapan selamat melalui popup dan hadiah kredit. Super Admin mendapat pemberitahuan, berita pada Insight khusus Super Admin, dan daftar kenaikan tingkat beserta waktu, royalti, hadiah, dan saldo kredit.
- Negara, provinsi, kabupaten/kota, kecamatan dan kode pos menjadi kolom langsung pada formulir Identitas Label yang sama, berdampingan dengan data identitas/alamat. TIDAK membuat tab, submenu, langkah atau formulir terpisah bernama Lokasi Operasional. Kolom ini termasuk syarat aktivasi. Hindari dua kolom kode pos dengan sumber berbeda. Penerapan syarat baru bagi label lama menunggu kebijakan transisi menjelang final.
- Bronze dimulai dari Rp1 juta; pengguna meminta kelipatannya. Ambang Silver sampai Diamond pada usulan sebelumnya sudah diterima. Hadiah Diamond diminta 50 kredit; turunan hadiah sampai Bronze diminta dirancang ulang.
- Semua label yang berhak mendapat hadiah, termasuk label bermasalah; tidak menghapus pembatasan akses yang berlaku. KOREKSI TERBARU: pemberian kumulatif seluruh hadiah historis Gold I–Diamond III belum disetujui karena pengguna mengkhawatirkan lonjakan kredit. Cari jalan tengah sebelum penerbitan hadiah historis; usulan berikut belum keputusan final.
- Pengguna mengusulkan fitur khusus pemberian bonus kepada label tertentu: pesan, jumlah, kredit sementara/permanen, popup yang HARUS DIKLAIM, batas waktu klaim, aktivasi kredit setelah klaim, notifikasi klaim ke Super Admin serta riwayat yang dapat ditelusuri.
- Website ini SUDAH BERJALAN dengan ratusan label yang bekerja sama bertahun-tahun. Menjelang final wajib mengingatkan dan mengajak pengguna mengevaluasi migrasi data serta kebijakan transisi yang seimbang bagi label dan Rilis Musik. Jangan memperlakukan semua akun sebagai pendaftar baru.
- Seluruh switch memakai satu perilaku animasi bersama. Jika ingin mengubah gaya/gerak dasarnya, usulkan dan tanyakan kepada pengguna terlebih dahulu; penggunaan ulang komponen yang sudah disetujui tidak memerlukan pertanyaan berulang.
- Setiap penemuan fitur baru harus disertai usulan apakah perlu memperbaiki menu lama, mengganti, atau menggabungkan fungsi. Jangan otomatis menambah menu.
- Saat banyak pembaruan, bahas celah yang perlu diselesaikan atau dibawa ke versi berikutnya. Simpan fitur dan kebijakan belum final serta usulan pengembangan ide.

## Usulan untuk dibahas — belum disetujui

### Editor bersama

Target konfigurasi: peran + halaman + ukuran layar. Tampilkan target dengan jelas; pratinjau peran tidak memberikan akses transaksi/identitas pengguna nyata. Sediakan versi tata letak, urungkan/batal, kembalikan versi, serta simpan dan terapkan. Pengguna lain tetap memakai versi lama sampai reload; jangan merender ulang formulir aktif secara paksa. Produksi memerlukan konfigurasi tersimpan di server; penyimpanan lokal V10.3 belum bisa menyebarkan perubahan ke pengguna lain.

### Tangga pencapaian dan hadiah awal untuk simulasi

Dasar: akumulasi royalti yang benar-benar telah dibayarkan kepada label. Bukan saldo masuk, tagihan menunggu, top-up kredit, atau penjumlahan ulang royalti anak label di master.

| Emblem | I | II | III | Hadiah per sublevel |
|---|---:|---:|---:|---:|
| Bronze | Rp1 juta | Rp2 juta | Rp4 juta | 2 kredit |
| Silver | Rp5 juta | Rp10 juta | Rp20 juta | 5 kredit |
| Gold | Rp35 juta | Rp50 juta | Rp75 juta | 10 kredit |
| Platinum | Rp100 juta | Rp150 juta | Rp250 juta | 25 kredit |
| Diamond | Rp500 juta | Rp750 juta | Rp1 miliar | 50 kredit |

Total jika seluruh 15 sublevel diberi hadiah: 276 kredit. Bronze II/III mengikuti usulan kelipatan dua. Hadiah ditafsirkan PER SUBLEVEL sebagaimana format pembahasan sebelumnya: Diamond I, II, III masing-masing 50 kredit (150 kredit pada keluarga Diamond). Turunan hadiah Bronze–Platinum dan kelipatan Bronze II/III masih usulan asisten; jangan mencatatnya sebagai persetujuan pengguna. Ambang Silver–Diamond sudah disetujui, Bronze I dan nominal hadiah Diamond berasal dari pengguna. Belum mengubah standar di kode V10.3.

Hadiah memiliki sumber tersendiri dalam kredit tambahan, tidak kedaluwarsa, bukan kredit harian dan tidak dapat dicairkan. Satu tingkat hanya memberi hadiah sekali per label. Satu pembayaran yang melewati beberapa tingkat menghasilkan satu rangkuman popup dan total hadiah dari tingkat yang belum diberi hadiah. Rilisan gagal mengembalikan kredit hadiah ke sumber semula tanpa mencetak hadiah baru.

Popup tidak memotong pengisian formulir dan tidak muncul berulang setelah ditutup. Penyerahan hadiah tidak bergantung pada label membuka popup. Pencapaian, transaksi hadiah dan berita menggunakan satu peristiwa dengan identitas unik untuk mencegah duplikasi.

### Penempatan menu dan berita

- Standar & Penanda: aturan pencapaian, ambang, arti emblem dan tautan konfigurasi hadiah.
- Paket & Kredit: sumber pengaturan hadiah/jenis kredit, harga dan penawaran; hindari dua konfigurasi hadiah yang saling berbeda.
- Manajemen Label: tab Pencapaian berisi riwayat/daftar kenaikan tingkat, dengan filter.
- Insight Super Admin: berita pencapaian yang bersumber dari peristiwa nyata dan mengarah ke daftar tersebut. Pemberitahuan mendesak tetap mendapat tempat tersendiri.
- Ringkasan label: emblem tertinggi beserta sublevel; detail berisi perjalanan pencapaian dan target berikutnya.

## Kebijakan belum final dan celah yang disimpan

1. Pelaksanaan hadiah historis Gold I–Diamond III dibuka kembali atas koreksi pengguna: jangan menerbitkan seluruh hadiah kumulatif. Pertimbangkan usulan penghargaan transisi satu kali menurut emblem tertinggi di bawah. Label bermasalah tetap ikut sesuai haknya; status masalah bukan alasan meniadakan hadiah. Verifikasi data historis dan keputusan transisi harus selesai sebelum penerbitan nyata.
2. Koreksi/pembalikan pembayaran setelah kredit hadiah terpakai masih perlu kebijakan. Jangan otomatis menciptakan saldo negatif atau hadiah ganda. Label bermasalah tetap menerima hadiah yang sah; kredit tercatat tidak otomatis mencabut pembatasan pengiriman atau akses.
3. Identitas label ketika akun bergabung, berpindah master, berganti nama atau dipisah: riwayat hadiah tidak boleh diulang.
4. Dampak kapasitas operasional dan biaya layanan dari kredit gratis; angka hadiah belum merupakan keputusan harga final.
5. Lingkup filter Admin diparkir untuk versi setelah ini; jangan menanyakan ulang sekarang.
6. Kelipatan Bronze II/III, turunan hadiah Bronze–Platinum, interpretasi 50 kredit per sublevel Diamond, diskon EP/Album, harga bulanan dan aturan pergantian paket/prorata belum seluruhnya final. Bedakan angka yang sudah ditentukan pengguna dari usulan lanjutan.
7. Peta memakai domisili operasional label, bukan menampilkan alamat pribadi lengkap atau lokasi dari tebakan. Data belum lengkap harus memiliki kelompok sendiri.

## Pengembangan ide berikutnya

Usulkan satu sumber peristiwa untuk pemberitahuan, berita Insight dan riwayat. Mulai dari pencapaian label, lalu evaluasi kebutuhan berita lain (rilisan pertama tayang, sebaran wilayah baru) sebelum memperluasnya. Jangan menambah skor popularitas atau verifikasi otomatis hanya karena kredit/paket dibeli.

### Usulan jalan tengah hadiah historis — diganti usulan lebih rendah, belum disetujui

- Emblem beserta sublevel mengikuti seluruh akumulasi royalti historis yang sah.
- Pengguna meminta penurunan lagi; usulan total 31/46/71 tidak diterima. Usulan baru: SATU hadiah transisi berdasarkan keluarga emblem tertinggi, Bronze 1, Silver 2, Gold 5, Platinum 10, Diamond 15 kredit. Angka ini TOTAL, tidak ditambah hadiah historis Bronze/Silver, tidak dijumlahkan antar-sublevel atau keluarga. Belum disetujui pengguna.
- Hadiah transisi dipisahkan dari hadiah kenaikan baru setelah penerapan; tidak mengubah usulan hadiah reguler Diamond 50 per tingkat. Kenaikan tingkat baru mengikuti aturan reguler yang akhirnya ditetapkan.
- Simpan posisi awal dan catatan penyelesaian transisi per label. Tingkat masa lalu ditandai pencapaian historis, bukan hadiah tertunggak. Kenaikan tingkat setelah sistem berlaku mendapat hadiah normal sekali per tingkat. Pergantian nama/master/reload tidak mengulang hadiah transisi.
- Super Admin melihat rekap jumlah penerima dan total kredit sebelum penerbitan; angka total aktual belum diketahui tanpa data historis. Menjadwalkan batch hanya mengatur laju penerbitan, bukan mengurangi total hak yang sudah disepakati.

### Bonus Kredit — fitur diminta, detail berikut usulan

Tempat khusus di area Paket & Kredit, hanya Super Admin. Pilih satu label, judul dan pesan ucapan, jumlah kredit, jenis Kredit Flex atau Kredit Sementara. KOREKSI PENGGUNA: batas klaim tetap 2 hari (48 jam) sejak dikirim. Flex tidak kedaluwarsa setelah diklaim; Kredit Sementara memakai masa berlaku sementara yang sudah dibahas, 2 hari (48 jam) sejak klaim. Tidak menawarkan pengaturan durasi bebas pada versi ini. Konfigurasi yang dikirim menjadi snapshot; perubahan tidak diam-diam mengubah tawaran lama.

Pengguna meminta tombol Pratinjau popup sebelum mengirim bonus. Gunakan komponen popup penerima yang sama (nama label, pesan, jumlah, jenis, tenggat klaim, lama penggunaan), dengan penanda pratinjau pada alat Super Admin. Pratinjau tidak mengirim notifikasi, mengaktifkan timer, mengklaim, menerbitkan kredit atau menulis transaksi nyata. Tenggat sebenarnya dimulai ketika bonus dikirim.

Istilah tampilan Kredit Pengembalian diganti menjadi Kredit Sementara. Jenis kredit menjelaskan masa berlaku; sumber tetap dicatat terpisah, misalnya pengembalian rilisan atau Bonus Rilis Musik. JANGAN tampilkan istilah bonus Super Admin kepada label. Pemberi/petugas dan perannya hanya di audit internal. Penggantian nama tidak mengubah saldo, masa berlaku atau asal kredit lama. Untuk pengembalian, waktu berlaku dimulai saat diterbitkan; untuk Bonus Kredit, saat diklaim.

Hadiah level otomatis dan Bonus Kredit manual dibedakan sumber serta cara pemberiannya. Bonus manual belum masuk saldo sebelum diklaim. Status tawaran: Menunggu klaim, Diklaim, Kedaluwarsa, atau Dibatalkan (bila belum diklaim). Batas klaim dan batas penggunaan kredit adalah dua waktu terpisah, selalu ditampilkan jelas dalam WIB. Kredit permanen tidak memiliki batas penggunaan, tetapi tawarannya tetap dapat kedaluwarsa sebelum klaim.

Klaim hanya oleh akun label penerima, satu kali secara atomik, sebelum batas waktu menurut server; tidak menghasilkan dua transaksi saat klik berulang, reload, atau akses beberapa perangkat. Klaim dan pembatalan bersamaan hanya boleh memiliki satu hasil. Setelah klaim, Super Admin mendapat notifikasi dan riwayat mencatat pemberi, penerima, pesan, jumlah, jenis, waktu kirim/klaim, batas waktu serta transaksi kredit terkait. Status klaim berbeda dari status saldo sudah digunakan/kedaluwarsa.

Popup memakai komponen perayaan yang sama dengan hadiah level, dengan CTA Klaim bonus. Menutup popup tidak otomatis mengklaim atau menghapus tawaran; tawaran tersedia di notifikasi/daftar bonus sampai habis waktu.

Usulan pengamanan: kredit sementara yang dialokasikan ke rilisan sebelum habis waktu tetap mengikuti proses hingga konfirmasi Tayang. Kedaluwarsa berlaku pada saldo yang belum dialokasikan. Aturan pengembalian setelah rilisan gagal harus mengikuti asal kredit dan kebijakan pengembalian yang disepakati, bukan diperbarui diam-diam saat mengganti nama; celah perpanjangan berulang dan kredit kembali setelah tenggat perlu dituntaskan sebelum implementasi. Kredit Flex tetap kembali bila rilisan gagal sesuai keputusan pengguna.

### Tab Kredit pada Label Monitor — diminta pengguna

Tambahkan tab Kredit pada tabel/menu Label Monitor yang sudah ada, tanpa membuat direktori label duplikat. Tampilkan saldo tersedia terkini per label: total tersedia, rincian harian/Flex/sementara bila relevan, dan waktu kedaluwarsa terdekat untuk sementara. Jangan tampilkan alokasi; angka tersedia mengecualikan kredit dialokasikan, terpakai, kedaluwarsa, serta bonus belum diklaim. Jangan menjumlahkan saldo master dan anak dua kali. Pembaruan harus mengikuti transaksi dan waktu kedaluwarsa server; angka tidak boleh berasal dari snapshot saat halaman pertama dibuka saja. Lingkup akses tetap mengikuti kewenangan menu yang ada; usulan baru tidak membuka data finansial kepada Admin.

### Penyesuaian Data Label — menu khusus Super Admin yang diminta pengguna

Tujuan: membantu migrasi ratusan label lama dengan merapikan informasi yang sudah tersedia menjadi struktur baru, tanpa meminta mereka mengisi ulang data yang sama. Ini pengecualian terarah untuk Super Admin; Admin tetap tidak bisa mengubah identitas lewat menu internal.

Usulan alur: daftar label beserta kelengkapan data -> panel data lama dan kolom baru berdampingan -> saran pemetaan dari informasi yang benar-benar tersedia -> Super Admin memeriksa/memperbaiki -> simpan perapian. Negara/provinsi/kabupaten-kota/kecamatan/kode pos masuk langsung ke Identitas Label yang sudah ada; bukan tab lokasi. Usulkan nama menu Penyesuaian Data Label di area Manajemen Label, sebagai ruang kerja khusus transisi; profil label tetap menjadi sumber data utama.

Sistem hanya menyarankan pemecahan alamat, tidak mengarang wilayah/kode pos yang tidak tersedia atau ambigu. Bila ada informasi kurang, kirim permintaan kelengkapan hanya pada kolom tersebut, terisi awal dengan data yang sudah diketahui. Label tidak mengulang aktivasi yang telah sah. Simpan sumber asli, sebelum/sesudah, petugas dan waktu perapian, serta versi data untuk mencegah penimpaan perubahan label yang bersamaan.

Batas: merapikan struktur informasi yang sama dapat disimpan Super Admin. Mengubah makna identitas penting (nama label/email/penanggung jawab/KTP), mengganti rekening, atau menyetujui kontrak atas nama label bukan perapian alamat dan tetap melalui alur konfirmasi/persetujuan terkait. Rekening dan kontrak tidak otomatis disetujui oleh penyimpanan perapian. Penyesuaian tidak otomatis mencabut akses operasional label lama.

Usulan pengembangan berikutnya: pratinjau perapian massal untuk data yang jelas, tampilkan perubahan sebelum diterapkan, tinjau kasus ambigu satu per satu. Kebijakan pengecualian, tenggang data belum lengkap, dan akses setelah masa transisi tetap dibahas menjelang final. Semua bagian ini masih rancangan; V10.3 belum diubah.

## Koreksi bahasa dan perapian rekening/identitas — 24 September 2026

### Bahasa produk

Pengguna menegaskan agar asisten kritis terhadap rancangan, memperbaiki bahasa dan menemukan celah sebelum diminta. Bonus Kredit adalah nama alat pengelolaan internal; bahasa penerima Bonus dari Rilis Musik DISETUJUI. KOREKSI: tidak memakai Terima kasih atau Selamat sebagai ucapan otomatis tanpa kejadian yang mendasari. Judul umum: Bonus dari Rilis Musik, nama label ditampilkan tersendiri; pesan netral misalnya Ada 5 kredit untuk rilisanmu berikutnya. Judul/pesan bisa disesuaikan pemicu yang benar, misalnya perilisan pertama, ulang tahun label, kampanye atau pemberian khusus tanpa peristiwa. Pemberian khusus tidak mewajibkan alasan mengada-ada. Usulan formulir: momen/tujuan (termasuk Pemberian khusus) -> saran pesan dapat diedit -> pratinjau popup. Ini alat penyusunan pesan, bukan otomatis menyalakan mesin kampanye baru. Jangan menyebut peran pengelola dalam judul/sumber hadiah pelanggan.

Pengguna menetapkan pengembalian kredit bermasalah tampil pada KARTU ATENSI label, bukan popup ucapan selamat dan tidak cukup hanya notifikasi. Kredit dikembalikan otomatis sesuai aturan asalnya, tanpa klaim. Kartu bersumber transaksi pengembalian aktual, menampilkan jumlah/jenis, rilisan terkait, penyebab yang relevan, masa berlaku jika ada dan tombol Lihat rincian. Jangan menyatakan Sudah dikembalikan sebelum transaksi berhasil. Notifikasi dan riwayat menjadi pendamping. Usulan perilaku: kartu dapat ditandai sudah dibaca tetapi menutup kartu tidak menutup masalah rilisan; pengingat kredit sementara mendekati kedaluwarsa mengikuti aturan pengingat bersama, jangan menghilangkan informasi sensitif otomatis sesaat setelah muncul.

### Perapian rekening penerima

Diminta pengguna: tambahkan perapian rekening di Penyesuaian Data Label milik Super Admin. Nama bank dipilih melalui pencarian dengan autocomplete dari direktori bank resmi. KOREKSI TERBARU: tetap sediakan Bank tidak ditemukan? Isi manual, termasuk bank luar negeri. Simpan negara dan nama bank manual tanpa menebak kode atau otomatis memasukkannya sebagai bank resmi terverifikasi pada master. Kebutuhan IBAN/SWIFT atau informasi pencairan lain mengikuti negara/jalur pencairan saat diperlukan, bukan dipaksakan untuk semua rekening. Nomor rekening TIDAK boleh diubah Super Admin melalui alat ini; penguncian harus berlaku di layanan penyimpanan/API, bukan hanya kolom yang dinonaktifkan. Nomor disimpan sebagai teks agar nol di depan tidak hilang. Nama pemilik disimpan dengan huruf awal tiap kata kapital sesuai ketentuan normalisasi di bawah.

Sumber master: direktori OJK bank umum konvensional dan syariah (halaman yang ditemukan menunjuk edisi Juni 2026), dengan sumber BPR/BPRS bila cakupan pencairan mendukungnya. Daftar bank berizin tidak sama dengan daftar bank yang didukung jalur pencairan. Cocokkan pengenal bank tujuan dengan daftar penyedia pencairan yang sebenarnya; penyedia belum ditetapkan dalam pembahasan ini. Jangan mengarang kode bank atau menganggap seluruh bank OJK langsung tersedia untuk transfer. Simpan nama resmi, nama tampilan, alias pencarian, identitas bank stabil, status dukungan dan tanggal sumber. Perbarui direktori tanpa mengubah riwayat rekening/transaksi lama.

Sumber diperiksa melalui web pada turn ini:
- OJK: https://ojk.go.id/id/kanal/perbankan/data-dan-statistik/Pages/Daftar-Alamat-Kantor-Pusat-Bank-Umum-Dan-Syariah.aspx (hasil pencarian menampilkan lampiran Juni 2026; isi seluruh lampiran belum diimpor/divalidasi).
- OJK FIND: https://find.ojk.go.id/Home
- blu: https://blubybcadigital.id/info/faq — blu aplikasi BCA Digital; bukan rekening BCA biasa.
- Jenius: https://www.jenius.com/faq/mengenal-jenius/tentang-jenius — rekening pada PT Bank SMBC Indonesia Tbk.
- SeaBank: https://www.seabank.co.id/perusahaan/info/seabank — PT Bank SeaBank Indonesia.

Pencarian menerima nama bank/nama layanan digital/singkatan/alias lama yang telah diverifikasi, lalu menampilkan kandidat bank resmi. Tidak membuat bank duplikat untuk nama aplikasi. Pencarian salah ketik memberikan saran, tidak otomatis mengganti bank ketika kandidat ambigu atau hanya mirip. Pilihan tidak langsung disimpan; tampilkan perubahan sebelum menyimpan. Label yang sudah merapikan data sendiri tidak ditimpa oleh versi lama; jika data berubah selama diperiksa, minta petugas meninjau versi terbaru.

Celah yang perlu dijaga: bank + nomor menentukan tujuan pembayaran pada jalur transfer, tetapi perapian catatan nama bank tidak melakukan transaksi atau memindahkan rekening nasabah. KOREKSI PENGGUNA: Super Admin punya DUA tindakan, Simpan perbaikan (langsung memperbaiki data nama bank yang diyakini salah berdasarkan data pendukung) dan Minta konfirmasi label (mengirim usulan perubahan, data aktif belum ditimpa sampai dikonfirmasi/diselesaikan sesuai alur). Tidak mewajibkan semua perubahan bank diajukan label. Riwayat mencatat nilai lama/baru serta siapa yang membetulkan; tampilan sebelum simpan memperlihatkan perbedaan dan nomor rekening terkunci. Pencairan tetap mencocokkan bank, nomor dan pemilik; penyimpanan koreksi tidak berarti verifikasi bank otomatis berhasil. Penggantian nomor tetap diajukan label sendiri. Perapian kapitalisasi pemilik bukan penggantian orang/pemilik; perubahan ejaan substantif bukan auto-correct. Jika pengguna menyebut nama rekening dalam konteks ini, implementasi harus membedakan field Nama Bank dan Nama Pemilik Rekening, bukan memberi hak mengganti pemilik tanpa sengaja.

Perapian kosmetik tidak mereset persetujuan sah. Perubahan tujuan/pemilik tidak mewarisi persetujuan rekening lama. Transaksi yang sedang diproses tetap mengacu versi rekening saat disetujui; jangan dialihkan diam-diam. Bila rekening lama diketahui salah, tahan pencairan terkait sampai rekening benar terkonfirmasi, bukan tetap mengirim ke tujuan salah. Semua perubahan punya nilai lama/baru, sumber dan petugas, tanpa kewenangan baru bagi Admin.

### Normalisasi identitas dan alamat

Ketentuan pengguna:
- Nama label mempertahankan penulisan khas, kapitalisasi dan tanda yang sah (bukan dipaksa Title Case).
- Nama penanggung jawab dan nama pemilik rekening: huruf pertama setiap kata kapital, huruf berikutnya kecil.
- Email disimpan lowercase, spasi tepi dibersihkan.
- Alamat dan kolom alamat terpisah memakai huruf depan tiap kata kapital; pilihan wilayah menggunakan nama baku direktori.

Usulan penyempurnaan agar format tidak merusak data: pertahankan singkatan resmi/inisial PT, CV, RT, RW, DKI, DIY serta angka Romawi dan tanda nama yang sah; jangan mengubah II menjadi Ii. Nama resmi bank mengikuti master, tidak dipaksa Title Case sehingga BCA tidak menjadi Bca. Simpan representasi rapi untuk formulir, tetapi bahan identitas asli, dokumen, nama hasil pengecekan bank dan riwayat legal tetap utuh untuk pencocokan. Untuk ejaan nama khusus, sediakan koreksi yang terjaga, bukan algoritme yang mengubah identitas tanpa bukti.

Tampilkan hasil perapian saat keluar dari kolom/sebelum Simpan agar pengguna melihat hasil, bukan menggeser kursor setiap ketikan; aturan juga dijalankan di server. Normalisasi penulisan saja tidak memicu pemeriksaan identitas ulang. Perubahan isi email/nama penting tetap mengikuti konfirmasi yang sudah dirancang. Migrasi email perlu memeriksa benturan akun setelah lowercase; jangan menggabungkan akun otomatis. Negara/wilayah internasional mengikuti struktur yang sesuai dan nama baku, tidak dipaksa struktur Indonesia. Data lama yang sudah dirapikan label dipertahankan. Semua ini rancangan, belum perubahan prototype atau impor master bank lengkap.

### Autocomplete wilayah dan penyimpanan

Pengguna menanyakan autofill kabupaten/kecamatan dan beban storage. Rekomendasi: simpan satu direktori wilayah administratif terpusat, dipakai seluruh label; label menyimpan rujukan wilayah yang dipilih, bukan salinan seluruh direktori. Provinsi memfilter Kabupaten/Kota, lalu Kecamatan. Pencarian kecamatan dapat menampilkan jalur lengkap agar nama sama di wilayah berbeda tidak tertukar; memilih hasil yang spesifik bisa mengisi induknya otomatis. Saran dari alamat lama perlu ditinjau bila ambigu. Mengganti wilayah induk membatalkan pilihan turunan yang sudah tidak cocok dengan penjelasan pada kolom, bukan menyimpan pasangan salah. Kode pos jangan otomatis ditebak dari kecamatan jika pemetaannya tidak tunggal. Luar negeri mengikuti struktur lokal dengan isian manual bila perlu.

Sumber resmi ditemukan: Ditjen Bina Administrasi Kewilayahan Kemendagri mempublikasikan informasi keputusan pemutakhiran kode/data wilayah 2025 (https://ditjenbinaadwil.kemendagri.go.id/berita/index/352); BPS menyediakan relasi kode wilayah BPS dan Kemendagri (https://sig.bps.go.id/bridging-kode/index). Pilih kode administratif Kemendagri sebagai rujukan identitas; jangan mencampur kode BPS tanpa pemetaan. Dataset final, versi terkini dan izin/akses unduhan perlu divalidasi saat implementasi; belum diimpor. Simpan versi/tanggal sumber untuk menangani perubahan wilayah dan menjaga riwayat.

Beban storage relatif kecil untuk data kode/nama/hubungan wilayah dibanding berkas foto/dokumen; belum ada angka ukuran terukur. Jangan menduplikasi direktori per label atau memuat seluruhnya setiap membuka formulir. Muat daftar sesuai provinsi/kabupaten yang dipilih. Manfaatnya: isian lebih cepat, konsistensi data, filter dan peta. Belum ada perubahan prototype.

### Keputusan terbaru: transisi alamat dan KTP wajib aktivasi

Ketentuan ini menggantikan rancangan formulir yang tetap meminta alamat jalan lengkap dan wilayah terpisah secara bersamaan untuk semua label.

- Label lama yang sudah aktif: tampilkan alamat lengkap lama sebagai acuan, bersama kolom wilayah terstruktur (negara, provinsi, kabupaten/kota, kecamatan, kode pos) di Identitas Label yang sama. Gunakan data terstruktur yang sudah benar; jangan meminta diisi ulang. Super Admin dapat merapikan melalui Penyesuaian Data Label, label dapat memperbarui melalui identitasnya sesuai kewenangan.
- Setelah seluruh data wilayah yang diwajibkan valid dan berhasil disimpan, kolom alamat lengkap lama menghilang dari formulir/profil operasional. Menyimpan sebagian/draft, menyimpan field lain, atau gagal menyimpan tidak boleh menghilangkan acuan lama. Riwayat sumber alamat lama tetap tersedia terbatas untuk audit/migrasi; hilang dari UI tidak berarti menghapus data asli atau mengubah kontrak historis.
- Akun baru langsung menggunakan wilayah terstruktur, tanpa kolom alamat jalan lengkap terpisah. Negara/wilayah luar Indonesia tetap mengikuti pola lokal, tidak dipaksa kecamatan Indonesia. Dokumen identitas alternatif bagi penanggung jawab yang tidak memiliki KTP Indonesia belum ditetapkan; simpan sebagai isu menjelang final, jangan membuka pembahasan tambahan tanpa kebutuhan saat ini.
- KTP penanggung jawab merupakan syarat WAJIB aktivasi pada Identitas Label, ditegaskan pengguna. KTP yang sudah diterima dan valid digunakan kembali, tidak meminta unggah ulang hanya karena transisi kolom alamat. Perapian tidak menonaktifkan atau meminta aktivasi ulang label lama; berkas lama yang benar-benar hilang/tidak terbaca masuk daftar penyesuaian tersendiri sesuai kebijakan transisi yang belum final.
- Super Admin dapat membuka KTP penanggung jawab langsung dari menu Penyesuaian Data Label, dekat data yang sedang diperiksa. Usulkan tombol Lihat KTP membuka viewer aman, bukan menampilkan foto KTP terbuka di tabel semua label. Otorisasi server dan akses berkas privat, bukan tautan publik; catat akses/perubahan sesuai audit. Tidak otomatis memperluas hak Admin di luar pemeriksaan aktivasi yang telah disepakati.
- Domisili penanggung jawab digunakan sebagai acuan awal lokasi operasional label sesuai keputusan pengguna; tidak perlu meminta alamat yang sama dua kali atau menambah tab/formulir lokasi. Alamat pada KTP menjadi sumber rujukan, tetapi bukan bukti bahwa lokasi operasional saat ini pasti sama. Wilayah terstruktur dapat dikoreksi apabila lokasi aktual berbeda; peta memakai data wilayah yang telah disimpan/dikonfirmasi, bukan klaim lokasi yang terverifikasi hanya dari KTP. Tidak menambah checkbox wajib atau narasi sistem pada halaman hanya untuk menjelaskan asumsi ini.

### KTP: penyesuaian gambar standar setiap unggahan

Pengguna menegaskan crop dan pembetulan orientasi harus SELALU menjadi bagian proses KTP agar siap direview. Terapkan pada unggahan baru maupun penggantian dokumen, bukan fitur opsional tersembunyi yang harus dicari. Untuk KTP lama yang belum mempunyai hasil penyesuaian, proses satu kali dengan jejak versi; jangan mengompresi/crop ulang setiap dokumen dibuka.

Alur rancangan: simpan berkas asli privat -> baca orientasi berkas dan arah kartu/tulisan -> deteksi batas kartu -> crop latar berlebih dengan margin aman -> luruskan orientasi/kemiringan -> tampilkan pratinjau hasil -> simpan turunan untuk review. Seluruh sisi kartu, tulisan, foto, dan bagian identitas harus tetap utuh. Luruskan perspektif hanya bila deteksi memadai; jangan memaksakan transformasi yang merusak keterbacaan.

Label dapat menggeser batas crop atau memutar hasil sebelum mengirim. Pada viewer Super Admin, tampilkan hasil yang sudah rapi secara default, dengan Lihat asli dan kontrol penyesuaian bila diperlukan. Perubahan crop/orientasi tidak mengganti isi identitas, tidak mengubah status persetujuan secara otomatis, dan tidak menimpa bahan pemeriksaan versi lama diam-diam. Admin yang sudah berwenang mereview aktivasi memakai hasil yang sama tanpa perlu mengulang perapian.

Selalu menjalankan pemeriksaan tidak berarti selalu memotong gambar secara paksa: jika gambar sudah tepat, hasil boleh tetap sama; jika batas kartu/orientasi tidak yakin atau kartu sudah terpotong, pertahankan gambar utuh dan minta penyesuaian di pratinjau. Foto buram/tidak terbaca diberi arahan unggah ulang, bukan merekayasa huruf/angka atau memakai generatif untuk merekonstruksi identitas. Tidak otomatis mengisi/mengubah data identitas dari pembacaan gambar tanpa pemeriksaan yang sesuai. Pembuatan turunan gagal tidak menghilangkan asli dan tidak boleh dianggap berhasil.

Rancangan dicatat, belum diterapkan pada prototype dan belum menghapus/memigrasikan data label.

## Pemeriksaan wajib menjelang final: layanan yang sudah berjalan

### Pembaruan prototipe 24 September 2026

- Studio diganti katalog tunggal 30 kondisi, urutan versi terbaru dahulu, dengan pergantian akun/halaman otomatis. Pergantian peran manual di dalam Studio melanjutkan contoh yang sama; pemulihan sesi awal tersedia.
- Chat/notifikasi menggunakan perilaku buka-tutup bersama.
- Impor direktori bank OJK Juni 2026 (105 bank) dan wilayah BPS semester 2 tahun 2025 (38 provinsi, 514 kabupaten/kota, 7.288 kecamatan) sudah diterapkan untuk autocomplete lokal di rekening dan identitas/aktivasi. Kode pos masih manual. Sumber dan pemetaan ambigu dicatat dalam reference-data/README.md.
- Alamat sumber lama dipertahankan; tampilan acuan lama hilang hanya sesudah wilayah lengkap berhasil disimpan. Tidak ada migrasi akun produksi. Menu perapian data Super Admin dan crop KTP otomatis tetap rancangan terpisah.


Pengingat berbasis tahap proyek, bukan jadwal kalender. Munculkan dalam pembahasan sebelum final/produksi:

- Pemetaan akun dan master lama; jangan membuat akun/riwayat duplikat.
- Hak paket aktif, masa berlaku, kontrak yang sudah disetujui, harga dan benefit lama.
- Saldo royalti, pembayaran historis, kredit serta rilisan yang masih diproses; rekonsiliasi sebelum dan sesudah migrasi.
- Peralihan centang verifikasi lama ke standar baru, pencapaian historis dan hadiah sekali saja.
- Data aktivasi baru seperti lokasi operasional: isi ulang hanya data yang kurang, usulkan masa penyesuaian, jangan menonaktifkan seluruh label lama secara mendadak.
- Komunikasi perubahan dan penanganan pengecualian; kebijakan melindungi hak label sekaligus kemampuan operasional Rilis Musik.
- Rencana uji migrasi, pemeriksaan hasil dan pemulihan bila terjadi ketidaksesuaian. Detail harus ditelusuri pada sistem/data lama menjelang final; saat ini belum dianggap sudah diaudit.


## Perkembangan draf 24 September 2026 — belum dirilis

Pengguna mengonfirmasi cakupan dua celah persetujuan, fitur tertunda, dan perapian daftar bank. Draf alur Bonus Kredit, pencapaian, tab kredit, perapian data, penyesuaian gambar identitas, peta, dan editor tata letak telah ditambahkan serta diuji di prototype-v10.3. Rincian hasil dan batas implementasi berada di prototype-v10.3/DRAFT-PENDING-WORK.md. Catatan usulan kebijakan di atas tetap historis; hadiah transisi tidak diterbitkan. Integrasi server lintas pengguna, OCR/orientasi tulisan, penyimpanan privat dokumen produksi dan migrasi akun lama belum selesai. Berkas HTML standalone/ZIP belum dibangun ulang.

## Pembahasan setelah V10.4 — 25 September 2026

Status: dialog rancangan; tidak ada implementasi atau rilis baru. Baseline rilis adalah prototype-v10.4/Rilis-Musik-V10.4.html. Catatan versi lebih lama di atas merupakan riwayat, bukan status terbaru.

### Paket/Flex diparkir atas permintaan pengguna

Pembahasan penamaan Flex, posisi tanpa langganan versus paket layanan, biaya layanan dalam harga kredit Rp35.000, nilai langganan Go/Pro/Business, harga tambahan kredit dan manfaat seperti WAMI ditunda. Jangan menetapkan harga/manfaat atau mengubah nama Flex berdasarkan usulan asisten sebelum dibahas kembali. Kebijakan pergantian paket/prorata juga belum final.

### Arahan UI dan alur yang sedang dibahas

- Urutan periode paket: Bulanan lalu Tahunan; pilihan masing-masing kartu tetap independen.
- Perbandingan paket tetap di panel sampai pengguna keluar sendiri. Pembayaran selesai atau pengguna selesai memilih dan menuju keadaan menunggu pembayaran mengantar ke dashboard. Kembali dari pembayaran untuk membandingkan paket mengembalikan panel beserta posisi scroll dan pilihannya.
- Registrasi/login pertama: sambutan sekali, pilihan bahasa selalu tersedia di kartu; lanjut ke aktivasi. Identitas lebih dulu, lalu kontrak, rekening dapat dilanjutkan. Pemilihan/pembayaran paket dikeluarkan dari prasyarat awal aktivasi sesuai koreksi terbaru pengguna.
- Identitas: tanda bintang merah untuk isian wajib; unggah/ganti KTP di samping kode pos, istilah jelas; tidak ada tombol simpan identitas/kirim pemeriksaan pada langkah ini, hanya Next. Penyesuaian crop/orientasi dan pratinjau gambar tetap diperlukan.
- Kontrak penuh dengan checklist persetujuan; usulan tombol pengguna Kirim dan Lanjutkan nanti atau Next ke rekening. Hubungan pengiriman pemeriksaan, ucapan selesai, dan langkah rekening masih perlu diperjelas dalam dialog; jangan menganggap kirim data berarti persetujuan otomatis.
- Penutup sesi diikuti pilihan tema Light–Auto–Dark, teks di sela slider, kemudian dashboard. Auto mengikuti tema perangkat, berlaku sebagai komponen global bersama.
- Step bar dashboard memanjang sampai mendekati tombol Lanjutkan.
- Header dan sidebar menggunakan dasar warna/transparansi kaca yang sama sesuai tema, tanpa garis pemisah, efek kaca sedikit ditingkatkan.

## Keputusan onboarding lanjutan — 25 September 2026

Status: kesepakatan rancangan setelah V10.4; belum perintah implementasi/rilis. Arahan terbaru mengesampingkan rancangan onboarding sebelumnya yang bertentangan.

- Kartu pertama tidak mengasumsikan nama akun Google sebagai nama label. Pilihan: Saya pengguna baru dan Klaim Label (menggantikan Hubungkan label saya). Pilihan bahasa tetap tersedia sepanjang kartu onboarding.
- Pengguna baru memperoleh sambutan kedua dan dapat menjelajah dashboard, menulis serta menyimpan draft sebelum membeli. Kredit/langganan dibeli saat diperlukan; persyaratan aktivasi disampaikan sebelum pembayaran dan kartu aktivasi muncul pada konteks setelah pembayaran atau saat hendak mengajukan rilisan. Draft tidak otomatis dikirim ketika aktivasi disetujui. Progres tersimpan, popup tidak berulang setiap menu.
- Jalur Klaim Label dipakai sementara: pencarian dengan nama/email lama atau undangan; konfirmasi melalui kontak lama yang tercatat; pemeriksaan hubungan akun dan persetujuan Super Admin sebelum memberi akses baru; jalur pemulihan jika email lama tidak dapat diakses. Label lama tetap memakai identitas data yang sama, tanpa menggandakan katalog, kontrak, royalti, atau hak paket.
- PENGINGAT BERBASIS TAHAP: ajak pengguna meninjau jalur Klaim Label bersama tim sebelum aturan ini difinalkan atau diterapkan pada akun produksi. Pengguna secara khusus meminta pengingat ini. Tidak ada tanggal atau pengingat kalender yang diminta. Jika pembahasan klaim/migrasi/menjelang final dibuka, munculkan kembali poin ini.
- Email berada di Identitas Label; boleh diisi otomatis dari registrasi/Google tetapi tetap dapat diedit. Bedakan email login dan kontak label secara internal. Penggantian kontak perlu konfirmasi kepemilikan email baru dan tidak otomatis mengganti kredensial login.
- Judul bidang lokasi menjadi Lokasi pada aktivasi dan edit identitas.
- Auto tema mengikuti waktu lokal pengguna (usulan yang diterima: terang 06.00–17.59, gelap 18.00–05.59), bukan preferensi tema perangkat. Pilihan Light–Auto–Dark global, transisi tanpa reload atau perubahan scroll.
- Ikon centang biru mengikuti referensi bergerigi biru dengan centang putih tanpa latar tambahan. Aktivasi atau klaim berhasil bukan syarat tunggal pemberian centang biru.
- Tidak ada penolakan final dalam pemeriksaan aktivasi. Pengajuan yang belum aman dikembalikan untuk perbaikan dan dapat diajukan ulang sampai memenuhi syarat. Tidak ada persetujuan otomatis karena jumlah percobaan/lama menunggu. Label belum dapat mengajukan rilisan sebelum disetujui; masa langganan belum berjalan sebelum akun disetujui. Koreksi harus jelas pada bagian terkait dan tidak mengulang isian yang sudah benar.
- Pengguna menyetujui bagian lain dari tanggapan sebelumnya. Jalur klaim tetap sementara menunggu pembahasan tim; kebijakan Flex/harga/manfaat tetap ditunda seperti catatan sebelumnya.

## Peralihan pembahasan ke M02 Rilisan — 25 September 2026

Pengguna meminta menyimpan celah dan melanjutkan pembahasan Rilisan berdasarkan repo. Versi berikutnya baru dirilis setelah menu Rilisan dibuat dan dialog selesai. Tahap saat ini hanya analisis dan pencatatan, bukan implementasi atau rilis. Revisi UI/onboarding yang disepakati setelah V10.4 tetap masuk cakupan berikutnya; pembukaan M02 tidak membatalkannya. Nomor rilis berikutnya belum ditetapkan melalui catatan ini.

Koreksi terbaru yang mengesampingkan catatan sebelumnya: email otomatis pada pengisian identitas awal boleh diedit langsung TANPA konfirmasi email baru. Ini bukan perubahan kebijakan kredensial login maupun persetujuan perubahan identitas akun yang sudah aktif. Pesan masa paket: **Masa langganan dimulai setelah akun labelmu aktif.**

Celah yang diparkir, untuk dibuka kembali saat konteksnya relevan:

- M01-G01 — Klaim Label: jalur sementara perlu dibahas bersama tim sebelum final; bukti kepemilikan dan pemulihan kontak harus mencegah akses salah ke katalog/royalti label lama.
- M01-G02 — Pergantian paket: prorata, sisa masa aktif, benefit terpakai dan penurunan Business belum final. Nama/harga/manfaat Flex, Go, Pro, Business tetap ditunda.
- M01-G03 — Transisi ratusan label lama: pertahankan hak paket/kontrak, katalog, royalti dan kredit; hindari aktivasi ulang menyeluruh. Wajib dibahas sebelum migrasi produksi.

Catatan peringatan setelah tanggal 20: gunakan tanggal 21 WIB sebagai awal peringatan untuk pencairan yang memang jatuh tempo pada periode terkait dan belum selesai. Jangan menandai permintaan periode berikutnya hanya karena tanggal kalender sudah lewat 20. Rekonsiliasi aturan periode dengan data aktual masih diperlukan sebelum implementasi.

Kode pembahasan kerja: M01 Manajemen Label; A01 alur registrasi/aktivasi/klaim; U01 perubahan UI/navigasi bersama; M02 Rilisan. Kode ini terpisah dari nomor versi rilis. Pemetaan repo dan usulan M02 tersimpan di analysis-v10/M02-RILISAN-REVIEW.md.

## Pelaksanaan V10.5 — 25 September 2026

Setelah dialog selesai, pengguna memberi perintah eksekusi. Rancangan M02 dan koreksi A01/U01 diterapkan dalam prototype V10.5, dengan pemetaan rinci pada `prototype-v10.5/SCOPE-V10.5.md`. Ini memperbarui status analisis sebelumnya, bukan mengubah repo produksi.

Keputusan terakhir yang diterapkan: foto artis opsional; aset lama kosong tetap kosong; cover baru wajib. Tanggal menampilkan “Diajukan pada [hari, tanggal · jam WIB]” satu baris, dengan saran layanan langsung dalam teks. Panel Standard/Express/MAX ringkas, posisi titik dan label sejajar; MAX memakai gelombang identitas dan titik putih. Kredit EP/Album diselesaikan per lagu yang dikonfirmasi tayang, sisanya tetap dialokasikan sampai hasil akhirnya jelas.

Revisi jumlah lagu/layanan menghitung selisih dengan persetujuan pengajuan, tanpa menarik ulang seluruh alokasi. Petugas membaca snapshot yang telah dikirim selama label mengubah draft revisi. Kesalahan konfirmasi tayang hanya dapat dikoreksi Super Admin dengan alasan dan mengembalikan alokasi, bukan menggandakan saldo tersedia.

M01-G01, M01-G02 dan M01-G03 tetap diparkir. Jangan membuka keputusan harga/Flex/prorata atau migrasi label lama secara sepihak. Untuk pembahasan berikutnya, evaluasi pengalaman M02 yang sudah bisa dicoba sebelum membuka menu baru. Lisensi cover/remix, opsi layanan tambahan, pemilihan DSP, serta integrasi produksi dicatat untuk tahap setelah penilaian M02.

## Evaluasi setelah V10.5 — 26 September 2026

Status: dialog dan pencatatan saja; belum izin implementasi atau rilis berikutnya.

Arahan pengguna: satu standar komponen untuk kartu atensi, lima ringkasan, dan wawasan pada ketiga peran; perubahan bersama termasuk ukuran kecuali diminta berbeda. Hapus Customize Layout beserta penerapan konfigurasi lamanya. Wawasan menjadi kartu besar di bawah header, isi dan penerimanya belum dibahas. Ukuran kartu atensi seragam. Ikon verifikasi tanpa outline tambahan dan sejajar tengah dengan nama; kebijakan verifikasi artis perlu dibahas sebelum diterapkan.

Koin R perlu ketebalan visual saat flip, kartu kredit animasi gold/coklat. Kontrol tema sehari-hari berupa Light–Auto–Dark langsung di header; dialog tema hanya sekali untuk onboarding label. Auto tetap mengikuti waktu. Profil label memakai tombol dokumen identitas yang diperbarui, perubahan foto menyatu dengan avatar, transisi tab halus dan lebar panel konsisten. Referensi baru: tabel wilayah dengan peta untuk kartu member Super Admin; susunan visual katalog musik untuk pengembangan Rilisan.

U01-T01 — Tema musiman (IDE DIPARKIR, belum keputusan fitur): pengguna ingin mengembangkan tema Natal/hari penting. Usulan persiapan: pisahkan mode kecerahan Light/Auto/Dark dari tema visual; gunakan variabel warna dan aset bersama; pertahankan warna semantik status dan centang verifikasi; hormati preferensi pengurangan animasi. Jadwal mulai/akhir, cakupan peran, pilihan kembali ke tema biasa dan pengelolaan oleh Super Admin perlu dibahas sebelum dibuat. Jangan menambahkan menu tema musiman sekarang.

Usulan yang belum disetujui: peta/tabel menggantikan kartu sebaran member yang sudah ada, bukan duplikat. Rilisan memiliki Galeri/Daftar dari sumber data dan filter yang sama; referensi tampilan musik tidak otomatis berarti fitur streaming sosial. Verifikasi artis harus membedakan identitas artis, keterkaitan katalog, dan kewenangan label; tautan, foto, atau verifikasi label saja bukan bukti kepemilikan artis.

## Pelaksanaan V10.6 — 27 September 2026

Pengguna menyepakati susunan utama Rilisan, meminta dasar verifikasi artis ditunda, lalu memberi perintah “Silahkan Rilis!”. Peta/tabel dan Galeri/Daftar yang sebelumnya berstatus usulan telah disetujui dan diterapkan. Detail lengkap memiliki Ringkasan, Lagu, Distribusi, Riwayat; panel kanan untuk pemeriksaan cepat. Tab Tayang hanya memuat rilisan seluruhnya tayang; sebagian tayang tetap Dalam proses sampai hasil akhir. Katalog lama memakai data yang tersedia tanpa menciptakan berkas/metadata yang kosong.

Perbaikan global setelah V10.5 ikut dirilis dalam prototype-v10.6; cakupan dan bukti ada di SCOPE-V10.6.md. Tidak ada perubahan situs produksi. Verifikasi artis, tema musiman, isi wawasan lanjutan, harga/Flex/prorata dan kebijakan migrasi/klaim tetap diparkir. Jangan mengimplementasikan poin tertunda tanpa dialog dan persetujuan lanjutan.

## Evaluasi setelah V10.6 — 27 September 2026

Status: pembahasan dan rancangan, belum perintah implementasi/rilis.

- Wawasan harus tepat di bawah header, selebar area dari batas sidebar sampai sisi kanan viewport; pindahkan keterangan versi/Studio menjadi kontrol melayang di bawah. Sapaan/judul dashboard berada setelah wawasan. Bar aktivasi yang belum lengkap tetap perlu mempertahankan prioritas sesuai keputusan sebelumnya.
- Wawasan memakai warna netral sesuai tema; hentikan dominasi blok warna identitas.
- Tema kembali berbentuk slider dengan thumb seperti sebelumnya, tiga posisi Light/Auto/Dark dengan ikon. Selaraskan pusat vertikal dan ukuran dengan kontrol header; label aksesibel/tooltip tetap tersedia.
- Koin R perlu perbaikan visual, ketebalan dan gerak; rancangan usulan: tepi lebih tipis, pantulan tenang, satu flip dengan jeda pada sisi depan. Bukan perintah membuat animasi/aset sekarang.
- Profil Label tab Kontrak masih terasa melebar. Batas lebar panel sudah ada pada V10.6, tetapi belum ada penguncian ruang scrollbar; uji pada kondisi scrollbar muncul/hilang dan zoom, bukan hanya satu viewport.
- Animasi Platform/Staff perlu dibenahi. Kode V10.5 dan V10.6 sama-sama memanggil enhance105 dalam satu render; pemanggilan ulang dapat menimpa transisi dengan posisi akhir. Konsolidasikan lifecycle animasi saat implementasi, tanpa mengubah gaya semua switch secara sepihak.
- Draf daftar wawasan per penerima disiapkan di analysis-v10/INSIGHT-DRAFT.md. Pengguna meminta belum dibahas dan belum dibuat dalam UI.
- Pengguna menanyakan kesiapan membuka menu baru. Usulan asisten: mulai pembahasan Royalti sebagai sumber data sebelum Penarikan; kode/menu belum disepakati. Jangan menganggap pertanyaan ini izin implementasi atau rilis.

## Penutupan pembahasan Royalti dan rilis V10.7

Pengguna telah meminta rilis setelah pembahasan susunan Royalti, impor, pemetaan, penerbitan, pencocokan penerimaan dan koreksi. Hasil prototype V10.7 dijelaskan dalam README-V10.7.md / SCOPE-V10.7.md. Koreksi akses terakhir: Kontrak Label hanya Super Admin. Visibilitas menu dan hak tindakan kelak dibahas di Staff & Akses; jangan otomatis membuka menu kepada Admin.

Tetap belum final: pencocokan pembayaran Believe yang parsial/valas; penyelesaian selisih setelah pembayaran label; hak laporan historis saat hubungan master multi-label berubah; migrasi saldo historis dan integrasi seluruh pembukuan lama. Prototype menahan keputusan pada kondisi belum final dan tidak membuat pembayaran nyata. Menu Penarikan belum dibuka sebagai implementasi baru.

Draf wawasan per peran tetap terpisah pada analysis-v10/INSIGHT-DRAFT.md. Belum diminta dibahas atau diimplementasikan sebagai daftar baru. Koreksi visual wawasan pada V10.7 tidak berarti isi draf tersebut sudah disetujui.

## Penarikan selesai dalam V10.8 — 28 September 2026

Implementasi prototype Penarikan mengikuti satu saldo per akun, termasuk master multi-label, minimal inklusif Rp1.000.000 dan seluruh saldo. Pengajuan/pembayaran/perbaikan/penundaan/koreksi terhubung lintas Label–Admin–Super Admin. Tidak ada pembatalan atau penarikan anak label. Bukti transfer dan biaya bank tidak dicatat; konfirmasi pembayaran mencatat petugas/waktu. Memo bank memakai bulan laporan terakhir, periode lengkap di atas pengajuan, tanpa kolom jadwal.

Tetap diparkir: aturan perpindahan anak label dan titik kepemilikan royalti; migrasi saldo dan rekening label lama; integrasi buku liabilitas historis; selisih pendapatan setelah pembayaran; dana Believe parsial/valas; backend autentikasi dan transaksi lintas perangkat. Tidak membuka kebijakan baru secara diam-diam. Dialog diperlukan sebelum pengerjaan versi berikutnya.

## Pembaruan UI V10.9 — 28 September 2026

Kartu atensi tiga peran sudah diganti desain compact statis, warna amber menjadi mustard dengan varian dark mode; latar dark lebih gelap dan wajah koin R dikembalikan ke emas dengan huruf gelap dan volume 3D. Semua catatan animasi atensi terdahulu batal sebagai spesifikasi: jangan menerapkan kembali pulse, wave atau hover fill. Respons interaksi hanya pada tombol.

Daftar isi Wawasan per peran tetap diparkir; panduan hanya memperjelas perbedaan fungsi atensi dan wawasan. Tidak membuka menu baru atau kebijakan lain. Bahas menu berikutnya bersama pengguna sebelum eksekusi.

## Pembahasan WAMI dan Penggunaan Kredit — 28 September 2026

Pengguna menyetujui pengajuan WAMI per lagu dengan metadata katalog dipakai kembali dan detail melalui panel kanan. Meminta panduan penggunaan kredit semua akun serta konfigurasi khusus; usulan penempatan adalah Standar & Penanda → Penggunaan Kredit dan perluasan Paket & Kredit khusus Super Admin. Belum izin implementasi/rilis. Temuan repo, baseline sementara, celah konfigurasi dan pertanyaan staf disimpan pada analysis-v10/WAMI-CREDIT-GUIDE-DISCUSSION.md.

Ingatkan sebelum finalisasi WAMI: verifikasi formulir/kolom/dokumen wajib, penggunaan metadata katalog, hasil penerimaan, dan syarat tayang kepada staf. Pengguna belum dapat bertanya sekarang. Repo lama punya alur WAMI, prototype V10.9 belum; jangan menyamakan keduanya. Data ISWC/BMAT dari impor bukan otomatis persyaratan pengajuan. WAMI tetap rupiah/benefit paket hingga ada keputusan lain, tidak otomatis dipotong kredit.

## Pelaksanaan V11.0 — 29 September 2026

Izin rilis telah diberikan; nomor versi langsung V11.0 setelah V10.9. WAMI dan panduan/konfigurasi penggunaan kredit telah diterapkan dalam prototype-v11.0. Detail alur, bukti uji dan batas ada di README-V11.0.md / SCOPE-V11.0.md. Hal ini menggantikan status belum ada izin pada catatan pembahasan sebelumnya, bukan mengesahkan persyaratan WAMI sebagai final.

Pengingat untuk pembahasan selanjutnya: minta staf memverifikasi formulir/dokumen wajib, metadata yang bisa digunakan kembali, bukti respons penerimaan, serta syarat lagu sudah tayang. Jangan memaksakan kolom impor hasil sebagai syarat pengajuan. Impor XLSX WAMI belum ditambahkan. Baseline biaya/kredit masih sementara; WAMI tetap rupiah atau benefit paket. Kebijakan lama yang diparkir tidak dibuka dalam rilis ini.

## Pembahasan setelah V11.0 — standar panel detail kanan

Pengguna meminta seluruh panel detail yang bergeser dari kanan mengikuti susunan informasi referensi codex-clipboard-28e2c11c-f64d-4814-a4d1-4ac0e64b9067.png. Eksekusi diminta nanti; belum ada izin mengubah UI atau merilis versi berikutnya.

Standar rancangan: header judul/tutup dan tindakan utama; identitas objek dengan foto/logo/cover yang tersedia; ringkasan fakta dalam grid; perkembangan proses bila relevan; aktivitas terbaru berupa timeline; catatan terpisah menurut hak akses. Terapkan komponen bersama pada semua peran/menu dengan isi sesuai konteks, mempertahankan DNA warna, tipografi, indikator, animasi dan tema yang berlaku. Jangan mengada-adakan persentase proses, tombol komunikasi, atau catatan pada panel yang tidak memerlukannya. Tombol detail lengkap hanya ketika tersedia tujuan nyata. Panel mempertahankan posisi halaman asal dan responsif; ini panel detail kanan, bukan sidebar navigasi kiri.

Usulan menu berikutnya: Layanan Tambahan (addons). Pada V11.0 masih outline v4.js, mencakup pesanan/hasil dan katalog layanan. Usulan pembahasan: katalog dan benefit paket → pemesanan/kelengkapan label → penanganan/revisi/hasil petugas → persetujuan dan riwayat, dengan konfigurasi Super Admin. Belum dianggap persetujuan implementasi. Tiket Bantuan (tickets) dapat dibahas sesudahnya. Konfirmasi persyaratan WAMI ke staf tetap diparkir, bukan penghambat pembahasan menu baru.

## Referensi grafik global — pembahasan setelah V11.0

Pengguna meminta semua grafik mengikuti referensi codex-clipboard-3d826793-d6a5-4d61-bfec-80c355c2207d.png dengan desain/animasi sesuai. Dicatat untuk eksekusi berikutnya bersama panel kanan; belum mengubah kode/rilis.

Arah desain: permukaan bersih sesuai tema, judul jelas dan pilihan periode di kanan atas, garis tren tipis dengan batang vertikal halus jika cocok untuk data, rentang disorot saat hover/tap, tooltip mengambang, label waktu ringkas dan ringkasan perubahan berbasis data. Animasi masuk/transisi periode halus dan sekali per perubahan, tidak berulang saat diam; reduced motion dihormati. Tooltip mendukung sentuhan iPad dan tidak terpotong. Warna grafik tetap bermakna, tidak semua wajib merah. Gunakan bahasa visual yang sama pada grafik perbandingan/komposisi tanpa mengubah semua bentuk menjadi grafik tren atau mendistorsi data. Ringkasan tidak mengarang sebab perubahan atau memakai data contoh sebagai fakta.

## Pembatalan konsep tema 3D — 30 September 2026

Pengguna membatalkan seluruh konsep dan rancangan tema 3D serta meminta kembali ke versi terakhir sebelum konsep tersebut, yaitu V11.1. Semua eksperimen dashboard kantor R1–R7, simulasi suasana kantor, dan rancangan menu Tema Suasana khusus Super Admin dibatalkan, bukan diparkir. Jangan memasukkannya kembali dalam rencana fitur atau implementasi tanpa permintaan baru pengguna. Pratinjau aktif pada port 4343 dipulihkan ke V11.1; tata letak, isi wawasan, efek UI, serta Studio mengikuti V11.1 sebelum eksperimen.

## Pembahasan Tiket Bantuan — 1 Oktober 2026

Pengguna menyetujui melanjutkan pembahasan menu berikutnya. Tahap ini analisis dan usulan alur, belum izin implementasi atau rilis. V11.1 tetap aktif; konsep 3D tetap batal.

Temuan referensi: repo-reference-v10/memory/SUPPORT_TICKET_WORKFLOW.md, frontend/src/components/label/tickets/ticketFormConfig.js, backend/routes/ticket_workflow_service.py, tickets.py, ticket_takedown_service.py. Pengajuan aktif utama mencakup takedown, perubahan metadata/audio/cover, pengajuan dan pencabutan Content ID. Backend juga mengenal not_live yang dipicu LiveTodayBanner; daftar kategori frontend belum seragam. Masalah Royalti dan Lainnya hanya dipertahankan untuk sejarah, bukan pengajuan baru. Form Content ID aktual telah berkembang menjadi pilihan lagu dan data/dokumen pencipta; jangan hanya menyalin catatan Iter64 yang lebih lama.

Usulan awal, belum disetujui: satu kasus/tiket dengan beberapa pintu masuk (detail rilisan dan menu Tiket Bantuan). Data rilisan, label, UPC dan seluruh ISRC terisi dari katalog yang berhak diakses; data saat pengajuan disimpan agar riwayat tetap bisa dibaca. Pilihan lagu bila permintaan menyangkut sebagian EP/Album. Label memiliki daftar kasusnya sendiri, Admin memiliki antrean/penanganan sesuai akses, Super Admin memantau dan mengalihkan penanganan. Panel detail mengikuti standar bersama judul, identitas, fakta, ringkasan permintaan, percakapan, aktivitas dan catatan internal terpisah.

Celah untuk dibahas bertahap: balasan Admin biasa tidak otomatis berarti Menunggu Label (repo saat ini mengubah status saat komentar); status Menunggu Label memerlukan tindakan meminta kelengkapan yang jelas. Penyelesaian tiket mencatat hasil, dan tindakan takedown menunggu konfirmasi distributor sebelum katalog ditandai turun. Satu tiket tidak boleh membuat perubahan metadata/berkas langsung pada katalog hanya karena diajukan. Hindari duplikasi kasus yang sama dan konflik dua petugas. Tiket baru tidak dianggap otomatis memotong kredit; tarif dan penggunaan kredit memerlukan keputusan tersendiri.

Pembahasan selanjutnya: struktur daftar/detail per peran, kategori dan formulir satu per satu, terutama formulir Content ID terbaru, alur selesai/perbaikan, pengingat dan eskalasi. Usulan hubungannya dengan chat: percakapan pada tiket menyimpan konteks kasus; penautan chat ke tiket memerlukan memilih pesan yang relevan, tidak menyalin semua percakapan.

### Usulan Perubahan Metadata — 1 Oktober 2026

Status: bahan dialog, belum keputusan akhir atau izin implementasi. Draft/revisi yang diminta petugas tetap diedit melalui Rilisan. Rilisan dalam pemeriksaan internal tidak membuka jalur perubahan paralel; usulan perubahan perlu dikoordinasikan dengan pemeriksa. Sesudah dikirim ke distributor atau tayang, perubahan memakai tiket dengan hasil terkonfirmasi.

Form memakai data katalog: identitas rilisan dan UPC/ISRC hanya-baca, pilihan data rilisan atau lagu, isian sebelumnya tersedia, alasan wajib, lampiran opsional, ringkasan hanya kolom yang benar-benar berubah. Subjek otomatis; tidak perlu deskripsi kedua yang mengulang alasan. Nama artis dan pencipta harus mengikuti struktur metadata Rilisan yang sudah dikembangkan, bukan enam kolom sederhana dari repo lama. Audio/cover tetap kategori tersendiri; perubahan jumlah lagu/jenis rilisan atau kode identifikasi tidak diperlakukan sebagai koreksi metadata biasa.

Usulan pengamanan: cegah pengajuan tanpa selisih; arahkan perubahan pada objek/kolom yang masih memiliki permintaan aktif ke kasus yang sama; jika sumber katalog berubah setelah form dibuka, tampilkan perbandingan baru sebelum pengajuan. Petugas meninjau perbedaan, meminta kelengkapan secara eksplisit, mencatat penerusan dan hasil distributor. Katalog hanya menerima perubahan yang telah dikonfirmasi berhasil, termasuk hasil parsial jika distributor memproses sebagian; jangan menandai seluruh permintaan selesai ketika masih ada bagian yang menunggu hasil. Tidak menetapkan biaya atau kredit baru pada tahap ini.

### Usulan Penggantian Audio dan Cover — 1 Oktober 2026

Status: lanjutan dialog yang diminta pengguna, belum izin implementasi atau rilis. Repo lama menyediakan WAV baru untuk satu lagu terpilih yang diverifikasi milik rilisan, serta JPG/PNG cover 3000×3000. Form lama masih meminta subjek/deskripsi manual; usulan baru memakai judul otomatis dan satu alasan penggantian wajib, tanpa mengulang isian.

Audio: tampilkan identitas rilisan, lagu/nomor urut/ISRC hanya-baca, berkas baru dengan nama/durasi/hasil pemeriksaan serta pemutar; pemutar berkas lama hanya bila berkas tersedia. Penggantian pada EP/Album ditargetkan ke lagu terpilih. Jika lagu diganti setelah upload, lepaskan pilihan berkas dan minta pemasangan ulang agar berkas tidak tertaut ke lagu keliru. Jangan otomatis menerapkan perubahan durasi pada titik cuplikan; periksa kembali bila di luar durasi baru. Perbedaan rekaman/versi membutuhkan penilaian petugas, bukan keputusan otomatis tentang kode ISRC atau distribusi ulang; kebijakan rinci belum final.

Cover: perbandingan cover saat ini dan usulan baru berdampingan, kosong bila aset historis tidak tersedia; pemeriksaan format/dimensi mengikuti standar pengajuan Rilisan. Jangan melakukan crop, peregangan, atau upscaling artwork secara otomatis. Tampilkan masalah spesifik dan minta berkas yang sesuai; pengguna dapat mengganti upload sebelum mengajukan.

Kedua kategori memakai Simpan Draft/Ajukan Penggantian dan panel detail bersama. Simpan versi berkas saat pengajuan, pertahankan versi sebelumnya untuk riwayat dengan akses terbatas; tidak menjanjikan retensi tanpa batas. Petugas membandingkan berkas, meminta perbaikan bila perlu, mencatat penerusan/hasil; katalog hanya beralih setelah hasil dikonfirmasi. Jangan menyamakan waktu pembaruan semua platform atau menyatakan berhasil di semuanya tanpa bukti. Cegah pengajuan aktif ganda pada objek yang sama. Biaya/kredit belum ditetapkan. Pembahasan berikutnya: Penurunan Rilisan (Takedown).

### Usulan Penurunan Rilisan (Takedown) — 1 Oktober 2026

Status: bahan pembahasan lanjutan, belum izin implementasi atau rilis. Repo lama menangani penurunan seluruh rilisan; penyelesaian tiket mengubah status live menjadi taken_down tanpa kolom hasil distributor yang eksplisit pada layanan penyelesaian. Jangan menyamakan klik selesai dengan bukti penurunan. Kemampuan menurunkan sebagian lagu/target platform perlu verifikasi staf/distributor sebelum ditawarkan; tidak diasumsikan tersedia.

Form usulan: pilih rilisan dan tampilkan identitas, UPC/seluruh ISRC hanya-baca, cakupan jelas seluruh rilisan termasuk semua lagu EP/Album, empat alasan lama dipertahankan (Revisi Metadata, Pindah Aggregator, Konflik Hak Cipta, Konflik Internal), penjelasan wajib dan lampiran opsional. Judul otomatis; ringkasan serta konfirmasi cakupan menyatu sebelum tombol Ajukan Penurunan. Koreksi draft/revisi internal mengikuti alur Rilisan. Permintaan setelah dikirim tetapi belum tayang tetap dapat ditinjau petugas, tanpa menjanjikan distribusi dapat dihentikan sebelum tayang.

Usulan alur: Diajukan → Dalam Penanganan → Menunggu Distributor → Selesai setelah hasil terkonfirmasi; Perlu Tanggapan Label hanya ketika ada kelengkapan tertentu yang diminta. Hasil mencatat waktu/referensi/cakupan konfirmasi dan kendala tersisa. Bila baru sebagian platform terkonfirmasi, tampilkan penurunan dalam proses, jangan menyatakan seluruh rilisan sudah diturunkan. Katalog serta riwayat tidak dihapus dan catatan royalti historis tetap terpisah dari status distribusi. Jangan otomatis mengembalikan kredit atau mencabut Content ID karena tiket takedown selesai; hubungannya perlu verifikasi sebelum kebijakan final.

Celah penting: alasan Revisi Metadata dapat mengarahkan pengguna ke penurunan yang tidak diperlukan. Tawarkan arahan teks menuju Perubahan Metadata tanpa mengganti kategori otomatis, dan pertahankan pilihan takedown jika memang dibutuhkan. Cegah tiket takedown aktif ganda, tandai hubungan dengan perubahan audio/cover/metadata yang masih berjalan, dan minta petugas menyelaraskan permintaan sebelum meneruskan perubahan yang bertentangan. Proses tidak boleh menutup masalah hanya dengan penolakan tanpa penjelasan/langkah yang dapat dilakukan label. Jangan menambahkan tombol pembatalan atau mengesahkan kebijakan pembatalan takedown melalui diskusi ini. Berikutnya: Pengajuan dan Pencabutan Content ID.

### Usulan Content ID — 1 Oktober 2026

Status: lanjutan diskusi, belum izin implementasi atau rilis. Temuan repo: pengajuan saat ini memilih lagu dan pencipta per lagu; nama/NIK/domisili/kota penandatanganan, KTP dan tanda tangan tiap pencipta, persetujuan penggunaan dokumen, serta pembuatan surat telah tersedia. Kedua kategori lama juga mewajibkan link YouTube dan pernyataan originalitas. Ini adalah baseline repo, bukan persyaratan distributor final.

Celah cakupan: Cabut Content ID lama hanya merekam URL tanpa membedakan pelepasan klaim video dengan penonaktifan pencocokan rekaman. Dokumentasi resmi YouTube membedakan release selected claims (https://support.google.com/youtube/answer/106993?hl=en) dan deactivate reference, yang memiliki pilihan mempertahankan atau melepaskan klaim sebelumnya (https://support.google.com/youtube/answer/107012?hl=en). Jangan memigrasikan makna tiket lama atau menyimpulkan cakupannya otomatis.

Usulan formulir satu kelompok Content ID dalam Tiket Bantuan, bukan menu sidebar baru: Ajukan Content ID; Lepaskan Klaim Video; Nonaktifkan Content ID. Pilihan kedua merupakan pengembangan kategori baru, belum disetujui. Pengajuan memilih lagu dengan metadata katalog/ISRC hanya-baca, data pencipta terisi jika tersedia tetapi bisa dikoreksi, peran/hubungan lagu diverifikasi pengguna, dokumen tiap pencipta disusun per orang dan surat dapat dipratinjau sebelum persetujuan/kirim. KTP penanggung jawab tidak otomatis menggantikan KTP pencipta. Dokumen/NIK dibatasi pada pemeriksa berwenang, tidak ditampilkan dalam daftar umum. Data sumber katalog tidak berubah otomatis dari isian surat.

Lepaskan Klaim Video: lagu terkait, link video (lebih dari satu boleh), informasi klaim yang tersedia, alasan wajib/lampiran pendukung; petugas memastikan klaim tersebut dalam cakupan pengelolaan Rilis Musik/distributor, tidak menjanjikan melepas klaim pihak lain. Nonaktifkan Content ID: lagu/cakupan terpilih, alasan wajib, dampak dan perlakuan klaim lama ditinjau petugas; jangan menggantungkan pengajuan ini hanya pada link video atau menyamakan dengan takedown distribusi. Belum membuka pilihan teknis penonaktifan kepada label sebelum kemampuan operasional distributor diverifikasi.

Status pengajuan dan kondisi Content ID lagu terpisah. Hasil dicatat per lagu atau per video; keberhasilan sebagian tidak menutup semua item. Permintaan berlawanan/duplikat aktif diselaraskan petugas. Persetujuan petugas atau dokumen berhasil dibuat bukan bukti Content ID aktif. Penerusan/hasil memerlukan referensi dan waktu yang tercatat.

Pertanyaan staf yang disimpan: tujuan operasional dua kategori lama, persyaratan dokumen/surat termasuk kasus pencipta luar negeri, apakah video wajib pada pengajuan awal, kelayakan rekaman, kemampuan menonaktifkan serta perlakuan klaim lama, bukti hasil dan biaya/benefit. Tidak menetapkan tarif/potongan kredit. Berikutnya menutup celah kategori Rilisan Belum Tersedia yang ditemukan di backend, lalu aturan tindak lanjut/penyelesaian tiket.

### Usulan Laporan Ketersediaan Rilisan — 1 Oktober 2026

Status: dialog dan pencatatan, belum izin implementasi/rilis. Repo lama membuka laporan not_live dari LiveTodayBanner untuk rilisan berstatus live dengan live_at hari ini (WIB); formulir hanya catatan bebas opsional dengan teks generik jika kosong. Hal ini dapat melewatkan kasus yang diketahui setelah hari pertama atau rilisan yang hilang setelah sebelumnya tersedia. Nama/cakupan usulan Masalah Ketersediaan Rilisan adalah pengembangan kategori lama, belum keputusan akhir.

Usulan pintu masuk Detail Rilisan dan Tiket Bantuan ke kasus yang sama, tidak bergantung banner hari pertama. Pilih rilisan, seluruh/sebagian lagu bila relevan, platform terdampak, kondisi belum tersedia atau sebelumnya tersedia lalu tidak ditemukan; tanggal rilis dan identifikasi katalog terisi. Penjelasan singkat wajib, link rilisan/video terkait atau tangkapan layar opsional; tautan tidak diwajibkan saat rilisan justru belum ditemukan. Platform yang belum diketahui diberi pilihan Belum yakin dan memerlukan penjelasan. Tidak mengunci kategori ini hanya pada status live karena laporan dapat terjadi pada rilisan delivered/partial setelah tanggal yang diharapkan.

Sebelum tanggal rilis, tampilkan konteks tanggal dan arahkan pengguna ke perkembangan distribusi bila hanya menanyakan jadwal; tetap izinkan penjelasan anomali seperti tautan hilang. Sesudah tanggal rilis, catat laporan untuk diperiksa tanpa otomatis menyimpulkan distributor gagal. Draft/revisi internal tetap mengikuti proses Rilisan, bukan dilaporkan sebagai gagal tayang. Form menghindari pengajuan aktif duplikat pada objek/platform sama; dampak tambahan dapat ditautkan ke tiket aktif dengan riwayat dan ringkasan cakupan terbaru, tidak menimpa pengajuan awal.

Petugas memeriksa katalog/status pengiriman/platform yang dikeluhkan, meminta kelengkapan bila perlu, dan meneruskan hanya ketika membutuhkan distributor. Toast cukup Laporan terkirim. Tim akan memeriksa ketersediaan rilisanmu., tidak menjanjikan setiap laporan sudah diteruskan ke Believe. Catat hasil per platform/lagu, waktu dan tautan/referensi pemeriksaan jika tersedia. Laporan atau klaim label sendiri tidak mengubah seluruh katalog menjadi gagal/tayang. Jika data memang perlu dikoreksi, melalui tindakan petugas terpisah yang tercatat; penyelesaian memerlukan penjelasan hasil dan item yang belum selesai tetap terbuka.

Atensi berisi tindakan nyata (Label: kelengkapan; Admin: laporan belum ditangani/tindak lanjut jatuh tempo), notifikasi untuk perkembangan biasa; Wawasan tidak menggandakan antrean. Pilihan prioritas/lewat tenggat memakai panduan global dan pemicu yang jelas, bukan semata kode kategori not_live atau semua balasan. Aturan target waktu, eskalasi dan pembukaan kembali dibahas berikutnya tanpa menjanjikan SLA baru.

### Penutupan usulan alur Tiket Bantuan — 1 Oktober 2026

Status: pembahasan dilanjutkan atas permintaan pengguna, belum izin implementasi atau rilis. Usulan status bersama: Diajukan, Dalam Penanganan, Perlu Tanggapan Label, Menunggu Distributor, Selesai. Status menjelaskan proses; penanggung jawab tiket dan pihak yang perlu bertindak merupakan informasi terpisah. Ambil Penanganan mencatat penanggung jawab; perubahan status/catatan tidak boleh otomatis mengambil alih tiket seperti perilaku repo lama. Pengalihan oleh Super Admin dicatat beserta alasan dan penerima, dengan kontrol konflik perubahan.

Tindakan menggantikan dropdown status bebas: Ambil Penanganan; Minta Kelengkapan (pesan spesifik wajib); Teruskan ke Distributor (referensi/waktu); Catat Tindak Lanjut (hasil pemeriksaan, langkah berikutnya); Selesaikan Tiket (hasil/cakupan/waktu, referensi bila relevan). Balasan biasa dan catatan internal tidak mengubah pihak yang ditunggu. Label memberi tanggapan melalui tindakan Kirim Kelengkapan agar kembali ke petugas; pesan chat biasa bukan bukti seluruh kelengkapan selesai. Catatan internal hanya bagi petugas berwenang.

Repo lama memiliki pengingat distributor setelah 3 hari kerja sejak penerusan/pemeriksaan terakhir, dan klik recheck memulai ulang siklus. Usulan mempertahankan angka 3 hari kerja sebagai baseline sementara untuk demo, bukan SLA penyelesaian dan perlu verifikasi staf. Pisahkan usia total tiket dari jadwal tindak lanjut berikutnya; riwayat penerusan awal tidak direset. Mencatat tindak lanjut membutuhkan hasil, bukan hanya klik untuk menghilangkan tenggat. Pembukaan panel, balasan umum, perubahan prioritas dan catatan internal tidak memulai ulang waktu. Kalender operasional/hari libur serta ambang respons internal, pengingat Label, dan eskalasi belum final; jangan mengarang angka baru.

Eskalasi: kasus belum memiliki petugas atau tindak lanjut terlewat masuk pemantauan Super Admin; petugas dapat Eskalasi dengan alasan jika kasus membutuhkan keputusan/koordinasi. Penanda eskalasi terpisah dari status Menunggu Distributor. Jangan menganggap semua laporan not_live otomatis mendesak. Pengingat tidak membuat notifikasi ganda per siklus; atensi menampilkan tindakan dengan sumber tiket yang sama.

Penyelesaian memerlukan ringkasan hasil yang terlihat Label, item lagu/video/platform yang berhasil, serta item tersisa; kasus dengan item belum selesai tetap terbuka. Hindari Selesaikan massal tanpa hasil individual. Kekurangan yang bisa diperbaiki kembali ke Label; kendala yang tidak bisa dipenuhi perlu penjelasan dan alternatif, tidak diganti label selesai palsu. Tidak membiarkan sistem auto-selesai/hapus karena Label lambat merespons.

Pembukaan kembali: Label punya Laporkan Masalah Masih Ada dengan penjelasan, ditautkan ke tiket selesai untuk triase petugas. Kasus lama yang sama dibuka kembali dengan riwayat hasil tetap tersimpan; masalah/perubahan baru dibuat tiket terkait, bukan menimpa hasil lama. Membuka kembali bukan menjalankan ulang tindakan distributor atau membatalkan perubahan katalog secara otomatis. Batas waktu pengajuan ulang tidak ditetapkan pada tahap ini.

Rancangan alur utama telah dibahas sebagai dasar evaluasi implementasi setelah persetujuan pengguna; bukan bukti fitur sudah selesai dibangun. Masih perlu keputusan staf terkait Content ID, biaya/benefit kredit, penurunan parsial, dan target waktu. Tiket historis/identitas lama dipertahankan; status/kategori ambigu tidak diterjemahkan otomatis menjadi hasil baru. Tidak membuka kebijakan yang diparkir atau mengerjakan prototype tanpa perintah implementasi/rilis.

### Rilis prototype V11.2 — 1 Oktober 2026

Pengguna memberi izin: “Silahkan rilis jika tidak ada yang dibahas.” Implementasi Tiket Bantuan selesai di `prototype-v11.2`, menggunakan V11.1 sebagai dasar. Pratinjau LAN tetap pada port 4343; versi dan Studio menampilkan V11.2. Seluruh konsep 3D tetap dibatalkan.

Delapan kategori tersedia: perubahan metadata, penggantian audio/cover, penurunan seluruh rilisan, pengajuan Content ID, pelepasan klaim video, penonaktifan Content ID, dan masalah ketersediaan. Formulir terhubung ke katalog yang berhak diakses, menyimpan sumber saat pengajuan dan menggunakan hasil per lagu/video/platform. Hasil yang dikonfirmasi memperbarui data yang relevan; pengajuan dan balasan biasa tidak mengubah katalog/status/penanggung jawab. Hasil sebagian tetap terbuka. Draft/revisi internal tetap melalui Rilisan.

Label mempunyai draft, tanggapan kelengkapan, laporan berulang dan penambahan dampak pada laporan ketersediaan. Admin mempunyai antrean, penanganan, penerusan, hasil dan tindak lanjut. Super Admin mempunyai pemantauan, pengalihan, eskalasi dan triase kasus berulang. Pengalihan dibatasi petugas dengan akses penanganan. Catatan internal terpisah dari tampilan Label. KTP pencipta dipersiapkan orientasi/batasnya lalu harus ditinjau; dokumen asli disimpan terpisah. Panel kanan, atensi, notifikasi, Pekerjaan Saya, ringkasan dashboard, serta panduan penanda terhubung ke tiket yang sama. Ada 15 kondisi V11.2 di Studio; akun mengikuti kondisi yang dipilih.

Pengamanan: cakupan duplikat dicegah, katalog yang berubah harus ditinjau kembali, penerusan permintaan berlawanan membutuhkan catatan penyelarasan, versi tiket mencegah tindakan dengan data lama, kegagalan penyimpanan memulihkan data, pengingat tidak berulang pada siklus yang sama. Membuka kembali kasus mempertahankan hasil lama dan tidak membatalkan perubahan katalog. Tidak ada penutupan massal, pemotongan kredit baru, atau penutupan otomatis akibat label lambat merespons.

Validasi: 34 pemeriksaan model; alur UI pengajuan–kelengkapan–penerusan–hasil–selesai–laporan ulang; unggahan dan peninjauan dokumen; reset berkas saat lagu berubah; draft setelah reload; catatan internal; tambahan dampak tanpa menimpa sumber; 15 kondisi Studio; panel desktop, iPad dan mobile; berkas HTML mandiri melalui HTTP dan file lokal. Pemeriksaan ini menguji prototype lokal, bukan backend produksi/distributor.

Belum menjadi kebijakan final: persyaratan/surat Content ID, pencipta luar negeri, kelayakan rekaman dan kebutuhan video, perlakuan klaim lama, penurunan parsial, biaya/benefit kredit, target respons dan eskalasi. Pengingat 3 hari kerja tetap baseline sementara, bukan SLA penyelesaian. Migrasi ratusan label dan kasus historis perlu pembahasan khusus sebelum penerapan produksi. Rilis ini tidak memigrasikan atau menafsirkan ulang kasus backend lama.

### Kelanjutan setelah V11.2 — arah pembahasan menu

Pengguna meminta membuka menu baru dan mempertahankan seluruh poin yang diparkir. Ini izin melanjutkan pembahasan, bukan implementasi atau rilis baru. Usulan berikutnya: Transaksi, pusat pembayaran masuk dari pembelian paket, kredit dan layanan tambahan. Referensi lokal memiliki Payments.jsx, Refunds.jsx dan XenditReconciliation.jsx; pengalaman pembelian/pesanan telah tersedia dalam prototype tetapi belum menjadi satu pusat penelusuran transaksi lengkap.

Urutan usulan: daftar/detail transaksi dan dampak pada pesanan atau hak layanan; ketidaksesuaian status pembayaran versus pemenuhan; pengembalian uang sesuai sumber kasus; pencocokan catatan penyedia pembayaran. Usulkan pengelompokan Transaksi, Pengembalian Dana, dan Pencocokan Pembayaran dalam menu yang sama, sesuai akses, sebelum menambah navigasi. Pembayaran royalti tetap menggunakan alur Penarikan/Daftar Pembayaran yang telah dibahas. Pengembalian uang dan pengembalian kredit tetap mempunyai sumber dan riwayat tersendiri. Tidak menetapkan harga atau membuka ulang kebijakan Flex/prorata melalui pembahasan ini.

Parkiran sebelumnya tetap berlaku: klaim/transisi label lama, harga/manfaat/pergantian paket, hadiah historis dan kebijakan pencapaian, fungsi kredit layanan, verifikasi persyaratan WAMI/Content ID, target respons/eskalasi, verifikasi artis, isi Wawasan dan tema musiman. Konsep 3D dan Customize Layout tetap dibatalkan, bukan fitur tertunda. Sesudah Transaksi, evaluasi penyempurnaan Staff & Akses, pengelolaan Sistem/Log Aktivitas, lalu audit alur lintas menu dan persiapan transisi produksi. Urutan ini usulan untuk dialog, bukan keputusan implementasi.

### Persetujuan alur Transaksi — 1 Oktober 2026

Pengguna menyetujui pembahasan daftar/detail dan penanganan kondisi pembayaran. Tetap tahap rancangan; belum izin implementasi atau rilis. Label melihat pembelian sendiri, Admin sesuai akses, Super Admin seluruh transaksi. Daftar: pembelian, label bagi pengelola, tanggal, nominal, status pembayaran, hasil pembelian sesuai jenis. Filter jenis/status/rentang tanggal dan panel kanan berisi identitas transaksi, ringkasan, pembayaran, hasil, riwayat serta tindakan sesuai kondisi. Status pembayaran terpisah dari pemenuhan: layanan masih dikerjakan bukan pembayaran gagal. Masa aktif paket dimulai sesudah aktivasi akun. Transaksi selesai tidak diedit nominalnya atau dihapus; koreksi tercatat terpisah.

Menunggu pembayaran: lanjutkan pembayaran yang sama selama berlaku. Pengguna tetap bisa membandingkan paket; selesai langkah pembayaran, termasuk menunggu konfirmasi, menuju dashboard. Kedaluwarsa dan belum dibayar: pembayaran baru terkait catatan lama dengan ringkasan terkini jika harga/penawaran berubah. Jika pengguna sudah membayar, periksa dahulu sebelum menawarkan pembayaran ulang. Saya sudah membayar hanya memicu pemeriksaan, tidak menandai berhasil. Pemeriksaan belum menemukan pembayaran: ajukan penelusuran dengan data transaksi otomatis; bukti diminta bila diperlukan. Tiket komunikasi terkait sumber transaksi, bukan penanganan ganda.

Pembayaran terkonfirmasi tetapi pemenuhan gagal: atensi Pembelian belum terselesaikan, rincian bagian yang belum dipenuhi dan tindakan berwenang Selesaikan pembelian. Pemeriksaan hasil sebelumnya mencegah pemberian kredit/hak ganda, penyelesaian dicatat. Pembayaran terlambat/ganda ditelusuri sebelum pemenuhan/refund; tidak otomatis memberi dua paket, menggandakan kredit, atau mengabaikan dana karena kedaluwarsa. Kebijakan dana berlebih/pengembalian belum ditetapkan. Berikutnya membahas Pengembalian Dana sebagai usulan baru, tidak mencampur pengembalian kredit atau pembatalan penarikan royalti.

### Lanjutan rancangan Transaksi — Pengembalian Dana, pencocokan dan akses

Pengguna meminta melanjutkan pembahasan. Berikut adalah usulan yang dibahas, bukan pengesahan seluruh kebijakan operasional, izin implementasi, atau rilis. Pengembalian Dana menangani uang pembelian; pengembalian kredit dan pembayaran royalti terpisah. Kasus terkait transaksi asal: pembayaran ganda/terlambat, pembelian tidak terpenuhi, selisih atau alasan lain. Alasan memulai pemeriksaan, tidak otomatis memberi hak refund. Perlihatkan uang diterima/dikembalikan dan hasil pembelian yang sudah diberikan/digunakan. Mendukung nominal penuh/sebagian dengan batas sisa dana; jangan otomatis mencabut kredit atau layanan ketika membuka pemeriksaan. Usulan status Dalam pemeriksaan, Perlu informasi, Siap dikembalikan, Pengembalian diproses, Dana dikembalikan; penutupan tanpa refund membutuhkan alasan penyelesaian. Tandai dana dikembalikan hanya setelah pelaksanaan dengan nominal/waktu/metode/referensi. Jalur asal diutamakan jika tersedia; transfer terpisah memerlukan konfirmasi tujuan, bukan otomatis rekening royalti. Kelayakan refund, perlakuan hasil yang terpakai, waktu, biaya dan kewenangan final belum ditetapkan.

Pencocokan Pembayaran untuk petugas sesuai akses: rentang periode, waktu pemeriksaan terakhir; Sesuai, Perlu diperiksa dan Belum dapat diperiksa. Kegagalan memperoleh data bukan nihil masalah. Jenis perbedaan: pembayaran belum tercatat, status/nominal berbeda, catatan ganda, pembayaran belum dikenali, catatan pengembalian tidak cocok. Cocokkan referensi pembayaran/transaksi, bukan hanya nama dan nominal. Panel dua sumber berdampingan dan riwayat tindakan. Perbarui dari penyedia hanya berdasarkan konfirmasi, dilanjutkan pemeriksaan pemenuhan agar tidak ganda. Jangan memasangkan pembayaran ambigu otomatis. Pemeriksaan massal boleh, penyelesaian dana/hak mengikuti tiap kasus; tidak ada Selesaikan semua tanpa hasil individual.

Usulan akses: Label transaksi sendiri dan permintaan pemeriksaan; Admin berwenang pemeriksaan, sinkronisasi dari konfirmasi, pemenuhan dan usulan refund; Super Admin persetujuan refund, pencatatan manual dan pengalihan. Akses lihat/tindakan dipisahkan; tidak ada tombol status Berhasil bebas. Satu kasus memiliki penanggung jawab; membuka panel tidak mengambil alih. Tiket Bantuan untuk komunikasi ditautkan, bukan pekerjaan penyelesaian ganda. Atensi untuk informasi yang wajib dilengkapi, pembelian belum terpenuhi, perbedaan belum ditangani, persetujuan atau pelaksanaan refund yang tertunda. Menunggu bayar biasa cukup daftar transaksi. Mustard untuk pemeriksaan tertunda, merah untuk kegagalan/risiko nyata. Notifikasi untuk perkembangan; pemeriksaan ulang tanpa perubahan tidak mengirim ulang. Wawasan pola transaksi, tidak menggandakan antrean kasus.

### Usulan rincian hasil pembelian per jenis

Paket: simpan ringkasan harga/durasi/benefit saat transaksi, status pemenuhan, awal/akhir masa aktif dan transaksi terkait; menunggu aktivasi tidak ditampilkan paket aktif, waktu paket mulai setelah aktivasi, pemeriksaan ulang tidak mereset durasi. Kredit: jumlah dibeli versus jumlah benar-benar ditambahkan dan tautan riwayat; saldo tersedia terkini terpisah dari hasil transaksi lama, tidak menganggap saldo berkurang sebagai gagal pemenuhan. Layanan: nama/cakupan/satuan/jumlah dan sumber pembayaran atau benefit yang digunakan, tautan permintaan serta proses layanan terpisah dari status pembayaran; tidak otomatis memotong kredit layanan yang belum disepakati. Semua ringkasan terkait pesanan asal; pemberian sebagian dicatat per bagian, tanpa memberi ulang bagian selesai. Harga/Flex/prorata/kredit layanan/kelayakan refund tetap diparkir. Seluruh bagian ini masih rancangan diskusi.

### Rilis prototype V11.3 — 1 Oktober 2026

Pengguna memberikan izin eksplisit “RILIS!”. Pembahasan Transaksi diterapkan dalam satu rilis lengkap: Transaksi, Pengembalian Dana, dan Pencocokan Pembayaran berada di satu menu, sesuai akses Label, Admin dan Super Admin. Pembelian paket, kredit, layanan tambahan dan WAMI ditautkan ke pesanan asal. Ringkasan harga, metode pembayaran dan hasil pembelian dipertahankan; status pembayaran dibedakan dari pemenuhan. Paket menunggu aktivasi belum mulai masa aktif. Riwayat percobaan pembayaran, penanganan kasus, permintaan informasi dan pengembalian dana dapat ditelusuri. Panel kanan mengikuti susunan informasi bersama.

Pengamanan prototype: konfirmasi pembayaran harus sesuai referensi, percobaan, nominal dan mata uang; pemeriksaan tanpa data tidak mengubah status menjadi berhasil. Pemenuhan tidak memberi hak/kredit dua kali. Persetujuan pengembalian dana dibatasi Super Admin dan sisa dana diterima; transfer terpisah membutuhkan konfirmasi rekening oleh Label. Pengembalian tidak otomatis mencabut hak yang sudah diberikan. Tindakan menggunakan versi data terbaru, penanggung jawab kasus dan pemulihan saat penyimpanan gagal. Seluruh pembayaran dan catatan penyedia tetap simulasi lokal, bukan transaksi bank atau integrasi backend produksi.

Validasi: 32 pemeriksaan model, 14 kondisi Studio dengan akun otomatis, alur pengembalian dana lengkap, pembelian dari menu asal, keterkaitan layanan, kegagalan penyimpanan, dan regresi kondisi versi sebelumnya. Daftar serta panel diuji pada desktop, iPad dan ponsel; berkas HTML mandiri diuji melalui HTTP dan file lokal. Pratinjau utama menggunakan V11.3; hasil verifikasi disimpan di prototype-v11.3/qa/release-verification.json.

Parkiran tetap dipertahankan: kelayakan pengembalian dana, perlakuan kredit/benefit yang terpakai, harga/prorata/Flex, kredit layanan, waktu penanganan serta transisi ratusan label lama belum menjadi kebijakan final. Konsep 3D dan Customize Layout tetap dibatalkan. Usulan pembahasan berikutnya Staff & Akses; belum diimplementasikan melalui rilis ini.

### Rilis prototype V11.4 — 1 Oktober 2026

Pengguna memberikan izin eksplisit “Eksekusi dengan baik!” setelah pembahasan Staff & Akses. Satu menu Staff & Akses berada di ruang Staff, dengan tab Daftar Staff dan Peran & Izin. Undangan, aktivasi simulasi, kirim ulang, pencabutan, email yang telah terdaftar, status akun, peran dan cakupan data berada dalam alur yang terhubung. Pengaturan lama dipetakan sebagai baseline; tidak ada pemindahan akun atau pemberian kewenangan keuangan khusus secara otomatis. Pengelolaan akun dan peran khusus Super Admin. Undangan tidak mengirim email dan aktivasi tidak menyimpan kata sandi.

Izin per tindakan disertai ketergantungan melihat daftar/detail, cakupan seluruh label atau label tertentu, serta izin dokumen identitas dan rekening lengkap terpisah. Daftar, pencarian, laporan, panel dan tindakan mengikuti sumber izin yang sama. Tinjauan sebelum menyimpan menunjukkan perubahan, staff terdampak dan pekerjaan yang membutuhkan pengalihan. Perubahan peran bersama berlaku pada semua penggunanya. Panel yang sudah terbuka tetap memeriksa kewenangan terbaru saat tindakan dilakukan. Pratinjau akses hanya untuk melihat dan tidak menjalankan operasi. Perubahan bersamaan ditolak untuk ditinjau ulang; kegagalan penyimpanan memulihkan data sebelumnya.

Penonaktifan biasa membutuhkan keputusan pekerjaan; penghentian mendesak memutus akses dan memasukkan pekerjaan terbuka ke Perlu pengalihan. Pengganti harus memiliki izin tindakan dan cakupan yang sesuai, termasuk izin sesudah perubahan peran bersama. Pengalihan hanya mengubah penanggung jawab, mempertahankan tahap, tenggat, riwayat dan hasil transaksi. Pekerjaan selesai tidak dibuka kembali. Aktivasi kembali meninjau peran/cakupan dan tidak mengembalikan pekerjaan atau izin sementara lama. Peran yang masih digunakan akun aktif, undangan atau akun nonaktif tidak bisa diarsipkan. Riwayat akses dan pemberitahuan staff tersedia; izin baru memerlukan tinjauan tanpa pemberian otomatis.

Validasi: 28 pemeriksaan model, 12 kondisi Studio Pratinjau dengan akun otomatis, alur undangan/aktivasi, perubahan peran, pengalihan biasa/mendesak, aktivasi kembali, pratinjau, versi data, pemulihan penyimpanan serta pembatasan dokumen dan rekening. Regresi versi sebelumnya mencakup transaksi yang memberikan kredit tepat satu kali dan tindakan pada panel setelah izin dicabut. Daftar dan panel diperiksa pada light/dark, desktop, tablet dan ponsel. HTML mandiri diuji melalui HTTP dan file lokal. Bukti pengujian dan verifikasi tautan utama disimpan di prototype-v11.4/qa.

Seluruh aturan masih prototype lokal, belum menggantikan autentikasi dan otorisasi backend produksi. Kebijakan masa berlaku undangan, keamanan sesi produksi, transisi ratusan label lama, klaim label bersama tim, harga/Flex/prorata, kredit layanan dan hadiah pencapaian historis tetap diparkir. Absensi dan payroll tidak dirancang ulang pada rilis ini. Konsep 3D dan Customize Layout tetap dibatalkan. Pembahasan berikutnya yang diusulkan: Sistem & Riwayat Aktivitas, setelah pengguna mengevaluasi Staff & Akses.

### Rilis prototype V11.5 — 1 Oktober 2026

Pengguna memberikan izin eksplisit “RILIS!” setelah pembahasan Sistem. Satu menu Sistem khusus Super Admin memuat Konten Website, Navigasi, Prosedur & Pengingat, serta Riwayat Aktivitas. Tidak menambah menu konfigurasi yang menggandakan sumber paket, kredit, kontrak atau izin Staff. Panel kanan menggunakan hierarki ringkasan, informasi, perubahan dan tindakan yang konsisten.

Konten mempunyai draf terpisah dari versi terbit, pratinjau website desktop/mobile, publikasi bagian terpilih dan riwayat versi. Pemulihan menghasilkan draf untuk ditinjau, bukan langsung mengganti versi aktif. Identitas perusahaan terpisah dari konten pemasaran; transaksi baru menyimpan identitas penerbit saat dibuat, tanpa menulis ulang dokumen lama. Pratinjau website terbit dan draf dapat dibandingkan secara lokal; tidak menerbitkan landing page produksi.

Navigasi mengatur nama Indonesia/Inggris, ikon yang tersedia, urutan, kelompok dan submenu menurut akun/ruang. Pratinjau Admin mengikuti izin Staff & Akses. Pengaturan tidak membuka akses atau menciptakan fitur baru; menu utama yang dilindungi tetap tersedia. Susunan terbit digunakan setelah reload, sehingga formulir aktif tidak berpindah saat konfigurasi disimpan. Pencarian serta judul menu menggunakan nama yang berlaku.

Prosedur menyimpan aturan dan kalender pada setiap tahap pekerjaan. Aturan baru secara biasa digunakan pada tahap baru; pekerjaan berjalan mempertahankan acuannya. Penerapan ke pekerjaan berjalan membutuhkan tinjauan perubahan tanggal dan konfirmasi; perubahan keadaan pekerjaan selama tinjauan harus ditinjau ulang. Catatan biasa tidak memulai ulang waktu. Baseline WAMI, tiket, layanan, revisi dan pengingat lama dipertahankan untuk evaluasi staf; periode pencairan 15–20 tidak diubah. Pengaturan ini tidak mengubah kredit, pembayaran atau hasil pekerjaan dengan sendirinya. Absensi dan payroll tetap memakai alur tersendiri.

Riwayat Aktivitas menggabungkan kejadian lintas menu dengan filter, rincian perubahan, alasan, sumber dan urutan aktivitas. Riwayat tidak memiliki tindakan edit/hapus. Identitas pelaku/waktu historis yang tidak tersedia ditandai, tidak dikarang. Kata sandi, token, NIK, nomor rekening dan isi dokumen tidak dimasukkan ke rincian log umum. Pembukaan dokumen melalui pemeriksa berwenang mencatat referensi akses tanpa salinan gambar. Draf, penerapan dan tindakan memeriksa versi data serta memulihkan keadaan saat penyimpanan gagal. Pratinjau akses bersifat hanya-baca.

Validasi: 36 pemeriksaan model, 14 kondisi Studio dengan akun otomatis, alur draf/publikasi/pemulihan, perubahan bersamaan, kegagalan penyimpanan, penerapan navigasi setelah reload, aturan tahap baru versus pekerjaan berjalan, penolakan tinjauan dampak kedaluwarsa dan perlindungan riwayat sensitif. Ada 14 pemeriksaan regresi versi terdahulu dan 8 integrasi tambahan. Tampilan light/dark, desktop, iPad dan ponsel serta HTML mandiri melalui HTTP dan file lokal lulus. Bukti tautan utama dan kecocokan HTML rilis dicatat di prototype-v11.5/qa/release-verification.json.

Rilis ini tetap prototype lokal, belum menggantikan backend produksi, penyimpanan audit permanen atau integrasi penyedia. Parkiran harga/Flex/prorata, benefit paket, kredit layanan untuk diverifikasi staf, kelayakan refund, hadiah historis Gold I–Diamond III, verifikasi artis, isi Wawasan per akun, masa berlaku undangan, klaim label lama bersama tim dan migrasi ratusan label tetap dipertahankan. Kalender/target respons masih baseline, bukan SLA final. Pembahasan transisi yang seimbang bagi label lama dan Rilis Musik wajib dilakukan sebelum penerapan produksi. Konsep 3D dan Customize Layout tetap dibatalkan.

## Pemetaan kesiapan penerapan setelah V12.0

Pada 3 Oktober 2026 pengguna menyetujui penyusunan daftar kesiapan per menu, bukti integrasi dan keputusan tim. V12.0 telah terbit atas instruksi pengguna sebelumnya; lingkup tahap ini adalah analisis kesiapan. Laporan berada di [Kesiapan penerapan Rilis Musik](C:/Users/rotam/.codex/.chatgpt-projects/g-p-6aad702d98fc8191a1f5a7db0fc5a835/production-readiness-v12.0-2026-10-03/KESIAPAN-PRODUKSI-V12.0.md), dengan sumber dan pemeriksaan keterlacakan pada direktori yang sama.

Pemetaan mencakup 24 nama menu bawaan V12.0 dan 9 kemampuan lintas menu. Status utama: 2 siap sebagai rancangan, 19 membutuhkan integrasi, dan 3 membutuhkan keputusan tim. Siap sebagai rancangan tetap membutuhkan porting/pengujian frontend terintegrasi. Belum ada menu dinyatakan siap produksi berdasarkan pemeriksaan ini. Seluruh kebutuhan keputusan disimpan sebagai 13 topik dengan batas bagian yang dipengaruhi.

Perbedaan terkonfirmasi pada salinan repo: registrasi mewajibkan MDA sebelum eksplorasi; checkout memerlukan verifikasi lengkap; pembayaran langsung memulai paket tahunan; checklist lama meminta alamat lengkap dan rekening sebelum unggah KTP; model profil belum menerima Lokasi terstruktur/email identitas; bank di luar inventaris ditolak; minimum penarikan memakai lebih dari Rp1 juta; pengajuan gabungan masih mempunyai child withdrawal; tanggal rilisan minimal tujuh hari tanpa pembedaan layanan; refund berfokus pada rilisan ditolak/dihapus; dan konten CMS langsung dipublikasikan. Semua membutuhkan pemetaan terhadap keputusan V12.0 sebelum penerapan. Rincian alokasi/riwayat per label dapat dipertahankan internal tanpa mengembalikan pengajuan terpisah kepada pengguna.

Repo juga memiliki role artist dan rute Dashboard Artis yang tidak termasuk navigasi bawaan V12.0. Kelanjutan aksesnya perlu disepakati sebelum mengganti router/auth lama; ini berbeda dari tipe label independent_artist maupun kebijakan centang artis. Prototipe tema otomatis masih memakai jam lokal browser; acuannya perlu diperiksa saat porting. Bootstrap server repo menjalankan normalisasi bank, sehingga lingkungan integrasi harus diisolasi sebelum server mulai. Pemeriksaan ini tidak menjalankan bootstrap atau mengakses database produksi.

Langkah berikutnya yang disarankan: pembahasan perlindungan hak label lama dan batas cakupan penerapan; konfirmasi repo/deployment terkini; lingkungan uji terisolasi; sumber server untuk identitas, akses dan keuangan; porting menu; kemudian simulasi transisi dan uji penerimaan. Hak paket lama, saldo, kontrak, kredit, hadiah historis, rekening dan pekerjaan berjalan harus dapat dibandingkan sebelum/sesudah. Harga, masukan staf, kebijakan klaim dan parkiran terdahulu tetap menunggu pembahasan pada lingkup yang relevan.

## Pembaruan arah pembayaran dan paket

Pada 3 Oktober 2026 pengguna menetapkan rupiah sebagai standar seluruh transaksi, dengan kredit sebagai opsi pembayaran yang selalu lebih murah. Nilai dan tarif belum ditetapkan; kewajiban memakai kredit untuk seluruh pembayaran rilisan digantikan oleh pilihan rupiah atau kredit. Pengguna meminta pengelolaan perpindahan paket mengacu pada ChatGPT serta memastikan manfaat semua label lama mempunyai tanggal berakhir yang jelas. Ini arahan rancangan untuk disimpan; belum izin pengembangan atau rilis.

Keputusan dan usulan adaptasi disimpan dalam [Pembahasan paket dan pembayaran](C:/Users/rotam/.codex/.chatgpt-projects/g-p-6aad702d98fc8191a1f5a7db0fc5a835/analysis-v10/PACKAGE-DECISIONS.md). Usulan: naik paket setelah pembayaran dengan selisih sisa periode; turun paket dan perubahan bulanan/tahunan pada periode berikutnya; manfaat paket lama tetap sampai akhir masa yang dibayar. Formula, cakupan kredit untuk membeli paket, dan dampak perpindahan Business ke satu label masih perlu dibahas. Tidak mengesahkan pembayaran berulang, penukaran royalti, refund otomatis dalam kredit atau hadiah historis.

## Masa pembaruan Lokasi label lama

Pada 4 Oktober 2026 pengguna menyetujui masa pembaruan Lokasi selama 30 hari sejak label pertama kali masuk setelah penerapan sistem baru. Jika belum selesai setelah tenggat, kasus masuk tindak lanjut Super Admin agar label dapat dibantu. Tenggat ini tidak otomatis menonaktifkan akun atau mewajibkan aktivasi ulang. Kelengkapan data Lokasi dipisahkan dari status operasional label.

Data lama yang tersedia tetap menjadi acuan, dan permintaan pembaruan hanya menyasar kolom yang belum lengkap. Penyesuaian dilakukan pada Identitas Label serta menu Penyesuaian Data Label yang sudah dirancang, tanpa membuat menu baru. Sesuai keputusan sebelumnya, alamat lengkap lama baru menghilang dari formulir aktif setelah seluruh wilayah wajib valid dan berhasil disimpan; sumber aslinya tetap dapat ditelusuri.

Masa 30 hari ini khusus pembaruan Lokasi. Penanganan KTP hilang/tidak terbaca, bukti pemeriksaan sebelumnya, tenggat dokumen sensitif dan dampak terhadap tindakan terkait masih memerlukan pembahasan. Persetujuan ini mencatat kebijakan rancangan; belum perintah implementasi atau rilis.

### Dasar pemeriksaan KTP label lama

Pada 4 Oktober 2026 pengguna menjelaskan bahwa KTP merupakan syarat beroperasi, sehingga menurut pemahamannya tidak ada label aktif yang KTP penanggung jawabnya belum diperiksa. Dasar rancangan transisi adalah mengakui pemeriksaan identitas label aktif lama. Pernyataan tersebut belum merupakan hasil inventaris data produksi; saat migrasi cocokkan dengan status dan bukti yang tersedia, tanpa mengarang tanggal, petugas atau hasil pemeriksaan yang tidak tercatat.

KTP lama yang valid dan terbaca digunakan kembali sesuai keputusan sebelumnya. Kekurangan arsip pada akun yang mempunyai bukti pemeriksaan ditangani sebagai pemulihan dokumen, bukan otomatis mengubahnya menjadi akun baru atau meminta aktivasi ulang. Kasus yang tidak cocok dengan catatan sistem masuk pemeriksaan khusus, bukan alasan mengulang pemeriksaan semua label aktif. Tenggat pemulihan dokumen dan dampak terhadap tindakan sensitif tetap perlu ditetapkan.

Usulan lanjutan: pergantian penanggung jawab atau dokumen identitas yang substantif mengikuti alur pemeriksaan perubahan identitas. Koreksi format, penyesuaian orientasi/cropping dan pemulihan salinan KTP penanggung jawab yang sama tidak otomatis dianggap pergantian penanggung jawab. Usulan ini tidak menyetujui perubahan identitas/rekening secara otomatis atau mengubah izin akses dokumen.

## Perlakuan kontrak label lama

Pada 4 Oktober 2026 pengguna menyetujui bahwa kontrak lama yang masih berlaku tetap digunakan sampai berakhir. Persetujuan atas ketentuan baru diminta saat perpanjangan, atau ketika perpindahan paket memang mengubah ketentuan kerja sama. Perubahan isi kontrak diperiksa bersama tim sebelum diterapkan; pembaruan UI tidak otomatis mewajibkan penandatanganan ulang.

Catatan penerapan: pertahankan versi dokumen serta bukti persetujuan sebelumnya, dan kaitkan persetujuan baru dengan ketentuan yang benar-benar ditawarkan. Harga serta perubahan manfaat paket tetap mengikuti pembahasan tersendiri. Keputusan ini merupakan kebijakan rancangan, belum izin mengubah kontrak produksi atau menerbitkan prototipe.

## Peralihan saldo royalti dan penarikan

Pada 4 Oktober 2026 pengguna menyetujui kebijakan peralihan pencatatan saldo dan penarikan: pertahankan pendapatan yang belum tersedia, saldo tersedia, nominal dalam penarikan dan pembayaran yang telah selesai sebagai catatan terpisah. Pendapatan yang sudah dibayarkan tidak kembali menjadi saldo tersedia ketika laporan lama diimpor. Penarikan berjalan diteruskan menggunakan nominal, cakupan periode dan rekening tujuan yang tercatat pada pengajuannya; perubahan profil tidak otomatis mengganti tujuan pembayaran tersebut.

Saldo yang sudah diajukan tetap dicatat dalam penarikan, sedangkan pendapatan baru setelah pengajuan mengikuti catatan sumbernya sendiri. Penggabungan tampilan master tidak menghapus alokasi/riwayat anak label atau mengubah kepemilikan pendapatan historis. Satu pengajuan saldo gabungan dan ambang inklusif Rp1 juta tetap mengikuti keputusan sebelumnya.

Pada 4 Oktober 2026 pengguna menjelaskan bahwa belum ada pencairan/pembayaran royalti baru, tetapi beberapa label sudah mengajukan permintaan dan menunggu jadwal pembayaran 15–20 Oktober 2026. Informasi ini menggambarkan siklus pembayaran yang sedang berjalan, bukan menyatakan tidak pernah ada pembayaran historis. Status dan kelengkapan catatan produksi tetap perlu dicocokkan sebelum menetapkan saldo awal.

Pengajuan Oktober yang berjalan diselesaikan melalui sistem lama. Status dibayarkan hanya diberikan setelah pembayaran terkonfirmasi. Sebelum peralihan, cocokkan saldo tersedia, nominal dalam penarikan dan hasil pembayaran. Satu pengajuan hanya boleh diproses pembayarannya melalui satu sistem. Tanggal 20 Oktober tidak otomatis mengubah pengajuan tertunda menjadi dibayarkan; kasus yang dibawa ke sistem baru tetap mempertahankan nominal, periode, rekening tujuan, status, alasan serta referensi pengajuan aslinya, tanpa meminta label mengajukan ulang.

Peralihan pencatatan keuangan dilakukan di antara siklus pembayaran, setelah pencocokan selesai dan sistem baru siap. Persetujuan ini menetapkan kebijakan rancangan, bukan tanggal penerapan produksi atau izin menjalankan pembayaran.

## Arah pemantauan keuangan label

Pada 4 Oktober 2026 pengguna memarkir kembali pembahasan emblem dan hadiah historis. Tidak ada persetujuan atas angka hadiah transisi. Fokus dialog beralih pada kebutuhan monitor terperinci untuk membaca pergerakan, pertumbuhan serta celah sensitif keuangan label, terpisah dari pengelolaan pekerjaan. Contoh yang diminta: label lama tidak beraktivitas tetapi masih menghasilkan royalti, serta penanda perkembangan pendapatan label aktif. Penamaan, indikator dan susunan menu masih dibahas; belum izin implementasi atau rilis.

Temuan pada salinan repo: admin_get_label dalam backend/routes/admin.py sudah menyediakan ringkasan royalti historis, pembayaran, saldo tersedia, dana menunggu serta nominal dalam penarikan. Royalty.py menyediakan rincian periode, platform, negara dan lagu, tetapi sebagian ringkasan khusus label hanya memasukkan status pending/available serta mengecualikan royalti historis yang telah diselesaikan. Ringkasan tersebut tidak dapat langsung dijadikan riwayat pertumbuhan lengkap. Prototipe V12.0 sudah memiliki Pemantauan Royalti dengan saldo, aktivitas dan tab kredit/pencapaian/bonus; belum membuktikan pemantauan pertumbuhan terintegrasi ke produksi. Kategori aktivitas prototipe memakai satu tanggal terakhir dan batas 90 hari/satu tahun; ini perlu ditinjau agar tidak mencampur kegiatan label, status akses dan aktivitas menghasilkan royalti.

Usulan asisten yang belum disetujui: kembangkan Pemantauan Royalti menjadi pusat Pemantauan Keuangan Label, menggunakan satu tujuan navigasi yang ada. Baca empat dimensi secara terpisah: aktivitas pengajuan/katalog; pendapatan per periode dan sumbernya; posisi saldo/penarikan/pembayaran; serta temuan yang mempunyai alasan dan bukti. Rincian per label dapat membuka panel kanan, sedangkan tindakan transaksi tetap menuju alur Penarikan, Transaksi atau Penyesuaian Data yang berwenang. Untuk tahap awal, usulkan akses penuh pada Super Admin; akses Admin mengikuti pembahasan kewenangan tersendiri.

Prinsip usulan: label tanpa rilisan baru tetapi tetap menghasilkan tidak otomatis bermasalah atau berhenti beroperasi. Bedakan pengajuan terakhir, login terakhir, periode terakhir menghasilkan, serta status paket/akses. Pertumbuhan memakai pendapatan pada periode laporan yang sebanding, bukan nominal penarikan atau saldo tersisa. Pendapatan yang telah dibayarkan tetap masuk analisis historis; pembayaran tidak menurunkan angka pendapatan periode asalnya. Data yang belum lengkap tidak diperlakukan sebagai nol atau penurunan. Pengguna kemudian mengoreksi bahwa penanda pendapatan yang dimaksud adalah emblem, sehingga usulan rentang nominal sebagai pengganti penanda tidak dilanjutkan. Nominal tinggi dan kenaikan besar tidak otomatis berarti sehat atau mencurigakan. Koreksi, kurs dan perubahan bagian royalti perlu terlihat sebagai konteks.

Usulan lanjutan: pisahkan hak royalti label dari bagian pendapatan Rilis Musik, serta kredit tersedia dari nominal uang; nilai kredit belum final. Pada master, pendapatan anak label dapat ditelusuri tanpa menggandakan total atau mengembalikan pengajuan terpisah. Temuan monitor merupakan petunjuk untuk ditinjau, bukan pembuktian pelanggaran atau perintah otomatis menahan dana, membatasi akses maupun mengirim bonus. Wawasan merangkum perkembangan menarik dan mengarah ke sumber monitor; Atensi hanya muncul jika terdapat kebutuhan tindakan yang jelas. Ambang tidak aktif, pertumbuhan, konsentrasi pendapatan, usia saldo dan eskalasi tetap belum ditetapkan.

### Fokus dana royalti yang belum ditarik

Koreksi pengguna pada 4 Oktober 2026: fokus utama adalah memantau dana royalti yang belum/tidak ditarik, termasuk label yang tidak lagi beraktivitas tetapi tetap menghasilkan. Pengguna ingin melihat data nyata mengenai manfaat keberadaan dana tersebut bagi perusahaan. Analisis label yang sering merilis tetapi pendapatannya menurun boleh dikembangkan pada tabel tersendiri. Penanda pendapatan yang dimaksud pengguna adalah konsep emblem. Pembahasan hadiah/ambang emblem tetap diparkir, tanpa mengesahkan angka atau mengubah dasar pencapaian.

Peninjauan tabel prototipe di luar repo bawaan: Manajemen Label memuat identitas, paket, pencapaian, akses, aktivitas dan aktivasi; Pemantauan Royalti memuat liabilitas operasional/nonoperasional, aktivitas terakhir, periode laporan, royalti periode, saldo belum dibayar, diproses, ditahan, tersedia dan pembayaran terakhir; Pencapaian memuat emblem, akumulasi royalti dibayarkan, kredit tersedia serta daftar kenaikan; Kredit dan Bonus memuat saldo tersedia, sumber kredit, kedaluwarsa serta riwayat pemberian/klaim. Pengembangan monitor harus bertolak dari tabel tersebut. Pemantauan Dana, Pencapaian dan Perkembangan Katalog mempunyai tabel/fokus terpisah, bukan disatukan menjadi penilaian kesehatan umum.

Usulan asisten yang belum disetujui: kembangkan tabel royalti dengan saldo tersedia yang belum diajukan, usia saldo per bagian dana, belum pernah menarik/pernah menarik, kondisi kelayakan pencairan dan pertambahan royalti ketika label tidak beraktivitas. Ringkasan dapat memperlihatkan dana yang telah diterima tetapi belum dibayarkan, bagian yang sudah diajukan dan yang belum diajukan, pengelompokan umur saldo, serta perubahan saldo awal + tambahan/koreksi - pembayaran = saldo akhir. Total tidak menggandakan anak label dan master. Umur dana dihitung sejak bagian royalti bersangkutan benar-benar tersedia, bukan hanya dari login/pengajuan/pembayaran terakhir; tanggal historis yang tidak tersedia ditandai belum diketahui. Alasan tidak menarik yang belum diketahui tidak dikarang menjadi keputusan sengaja membiarkan dana.

Celah penting: royalti tercatat/belum tersedia dapat belum diterima perusahaan, sehingga tidak seluruh saldo belum dibayar merupakan kas yang mengendap. Kas aktual serta pencocokan dana distributor/bank dibutuhkan sebelum menyebut manfaat arus kas nyata atau kecukupan dana pembayaran. Umur kas sejak penerimaan perusahaan dan umur saldo sejak tersedia untuk penarikan adalah dua acuan berbeda. Usulan simulasi kebutuhan kas memakai bagian saldo yang berhak ditarik serta pengajuan berjalan, bukan memprediksi bahwa label tidak akan menarik. Lamanya tidak menarik tidak menetapkan hak tersebut menjadi pendapatan permanen perusahaan. Acuan umum penghapusan kewajiban keuangan hanya ketika kewajiban berakhir terdapat pada [IFRS 9 paragraf 3.3.1 dalam lampiran dokumen IASB](https://www.ifrs.org/content/dam/ifrs/meetings/2024/september/iasb/ap11-project-commencement.pdf#page=19); penerapan akuntansi/hukum/kontrak khusus Rilis Musik belum ditetapkan melalui dialog ini. Monitor yang diusulkan bersifat pengamatan, tanpa mengubah hak label atau menghambat penarikan.

Dasar emblem prototipe saat ini adalah akumulasi royalti dibayarkan. Akibatnya label berpendapatan besar yang belum pernah menarik dapat belum mempunyai emblem sesuai besarnya royalti tercatat. Catat sebagai persoalan definisi pencapaian untuk dibahas saat topik dibuka kembali; jangan mengganti dasar, menerbitkan hadiah, atau mencampur pendapatan tercatat dengan pembayaran tanpa keputusan pengguna. Tidak ada perubahan kode maupun rilis pada pembahasan monitor ini.

### Usulan susunan tabel pemantauan dana

Pada 5 Oktober 2026 pengguna meminta melanjutkan pembahasan. Detail berikut merupakan usulan untuk ditinjau, bukan persetujuan implementasi atau rilis. Fokusnya tab Pemantauan Dana dalam wadah pemantauan yang ada. Pencapaian tetap tabel tersendiri; perkembangan katalog/penurunan pendapatan ditempatkan pada tabel lain. Usulan tampilan awal memuat semua label, diurutkan menurut saldo tersedia belum diajukan terbesar, dengan filter untuk label yang lama tidak beraktivitas.

Usulan empat ringkasan: hak royalti yang dananya telah diterima tetapi belum dibayarkan; saldo tersedia belum diajukan; nominal dalam pengajuan berjalan; serta bagian saldo tersedia belum diajukan yang berumur lebih dari 365 hari. Ringkasan kedua sampai keempat adalah bagian dari yang pertama dan tidak dijumlahkan lagi. Royalti yang belum diterima terlihat terpisah. Dana telah diterima dan belum dibayarkan merupakan catatan kewajiban terkait penerimaan, bukan bukti bahwa jumlah yang sama masih utuh di rekening saat ini; saldo bank aktual memerlukan pencocokan tersendiri.

Usulan kolom utama: Label (dengan konteks aktivitas terakhir yang relevan dan pengelola); Tersedia belum diajukan; Bagian lebih dari satu tahun; Royalti laporan terakhir (beserta periode); Pembayaran terakhir; Kondisi pencairan; serta tombol detail. Jumlah royalti periode adalah arus pendapatan, sedangkan saldo adalah posisi dana; keduanya tidak dijumlahkan. Dana dalam pengajuan terlihat pada ringkasan/detail dan tidak tercampur ke nominal belum diajukan. Besar bagian saldo lama harus terlihat, sehingga satu saldo kecil yang tua tidak memberi kesan seluruh saldo sudah mengendap lama.

Usulan filter: semua label; memenuhi syarat pengajuan tetapi belum diajukan; belum pernah menerima pembayaran (hanya jika riwayat lengkap); lama tidak beraktivitas tetapi masih menghasilkan; dan memiliki saldo tersedia belum diajukan berumur lebih dari satu tahun. Filter dapat beririsan; hitung total dari label/dana unik pada hasil, bukan menjumlahkan jumlah atau nominal tiap filter. Pilihan urutan dapat berdasarkan nominal tersedia, nominal saldo lama atau pembayaran terakhir.

Usulan rincian panel kanan: ringkasan label dan penerima pencairan; pembagian saldo; umur saldo menurut rentang 0–90, 91–180, 181–365 dan lebih dari 365 hari; riwayat penerimaan, ketersediaan, pengajuan serta pembayaran; lalu kondisi pencairan dan catatan dengan sumber/waktu. Tanggal yang tidak tersedia diberi kelompok belum diketahui. Tidak memakai tanggal impor, login atau periode penghasilan sebagai pengganti tanggal ketersediaan. Label lama tanpa riwayat lengkap diberi keterangan belum ada pembayaran tercatat, bukan langsung dinyatakan tidak pernah menarik. Catatan mengenai alasan tidak mengajukan harus bersumber dari fakta/tanggapan yang tercatat.

Kondisi pencairan memakai aturan dan bukti yang berlaku: misalnya belum mencapai minimum, dapat diajukan, pengajuan sedang berjalan, atau data penerima memerlukan tindak lanjut. Status ini tidak otomatis menahan dana dan tidak disimpulkan dari label lama tidak beraktivitas. Pada multi-label, nominal setiap label asal dapat ditelusuri, sedangkan minimum inklusif Rp1 juta, kelayakan dan pengajuan mengikuti saldo gabungan master. Ringkasan master tidak dihitung lagi sebagai royalti tambahan; tidak mengembalikan pengajuan per anak label.

Temuan sumber tambahan: backend/routes/balance_utils.py mengurangi nominal pengajuan requested/approved dari sumber saldo tersedia, dan backend/routes/royalty.py mencatat dana_received_at pada proses konfirmasi penerimaan. Kolom tersebut belum membuktikan tanggal penerimaan bank aktual ataupun umur semua saldo historis. Integrasi perlu mencocokkan sumber, membedakan kas aktual/kewajiban, dan menjelaskan waktu pembaruan monitor. Simulasi kebutuhan pembayaran tetap usulan pengembangan setelah dasar data nyata dapat dicocokkan; belum menetapkan prediksi perilaku label atau keuntungan permanen.

### Usulan penanda dan tindak lanjut pemantauan dana

Pada 5 Oktober 2026 pengguna meminta meneruskan pembahasan. Topik berikutnya yang diusulkan adalah penempatan informasi dan kebutuhan tindakan dalam monitor. Detail berikut belum disetujui dan tidak mengubah prototipe.

Usulan informasi pada tabel/filter: saldo tersedia belum diajukan, bagian saldo berumur lama, serta label lama tidak beraktivitas yang masih menghasilkan. Kondisi tersebut sendiri tidak menandakan pelanggaran atau memerlukan Atensi mendesak. Status belum pernah menerima pembayaran hanya digunakan jika riwayat lengkap. Data lama yang belum lengkap diberi keterangan yang tepat tanpa menebak niat label.

Usulan Atensi internal Super Admin: pengajuan belum terkonfirmasi selesai setelah siklus pembayaran yang memang berlaku untuk pengajuan tersebut; data penerima yang mempunyai kekurangan/ketidaksesuaian terkonfirmasi dan memerlukan tindak lanjut pembayaran; serta selisih pencatatan yang telah dicocokkan pada cakupan dan waktu acuan yang sama. Keterlambatan pembaruan daftar tidak otomatis dianggap selisih keuangan. Nama, arti serta pemicu penanda dimasukkan ke Standar & Penanda sebelum penerapan.

Setiap Atensi yang diusulkan memuat alasan, nominal terkait, sumber/periode, waktu ditemukan dan tindakan berikutnya. Arah tindakan menggunakan menu yang sudah ada: pengajuan menuju Penarikan/daftar pembayaran, data penerima menuju Penyesuaian Data Label, dan selisih menuju pemeriksaan sumber royalti/riwayat. Penanganan dapat dicatat pada riwayat kasus dan Riwayat Aktivitas, tanpa membuat sidebar baru. Satu masalah mempunyai satu riwayat; pembukaan/reload tidak menciptakan peringatan berulang. Kasus dinyatakan selesai setelah kondisi sumbernya benar-benar terselesaikan, bukan sekadar menutup kartu atau menandai catatan sebagai selesai.

Usulan tahap awal hanya memunculkan peringatan internal pada Super Admin. Pesan otomatis kepada label belum ditetapkan; komunikasi berikutnya mengikuti keputusan/tindakan berwenang setelah pemeriksaan. Atensi tidak mengubah saldo, memulai pengajuan atas nama label, menahan dana atau memberi hadiah dengan sendirinya. Wawasan dapat menampilkan pola/pergerakan yang menarik dari monitor, sementara Atensi membawa kebutuhan tindakan yang jelas. Cakupan Admin tetap mengikuti pembahasan Staff & Akses.

### Usulan pencocokan monitor dengan penerimaan dan kas nyata

Pada 5 Oktober 2026 pengguna meminta melanjutkan dialog. Bagian ini merupakan usulan rancangan pencocokan sumber keuangan, belum persetujuan implementasi, integrasi rekening atau rilis. Pencocokan ditempatkan dalam wadah pemantauan yang ada, dengan rincian pada panel kanan; tidak menambah sidebar atau modul pembukuan penuh.

Pisahkan empat angka: hak royalti label menurut laporan dan koreksi yang sah; penerimaan nyata dari distributor beserta bagian yang menjadi hak label; pembayaran royalti yang telah terkonfirmasi; serta kas aktual yang tersedia/dialokasikan untuk pembayaran pada waktu pemeriksaan tertentu. Penerimaan distributor dapat mencakup bagian perusahaan dan beberapa periode. Hak label yang dananya telah diterima dikurangi pembayaran terkait menghasilkan hak belum dibayarkan, bukan saldo bank terkini. Pengajuan berjalan tetap bagian dari hak belum dibayarkan; tidak dikurangkan sebagai pembayaran. Kas dari pembelian paket/kredit/layanan tidak otomatis dianggap dana royalti. Perbandingan kas dengan kewajiban harus memakai cakupan dan waktu acuan yang sama.

Temuan repo: backend/routes/xendit_reconciliation.py membandingkan transaksi masuk PAYMENT yang berhasil dengan catatan pembelian paid, serta membaca saldo CASH/HOLDING penyedia. Ini dasar pencocokan uang pembelian, bukan bukti pencocokan penerimaan distributor ke rekening perusahaan. Backend/routes/royalty.py mengisi dana_received_at dengan finished_at setelah proses penerimaan selesai; tanggal tersebut tidak membuktikan tanggal dana dikreditkan bank. Temuan hanya dari salinan kode, bukan hasil pemeriksaan rekening atau integrasi produksi.

Usulan tahap pertama memakai pencocokan manual terstruktur pada tindakan penerimaan yang sudah ada: sumber/distributor, laporan atau periode terkait, tanggal penerimaan nyata, nominal dan mata uang yang dikreditkan, rekening perusahaan tujuan serta referensi transaksi jika tersedia. Mata uang sumber tetap dapat ditelusuri, sedangkan monitor mengikuti standar rupiah dengan dasar konversi yang tercatat. Satu penerimaan dapat dialokasikan ke beberapa laporan, dan satu laporan dapat diterima bertahap; alokasi tidak boleh melebihi dana penerimaan atau menggandakan penerimaan yang sama. Bila sumber tidak menyediakan alokasi yang andal, tampilkan bagian belum dapat dicocokkan tanpa mengarang tanggal/nominal per label. Tidak menghitung ulang hak historis menggunakan kurs atau bagian royalti terbaru.

Pencocokan tidak menjalankan ulang pemberian saldo yang telah selesai. Koreksi penerimaan/alokasi mempertahankan catatan sebelum/sesudah, sumber dan petugas berwenang; selisih diarahkan ke pemeriksaan sumber. Tidak mengubah saldo semua label, menahan hak yang sudah sah atau menyelesaikan pembayaran otomatis. Catatan saldo awal dan pembayaran lama yang sudah cocok tetap dipertahankan; kekurangan arsip diberi status belum dapat dicocokkan, bukan diperlakukan sebagai penerimaan nol atau dibuat menjadi transaksi baru.

Usulan status pencocokan: Sudah dicocokkan, Perlu diperiksa, dan Belum dapat dicocokkan, dengan sumber serta waktu pemeriksaan. Status pencocokan terpisah dari status royalti dan pembayaran. Data yang belum diperiksa tidak ditampilkan sebagai sesuai; saldo kas yang belum tersedia tidak ditampilkan nol. Status hanya berlaku untuk sumber/cakupan yang benar-benar diperiksa, bukan pernyataan seluruh keuangan telah aman.

Kas pembayaran memerlukan catatan tersendiri mengenai rekening/saldo aktual, waktu acuan dan nominal yang dialokasikan untuk pencairan; batas kas yang bebas dari kebutuhan lain belum ditetapkan. Saldo penyedia atau rekening tunggal tidak otomatis mewakili seluruh kas perusahaan, dan transfer antarrekening perusahaan tidak dihitung sebagai penerimaan distributor baru. Pencocokan tahap awal tidak mensyaratkan integrasi bank otomatis ataupun unggah bukti untuk setiap pembayaran royalti; keputusan sebelumnya mengenai tombol pembayaran dan email bank tetap berlaku.

Contoh hipotetis untuk menjelaskan monitor: hak label yang dananya telah diterima Rp100 juta, pembayaran terkonfirmasi Rp30 juta, sehingga Rp70 juta belum dibayarkan. Bila Rp20 juta sudah diajukan, sisanya Rp50 juta tersedia belum diajukan dengan asumsi tidak ada kondisi saldo lain. Rp70 juta tidak membuktikan nominal yang masih ada di bank. Pembahasan berikutnya adalah simulasi kebutuhan pembayaran berdasarkan kewajiban, kelayakan pengajuan dan kas yang telah dicocokkan, bukan perkiraan bahwa label tidak akan pernah menarik.

### Persetujuan arah pencocokan dan peninjauan kebutuhan emblem

Pada 5 Oktober 2026 pengguna menyetujui penjelasan pencocokan dana pada jawaban sebelumnya: membedakan hak label, penerimaan nyata, pembayaran terkonfirmasi dan kas untuk pencairan; melengkapi pencatatan penerimaan dengan tanggal nyata, nominal, sumber/periode, rekening tujuan dan referensi jika tersedia; serta menampilkan status dan waktu pencocokan tanpa menganggap data yang belum tersedia sebagai nol. Persetujuan ini merupakan arah rancangan, bukan izin implementasi, integrasi rekening atau rilis. Rincian tambahan yang belum dibahas eksplisit tetap usulan.

Pengguna kemudian mempertanyakan apakah emblem diperlukan untuk pemantauan, dan melaporkan banyak data legacy tidak akurat. Kekhawatirannya: emblem beserta bonus menyiratkan jumlah royalti yang menurut label belum pernah diterima. Topik emblem dibuka kembali untuk penilaian kebutuhan dan risiko; belum ada keputusan menghapus, mengganti dasar, menerbitkan hadiah historis atau mengubah nominal/ambang.

#### Pemeriksaan terbatas pada sumber dan model prototipe

Pemeriksaan membaca sumber referensi tanpa mengubahnya. Uji terisolasi menjalankan pending-model.js dari V12.0 di memori dengan data hipotetis, tanpa database produksi, rekening, transaksi asli, penyimpanan pratinjau atau rilis. Empat kondisi selesai diuji pada 5 Oktober 2026:

- Angka pembayaran historis Rp5 juta dapat menetapkan Bronze I–III dan Silver I meskipun simulasi tidak menyediakan catatan pembayaran terperinci. Model tidak memberi kredit retroaktif saat menetapkan posisi awal; pengamanan ini ada. Akan tetapi, angka historis belum melalui pemeriksaan bukti dalam model tersebut.
- Koreksi angka pembayaran historis dari Rp800 ribu menjadi Rp1 juta, tanpa menambah catatan pembayaran baru, memicu Bronze I, satu berita kenaikan dan 2 kredit menurut nilai simulasi prototipe. Ini menunjukkan kenaikan angka lama dapat diperlakukan seperti pencapaian baru; bukan bukti transaksi atau kredit demikian telah terjadi di produksi.
- Pencocokan berulang pada kondisi yang sama tidak menambah hadiah atau berita kedua. Pencegahan pemberian ganda dalam kondisi ini bekerja; hal itu tidak membuktikan kebenaran data sumbernya.
- Koreksi turun menjadi Rp700 ribu menandai needsPaymentReview, tetapi akumulasi pencapaian tetap Rp1 juta, emblem tetap Bronze I dan 2 kredit tetap ada. Ini tidak menjalankan penarikan kredit otomatis; penyelesaian dampak koreksi terhadap informasi label dan hadiah masih memerlukan kebijakan.

Temuan sumber tambahan: royalty.py dapat memberi status withdrawn pada baris laporan lama berdasarkan last_withdrawn_period, bukan berdasarkan bukti setiap transfer. Status baris tersebut tidak cukup sebagai bukti pembayaran nyata. Ringkasan admin_get_label mengambil nominal pembayaran dari withdraw_requests berstatus paid, yang perlu dicocokkan dengan riwayat pembayaran yang tersedia. Uji di atas membuktikan perilaku model, bukan kelengkapan atau ketepatan seluruh data legacy.

#### Pandangan dan alternatif yang diusulkan

Usulan asisten: emblem tidak diperlukan untuk pemantauan keuangan. Monitor utama memakai angka, cakupan periode, umur dana, kondisi pencairan dan status pencocokan sumber. Emblem tidak dijadikan ukuran kesehatan keuangan, kepercayaan/verifikasi, hak pencairan atau status masalah. Emblem dan bonus adalah fitur apresiasi terpisah, sehingga pemantauan dapat berjalan tanpa menunggu penyelesaian definisi pencapaian.

Alternatif pertama dan rekomendasi untuk tahap awal: lanjutkan monitor tanpa bergantung pada emblem; tunda penerbitan emblem/bonus otomatis berdasarkan nominal legacy. Konsep emblem tetap tersedia untuk pembahasan tersendiri, tanpa menghapusnya dari prototipe dalam turn ini. Data lama yang belum dapat dicocokkan tidak diberi nilai nol atau dianggap label tidak berprestasi. Bonus dari Rilis Musik yang diberikan secara khusus dapat tetap dibahas/digunakan sesuai kewenangan dan alur klaim yang telah ditentukan, dengan alasan yang nyata; bonus tidak perlu menyatakan label telah menerima nominal royalti tertentu.

Alternatif kedua jika emblem finansial tetap diinginkan: gunakan sumber yang dapat ditelusuri dan titik awal yang jelas. Periode/cakupan penghitungan tampil kepada label dan dihitung sama pada semua akun yang mengikuti kebijakan. Sejarah lama hanya ditambahkan sesudah pencocokan memadai; pemeriksaan data tidak otomatis menerbitkan seluruh hadiah historis. Tidak cukup mengganti nama dari royalti dibayarkan menjadi pendapatan untuk mengatasi ketidakakuratan. Pembayaran terkonfirmasi mengukur uang yang telah dicairkan dan dipengaruhi kebiasaan penarikan; pendapatan royalti terkonfirmasi mengukur penghasilan katalog, dapat belum dibayarkan dan tetap memerlukan laporan/konversi/alokasi yang sah. Keduanya berbeda dan tidak boleh dicampur. Memulai dari periode baru perlu kebijakan yang adil bagi label lama tanpa menganggap prestasi sebelumnya tidak ada; bukan otomatis mereset seluruh label.

Alternatif ketiga: pencapaian nonfinansial dari peristiwa yang sah, misalnya rilisan pertama yang benar-benar tayang. Ini dapat mengurangi klaim nominal royalti, tetapi juga membutuhkan dasar dan kebijakan transisi. Jangan mengganti emblem lama dengan tangga baru atau mengaitkan bonus otomatis tanpa keputusan pengguna.

Usulan pengamanan bila emblem dilanjutkan: sumber pencapaian harus spesifik, dapat ditelusuri dan telah dicocokkan; perubahan angka historis tidak dianggap pembayaran/penghasilan baru; perbaikan data, kenaikan pencapaian dan penerbitan hadiah menjadi peristiwa terpisah dengan riwayat yang saling terkait. Label dapat melihat dasar, periode dan rincian pencapaian serta meminta pemeriksaan. Koreksi setelah hadiah diberikan tidak diam-diam mengambil kredit, menciptakan saldo negatif, menurunkan emblem atau mengubah saldo royalti; keputusan penanganannya disimpan tersendiri. Pembatasan akun tidak menghapus hadiah yang memang sah, sesuai ketentuan pengguna sebelumnya.

Validasi lanjutan sebelum penerapan memerlukan data yang dapat dicocokkan: pembayaran aktual versus catatan paid; baris historis yang settled melalui cutoff; impor ulang/duplikasi; koreksi positif dan negatif; pembayaran gabungan master beserta alokasi sumber; perubahan nama/akun/pengelola; dan kesesuaian angka serta definisi yang terlihat oleh label dengan yang dipakai petugas. Uji aritmetika/hadiah sekali saja tidak menggantikan pencocokan sumber. Tidak menjalankan audit produksi atau mengubah perilaku prototipe pada pembahasan ini.

### Usulan dasar emblem: hasil katalog dan apresiasi perjalanan label

Pada 5 Oktober 2026 pengguna meminta pandangan tentang membuat ulang mekanisme emblem: apakah pencapaian total royalti cocok, atau terdapat dasar penghargaan yang lebih tepat. Seluruh bagian berikut merupakan usulan asisten untuk dialog, bukan keputusan mengganti dasar, ambang, nominal hadiah atau perilaku prototipe.

Total royalti cocok untuk satu tujuan yang spesifik: mengakui hasil komersial katalog. Ia tidak cukup sebagai ukuran keseluruhan nilai label, kualitas musik, kepercayaan, verifikasi atau kesehatan keuangan. Akumulasi besar juga dipengaruhi umur dan ukuran katalog; jangan menjadikannya peringkat kualitas atau satu-satunya jalan apresiasi. Tidak menggunakan saldo yang belum ditarik sebagai dasar hadiah karena saldo dipengaruhi penarikan, dan tidak mengaitkan penghargaan dengan membiarkan dana berada di perusahaan.

Jika keluarga Bronze sampai Diamond tetap digunakan untuk hasil komersial, usulkan dasar akumulasi hak royalti bersih label yang terkonfirmasi pada cakupan periode yang dinyatakan. Dasar ini berbeda dari mekanisme lama akumulasi pembayaran. Hak label dihitung menurut laporan sumber yang sudah diperiksa, bagian label serta kurs yang berlaku pada sumber historis, dan koreksi yang disahkan; tidak memakai pendapatan bruto distributor, bagian perusahaan, saldo kredit atau nominal pengajuan penarikan. Penarikan tidak mengurangi pencapaian. Penerimaan distributor dan pembayaran kepada label tetap mempunyai catatan tersendiri; emblem tidak menyatakan uang telah diterima label. Publikasi teknis sebuah laporan atau status paid/withdrawn saja tidak cukup menjadi pemeriksaan kebenaran sumber.

Untuk masa awal, riwayat legacy yang belum dapat dicocokkan tidak digunakan menerbitkan emblem/bonus otomatis. Cakupan periode dan sumber yang benar-benar diperiksa ditampilkan, tanpa menyebut total sepanjang kerja sama bila riwayat belum lengkap. Prestasi lama tidak diperlakukan nol atau dihapus; dapat diakui setelah pencocokan, dengan perlakuan hadiah historis yang tetap menunggu kebijakan. Mengganti istilah pembayaran menjadi penghasilan tidak menyelesaikan data yang keliru. Tanggal awal, kelengkapan antar-label dan cara mengakui sejarah lama perlu disepakati agar tangga baru tidak merugikan label lama.

Usulan susunan apresiasi yang sederhana: satu tangga emblem utama untuk hasil komersial katalog, ditambah apresiasi atas peristiwa penting yang tidak dicampur menjadi skor atau tangga finansial. Contoh peristiwa: rilisan pertama benar-benar tayang, katalog mencapai tonggak rilisan unik yang telah dikonfirmasi, atau ulang tahun kerja sama berdasarkan tanggal yang dapat dibuktikan. Tanggal kerja sama tidak ditebak dari tanggal impor/akun. Jumlah unggahan/draf, login, pembelian kredit dan harga paket tidak digunakan sebagai pencapaian katalog. Perubahan metadata atau pengajuan ulang rilisan yang sama tidak dihitung sebagai rilisan baru. Hadiah untuk setiap tonggak tidak otomatis diasumsikan ada; kebijakan dan dampak biayanya perlu ditetapkan.

Alternatif untuk penerapan awal jika riwayat keuangan belum cukup andal: mulai apresiasi dari peristiwa katalog baru yang dapat dikonfirmasi, sementara emblem finansial tetap ditunda. Penghargaan nonfinansial tetap membutuhkan sumber yang sah dan pencegahan peristiwa/hadiah ganda; ia bukan jalan untuk melewati masalah ketepatan data. Penarikan dan hak royalti tidak bergantung pada penghargaan ini.

Bonus dari Rilis Musik tetap menjadi mekanisme pemberian tersendiri dengan pesan/alasan, penerima, kredit, masa klaim dan riwayat sesuai kebijakan yang telah dibahas. Emblem mengakui pencapaian; hadiah adalah benefit menurut kebijakan yang berlaku, bukan pembuktian pembayaran royalti atau perubahan saldo royalti. Perbaikan sejarah, pengakuan pencapaian dan penerbitan hadiah mempunyai peristiwa berbeda yang dapat ditelusuri. Pencapaian yang disahkan dapat dihubungkan ke satu hadiah yang memang berlaku tanpa menggandakan penerbitan; perbaikan angka sejarah tidak langsung menerbitkan seluruh hadiah lewat model lama.

Penempatan menggunakan bagian Pencapaian dan Bonus yang sudah dirancang, tanpa sidebar baru atau skor gabungan royalti, jumlah rilisan dan lama kerja sama. Monitor keuangan tetap berdiri di atas angka dan pencocokan sumber, tidak menunggu emblem. Pandangan ini belum mengesahkan penghapusan emblem, mekanisme baru, ambang Bronze–Diamond, hadiah turunan ataupun kebijakan transisi.

### Lanjutan usulan: posisi awal, kenaikan baru dan penerbitan hadiah

Pada 5 Oktober 2026 pengguna menyatakan lumayan sepakat dan meminta melanjutkan. Ini dukungan atas arah pembahasan, bukan persetujuan final seluruh dasar/perhitungan, hadiah, ambang atau kebijakan transisi; tidak ada izin implementasi atau rilis. Usulan berikut memperjelas penerapan agar masalah sumber legacy tidak diteruskan ke hadiah.

Pisahkan tiga kejadian: pengakuan posisi awal dari sejarah yang telah dicocokkan; kenaikan baru dari royalti/peristiwa katalog yang sah sesudah titik penerapan yang disepakati; dan koreksi/perluasan kelengkapan data sejarah. Posisi awal mengakui emblem yang berhak menurut sumber dan cakupan yang telah diperiksa, tanpa langsung menerbitkan seluruh hadiah tingkat lama. Koreksi sejarah dapat mengubah dasar pengakuan setelah pemeriksaan, tetapi tidak menjadi peristiwa pendapatan/pembayaran baru atau hadiah otomatis. Kenaikan baru hanya memakai sumber yang disahkan dan aturan hadiah yang benar-benar berlaku.

Titik penerapan dan cakupan periode belum ditentukan. Laporan untuk periode sebelum titik penerapan yang baru diimpor/dikonfirmasi kemudian tetap bagian sejarah; bukan kenaikan baru hanya karena tanggal impor, penerimaan bank atau penyimpanan baru. Perlakuan periode yang melintasi batas perlu disepakati sebelum penerapan. Riwayat yang tidak lengkap tidak dipaksa menjadi akumulasi sepanjang kerja sama, tidak dianggap nol dan tidak menampilkan label lama sebagai belum pernah berprestasi. Jika sumber finansial belum memadai, catat royalti/peristiwa baru yang sah dan gunakan apresiasi nonfinansial yang dapat dibuktikan; penerbitan emblem finansial menunggu dasar yang memadai tanpa mengubah hak royalti, akses atau penarikan.

Contoh usulan: label yang berdasarkan sejarah sah sudah mencapai Gold I diakui pada Gold I; tidak diminta mengejar Bronze lagi. Kenaikan yang sah kemudian menuju Gold II mengikuti kebijakan hadiah reguler yang akhirnya ditetapkan. Jika laporan sejarah terlambat justru mengubah posisi awalnya, perubahan tersebut mengikuti tinjauan sejarah dan tidak otomatis dianggap kenaikan reguler. Hadiah sejarah/transisi tetap kebijakan tersendiri yang belum final; pengakuan emblem tidak menciptakan janji seluruh hadiah lama tertunggak.

Usulan hadiah pencapaian yang sah mempertahankan perilaku yang sebelumnya diminta: kredit tambahan diberikan sekali sesuai tingkat/peristiwa dan kebijakan yang berlaku, kemudian ucapan muncul pada waktu yang tidak memotong formulir. Tidak memerlukan klaim seperti tawaran Bonus dari Rilis Musik. Bonus khusus tetap memakai klaim 48 jam dan kredit baru aktif sesudah klaim, dengan jenis/masa berlaku sesuai kebijakan yang telah dibahas. Membuka popup, mengimpor ulang laporan, mengganti nama atau memindahkan pengelola tidak menerbitkan hadiah kedua. Identitas penerima pencapaian/hadiah mengikuti pemilik katalog yang disepakati, bukan hanya nama tampilan atau akun yang sedang mengelola. Alokasi multi-label tetap dapat ditelusuri tanpa menggandakan penghasilan maupun hadiah di master dan anak label.

Sebelum pengakuan/penerbitan, usulkan ringkasan Super Admin yang menunjukkan sumber dan cakupan, posisi awal atau tingkat sebelumnya, tingkat hasil, jenis kejadian (sejarah/kenaikan/koreksi), penerima serta hadiah yang memang berlaku. Ringkasan dapat dilakukan bersama untuk sumber/batch yang sah, tidak membutuhkan persetujuan manual setiap klik pengguna. Nominal dan jumlah penerima dapat ditinjau sebelum aturan/penerbitan hadiah berjalan; keputusan nilai kredit/biaya layanan tidak diasumsikan selesai melalui rancangan ini. Pembatasan akun atau pekerjaan bermasalah tidak menghapus hadiah yang sah, sesuai instruksi pengguna terdahulu.

Jika koreksi memengaruhi emblem/hadiah yang sudah diberikan, hentikan penerbitan tambahan pada dasar yang sedang diperiksa dan tangani kasus tersebut melalui riwayat. Tidak menarik kredit, membuat saldo negatif, menurunkan emblem diam-diam atau mengubah saldo royalti dari aturan hadiah. Keputusan koreksi informasi yang benar serta perlakuan hadiah yang sudah dipakai belum final dan perlu penjelasan kepada label terdampak. Pemeriksaan hanya pada sumber/kasus terkait, bukan penghentian seluruh layanan atau penarikan semua label.

Monitor dana tetap berjalan terpisah dari penghargaan. Setelah arah penerapan ini disepakati, bahasan berikutnya dapat kembali ke simulasi kebutuhan pembayaran berdasarkan hak yang dapat diajukan, pengajuan berjalan dan kas yang sudah dicocokkan. Mekanisme emblem/hadiah yang baru belum diterapkan pada prototipe maupun produksi.

### Peninjauan penghapusan emblem — belum diputuskan

Pada 5 Oktober 2026 pengguna mempertimbangkan bahwa fungsi emblem telah tergantikan oleh pemantauan royalti, menyatakan tidak ingin label mengetahui tingkatan emblem, dan meminta penjelasan apakah lebih baik menghapus fitur. Ini pertanyaan rancangan, bukan instruksi penghapusan atau izin perubahan prototipe/rilis. Dukungan parsial sebelumnya atas arah emblem tidak berarti mekanisme/ambang/hadiah baru sudah final.

Pandangan asisten: kebutuhan awal membaca besarnya pendapatan dan kondisi dana dapat dipenuhi lebih tepat oleh angka, periode, filter dan detail sumber di pemantauan. Emblem tidak diperlukan untuk tujuan tersebut. Fungsi lain emblem adalah pengakuan pencapaian yang dilihat pengguna serta perjalanan menuju tingkat berikutnya; fungsi ini berbeda dari monitor. Bila pengguna tidak menginginkan tingkatan yang diketahui label, tangga emblem kehilangan tujuan tersebut dan tidak perlu dipertahankan hanya sebagai aset visual atau kategori logam internal.

Rekomendasi asisten untuk dibahas: hapus fitur emblem bertingkat dari rancangan produk dan gunakan pemantauan untuk analisis, sedangkan Bonus dari Rilis Musik tetap menjadi mekanisme apresiasi berdasarkan alasan/peristiwa yang nyata dengan kewenangan, klaim dan riwayat sesuai kebijakan yang telah dibahas. Tidak mengganti emblem dengan tangga tersembunyi yang secara otomatis menentukan hadiah, akses atau perlakuan label. Segmentasi internal yang berguna memakai nama sesuai fakta dan sumbernya; kondisi dana tidak dijadikan penilaian mutu, reputasi atau hak label. Perkembangan pendapatan/katalog tetap memakai tabel tersendiri sesuai arahan pengguna, bukan dicampur ke fokus dana belum ditarik.

Jika penghapusan kemudian disetujui, cakupannya perlu meliputi emblem pada profil/daftar, tab/riwayat kenaikan tingkat, panduan dan konfigurasi ambang, target/progres menuju tingkat berikutnya, pemicu kredit berdasarkan kenaikan, popup dan kabar pencapaian tingkat, serta kondisi Studio yang bergantung pada emblem. Tetap pertahankan sumber laporan, pembayaran, pencocokan, saldo dan riwayat kredit/bonus yang memang sah; penghapusan fitur penghargaan tidak menghapus atau menarik hadiah yang telah disahkan. Hadiah tingkat/historis yang belum menjadi kebijakan final tidak diperlakukan sebagai janji hadiah tertunggak. Daftar ini merupakan usulan cakupan, belum pekerjaan penghapusan.

Kabar Wawasan dapat memakai peristiwa yang relevan dan dapat dibuktikan dari sumber monitor/katalog atau pemberian bonus tanpa tingkat emblem. Keputusan penghapusan, rincian penggantinya dan penerbitan prototipe tetap menunggu arahan pengguna. Tidak ada perubahan kode, data keuangan atau prototipe dalam turn ini.

### Penamaan pembayaran, paket dan gagasan AI — 5 Oktober 2026

Pengguna meminta menyimpan dahulu usulan penghapusan emblem dan membuka pembahasan nama kredit/token, calon paket Free–Studio–Pro–Business, layanan tiap paket serta AI agent bagi staf/member. Usulan penghapusan emblem diparkir; belum perintah menghapus fitur. Nama, nilai saldo, harga, kuota/manfaat, penyedia AI, implementasi dan rilis belum diputuskan.

Usulan asisten: Token R untuk satuan pembayaran layanan, terpisah dari credits kontributor musik dan token pemrosesan AI; Basic–Studio–Pro–Business untuk tanpa langganan, kebutuhan rilisan rutin, dukungan pengembangan katalog, dan operasional tim/multi-label. Free hanya tepat dengan penjelasan akun gratis dan layanan sesuai pemakaian. Rupiah tetap standar transaksi dan pilihan token harus lebih hemat sesuai arahan pengguna. Pemisahan fungsi saldo rilisan/layanan, hak saldo lama, jatah harian dan manfaat paket lama tidak diubah melalui penamaan. Semua benefit AI baru, WAMI/promosi dan kolaborasi masih usulan untuk dievaluasi.

Rincian sumber, alternatif nama, tabel manfaat, batas klaim layanan, masukan staf dan rancangan AI disimpan di analysis-v10/PACKAGE-DECISIONS.md, bagian Pembahasan penamaan dan manfaat paket dengan AI — 5 Oktober 2026. Asisten mengusulkan bantuan internal terlebih dahulu untuk evaluasi ketepatan/biaya, kemudian fungsi member yang siap; ini urutan pengembangan masa depan, bukan izin mulai bekerja atau membagi rilis prototipe menjadi dua fase. Tidak ada perubahan kode atau rilis.

### Pembeda paket dan nama Token — kelanjutan 5 Oktober 2026

Pengguna menyetujui arah sejauh ini, meminta penilaian nama Basic/Regular dan alternatif, menegaskan manfaat harus terasa serta mudah dipahami, dan terbuka pada menu berbeda antar-paket. Nama paket, detail layanan, kuota dan harga belum final. Pengguna meminta sementara menyebut satuan sebagai Token; peruntukannya baru dibahas setelah paket. Tidak memakai Token R sebagai nama yang sudah disetujui, tidak mulai mengubah saldo atau fitur.

Usulan asisten untuk ditinjau: Regular–Studio–Pro–Business. Regular untuk layanan satuan tanpa langganan, Studio untuk rencana/persiapan rilisan rutin, Pro untuk kampanye dan pengembangan katalog dengan layanan terukur, Business untuk pengelolaan tim/multi-label. Rencana Rilisan, Kampanye Rilisan dan Tim & Label merupakan calon ruang/menu dengan alur nyata, bukan manfaat produksi yang sudah tersedia. Perluas menu lama jika hanya variasi alat/kuota; jangan menggandakan pesanan atau memenuhi sidebar dengan menu terkunci. Hak dasar, kualitas pemeriksaan wajib dan hasil/riwayat yang sah tetap dijaga lintas paket. Rincian disimpan dalam analysis-v10/PACKAGE-DECISIONS.md, bagian Lanjutan nama paket dan pembeda kemampuan kerja — 5 Oktober 2026. Tidak ada implementasi atau rilis pada turn ini.

### Pilihan Basic dan pembahasan Studio — 5 Oktober 2026

Pengguna memilih Basic sebagai nama layanan dasar dan meminta rincian Studio. Ini menggantikan kandidat Regular pada arah penamaan terkini, tanpa menetapkan harga/manfaat/kuota atau migrasi paket lama. Peruntukan Token tetap dibahas setelah paket. Usulan Studio: satu label dengan pemakaian rilisan yang termasuk dan terukur, tab Rencana dalam menu Rilisan untuk kalender/persiapan lintas draft, templat pengaturan yang dapat dipakai ulang, ringkasan kesiapan per lagu/draft, serta calon asisten persiapan di formulir. Semua rincian tersebut masih usulan; Basic tetap mendapat draft, penggunaan data katalog/artis yang sah, pemeriksaan dan hak dasar. Tidak menambah sidebar yang menggandakan draft/pesanan.

Jatah harian lama tidak diganti melalui pembahasan ini; mekanisme, jumlah, harga dan AI belum disahkan. Volume staf keseluruhan bukan rata-rata pemakaian satu label. WAMI/promosi tetap layanan satuan yang dapat dibeli menurut katalog; percepatan Standard/Express/MAX tidak otomatis termasuk karena nama Studio. Rincian dan batas kelanjutan tersimpan di analysis-v10/PACKAGE-DECISIONS.md, bagian Pilihan Basic dan rincian Studio untuk ditinjau — 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Arah Studio disetujui; empat kecepatan masih usulan — 5 Oktober 2026

Pengguna menyetujui rincian manfaat Studio yang telah dijelaskan; jumlah, harga, peruntukan Token dan kesiapan AI tetap belum ditentukan. Usulan berikutnya: Standard >=7 hari, Express 5, MAX 4 dan Ultra 3. Pengguna meminta pertimbangan, bukan menerapkan layanan keempat. Pendapat asisten: tiga nama Standard–Express–MAX lebih sederhana dahulu, tanpa mengesahkan angka sebagai jaminan tayang. MAX lama 3 hari tidak diam-diam dipindah ke 4 untuk pengajuan/manfaat yang telah diterima.

Pemeriksaan sumber resmi Spotify 5 Oktober 2026 menemukan acuan 5 hari kerja dari pengiriman ke Spotify, sehingga angka sejak pengajuan label harus dibedakan dari pemeriksaan/penerusan internal dan konfirmasi tayang. Hari kerja/kalender, titik mulai, jam batas, revisi, kapasitas dan kemampuan jalur Believe perlu ditentukan sebelum janji tanggal. Calon jatah Express sebagai manfaat Studio masih usulan untuk ditinjau, belum disahkan. Rincian sumber dan pertimbangan tersimpan di analysis-v10/PACKAGE-DECISIONS.md, bagian Persetujuan arah Studio dan usulan empat layanan kecepatan — 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Tiga layanan dipertahankan; dialog berlanjut ke Pro — 5 Oktober 2026

Pengguna menyetujui arah tiga tingkat Standard–Express–MAX dan meminta melanjutkan. Ultra tidak ditambahkan; angka hari masih menunggu verifikasi kemampuan dan cara hitung, bukan jaminan tayang yang sudah disahkan. Arah Express terbatas untuk Studio tetap bergantung kapasitas/biaya, tanpa angka atau cakupan final. Asisten melanjutkan usulan Pro: manfaat Studio ditambah jatah pengurusan WAMI per lagu, konten promosi gambar per set dengan hasil manusia, kampanye yang menautkan rencana/pesanan yang sama, serta evaluasi katalog dan bantuan promosi bersumber. Semua rincian Pro masih untuk dinilai, bukan persetujuan fitur melalui jawaban sebelumnya.

Kampanye memperluas konteks Rilisan dan menghubungkan Layanan Tambahan; tidak menggandakan sidebar/pesanan. Laporan dan hak dasar tetap untuk semua paket; WAMI/promosi tetap bisa dibeli satuan. Jumlah, harga, cakupan biaya/hasil/revisi dan AI belum final; Business lalu Token menjadi urutan diskusi berikutnya. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Tiga tingkat dipertahankan dan pembahasan Pro — 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Arah Pro disetujui; WAMI dan desain wajib mempunyai kuota — 5 Oktober 2026

Pengguna menyetujui arah Pro dan meminta limit/kuota agar WAMI serta gambar promosi tidak membeludak. Usulan: dua kuota bulanan terpisah sesuai tanggal aktif paket, per lagu WAMI dan per set desain; tahunan membuka jatah bulanan, sisa belum digunakan tidak menumpuk. Pesanan valid mencadangkan hak pada periode asal, revisi dalam cakupan tidak memakai jatah baru, pesanan yang sah tetap diselesaikan setelah periode berakhir dan kegagalan internal mengikuti pemulihan hak yang telah dibahas. Pembelian tambahan harus terlihat dan disetujui, tidak otomatis ditagihkan.

Periode/reset/jumlah/batas revisi masih untuk dinilai; pembelian saldo/pesanan dan manfaat lama tidak dihapus atau dibatasi surut. Kapasitas pengerjaan total dan estimasi antrean perlu diatur bersama kuota pelanggan tanpa menolak hak yang sudah dijual. Waktu rata-rata set gambar perlu diverifikasi staf karena data lama masih bercampur video. Pengaturan merujuk katalog/manfaat paket yang sama, tanpa menu baru. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Arah Pro disetujui dan pembatasan manfaat — 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Kuota Pro diterima sebagai arah awal; Business untuk ditinjau — 5 Oktober 2026

Pengguna menyetujui sejauh ini model kuota dan meminta lanjut; jumlah/harga/cakupan hasil serta kapasitas masih belum final. Usulan berikut Business: tim satu label maupun pengelola multi-label, akun anggota dan izin per label/tindakan, tinjauan draft internal sesuai kebutuhan, kuota WAMI/gambar bersama yang tercatat per label serta ringkasan pekerjaan/laporan gabungan. Calon Tim & Label untuk member terpisah dari Staff & Akses internal; Rilisan, pesanan dan royalti menggunakan wadah/sumber yang sama. Rincian Business belum disetujui melalui jawaban yang hanya menerima model kuota Pro.

Penarikan master tetap dari akumulasi saldo tersedia sesuai ketentuan yang sudah disepakati, bukan memberi hak finansial otomatis kepada operator. Penambahan label tidak menerbitkan jatah baru atau memberi hak katalog tanpa kewenangan. Batas label/anggota/manfaat menunggu biaya dan kapasitas. Katalog/royalti/riwayat tetap sah setelah paket habis; aktivitas baru tim dan pengelolaan multi-label saat turun paket masih perlu dibahas. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Kuota Pro disetujui sebagai arah awal; pembahasan Business — 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Business disimpan dan dialog beralih ke Token — 5 Oktober 2026

Pengguna meminta menyimpan dulu Business lalu membahas Token. Rancangan/celah Business tetap tersimpan untuk ditinjau kembali, belum pengesahan seluruh detail atau izin implementasi. Usulan Token meneruskan dua fungsi yang sebelumnya disukai: Token Rilisan dan Token Layanan, dengan tarif/unit yang jelas dan saldo terpisah tanpa konversi 1:1 otomatis. Rupiah tetap pilihan transaksi dan jalur Token harus lebih hemat dalam biaya perolehan yang dinyatakan; angka tarif belum final. Kuota WAMI/desain memenuhi pesanan secara langsung tanpa pemotongan Token/tagihan kedua atau penerbitan saldo ulang.

Asal pembelian, paket, bonus dan sementara menentukan hak/masa berlaku, bukan empat mata uang baru. Jadwal Token paket masih perlu ditinjau; kuota layanan bulanan tidak mengubah jatah Token harian lama. Pembelian/perpanjangan paket lewat Token, penukaran royalti, pembayaran campuran dan pemetaan saldo lama belum disahkan. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Business disimpan; pemetaan fungsi Token — 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Usulan Token Rilisan paket per periode bulanan — 5 Oktober 2026

Pengguna meminta melanjutkan pembahasan Token. Rekomendasi asisten: Token Rilisan paket diberikan di awal periode bulanan sesuai tanggal aktif paket; tahunan juga membuka jatah bulanan, sisa belum dicadangkan tidak menumpuk. Jumlah baru harus dihitung dari biaya/pemakaian/kapasitas, tidak otomatis 5 harian dikalikan 30 menjadi 150 saldo bebas. Ini usulan untuk dinilai, belum pengganti aturan harian atau manfaat pelanggan lama yang masih sah.

Pencadangan pengajuan valid tetap melekat pada periode asal sampai penyelesaian, tanpa debit jatah bulan baru. Pembelian, bonus dan sementara mengikuti hak/masa berlaku masing-masing. Kuota WAMI/desain tidak sekaligus menghasilkan Token Layanan tambahan; kapasitas pengerjaan diatur terpisah agar EP/Album tetap dapat diajukan utuh. Durasi pemulihan saldo bulanan setelah periode habis, cakupan Express, angka/prorata/konversi/transisi masih perlu ditetapkan. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Pemberian Token paket harian atau bulanan — usulan 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Tarif Token Rilisan dan simulasi jumlah paket — usulan 5 Oktober 2026

Pengguna meminta membahas jumlah Token dan tarif layanan. Acuan usulan dari baseline prototype: Standard 1, Express 2, MAX 3 Token total per lagu, untuk semua paket; harga/biaya belum disahkan. Simulasi Studio 10 dan Pro 10 Token Rilisan per periode bulanan dipakai menguji satu Album sepuluh lagu Standard, bukan menetapkan kuota komersial. Pro memperoleh tambahan nilai melalui WAMI/desain/Kampanye Rilisan, sehingga jatah rilisan tidak otomatis harus lebih besar. Basic tanpa pemberian bulanan langganan; hak saldo yang sah tetap berlaku. Business tetap disimpan.

Usulan manfaat Express terbatas menanggung tambahan percepatan per lagu, dengan biaya dasar tetap dipenuhi dan tanpa debit/penerbitan saldo ganda; jumlah/cakupan belum final. Nilai beli Token dan tarif rupiah pembanding harus memastikan jalur Token lebih murah. Jumlah pelanggan, pemakaian, biaya lengkap dan kapasitas total menentukan kuota final; volume staf total bukan pemakaian per label. Hak/manfaat lama tidak diubah melalui simulasi. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Tarif Token Rilisan dan simulasi jumlah paket — usulan 5 Oktober 2026. Tidak ada implementasi atau rilis.

### Harga beli Token dan tarif rupiah pembanding — usulan 5 Oktober 2026

Pengguna meminta lanjut membahas harga. Repo mempunyai acuan Rp35.000 per lagu dan Rp200.000 per Album, belum verifikasi harga live. Sepuluh Token seharga Rp35.000 atau Rp30.000 akan lebih mahal daripada acuan rupiah Album, sehingga perlu keputusan tarif bundel; jangan menaikkan harga rupiah diam-diam untuk membuat Token tampak hemat. Simulasi asisten: Token Rilisan Rp30.000/unit, Single/EP Standard 1, Express 2, MAX 3 per lagu dibanding rupiah Rp35.000/Rp70.000/Rp105.000; harga Express/MAX adalah usulan simulasi, bukan data repo.

Usulan pengecualian Album Standard 6 Token total (Rp180.000) dibanding Rp200.000 perlu persetujuan tersendiri karena mengubah rancangan satu Token per lagu untuk Album. Cakupan Album, percepatan, alokasi/pemulihan per lagu serta ketelitian pecahan masih perlu ditetapkan. Simulasi Token Layanan Rp10.000/unit, WAMI 9 Token (Rp90.000) dibanding rencana Rp100.000 belum menentukan harga jual final atau mengubah penawaran lama Rp50.000. Pembelian pas kebutuhan, perbandingan biaya lengkap dan snapshot pesanan menjadi arah usulan; kuota paket akhir, saldo lama dan diskon massal belum ditetapkan. Rincian di analysis-v10/PACKAGE-DECISIONS.md, bagian Harga beli Token dan tarif rupiah pembanding — usulan 5 Oktober 2026. Tidak ada implementasi atau rilis.


### Token diparkir; rilis prototype V12.1 — 5 Oktober 2026

Pengguna tidak menyetujui usulan harga terakhir dan meminta memarkir pembahasan Token. Angka harga, jumlah manfaat, konversi, tarif bundel Album, serta dua saldo Token tidak diterapkan. Proposal sebelumnya tetap merupakan riwayat diskusi, bukan kebijakan yang disetujui. Perilaku kredit, harga dan hak lama pada V12.0 menjadi baseline.

Permintaan merasakan rilis terbaru dilaksanakan sebagai prototype V12.1: pemantauan dana dan katalog, tindak lanjut data label lama, serta Rencana dan Kampanye Rilisan. Paket Basic/Studio/Pro/Business adalah arah nama dan manfaat yang telah disepakati; angka dan kebijakan komersial yang belum final tidak dijadikan penawaran baru. Business rinci dan emblem tetap diparkir. Rilis ini tidak melakukan migrasi atau transaksi produksi.

### V12.1 diterbitkan — 5 Oktober 2026

Prototype V12.1 telah diterbitkan atas permintaan pengguna merasakan versi terbaru. Ruang lingkup: Pemantauan Dana, Perkembangan Katalog, pencatatan posisi kas, tindak lanjut lokasi label lama, Rencana Rilisan dan Kampanye Rilisan. Sembilan kondisi baru otomatis memilih akun yang sesuai di Studio Pratinjau. Harga/angka/manfaat Token tidak diterapkan; rincian komersial paket dan emblem tetap diparkir. Baseline kredit dan transaksi V12.0 dipertahankan.

82 pemeriksaan model dan antarmuka lolos; akses LAN, unduhan HTML, nomor versi, pergantian akun dan hash rilis telah diverifikasi setelah penerbitan. Bukti: prototype-v12.1/qa/verification121.json dan prototype-v12.1/qa/release-verification121.json. Rilis ini adalah prototype, bukan migrasi atau transaksi produksi. Tautan aktif: http://192.168.1.10:4343/.
