# Pembahasan Layanan Tambahan — 29 September 2026

Status: pembahasan setelah V11.0, belum izin implementasi/rilis. Pengguna meminta melanjutkan menu berikutnya. Perubahan panel detail kanan juga ditunda sampai eksekusi berikutnya.

## Dasar repo yang diperiksa

- prototype-v11.0/v4.js: addons masih outline; pesanan dan katalog direncanakan sebagai tab satu area.
- repo-reference-v10/backend/routes/addon_orders.py: pesanan per pasangan release/product, sumber berbayar atau benefit paket, status pending/in_progress/delivered/completed/cancelled, hasil berkas/tautan, pemberitahuan/email, backfill pesanan berbayar lama.
- frontend/src/components/label/LabelAddonOrders.jsx: label membaca hasil dan status dari pesanan terkait rilisan; belum ada alur label menerima hasil atau meminta revisi pada komponen ini.
- frontend/src/pages/admin/AddonOrders.jsx: katalog dengan nama/deskripsi/harga/jenis hasil/aktif; penanganan pesanan dan unggah hasil; pengelolaan melalui izin addon.manage (tidak khusus super pada kode ini).
- backend/routes/cms_defaults.py: benefit VIP lama menyebut konten promosi JPG. Visualizer dan link preset/smart link disebut sebagai contoh layanan di modul; belum memverifikasi katalog database aktual atau daftar harga live.

## Usulan untuk dinilai

Satu menu Layanan Tambahan: Label melihat Pesanan Saya dan Pilihan Layanan; Admin menangani Antrean/Penanganan Saya/Hasil Dikirim/Selesai; Super Admin memakai alur pekerjaan sama plus pengaturan katalog. Konfigurasi layanan ada dalam menu ini, benefit paket tetap di Paket & Kredit menggunakan referensi layanan yang sama.

Katalog menjelaskan hasil/format, satuan per lagu atau per rilisan, kebutuhan bahan, estimasi setelah bahan lengkap, harga atau Termasuk paket, batas revisi. Jangan menyamakan seluruh layanan gratis hanya karena nama paket; jangan otomatis memakai kredit rilisan sebelum ada keputusan.

Label dapat memesan dari menu atau konteks rilisan dengan pesanan yang sama. Usulan: boleh pesan sebelum tayang untuk aset promosi; ketergantungan tiap layanan berbeda (smart link DSP membutuhkan tautan tersedia). Metadata/cover/audio dipakai ulang, formulir hanya kebutuhan tambahan. Harga/benefit dan spesifikasi dikunci saat pesanan diterima. Kekurangan bahan bukan alasan menagih ulang.

Alur usulan: pilih layanan/rilisan/lagu -> lengkapi kebutuhan -> pembayaran atau benefit -> pemeriksaan -> dikerjakan -> hasil dikirim -> diterima/permintaan revisi -> selesai. Revisi tetap dalam pesanan yang sama dengan riwayat versi hasil. Batas revisi/estimasi/batal/kompensasi belum ditetapkan dan perlu dialog sebelum penerapan.

## Celah repo yang perlu diselesaikan saat rancangan matang

- Endpoint status mengizinkan lompat ke delivered/completed tanpa memastikan hasil tersedia.
- Status dikirim versus selesai belum mempunyai konfirmasi label yang tegas pada komponen yang diperiksa.
- Unggah hasil memakai key file yang sama per order/ekstensi sehingga tidak menyediakan versi hasil utuh; endpoint mengizinkan unggah pada completed dan mengubah kembali menjadi delivered.
- Dedupe release/product mencegah duplikasi tetapi juga menghalangi pesanan baru yang sah untuk objek berbeda dalam album atau pesanan ulang; satuan layanan harus disepakati.
- Hak katalog pada repo lama dapat diberikan admin addon.manage; usulan desain terbaru membatasinya pada Super Admin.

Pertanyaan tahap berikutnya: daftar layanan aktual dan hasilnya, harga/satuan, kebutuhan bahan, jatah benefit, batas revisi dan penyelesaian saat label diam, estimasi (1–8 jam informasi staf adalah waktu produksi bukan janji selesai total), pembatalan/ketidakmampuan menyelesaikan. Jangan memaksa semua pertanyaan dijawab sekaligus.

## Kelanjutan pembahasan — formulir dan penanganan

Pengguna meminta melanjutkan setelah usulan formulir dan alur petugas. Rancangan dibawa ke tahap berikutnya, belum izin implementasi/rilis:
- Formulir sesuai layanan; pakai ulang metadata/cover/audio. Bahan pengganti khusus pesanan tidak mengubah katalog.
- Setelah pembayaran/benefit: pemeriksaan -> mulai pengerjaan atau minta kelengkapan yang spesifik; label memperbaiki bagian terkait dalam pesanan yang sama.
- Kelengkapan bahan tidak dihitung sebagai revisi hasil. Kesalahan petugas terhadap spesifikasi diperbaiki tanpa mengurangi jatah revisi; perubahan keinginan label mengikuti cakupan layanan. Jumlah jatah belum final.
- Unggah hasil adalah draft petugas; Kirim hasil merupakan tindakan terpisah setelah pratinjau. Hasil mempunyai versi. Label menerima atau meminta revisi. Tidak otomatis selesai hanya karena label diam.
- Estimasi dimulai setelah kebutuhan lengkap dan pesanan siap dikerjakan, bukan langsung setelah pembayaran. Waktu produksi 1–8 jam dari staf bukan janji total penyelesaian.
- Panel kanan memakai standar referensi terbaru, memisahkan catatan internal dan pesan untuk label.

## Usulan lanjutan untuk dinilai — belum keputusan final

Pengingat antrean siap diperiksa 2/4 jam kerja; kekurangan bahan 4/24 jam dan tindak lanjut 48 jam; hasil menunggu label 24/48 jam dan tindak lanjut petugas 72 jam, tanpa penerimaan otomatis. Durasi pengerjaan per layanan, jangan dipaksa 4 jam untuk pekerjaan video yang dapat 8 jam. Satu daftar revisi per versi hasil; pengiriman berulang tidak menjadi pesanan/biaya baru. Benefit dan spesifikasi dikunci ketika pesanan diterima. Perubahan besar di luar cakupan memerlukan persetujuan label sebelum tindakan atau biaya tambahan. Kegagalan layanan berbayar rupiah belum memiliki kebijakan penyelesaian final; jangan otomatis mengubahnya menjadi kredit rilisan.

## Arah kredit disepakati — kelanjutan dialog

Pengguna menyukai konsep dua fungsi saldo: Kredit Rilisan dan Kredit Layanan, dengan dua desain koin dalam keluarga visual yang sama. Nilai kredit layanan, kelayakan per sumber, perpindahan saldo dan perlakuan kredit lama belum final. Harian/sementara/pembelian/bonus tetap dimensi sumber atau masa berlaku, bukan otomatis koin ketiga. Semua layanan termasuk WAMI dapat disiapkan mendukung pembayaran rupiah/kredit layanan/benefit, namun pengaktifannya dan harga belum disepakati. Ketentuan V11.0 WAMI rupiah/benefit tetap berlaku sampai implementasi baru disetujui. Tidak mengubah hak kredit yang sudah dibeli secara diam-diam.

Pengguna meminta kembali ke bahasan utama Layanan Tambahan. Tahap berikutnya berupa usulan susunan halaman dan hubungan antarakun, bukan implementasi: daftar pesanan sebagai halaman utama bagi label yang sudah punya pesanan; keadaan kosong mengarahkan ke katalog; rincian cepat di panel kanan mengikuti referensi; kebutuhan banyak/video besar dapat dibuka dalam detail penuh. Kedua jalur pemesanan (menu layanan/detail rilisan) menuju pesanan yang sama. Daftar pekerjaan petugas mengacu objek pesanan yang sama. Katalog tidak menggabungkan seluruh benefit menjadi gratis semua layanan.

## Keputusan satuan layanan — disetujui pengguna

Pengguna menjawab "Oke setuju" terhadap susunan berikut:
- Registrasi WAMI: per lagu; pengajuan banyak lagu boleh digabung dalam proses pemilihan, hasil/status tetap per lagu dan tidak membuat pendaftaran ganda tanpa dasar.
- Konten promosi gambar: per set desain, satu konsep untuk satu rilisan. Format/ukuran yang termasuk harus disebutkan; konsep baru adalah set baru. Jangan menganggap Feed+Story sudah menjadi hasil operasional bila staf baru menyediakan satu JPG.
- Video visualizer: per lagu, satu hasil utama dengan durasi/format yang disebutkan. Versi vertikal/potongan pendek bukan otomatis termasuk. Label bisa memilih sebagian lagu dalam album.
- Smart link: per rilisan (Single/EP/Album), satu halaman tautan. Penambahan tautan platform yang belum tersedia merupakan kelengkapan halaman yang sama; batas perubahan setelah selesai belum final.
- Satuan sama untuk rupiah, Kredit Layanan, dan benefit paket. Contoh satu set gratis per rilisan bukan keputusan besaran benefit.
- Cegah duplikasi tindakan/pembayaran; tampilkan pesanan berjalan. Pembelian konsep baru atau versi hasil tambahan tetap dimungkinkan dengan cakupan berbeda.

Belum izin implementasi/rilis. Tahap pembahasan berikutnya: konfigurasi cakupan hasil per layanan sebagai acuan bersama katalog, pesanan, harga dan benefit; besaran harga kredit, benefit, durasi dan jatah revisi belum final. Pertahankan ketentuan pesanan lama saat katalog berubah.

## Rancangan penyelesaian pesanan bermasalah

Pengguna meminta menyelesaikan pembahasan masalah. Ini rumusan rancangan yang diajukan untuk dinilai, bukan izin implementasi/rilis dan bukan konfirmasi angka harga/estimasi/jatah revisi.

1. Bahan kurang/tidak sesuai: status Perlu kelengkapan; petugas menyebut bagian dan alasan, label memperbaiki bagian tersebut dalam pesanan sama. Tidak menagih ulang atau mengurangi jatah revisi. Pengingat 4/24 jam, atensi tindak lanjut petugas 48 jam; tidak batal otomatis. Pengerjaan belum mulai sampai bahan cukup. Jika kekurangan ditemukan setelah pekerjaan dimulai, simpan alasan/jeda/waktu yang sudah berjalan; jangan menghapus keterlambatan sebelumnya.
2. Pengerjaan terlambat: status pekerjaan tetap dengan indikator Lewat estimasi; petugas mencatat sebab dan mengusulkan waktu baru, label diberi pemberitahuan. Estimasi awal tetap tersimpan. Super Admin menerima atensi jika melewati estimasi atau petugas tidak menindaklanjuti. Tidak selesai otomatis, tidak menjadikan catatan kendala sebagai reset waktu.
3. Kesalahan hasil terhadap cakupan yang disepakati: perbaikan tanpa biaya dan tanpa pengurangan jatah revisi, menggunakan pesanan sama/versi hasil baru. Petugas mengklasifikasi dengan alasan; jika label tidak sepakat diarahkan untuk peninjauan Super Admin pada pesanan yang sama.
4. Permintaan baru di luar cakupan: label mendapat ringkasan pekerjaan tambahan, biaya/hak benefit tambahan dan estimasi; tidak memotong saldo/menagih atau mengerjakan tambahan sebelum persetujuan label. Penolakan tambahan tidak membatalkan hak pesanan awal. Pekerjaan tambahan dicatat sebagai perubahan pesanan atau pesanan terkait, bukan mengubah cakupan awal diam-diam; representasi final masih dapat disederhanakan saat UI dibahas.
5. Label belum merespons hasil: Menunggu tanggapan, pengingat 24/48 jam lalu tindak lanjut petugas pada 72 jam; tidak otomatis diterima/selesai, tidak otomatis hapus hasil. Hasil dan riwayat tetap bisa diakses oleh akun berhak.
6. Layanan tidak dapat diselesaikan: petugas Ajukan penyelesaian -> Super Admin meninjau -> tawaran waktu baru/pengganti kepada label. Perubahan layanan/waktu membutuhkan persetujuan label; bila tidak ada penyelesaian yang disepakati dan layanan tidak terpenuhi, kembalikan pembayaran bagian yang tidak terpenuhi. Rupiah kembali lewat jalur rupiah; Kredit Layanan dikembalikan sekali sesuai sumber/ketentuan asal. Tidak otomatis mengonversi rupiah menjadi kredit atau Kredit Layanan menjadi Kredit Rilisan. Untuk benefit paket pulihkan hak layanan; bila paket sudah berakhir, usulan hak pengganti satu kali untuk layanan tersebut, bukan memperpanjang seluruh paket. Untuk hasil parsial jangan memotong berdasarkan persentase perkiraan petugas: rincian hasil yang diterima dan penyelesaian nilainya harus ditinjau Super Admin serta disepakati label.
7. Pengembalian: periksa status pembayaran aktual, kaitkan ke pesanan/pembayaran asal, cegah pengembalian lebih dari yang dibayar/duplikasi. Menyetujui pengembalian belum berarti uang sudah kembali; status Menunggu pengembalian sampai keberhasilan dicatat. Catat jumlah/sumber/alasan/pelaku/waktu; label melihat status dan alasan relevan, tidak catatan internal. Pengembalian menjadi atensi pada dashboard label dan Super Admin, bukan hanya notifikasi. Tidak menyediakan tombol pembatalan bebas untuk label.

Estimasi produksi/jatah revisi/ketentuan nominal masih membutuhkan staf. Jangan memberi estimasi seragam pada visualizer dan pekerjaan ringan. Sebelum rilis prototype, tampilkan data contoh sebagai contoh dan simpan pertanyaan staf yang belum terjawab.

## Kelanjutan setelah alur penyelesaian masalah

Pengguna menjawab "Oke silahkan lanjutkan!" setelah rumusan penyelesaian masalah; lanjutkan pematangan rancangan, belum perintah implementasi atau rilis. Alur masalah menjadi dasar pembahasan berikutnya. Estimasi, harga, jumlah kredit layanan dan jatah revisi tetap belum final.

Usulan penutupan rancangan UI/status:
- Pisahkan status pekerjaan (Menunggu pemeriksaan, Perlu kelengkapan, Dikerjakan, Menunggu tanggapan, Revisi, Dalam penyelesaian, Selesai) dari status pembayaran (Menunggu pembayaran, Dibayar, Termasuk paket, Menunggu pengembalian, Dikembalikan).
- Pesanan belum dibayar terlihat bagi label dengan tindakan Lanjutkan pembayaran, tetapi belum masuk Antrean petugas. Saat benefit terpenuhi dapat masuk pemeriksaan tanpa pembayaran tambahan.
- Lewat estimasi adalah indikator atensi, bukan tahap pengganti pekerjaan. Status Selesai hanya setelah hasil diterima; kasus yang berakhir tanpa hasil memakai penutup spesifik seperti Ditutup · pembayaran dikembalikan, bukan klaim pekerjaan selesai.
- Tampilan daftar menonjolkan status pekerjaan dan satu tindakan relevan, rincian pembayaran di panel; dua status boleh ditampilkan bersama saat pengembalian sensitif.
- Perkembangan menampilkan tahap nyata, bukan persentase buatan. Semua penanda baru wajib masuk Standar & Penanda dengan arti, pemicu, pihak bertindak dan kondisi berakhir.
- Catatan internal dan percakapan/pesan label terpisah. Pengingat menghasilkan atensi operasional; wawasan memuat agregat bila kelak isinya disepakati.
- Cakupan versi usulan: Layanan Tambahan lintas peran, katalog dan benefit terhubung, jalur masalah/hasil/revisi, standar panel kanan global, pembaruan grafik global. Dua fungsi kredit telah disetujui sebagai konsep, tetapi pemisahan saldo/transaksi tidak boleh dianggap siap diimplementasikan tanpa aturan nilai dan transisi; skema kredit layanan tetap ditunda sampai keputusan tersebut, pembayaran rupiah/benefit dapat menjadi baseline.
