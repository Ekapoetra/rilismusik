# Keputusan paket sementara — 23 September 2026

- Flex: bayar per satu rilisan atau per satu album. Definisi batas rilisan/album dan harga belum ditetapkan; jangan mengubah perhitungan lama diam-diam.
- Go, Pro, Business: pilihan bulanan dan tahunan. Harga dan manfaat final akan dibahas kemudian. Data paket lama tidak otomatis dikonversi durasinya.
- Tawaran Perpanjang paket dan Lihat pilihan paket berada di akun label. Management Label internal hanya menampilkan kondisi paket, dampak akses, serta tindakan administratif yang memang diizinkan; bukan tombol pembelian atas nama label.
- Perpindahan Business ke paket satu label memerlukan aturan penanganan label yang sudah dikelola sebelum diterapkan.
- KYC tetap dipertahankan sebagai kondisi pemeriksaan administrasi. Centang reputasi merupakan penilaian terpisah. Dampak KYC ditentukan per tindakan dan objek label.

## Pembaruan pembahasan — pembayaran di muka dan pengiriman

Keputusan terbaru menggantikan usulan membayar Flex saat mengirim: semua member membayar terlebih dahulu. Flex memperoleh jatah pengiriman dari pembelian. Go/Pro/Business memiliki rancangan batas 5 rilisan per hari untuk paket bulanan maupun tahunan; harga dan manfaat final belum ditetapkan. Belum diimplementasikan.

Istilah yang diusulkan: Kredit Rilisan untuk hak pengiriman yang dibeli; Batas Pengiriman Harian untuk pembatasan frekuensi. Hindari menyamakan kredit yang tersimpan dengan batas harian yang direset. Pembedaan kredit rilisan/album, kapan kredit terpakai/dikembalikan, masa berlaku kredit, dan cakupan batas Business masih perlu ditetapkan.

Pengguna mengusulkan penanganan pembatalan/refund melalui pengembalian jatah rilisan. Ini belum menetapkan bahwa seluruh pengembalian uang dihapus: kasus pembayaran ganda, aktivasi gagal, dan pembatalan sebelum layanan tersedia memerlukan ketentuan tersendiri.

Simpan untuk masa depan: konversi royalti menjadi alat pembayaran/kredit layanan, mungkin berlaku lintas paket dan menjadi dasar penyusunan harga. Jangan mengimplementasikan, memotong royalti, atau mengubah perhitungan liabilitas pada tahap ini.

Pesan dashboard yang diminta: Aktivasi akun (persyaratan operasional belum lengkap), Akun sedang diperiksa (pengajuan sedang diperiksa), Lengkapi rekening (rekening belum lengkap). Kekurangan rekening tidak mengembalikan akun operasional menjadi belum aktif. Kondisi perbaikan harus tetap menyediakan arahan yang spesifik.

Istilah KYC tidak ditampilkan pada produk baru; hanya digunakan untuk pemetaan proses/data lama selama pembangunan.

## Pembaruan: satu istilah kredit

Arahan pengguna terbaru: gunakan Kredit untuk seluruh paket. Flex memiliki kredit pembelian yang dapat menumpuk. Paket berlangganan mendapat kredit harian yang diperbarui setiap hari. Sediakan Tambah kredit; pembelian tambahan dicatat terpisah, tidak kedaluwarsa saat paket berakhir, dan dapat digunakan dengan layanan Flex setelah langganan berakhir. Ini menggantikan usulan membatasi pengiriman baru sepenuhnya ketika paket berakhir; pembatasan selain paket tetap berlaku. Cakupan Business setelah berakhir masih perlu ditetapkan.

Usulan yang belum disetujui: tampilkan Kredit Harian dan Kredit Tambahan terpisah, gunakan harian lebih dahulu, reservasi saat submit diterima, konsumsi final saat penyerahan ke distributor berhasil/terkonfirmasi. Revisi pada pengajuan sama tidak mengurangi kredit baru. Pembatalan sebelum penyerahan melepas reservasi; sesudah penyerahan perlu penyelesaian sesuai penyebab, bukan pengembalian otomatis. Kredit pembelian kembali ke sumbernya; kredit harian hanya kembali pada periode asal dan tidak berubah menjadi kredit permanen. Kompensasi kegagalan layanan setelah periode harian berakhir perlu aturan tersendiri. Penyerahan yang hasilnya belum pasti harus direkonsiliasi sebelum debit/pengembalian ulang.

Bukti sumber: releases.py memisahkan submitted/under_review/need_revision/approved/delivered/live dan mengizinkan pengajuan ulang setelah revisi/penolakan. refund_service.py saat ini hanya mencatat refund transfer manual pembayaran rilisan yang ditolak/dihapus, bukan wallet kredit otomatis. Status delivered di repo merupakan tindakan admin, sehingga belum cukup untuk mengasumsikan bukti penerimaan distributor yang otomatis.

Pertanyaan sebelum final: satuan kredit album vs rilisan, biaya aktual dan titik biaya distributor, penolakan setelah penyerahan, pembatalan saat review, batas kredit Business bersama master, pembelian Flex pada label anak setelah Business habis. Konversi royalti tetap ditunda.

## Keputusan satuan kredit dan pengingat kontekstual

- Pengguna menetapkan 1 kredit = 1 lagu. Flex menyediakan pilihan pembelian cepat Single, EP, Album, serta jumlah kredit manual. Ini pilihan jumlah pembelian, bukan jenis mata uang/kredit yang berbeda. Harga bundel dan batas jumlah lagu belum ditetapkan ulang.
- Usulan batas awal mengikuti cakupan harga situs: Single 1 lagu, EP 2–6 lagu, Album 7–12 lagu; belum merupakan keputusan baru pengguna.
- Tidak membuat pengingat terjadwal. Ketika pengguna kembali bertanya tentang tiga data, ingatkan untuk menanyakan staff: rata-rata lagu/album per label per bulan; waktu kerja penanganan termasuk pemeriksaan/revisi; biaya dan waktu WAMI serta pembuatan konten promosi. Harga paket ditunda sampai data mendukung.

## Pembaruan pembayaran dan perpindahan paket

Pada 3 Oktober 2026 pengguna menambahkan arah rancangan berikut untuk disimpan dan disesuaikan dalam pembahasan. Pengembangan fitur serta penerapannya belum diizinkan. Bagian ini menjadi acuan terbaru bila bertentangan dengan usulan terdahulu.

- Seluruh transaksi menggunakan standar rupiah. Kredit menjadi opsi pembayaran; pembayaran rupiah tetap tersedia. Pengguna menegaskan bahwa membayar dengan kredit harus lebih murah daripada membayar rupiah. Nilai kredit, tarif layanan dan besarnya selisih belum ditetapkan.
- Arah ini menggantikan asumsi bahwa pelanggan wajib membeli atau menggunakan kredit untuk setiap pembayaran rilisan. Satu kredit dasar per lagu tetap menjadi acuan jalur kredit yang telah dibahas; tarif rupiah dan tarif layanan lain belum disahkan melalui pembaruan ini.
- Pengguna meminta pengelolaan perpindahan paket mengacu pada ChatGPT dan meminta penyesuaian oleh asisten. Acuan tersebut tidak otomatis menetapkan harga, formula pengembalian, pembayaran berulang atau cakupan kredit yang boleh digunakan.
- Pengguna memastikan seluruh manfaat label lama mengikuti paket dengan tanggal berakhir yang jelas. Tidak perlu mengasumsikan manfaat tanpa batas waktu; manfaat yang telah dibayar perlu dipetakan terhadap tanggal akhir aktual setiap pelanggan.

### Harga rupiah dan pilihan kredit

Usulan penyesuaian: satu pesanan menyimpan layanan, harga rupiah, tarif kredit yang berlaku saat pembelian, pilihan pembayaran dan hasilnya. Membayar dengan salah satu pilihan memenuhi pesanan yang sama, tanpa tagihan tambahan melalui pilihan lainnya. Diskon kredit harus dihitung terhadap biaya memperoleh kredit yang menjadi acuan, termasuk pembelian bundel; jumlah kredit yang lebih kecil tidak cukup untuk membuktikan biaya lebih murah.

Royalti, saldo pencairan dan pembayaran kepada label tetap menggunakan rupiah. Pembaruan ini belum mengesahkan penukaran royalti menjadi kredit, pembayaran campuran rupiah/kredit, atau pengembalian dana otomatis menjadi kredit.

Cakupan kredit untuk pembelian paket masih perlu dipastikan, terutama penggunaan kredit harian/bonus untuk membeli paket yang menghasilkan kredit kembali. Usulan pencegahan: pembelian kredit sendiri dibayar rupiah; tentukan kredit yang memenuhi syarat untuk membeli paket agar tidak terbentuk siklus pembelian/perpanjangan tanpa pembayaran. Ini usulan, bukan batas baru yang telah disepakati. Kredit pembelian, harian, sementara dan bonus tetap memiliki asal serta ketentuan masing-masing.

### Acuan ChatGPT dan penyesuaian untuk Rilis Musik

Dokumentasi resmi yang diperiksa pada 3 Oktober 2026 menunjukkan bahwa [ChatGPT Business](https://help.openai.com/en/articles/8792536-managing-billing-and-seats-in-chatgpt-business) mengenakan selisih prorata untuk peningkatan kursi berbayar pada sisa periode. Penurunan berjadwal dan perubahan bulanan/tahunan berlaku pada pembaruan berikutnya. [Pembatalan langganan ChatGPT](https://help.openai.com/en/articles/7232927-canceling-your-chatgpt-subscription) menghentikan perpanjangan dan biasanya mempertahankan akses sampai periode berjalan selesai. Aturan tersebut khusus pada konteks yang dijelaskan sumber, bukan bukti seluruh paket ChatGPT mengikuti formula yang sama.

Usulan adaptasi untuk Rilis Musik:

| Tindakan | Perilaku yang diusulkan |
| --- | --- |
| Naik paket | Berlaku setelah pembayaran berhasil dikonfirmasi. Pada periode yang sama, tagih selisih sesuai sisa masa aktif dan pertahankan tanggal akhir. Formula, diskon dan pembulatan menunggu harga final. |
| Turun paket | Dijadwalkan setelah masa paket berjalan selesai; manfaat berjalan tetap tersedia sampai tanggal itu. Pengguna dapat membatalkan perubahan yang belum berlaku. |
| Bulanan ke tahunan atau sebaliknya | Jadwal baru berlaku pada periode berikutnya. Bila disertai naik paket, peningkatan memakai periode berjalan, sedangkan perubahan durasi tetap menunggu periode berikutnya. |
| Hentikan perpanjangan | Paket yang sudah dibayar tetap berjalan hingga berakhir. Pembayaran otomatis tidak diasumsikan tersedia; penerapannya menunggu kemampuan penyedia dan persetujuan pelanggan. |

Sebelum konfirmasi, tampilkan paket saat ini, paket tujuan, manfaat yang berubah, tanggal berlaku, tagihan sekarang dan biaya periode berikutnya. Kegagalan atau status pembayaran belum pasti mempertahankan paket aktif sampai hasil pembayaran diketahui. Berpindah paket tidak menggandakan jatah kredit harian dan tidak menghapus kredit pembelian yang masih sah.

### Perlindungan paket dan pelanggan lama

Usulan: manfaat lama dipertahankan sampai tanggal akhir yang sudah dibayar. Perpanjangan menggunakan penawaran baru dengan penjelasan perubahan; perpindahan lebih awal memerlukan persetujuan terhadap dampak manfaat dan perhitungan sisa periode. Jangan langsung menyetarakan paket lama dengan Go/Pro/Business berdasarkan nama atau menganggap nilai prorata paket lama sama dengan harga baru.

Perpindahan Business ke paket satu label harus mempertahankan katalog, royalti, rekening dan riwayat semua label. Penentuan label yang tetap dikelola serta akses setelah perpindahan masih perlu dibahas. Tidak menyalin perilaku penonaktifan workspace ChatGPT sebagai alasan menutup akses royalti label.

Pembahasan selanjutnya: batas kelengkapan data baru bagi label lama selama masa penyesuaian. Kebijakan hadiah historis, harga paket, kelayakan refund serta masukan staf tetap terbuka.

## Pembahasan penamaan dan manfaat paket dengan AI — 5 Oktober 2026

Pengguna meminta menyimpan dahulu usulan penghapusan emblem, kemudian membuka pembahasan nama kredit/token dan paket. Kandidat pengguna adalah Free, Studio, Pro, Business; pengguna juga meminta pengembangan gagasan AI agent untuk pekerjaan internal maupun layanan member. Ini diskusi, belum keputusan nama, manfaat, kuota, harga, penyedia AI, implementasi atau rilis. Usulan penghapusan emblem tetap diparkir; tidak dihapus maupun dikembangkan pada turn ini.

### Nama satuan pembayaran

Penggunaan credits dalam musik memang menunjuk kontributor/peran karya. Sumber primer yang diperiksa: [Spotify — Clickable song credits](https://support.spotify.com/us/artists/article/song-credits/) menyebut metadata produser, engineer, penulis lagu dan artis yang dikirim label/distributor. Repo/formulir lama juga mengenal Lagu & Kredit untuk kontributor, yang telah diusulkan menjadi Lagu & Kontributor. Kredit Layanan masih dapat dipakai dengan konteks yang jelas; istilah kredit bukan otomatis salah.

Rekomendasi asisten untuk dibahas: Token R sebagai nama satuan pembayaran layanan internal Rilis Musik, mempertahankan keluarga visual koin R. Alternatif Unit R lebih literal tetapi kurang kuat sebagai nama produk; Poin R lebih cocok bila fungsi utamanya hadiah/loyalitas, sehingga tidak direkomendasikan sebagai nama utama pembayaran layanan. Harga dan transaksi tetap mengikuti standar rupiah, dengan token sebagai pilihan yang lebih hemat sesuai arahan pengguna. Pergantian nama tidak mengubah nominal, hak, masa berlaku atau pemakaian saldo yang sudah dibeli.

Pemisahan fungsi Kredit Rilisan/Kredit Layanan yang sebelumnya disukai tetap konsep dua fungsi sampai aturan nilai/transisinya final; bila nama token dipilih, istilahnya dapat menjadi Token Rilisan dan Token Layanan dalam keluarga Token R. Tidak menyatukan saldo tersebut dengan kurs 1:1 atau menganggap satu token mempunyai tarif sama untuk seluruh layanan. Acuan satu kredit dasar per lagu tetap perlu dipetakan secara eksplisit saat nama/nilai final disahkan. Sumber pembelian, harian, bonus dan sementara tetap menentukan hak/masa berlaku, bukan empat mata uang atau desain koin baru.

Token R tidak disamakan dengan token pemrosesan model AI. Untuk member, penggunaan AI sebaiknya dinyatakan menurut hasil/proses yang jelas, misalnya pemeriksaan satu draft rilisan atau pembuatan satu set teks promosi. Biaya pemrosesan AI diperhitungkan internal; bukan istilah teknis yang membingungkan saldo produk. Pembelian saldo sendiri tetap mengikuti jalur rupiah; kelayakan sumber token untuk membeli/perpanjang paket belum final dan harus mencegah hadiah/kuota menciptakan siklus langganan tanpa pembayaran.

### Nama paket dan nilai yang ditawarkan

Rekomendasi utama asisten: Basic, Studio, Pro, Business. Basic berarti akun tanpa biaya langganan dengan layanan dibayar sesuai penggunaan. Free dapat digunakan hanya dengan penjelasan Akun gratis, layanan dibayar sesuai penggunaan, karena nama itu tidak boleh memberi kesan distribusi/WAMI/pembuatan konten gratis. Alternatif Starter dapat dipertimbangkan, tetapi kurang cocok untuk label lama yang memilih tanpa langganan. Studio lebih dekat dengan konteks musik daripada Go; Pro tetap menandai kebutuhan layanan lebih luas; Business perlu dibedakan melalui pengelolaan organisasi, bukan sekadar tambahan kuota.

| Paket usulan | Kebutuhan utama | Manfaat calon untuk dibahas |
| --- | --- | --- |
| Basic | Merilis sesekali tanpa langganan | Akses dasar satu label, katalog, laporan dan pencairan miliknya, pembelian rilisan/layanan sesuai pemakaian; bantuan dasar dan pemeriksaan wajib tetap tersedia. |
| Studio | Rutin menyiapkan dan mengirim rilisan | Hak/kuota rilisan yang terukur, nilai pemakaian yang lebih hemat pada volume sasaran, alat penjadwalan/persiapan dan asisten AI metadata/teks promosi dengan kuota jelas. |
| Pro | Mengembangkan katalog dengan dukungan layanan | Manfaat Studio ditambah calon kuota pengurusan WAMI per lagu, konten promosi per set, pembahasan/pendampingan dengan cakupan tertentu dan bantuan analisis katalog. Hasil manusia dibedakan dari draft AI mandiri. |
| Business | Mengelola tim atau beberapa label | Manfaat Pro dengan cakupan/kuota yang disepakati, pengelolaan multi-label, calon akses kolaborator, pekerjaan massal, laporan gabungan dan dukungan operasional terjadwal. Kolaborator member/otomasi baru bukan fitur produksi yang telah tersedia. |

Semua manfaat merupakan usulan, bukan paket yang sudah dapat dijual. Nama baru tidak memetakan paket lama otomatis. Kuota, batas label/anggota, tarif, jatah revisi dan waktu layanan belum ditentukan. Business dapat dibahas untuk tim satu label maupun pengelola multi-label; jangan menghapus pilihan satu/multi-label yang sebelumnya diminta tanpa pembahasan. Hak royalti, laporan dasar, keamanan, pemeriksaan wajib dan kualitas pemrosesan yang benar tidak dijadikan pembeda akses antara paket gratis/berbayar. Standard/Express/MAX tetap layanan kecepatan rilisan yang terpisah; paket Pro/Business tidak otomatis berarti seluruh rilisan memakai Express/MAX.

Paket berlangganan perlu memberi nilai terukur dari pemakaian yang termasuk, penghematan biaya, layanan nyata atau alat kerja. Tidak menaikkan tarif Basic hanya agar langganan terlihat menarik; hitung manfaat dengan volume sasaran dan biaya sungguhan. Jatah rilisan harian berasal dari keputusan terdahulu dan tidak diganti diam-diam. Usulan untuk pembahasan berikutnya: evaluasi kuota per periode langganan bagi rencana EP/Album agar tidak memaksa pengguna merilis setiap hari; ini belum persetujuan mengubah aturan. Kuota AI dapat mempunyai hitungan proses/hasil tersendiri tanpa mengubah saldo rilisan.

Masukan staf tersimpan menjadi acuan biaya, bukan janji waktu layanan: pemeriksaan/pengiriman per lagu, pengerjaan WAMI per lagu dan dokumen batch, serta konten promosi 1–8 jam dengan bobot berbeda. Jatah pengurusan WAMI harus menyebut cakupan, kelengkapan, biaya pihak terkait jika berlaku serta hasil yang bisa diberikan; tidak menjanjikan penerimaan oleh WAMI. Konten gambar per set dan visualizer per lagu tidak diperlakukan sebagai satu jatah kerja yang setara. Biaya langsung, biaya AI dan kapasitas perlu dilengkapi sebelum menetapkan kuota/manfaat tanpa batas. Manfaat lama yang sudah dibayar tetap sampai akhir masa aktif sesuai keputusan transisi.

### AI untuk pekerjaan Rilis Musik

Sumber primer [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) membedakan alur yang ditentukan sebelumnya dari agen yang menentukan penggunaan alat/langkah secara dinamis, dan menganjurkan kompleksitas ditambah berdasarkan hasil evaluasi. Dokumen ini dipakai untuk prinsip rancangan umum, bukan pilihan vendor/framework ataupun bukti integrasi Rilis Musik sudah ada.

Usulan fungsi yang dekat dengan alur saat ini:

- Asisten Rilisan untuk label/staf: membantu kelengkapan metadata, menjelaskan ketidaksesuaian dan menyusun daftar perbaikan. Pemeriksaan format/durasi/ukuran/kalkulasi mengikuti aturan dan alat pemeriksa, bukan tebakan AI. Nama pencipta, hak, identitas atau data yang belum ada tidak diisi karangan.
- Asisten Promosi untuk member: draft deskripsi rilisan, bio berdasarkan bahan yang diberikan, caption, brief dan rencana promosi. Hasil dapat dipilih/diedit pengguna; tidak menjanjikan playlist, jumlah pendengar atau royalti.
- Asisten Katalog untuk member/pengelola: menjawab pertanyaan dari laporan yang boleh diakses, menyebut periode dan sumber serta keterbatasan. Angka dihitung oleh sistem, AI membantu penjelasan; tidak menebak data legacy atau menyebut saldo sebagai pendapatan perusahaan.
- Agen Operasional internal: mengumpulkan konteks pengajuan/tiket, menyiapkan ringkasan, daftar kelengkapan, bahan pengiriman dan draft tindak lanjut sesuai prosedur. Tindakan pengiriman eksternal dan keputusan substantif mengikuti persetujuan petugas berwenang.
- Bantuan Dokumen WAMI: menyiapkan draft data/formulir dari sumber katalog yang terkonfirmasi, memperlihatkan kekurangan dan perbedaan untuk diperiksa. Tidak menandatangani persetujuan, mengesahkan hak cipta atau menyatakan pendaftaran diterima sendiri.

AI internal adalah kemampuan operasional perusahaan dan dapat meningkatkan layanan semua paket; bukan alasan mengurangi kualitas layanan Basic. Pembeda paket adalah alat AI yang memang dapat dipakai member, cakupan hasil dan kuotanya. AI hadir pada formulir rilisan, pesanan promosi, laporan atau panel pekerjaan sesuai konteks, bukan otomatis menambah sidebar/chat baru yang menggandakan fungsi.

Urutan pengembangan yang diusulkan untuk masa depan: evaluasi bantuan internal pada contoh kerja terisolasi; uji waktu, ketepatan, biaya dan batas akses; kemudian tawarkan fungsi member yang telah terbukti sesuai kuota. Belum instruksi mengerjakan tahapan ini atau memisahkan rilis prototipe menjadi dua fase. Proses menyalin ke Believe masih manual menurut masukan staf; otomasi pengiriman memerlukan jalur integrasi yang sah dan hasil terkonfirmasi, bukan diasumsikan tersedia. Agen tidak mengesahkan KTP/rekening/hak, mengubah royalti atau menjalankan pencairan bebas. Izin dibatasi menurut akun dan tindakan; dokumen maupun data label lain tidak terbuka melalui AI. Tidak mengirim data ke penyedia AI pada pembahasan ini.

Prioritas dialog berikutnya yang diusulkan: pilih penamaan dan peran empat paket dahulu, lalu bedah Studio terhadap biaya pemakaian Basic; setelah itu kuota/hasil WAMI, promosi dan AI untuk Pro/Business. Harga dan angka manfaat tidak ditetapkan dalam turn ini.

## Lanjutan nama paket dan pembeda kemampuan kerja — 5 Oktober 2026

Pengguna mendukung arah pembahasan sejauh ini, tetapi meminta penilaian ulang nama paket pertama, termasuk Regular. Nama Basic belum final. Pengguna menegaskan pembeda paket harus mudah dimengerti, memberi kemudahan dan fitur yang benar-benar berguna, serta mengizinkan pembahasan menu yang berbeda antar-paket bila memang diperlukan. Ini arahan rancangan, bukan izin implementasi/menu baru atau rilis. Peruntukan saldo dibahas setelah paket; untuk sekarang pengguna meminta menyebutnya Token. Token R tetap kandidat historis asisten, tidak menjadi nama yang telah dipilih pengguna; tidak mengubah saldo/kode melalui pembaruan istilah ini.

### Kandidat nama pertama

Rekomendasi asisten untuk ditinjau: Regular–Studio–Pro–Business, dengan keterangan Regular: Tanpa langganan, bayar sesuai penggunaan. Regular dinilai lebih netral terhadap usia/pengalaman label daripada Basic/Starter, tetapi namanya sendiri tidak menjelaskan biaya sehingga keterangan tetap diperlukan. Basic mudah dipahami sebagai dasar tetapi dapat terasa sebagai pilihan paling minimal; Essential menonjolkan kebutuhan inti tetapi kurang langsung menjelaskan cara bayar; Mandiri dekat dengan bahasa Indonesia tetapi tidak boleh memberi kesan pelanggan kehilangan bantuan/pemeriksaan staf. Starter kurang cocok untuk label lama yang memilih layanan satuan. Jangan memakai Standard/Standar untuk paket karena sudah menjadi nama layanan kecepatan rilisan. Seluruh penilaian nama merupakan pendapat desain, bukan hasil survei pelanggan atau keputusan nama final.

### Susunan kemampuan dan menu untuk ditinjau

Pembeda terutama pada cara kerja member, bukan nilai/reputasi label atau kualitas pemrosesan wajib. Dasar katalog/rilisan, royalti/laporan/pencairan miliknya, identitas, transaksi, hasil pesanan dan bantuan tersedia sesuai haknya di semua paket. Pengguna Regular tetap dapat membeli layanan satuan seperti WAMI/promosi menurut katalog dan persyaratan yang berlaku. Paket Pro menawarkan kemudahan terintegrasi, cakupan dan jatah layanan; tidak mengambil hak laporan dasar atau memaksa berlangganan untuk mendapatkan hasil layanan satuan yang telah dibayar.

| Paket usulan | Kemampuan yang dirasakan | Menu/ruang calon |
| --- | --- | --- |
| Regular | Menyiapkan satu rilisan/pesanan dengan alur langsung dan membayar sesuai pemakaian. | Menu dasar; layanan satuan di wadah layanan yang ada. |
| Studio | Menyiapkan beberapa rilisan sebagai rencana, memakai ulang data/pengaturan yang sah, melihat kalender dan daftar persiapan lintas draft. | Rencana Rilisan dengan kalender dan persiapan; bantuan AI di formulir rilisan. |
| Pro | Mengelola persiapan kampanye beserta brief, materi promosi, hasil/revisi dan jadwal; pengurusan WAMI dengan jatah/cakupan jelas; bantuan membaca perkembangan katalog. | Kampanye Rilisan yang menautkan pesanan/hasil layanan yang sama; analisis tambahan tetap di konteks katalog/laporan. |
| Business | Membagi pekerjaan ke kolaborator menurut akses, mengelola beberapa label, meninjau proses dan laporan gabungan tanpa berpindah akun untuk tiap tugas. | Tim & Label sebagai ruang pengelolaan member; berbeda dari Staff & Akses internal Rilis Musik. |

Manfaat bersifat calon. Kalender/perencanaan, kampanye terintegrasi, kolaborator member dan AI tidak dinyatakan sudah tersedia di produksi. Kuota, harga, jumlah kolaborator/label dan waktu layanan belum diputuskan. Manfaat Studio/Pro dapat diwariskan ke tingkat berikutnya, sedangkan Business menambah pengelolaan organisasi. Cakupan satu/multi-label tetap perlu diselaraskan dengan pilihan yang diminta sebelumnya; tidak mengubah pengajuan royalti gabungan master menjadi pengajuan per anak.

Rencana Rilisan mengatur pekerjaan persiapan dan jadwal yang diminta; perubahan kalender tidak otomatis mengganti tanggal pengiriman/tayang yang telah disahkan. Validasi wajib dan arahan perbaikan dasar tersedia semua paket. AI Studio dapat membantu menjelaskan kekurangan atau menyiapkan teks dari sumber yang diberikan, tanpa menjadikan kebenaran metadata sebagai keistimewaan paket mahal.

Kampanye Rilisan menghubungkan rencana promosi dengan pesanan layanan, hasil dan revisi yang sudah dirancang, bukan membuat pesanan/saldo/riwayat kedua. Paket Pro dapat menawarkan kuota pengurusan WAMI dan materi promosi dengan satuan jelas; pekerjaan video dan gambar tidak dianggap setara. Pengurusan WAMI tidak menjamin penerimaan pihak WAMI. AI Pro membantu brief/caption dan penjelasan laporan bersumber, tanpa menjanjikan jumlah pendengar/royalti.

Tim & Label adalah rancangan baru untuk kolaborator member: misalnya operator menyiapkan draft dan pengelola meninjau sesuai izin. Ini tidak memberi role Admin Rilis Musik kepada anggota label. Akses ke dokumen, rekening dan keuangan dibatasi menurut kebutuhan/peran, dan seluruh pekerjaan tetap mengacu sumber katalog/pesanan yang sama. Pengelolaan yang lebih luas tidak menggandakan saldo, penghasilan atau hak pencairan.

Setiap menu baru harus mempunyai pekerjaan, masukan, hasil dan hubungan yang jelas. Perubahan kuota/diskon saja ditampilkan dalam menu layanan yang sama; tidak perlu menu khusus untuk membedakan tarif. Jika sebuah ruang hanya variasi tampilan/alat pada proses lama, perluas menu lama. Menu tersendiri digunakan bila pekerjaan berulang mempunyai alur dan objek yang jelas, seperti rencana beberapa rilisan atau kampanye dengan berbagai hasil. Calon menu baru baru masuk navigasi ketika fungsinya siap dan paket/aksesnya sesuai; perbandingan manfaat berada di Pilihan Paket tanpa memenuhi sidebar dengan menu terkunci. Penerapan visual tetap memakai DNA global yang telah dibangun.

Penurunan/berakhirnya paket tidak menghapus katalog, laporan, hasil dan riwayat yang sah. Pesanan yang telah diterima menurut hak/manfaat saat pemesanan tetap mengikuti penyelesaian yang disepakati. Kemampuan premium untuk membuat pekerjaan/rencana baru mengikuti paket yang berlaku; penanganan tim/multi-label sesudah Business berakhir masih membutuhkan kebijakan khusus yang diparkir. Perbedaan ini untuk ruang member; akses dan pekerjaan Admin/Super Admin tetap mengikuti izin internal, bukan paket staf.

Urutan dialog yang diusulkan: kunci nama serta pekerjaan utama masing-masing paket, lalu rincikan Studio sebagai paket berlangganan pertama sebelum menetapkan jumlah/harga; setelah paket jelas baru membedah peruntukan Token sesuai urutan pengguna. Tidak ada perubahan prototipe pada pembahasan ini.

## Pilihan Basic dan rincian Studio untuk ditinjau — 5 Oktober 2026

Pengguna memilih Basic sebagai nama layanan dasar dan meminta melanjutkan rincian Studio. Basic menggantikan kandidat Regular dalam usulan susunan paket terkini; nama kandidat dan pembahasan lama tetap riwayat. Pilihan nama tidak mengesahkan harga, kuota, manfaat baru atau migrasi paket lama. Peruntukan Token tetap dibahas setelah struktur paket. Turn ini hanya diskusi dan pencatatan, bukan izin implementasi/rilis.

### Tujuan dan manfaat Studio yang diusulkan

Studio ditujukan untuk satu label yang rutin menyiapkan rilisan dan membutuhkan perencanaan yang lebih praktis. Satu label dapat mempunyai banyak artis; jumlah artis sendiri bukan pembeda Business. Usulan pesan manfaat: Siapkan rilisan rutin dengan lebih terencana dan hemat. Ini belum janji penghematan yang telah terbukti: biaya langganan dan pemakaian perlu dibandingkan dengan Basic pada volume sasaran yang nyata.

| Manfaat calon | Pekerjaan dan hasil yang dirasakan | Penerapan |
| --- | --- | --- |
| Pemakaian rilisan yang termasuk | Sejumlah pemakaian layanan rilisan menjadi bagian manfaat berlangganan, sehingga nilai paket dapat dibandingkan dengan pembayaran satuan Basic. | Ringkasan manfaat paket yang jelas. Jumlah, satuan saldo dan masa berlaku belum ditetapkan melalui pembahasan Studio. Standard/Express/MAX tetap jalur layanan terpisah; tidak otomatis memberikan percepatan gratis. |
| Rencana beberapa rilisan | Pilih draft yang sudah ada atau buat draft, tetapkan tanggal yang diinginkan, lalu lihat kalender serta persiapan Single/EP/Album milik satu label. | Tab Rencana di menu Rilisan, bukan sidebar/pesanan kedua. Mengacu draft dan lagu yang sama. Basic tetap dapat membuat beberapa draft dan melihat status rilisan miliknya. |
| Templat persiapan | Simpan kombinasi pengaturan pilihan yang dapat digunakan ulang agar isian berulang lebih sedikit. Semua hasil isian awal tetap dapat diedit. | Pada formulir/rencana. Penggunaan data label/artis yang sudah sah serta validasi dasar tetap tersedia di Basic. Templat tidak menyalin ISRC/UPC ke karya baru atau menganggap hak/dokumen/cover baru sudah sah. |
| Ringkasan kesiapan | Lihat kekurangan audio, cover, metadata dan kontributor pada setiap draft/lagu dalam satu daftar persiapan. Buka langsung bagian yang perlu dilengkapi. | Tampilan gabungan dalam Rencana. Pemeriksaan wajib, arahan perbaikan, status dan pemberitahuan dasar tetap untuk semua paket. Ringkasan persiapan tidak menjadi pengesahan distributor. |
| Asisten persiapan | Usulan bantuan memahami isian serta menyusun deskripsi/caption dari bahan yang diberikan pengguna, dengan hasil yang dapat ditinjau dan diedit. | Di konteks draft/formulir. Kuota hasil/proses AI dibahas kemudian; bukan chat/sidebar tambahan dan belum fitur produksi. Tidak mengarang kontributor/hak, menyimpan atau mengirim draft tanpa keputusan pengguna. |

Contoh untuk menjelaskan alur, bukan kuota: label merencanakan dua Single dan satu EP. Ia memilih draft dalam tab Rencana, mengatur tanggal yang diminta, memakai templat, memeriksa kekurangan setiap lagu, melengkapi melalui formulir yang sama lalu mengajukan rilisan setelah siap. Kalender memperlihatkan tanggal rencana dan kesesuaian layanan; perubahan tanggal rencana tidak otomatis mengubah rilisan yang sudah diajukan/disahkan. Rencana bukan fitur pengiriman otomatis.

Studio tetap dapat membeli WAMI, konten promosi dan layanan lain secara satuan menurut katalog yang berlaku. Tidak memasukkan seluruh layanan tambahan, pekerjaan promosi manusia, kampanye terintegrasi, kolaborator/multi-label atau janji jumlah pendengar/royalti ke manfaat Studio melalui usulan ini. Cakupan Pro/Business masih perlu dibedah; hak yang sudah dibeli dan hasilnya tidak dipaywall ulang karena paket.

### Batas keputusan dan kelanjutan

Rancangan lama tentang jatah harian tidak diganti menjadi bulanan diam-diam. Usulan peninjauan untuk EP/Album dan pekerjaan berkelompok tetap terbuka; rincian mekanisme dipisahkan untuk pembahasan Token. Data staf sekitar 50 lagu langganan dan 20–30 lagu Flex per bulan adalah volume keseluruhan, bukan rata-rata satu label atau bukti kuota Studio. Jangan menetapkan angka/harga paket dari pembagian asumsi tanpa data pengguna sasaran, biaya dan kapasitas.

Basic tetap mempunyai kualitas pemeriksaan yang benar, penggunaan katalog/artis yang sah, draft, status, laporan/royalti/pencairan dan bantuan dasar. Studio menambah perencanaan gabungan, templat yang dapat disimpan, manfaat pemakaian yang terukur serta calon bantuan persiapan; perbedaan paket tidak mengorbankan hak dasar. Tidak memaksa berlangganan untuk menyelesaikan draft yang telah dibuat.

Usulan ketika Studio berakhir: katalog, draft, rencana, materi/hasil dan riwayat yang sah tetap tersimpan dan dapat dilihat menurut hak pengguna; draft dapat dilanjutkan melalui Basic dengan biaya/hak layanan yang berlaku. Kemampuan premium untuk rencana/templat baru mengikuti paket aktif. Manfaat lama yang telah dibayar tetap sampai akhir masa aktif dan tidak dipetakan otomatis berdasarkan nama baru.

Urutan diskusi berikutnya: nilai manfaat kerja Studio terlebih dahulu; kemudian rincikan cakupan Pro/Business dan peruntukan Token, baru menetapkan jumlah pemakaian/harga serta membandingkan biaya efektif dengan Basic. Seluruh rincian Studio di bagian ini merupakan usulan asisten, bukan persetujuan manfaat pengguna. Tidak ada perubahan kode, prototipe, saldo atau layanan produksi.

## Persetujuan arah Studio dan usulan empat layanan kecepatan — 5 Oktober 2026

Pengguna menyetujui rincian Studio yang baru dijelaskan: manfaat pemakaian rilisan, perencanaan beberapa rilisan di menu Rilisan, templat persiapan, ringkasan kesiapan dan arah asisten persiapan. Jumlah, harga, mekanisme Token dan kesiapan/penyedia AI tetap belum ditetapkan sebagaimana batas penjelasan sebelumnya. Pengguna kemudian mengusulkan Standard >=7 hari, Express 5 hari, MAX 4 hari dan Ultra 3 hari, dan meminta pertimbangan apakah berlebihan. Empat layanan dan perubahan angka tersebut belum disetujui atau diterapkan.

Pendapat asisten untuk dibahas: pertahankan tiga tingkat Standard–Express–MAX dahulu. Express 5 dan MAX 4 serta Ultra 3 hanya berselisih sehari; tingkat keempat perlu kebutuhan dan alur penanganan yang terbukti, bukan semata harga lebih tinggi. Nama MAX telah memberi kesan tertinggi sehingga Ultra di atasnya memerlukan peninjauan nama/posisi. Rancangan lama di M02-RILISAN-REVIEW.md memakai Standard 7 hari kerja, Express 5 dan MAX 3 dengan pengecualian Jumat; memindahkan MAX ke 4 hari tidak boleh mengurangi ketentuan pengajuan/manfaat yang sudah diterima. Usulan tiga nama tidak sekaligus mengesahkan angka lama sebagai jaminan tayang.

Ada celah mendasar pada janji tanggal: [Spotify — Music not live on release day?](https://support.spotify.com/us/artists/article/music-not-live-on-release-day/) diperiksa 5 Oktober 2026, menyatakan memerlukan 5 hari kerja untuk musik baru dan pengiriman mendekati tanggal rilis bisa menyebabkan keterlambatan. Titik tersebut adalah pengiriman ke Spotify, bukan klik pengajuan label ke Rilis Musik. Sumber ini tidak membuktikan tayang 3 hari mustahil, tetapi angka 3/4/5 hari sejak pengajuan label belum layak dijamin dari rancangan sendiri. Belum ditemukan bukti perjanjian/jalur percepatan khusus Rilis Musik–Believe yang menjamin batas tersebut. Pengiriman internal lebih cepat tidak dianggap otomatis mempercepat pemeriksaan platform.

Sebelum membakukan angka, tentukan apakah hari kerja/kalender, titik pengajuan valid (kelengkapan dan pembayaran terkonfirmasi), jam batas, hari libur, dampak revisi, kapasitas dan cakupan platform. Bedakan jarak minimum pengajuan ke tanggal yang diminta, target pemeriksaan/penerusan internal, dan tayang yang benar-benar terkonfirmasi. Jangan menampilkan Standard >=7 sebagai wajib menunggu lebih lama dari tanggal jauh yang dipilih. Percepatan dapat diusulkan sebagai penanganan prioritas dengan tanggal diminta serta kelayakan yang dijelaskan sebelum pembayaran; bentuk penawaran dan penyelesaian biaya bila komitmen internal gagal masih perlu disepakati, bukan mengganti arti layanan diam-diam.

Calon manfaat Studio yang bisa ditinjau berikutnya adalah jatah Express terbatas jika kapasitas dan cakupannya mendukung. Ini belum manfaat tambahan yang disahkan, belum harga/kuota, dan tidak membuat Studio otomatis memperoleh MAX/Ultra. Ultra tetap kandidat pengguna untuk penilaian, bukan fitur baru ataupun topik yang dianggap telah diputuskan untuk dihapus. Tidak ada perubahan kode, prototipe, layanan atau rilis.

## Tiga tingkat dipertahankan dan pembahasan Pro — 5 Oktober 2026

Pengguna menyetujui pertimbangan sebelumnya dan meminta melanjutkan dialog. Arah terkini mempertahankan Standard–Express–MAX, tanpa menambahkan Ultra. Angka hari tidak menjadi jaminan tayang sebelum kemampuan operasional/jalur distributor, unit hari dan titik hitung diverifikasi. Arah jatah Express terbatas untuk Studio dapat dilanjutkan dengan syarat kapasitas dan biaya jelas; jumlah, harga serta cakupan tetap belum diputuskan. Pengajuan/manfaat yang sudah diterima tidak diubah diam-diam. Tidak ada izin implementasi atau rilis.

Bahasan berikut yang diajukan asisten adalah Pro: mewarisi arah manfaat Studio, kemudian menambah dukungan pengembangan rilisan melalui pengurusan karya, materi promosi dan evaluasi katalog. Rincian berikut masih usulan untuk dinilai, bukan manfaat yang telah disahkan atau fitur produksi.

| Manfaat calon Pro | Hasil yang konkret | Batas yang perlu ditetapkan |
| --- | --- | --- |
| Pengurusan WAMI | Jatah pengurusan per lagu yang dipilih, pemakaian data terkonfirmasi, daftar kebutuhan, pengajuan dan tindak lanjut sesuai proses layanan yang telah dibahas. | Jumlah, cakupan biaya, kelayakan hak dan dokumen; tidak menjamin penerimaan WAMI, tidak otomatis mendaftarkan seluruh katalog atau menggandakan pengajuan yang sudah ada. |
| Konten promosi gambar | Set desain yang dikerjakan petugas berdasarkan brief untuk rilisan tertentu, dengan hasil dan riwayat revisi dalam pesanan yang sama. | Jumlah set, konsep, format dan revisi dijelaskan; video visualizer mempunyai satuan/cakupan tersendiri dan tidak otomatis termasuk. Kesalahan petugas terhadap cakupan tetap diperbaiki tanpa mengurangi revisi. |
| Kampanye Rilisan | Menghubungkan jadwal rencana, daftar materi, pesanan layanan, hasil dan kebutuhan revisi untuk persiapan sebelum/saat/setelah rilis. | Perluasan konteks Rencana Rilisan di menu Rilisan, menautkan pesanan Layanan Tambahan yang sama; tidak menjadi layanan penayangan iklan atau jaminan hasil promosi. |
| Evaluasi katalog dan asisten promosi | Perbandingan dari laporan yang benar-benar tersedia, pemilihan rilisan/lagu/periode serta bantuan draft brief, caption dan penjelasan perubahan angka. | Tetap di katalog/laporan atau kampanye terkait. Laporan dasar terbuka sesuai hak di semua paket; angka dihitung sistem, sumber/periode terlihat, AI tidak menebak data legacy, hak atau hasil masa depan. Kuota AI dan kesiapan belum final. |

Contoh alur, bukan kuota: label memilih satu rilisan untuk kampanye, memeriksa kelengkapan rencana, memilih lagu yang memerlukan pengurusan WAMI serta kebutuhan set promosi, mengirim brief, meninjau hasil/revisi, lalu membaca perkembangan berdasarkan periode laporan yang tersedia. Manfaat paket memenuhi pesanan layanan yang sama; tidak membuat pesanan/pembayaran kedua dari kartu kampanye. WAMI tidak selalu diperlukan untuk setiap rilisan atau setiap bulan; nilai paket jangan dihitung dengan asumsi semua pelanggan selalu memakai seluruh jatah. Label dengan katalog yang sudah terdaftar tetap perlu merasakan nilai melalui materi promosi/perencanaan/evaluasi, tanpa memaksa pendaftaran ulang.

Pro tidak menawarkan jumlah pendengar, playlist atau royalti yang pasti. Pemeriksaan wajib, bantuan dasar dan hasil yang dibeli bukan hak yang hanya tersedia di Pro. Pelanggan Basic/Studio tetap dapat membeli WAMI/konten promosi secara satuan. Pro membedakan manfaat yang termasuk dan pengelolaan terhubung, dengan kapasitas staf nyata; bukan hanya tambahan badge, AI generik atau kuota angka. Express/MAX tetap cakupan terpisah dan Pro tidak otomatis memperoleh MAX tanpa aturan yang disepakati.

Urutan berikut: nilai cakupan hasil Pro dahulu, lalu Business, kemudian peruntukan Token serta jumlah/harga manfaat. Tidak mengaktifkan katalog layanan, AI, kampanye atau paket pada pembahasan ini. Pro belum disetujui melalui respons pengguna yang hanya menerima bahasan percepatan sebelumnya.

## Arah Pro disetujui dan pembatasan manfaat — 5 Oktober 2026

Pengguna menyetujui arah Pro yang telah dijelaskan dan meminta limit/kuota WAMI serta konten promosi gambar agar volume tidak membeludak. Kebutuhan kuota disetujui; jumlah, periode, reset, revisi dan ketentuan penggunaan berikut masih usulan untuk ditinjau. Tidak ada izin implementasi atau rilis. Peruntukan Token tetap menunggu pembahasan tersendiri.

Usulan model: dua kuota terpisah pada setiap periode bulanan paket, WAMI per lagu dan gambar per set desain (satu konsep untuk satu rilisan, format yang ditentukan). EP/Album dengan lima lagu yang dipilih untuk pengurusan WAMI memakai lima jatah, bukan satu karena satu rilisan/pesanan. Varian ukuran gambar yang memang termasuk cakupan satu set tidak dihitung sebagai konsep/pesanan baru; tidak menganggap semua format atau video termasuk. Kuota tahunan dibuka per periode bulanan, bukan seluruh jatah tahun di awal. Periode mengikuti tanggal aktif/pembaruan paket, bukan tanggal satu kalender agar aktivasi pertengahan bulan tidak mendapat periode pendek. Penanganan tanggal akhir bulan tetap perlu dirinci sebelum penerapan.

Sisa manfaat bulanan yang belum digunakan diusulkan tidak menumpuk ke periode berikutnya. Ini hak manfaat paket, bukan menghapus Token pembelian, pesanan berbayar atau manfaat legacy yang masih sah. Ketentuan perlu tampil sebelum pembelian dan tidak diterapkan surut pada paket lama. Saat kuota habis, pembelian layanan tambahan tetap tersedia dengan harga yang terlihat serta persetujuan pengguna; tidak ada biaya/pemotongan otomatis. Penukaran jatah WAMI ke desain atau ke saldo tidak diasumsikan diperbolehkan melalui model ini.

Saat pesanan valid diterima, cadangkan jumlah manfaat sekali untuk periode asal agar pengajuan paralel tidak memakai hak yang sama. Menyimpan draft tidak memakai kuota. Kelengkapan dan revisi dalam cakupan tidak memakai jatah baru; konsep baru/pekerjaan tambahan membutuhkan ringkasan dan persetujuan sebelum hak/biaya tambahan dipakai. Jika layanan tidak dapat dikerjakan karena Rilis Musik, pulihkan manfaat menurut alur penyelesaian yang telah dibahas. Pesanan sah yang diterima selama masa aktif tetap diselesaikan setelah periode/paket berakhir dan tidak mengurangi kuota periode baru. Jika pemulihan setelah periode berakhir diperlukan, hak pengganti satu kali untuk layanan yang sama mengikuti penyelesaian terdahulu, bukan otomatis memperpanjang paket atau menjadi Token permanen. Titik pemakaian final per layanan perlu disejajarkan dengan cakupan hasil dan penutupan pesanan; WAMI pengurusan tidak bergantung janji penerimaan pihak WAMI.

Kuota per pelanggan perlu disertai batas pengerjaan bersamaan sesuai kapasitas total petugas dan estimasi antrean. Jangan menolak hak yang sudah dijual atau menghabiskan masa kuota karena antrean internal penuh; jatah yang telah dicadangkan tetap melekat pada pesanan yang sah. Konfigurasi memakai pengaturan manfaat paket yang merujuk katalog layanan yang sama, tanpa menu/sidebar baru. Tampilkan total jatah, tersedia, dicadangkan/digunakan dan tanggal pembaruan di konteks layanan/paket. Perpindahan paket pada periode sama tidak otomatis memberi kuota penuh kedua; formula manfaat tambahan saat naik paket masih perlu dibahas.

Jumlah jatah tidak ditentukan asal: waktu WAMI per lagu telah dicatat staf, sedangkan angka konten promosi 1–8 jam masih bercampur pekerjaan gambar/video dan belum menunjukkan waktu rata-rata satu set gambar. Kebutuhan verifikasi staf: waktu aktif gambar per set/varian, jatah revisi, kapasitas bulanan dan biaya langsung; volume keseluruhan staf bukan pemakaian per pelanggan. Besaran Pro/Business dan antrean ditentukan dari kapasitas serta biaya tersebut, bukan hanya perkalian jumlah label. Kuota bersama Business masih topik berikutnya, belum diputuskan melalui kuota Pro.

## Kuota Pro disetujui sebagai arah awal; pembahasan Business — 5 Oktober 2026

Pengguna menyetujui sejauh ini model kuota yang dijelaskan dan meminta melanjutkan. Arah awal mencakup kuota WAMI per lagu dan gambar per set, diperbarui per periode bulanan paket (termasuk pembukaan bulanan bagi tahunan), sisa belum digunakan tidak menumpuk, pencadangan saat pesanan valid diterima, revisi dalam cakupan tanpa jatah baru, hak pesanan tetap berjalan setelah periode berakhir, pembelian tambahan atas persetujuan dan pemulihan bila kegagalan internal. Jumlah, harga, format hasil, revisi dan rincian teknis tanggal/estimasi tetap menunggu penetapan serta kapasitas. Persetujuan rancangan bukan izin implementasi/rilis.

Asisten melanjutkan Business untuk ditinjau: ruang kerja organisasi bagi satu label dengan tim maupun pengelola beberapa label. Pilihan satu/multi-label yang telah diminta tetap diperhitungkan. Business mewarisi alat Studio/Pro dengan cakupan manfaat tersendiri, bukan otomatis menggandakan kuota Pro untuk setiap label. Seluruh rincian Business berikut masih usulan.

| Kemampuan Business calon | Perilaku yang diusulkan |
| --- | --- |
| Tim dengan akun masing-masing | Undang anggota, tetapkan label yang boleh dikerjakan dan tindakan yang diizinkan. Contoh peran pengelola utama, pengelola dan operator; izin keuangan/dokumen sensitif ditentukan tersendiri. Batas anggota belum ditetapkan. |
| Pengelolaan satu atau beberapa label | Pilih label aktif ketika bekerja; identitas, katalog, formulir, kontrak, persyaratan dan riwayat tetap merujuk label sasaran. Ringkasan keseluruhan hanya memuat label yang boleh diakses. Membeli paket tidak memberi hak atas label lain atau memindahkan katalog/kepemilikan. |
| Pembagian dan tinjauan pekerjaan | Operator menyiapkan draft/bahan, pengelola meninjau dan pihak berwenang mengajukan. Tinjauan internal dapat diaktifkan sesuai kebutuhan, bukan langkah wajib tambahan bagi semua pelanggan. Pemeriksaan Rilis Musik tetap mengikuti pengajuan yang sama. |
| Kuota layanan bersama | WAMI dan set gambar menjadi jatah Business bersama per periode, terpisah per layanan; pemakaian tercatat menurut label dan pesanan. Menambah label/anggota tidak otomatis menerbitkan jatah baru. Jumlah sesuai kapasitas dan harga, belum ditentukan. |
| Ringkasan pekerjaan dan laporan gabungan | Tampilkan pekerjaan/rencana/kampanye serta laporan yang tersedia, dengan filter label dan rincian sumber. Angka tidak dijumlahkan dua kali pada master dan anak. Bantuan AI jika kelak tersedia mengikuti izin/sumber yang sama, tanpa menebak data. |

Calon menu Tim & Label mengatur tim pelanggan dan hubungan pengelolaan label. Staff & Akses tetap untuk petugas internal Rilis Musik. Rencana/kampanye memakai menu Rilisan yang sudah diusulkan, pesanan memakai Layanan Tambahan yang sama, laporan tetap dalam wadah royalti/laporan. Tidak membuat sidebar duplikat setiap anak label. Seluruh tampilan mengikuti DNA dan standar global yang telah ditetapkan; belum ada pembuatan UI.

Penarikan master tetap menggunakan akumulasi saldo tersedia seluruh label yang dikelola menurut ketentuan yang sudah disepakati, dengan ambang Rp1.000.000; rincian per label dipertahankan untuk penelusuran. Business tidak otomatis memberi operator hak melihat keuangan, mengganti rekening atau mengajukan penarikan. Hubungan label yang sudah ada memakai jalur kewenangan/verifikasi pengelola yang sah; aturan klaim lama yang diparkir untuk tim tidak diselesaikan sepihak. Pembatasan salah satu label ditangani sesuai lingkupnya, tidak otomatis mencabut login/akses semua label dalam pengelolaan.

Katalog, royalti, hasil dan riwayat yang sah tetap dipertahankan jika paket berakhir. Kebijakan aktivitas baru bagi anggota tim, pilihan label aktif dan pengelolaan multi-label ketika turun paket masih celah yang perlu dibahas; tidak otomatis memutus hubungan atau menghapus hak. Mencatat celah tidak mengesahkan kolaborasi berbayar tetap penuh tanpa batas setelah kedaluwarsa. Sesudah manfaat Business dinilai, pembahasan peruntukan Token dapat dilanjutkan; harga/kuota, migrasi manfaat lama serta izin implementasi/rilis tetap terpisah.

## Business disimpan; pemetaan fungsi Token — 5 Oktober 2026

Pengguna meminta menyimpan dahulu Business lalu melanjutkan ke Token. Simpan rancangan Business beserta celah masa berakhir/penurunan, batas label/anggota, kuota dan harga untuk dibahas kembali; tidak menafsirkan permintaan menyimpan sebagai pengesahan seluruh detail atau izin implementasi/rilis. Nama satuan tetap Token sesuai pilihan pengguna. Pembahasan ini memetakan penggunaan, belum menetapkan kurs/tarif, paket pembelian, kuota penerbitan atau migrasi saldo.

Usulan asisten meneruskan konsep dua fungsi yang sebelumnya disukai: Token Rilisan untuk pembayaran rilisan dan percepatannya, serta Token Layanan untuk WAMI, desain promosi, visualizer, smart link dan layanan tambahan lain yang memenuhi syarat. Acuan sebelumnya satu kredit Standard per lagu dapat dipakai menilai satu Token Rilisan Standard per lagu; EP/Album mengikuti jumlah lagu. Baseline prototype Express 2/MAX 3 per lagu bukan otomatis keputusan tarif baru. WAMI tetap per lagu, gambar per set desain, visualizer per lagu, smart link per rilisan; jumlah Token Layanan untuk setiap unit ditetapkan menurut tarif/cakupan. Dua saldo tidak dijumlahkan sebagai satu nominal yang setara dan tidak dikonversi 1:1 tanpa nilai/hak yang disepakati. Dua varian koin R tetap arah visual, bukan pembuatan aset pada turn ini.

Seluruh layanan tetap mempunyai harga rupiah dan pilihan pembayaran Token yang berlaku. Sesuai keputusan pengguna, jalur Token harus lebih murah dalam nilai rupiah efektif berdasarkan biaya membeli jumlah Token yang diperlukan, bukan sekadar jumlah unit lebih kecil. Tampilkan tarif rupiah, tarif Token, nilai perbandingan, kebutuhan pembelian saldo serta sisa saldo/top-up secara jelas. Harga, diskon/bundel serta kecukupan pembelian minimal perlu diuji sebelum klaim hemat. Token pembelian ditambah setelah pembayaran rupiah terkonfirmasi. Tidak mengaitkan harga dengan angka contoh prototipe atau melakukan transaksi nyata.

Kuota WAMI/desain yang termasuk Pro/Business adalah hak layanan terpisah: ketika memenuhi pesanan lewat manfaat paket, tidak sekaligus memotong Token/rupiah atau menerbitkan saldo yang otomatis bisa dipakai ulang. Pesanan menampilkan satu jalur: Termasuk paket, Bayar rupiah atau Bayar dengan Token yang memenuhi syarat; pembayaran/benefit disimpan pada pesanan yang sama. Pembayaran campuran tidak disahkan melalui pembahasan ini. Kuota tidak otomatis dapat ditukar antar-layanan/menjadi Token.

Pisahkan fungsi saldo dari asalnya: pembelian, pemberian paket, bonus, sementara/pemulihan. Token pembelian tetap mengikuti hak permanen/tidak habis karena langganan berakhir yang sudah disepakati. Token paket mengikuti masa/reset manfaat yang disetujui; jatah harian lama belum diubah menjadi bulanan hanya karena kuota WAMI/desain bulanan. Bonus mengikuti sumber/jenis pemberian: batas klaim 48 jam terpisah dari masa berlaku saldo setelah klaim; bonus permanen dan sementara tidak disamakan. Saldo sementara menampilkan waktu kedaluwarsa aktual, tidak diberi 48 jam baru setiap pembukaan/perubahan; aturan pemulihan sumber harian/sementara mengikuti pemeriksaan ketentuan lama. Rincian pemberian harian/periode, urutan sumber dan kelayakan penggunaan pada setiap fungsi perlu dibahas sebelum implementasi.

Untuk rilisan, pengajuan yang diterima mencadangkan saldo sekali; penyelesaian mengikuti konfirmasi tayang per lagu sesuai rancangan yang telah disepakati, termasuk EP/Album parsial. Untuk layanan tambahan, kaitkan pemakaian/pemulihan pada hasil dan cakupan pesanan yang sama; titik final per layanan masih perlu diselaraskan. Pengembalian rupiah mengikuti jalur rupiah, Token mengikuti fungsi/sumber asal dan hak manfaat dipulihkan sebagai layanan sesuai ketentuan; tidak memaksa rupiah menjadi Token atau memindahkan sumber sementara ke permanen. Royalti/pencairan tetap rupiah dan penukarannya menjadi Token masih diparkir.

Pembelian/perpanjangan langganan melalui Token belum ditetapkan. Usulan tahap awal memfokuskan Token pada rilisan dan layanan tambahan; kelayakan Token paket/bonus untuk membeli paket penghasil Token memerlukan aturan yang mencegah siklus penerbitan manfaat tanpa pembayaran. Pemakaian AI bagi member memakai hasil/proses yang jelas pada paket/layanan sesuai keputusan kelak, bukan token pemrosesan model sebagai saldo produk. Nama baru tidak memindahkan atau menurunkan hak saldo lama diam-diam; perlu pemetaan sumber/fungsi/nilai/masa berlaku yang dapat ditelusuri. Dialog berikutnya menilai apakah pemberian Token paket tetap harian atau per periode agar cocok untuk Single/EP/Album. Tidak ada perubahan kode, saldo, data pelanggan atau rilis.

## Pemberian Token paket harian atau bulanan — usulan 5 Oktober 2026

Pengguna meminta melanjutkan pembahasan sesudah pemetaan fungsi Token. Arah dua fungsi dan pemisahan sumber menjadi dasar dialog; kelanjutan bukan penetapan nilai/konversi/kuota atau izin implementasi. Business dan kebijakan akhir paketnya tetap disimpan, tidak dibuka kembali dalam turn ini.

Rekomendasi asisten untuk ditinjau: Token Rilisan paket diberikan sekaligus di awal setiap periode bulanan, berlaku sampai pembaruan berikutnya, dengan sisa yang belum dicadangkan tidak menumpuk. Bulanan mengikuti tanggal aktif/pembaruan paket (masa awal setelah aktivasi sesuai aturan terdahulu), bukan tanggal satu kalender. Tahunan tetap menerbitkan jatah bulanan selama masa aktif, bukan seluruh Token setahun di awal. Ini usulan mengganti rancangan harian yang telah dibahas; belum mengganti aturan aktif atau manfaat lama sampai pengguna menyetujui kebijakan, jumlah dan transisinya.

Dasar: pengajuan EP/Album membutuhkan pencadangan per lagu secara utuh; jatah harian yang tidak menumpuk dapat memaksa pembelian tambahan meskipun pelanggan jarang memakai manfaat pada hari lain. Jatah bulanan memberi pengguna kesempatan menyiapkan beberapa rilisan sesuai rencana. Contoh satu Album 10 lagu Standard hanya menjelaskan satuan dasar yang sebelumnya dibahas, bukan kuota bulanan yang ditetapkan. Kelayakan tanggal/percepatan, kelengkapan dan kapasitas tetap mengikuti aturan tersendiri.

Jumlah bulanan dihitung berdasarkan pemakaian sasaran, biaya dan kapasitas nyata; jangan otomatis mengalikan 5 Token/hari menjadi 150 Token yang dapat dipakai sekaligus. Angka 150 hanya ilustrasi periode 30 hari dan bukan pemberian baru: saldo bebas bulanan mempunyai fleksibilitas/beban berbeda dari jatah harian. Batas antrean/pengerjaan dibedakan dari hak pemakaian Token; bila batas pengajuan harian dipertahankan, definisinya perlu mengizinkan EP/Album utuh, bukan diam-diam memecah karya atau mempertahankan batas lagu yang membuat manfaat bulanan tidak dapat digunakan. Jenis/jumlah batas operasional belum ditentukan pada turn ini.

Token pembelian tetap tersimpan sesuai hak permanen yang sudah disepakati. Bonus dan sementara mengikuti ketentuan pemberian/masa berlaku, tidak ikut hangus hanya karena periode paket berganti. Penggunaan sumber yang memenuhi syarat mendahulukan kedaluwarsa terdekat, kemudian saldo permanen; sumber dan jumlah ditampilkan sebelum pengajuan agar pemakaian Token pembelian yang diperlukan jelas dan disetujui. Jika saldo tidak cukup, pengguna dapat memilih pembelian tambahan atau jalur pembayaran yang berlaku; tidak ada debit rupiah otomatis ataupun persetujuan pembayaran campuran melalui model ini.

Saldo paket yang sudah dicadangkan pada pengajuan valid sebelum periode berakhir tetap melekat pada pengajuan/periode asal. Pergantian periode tidak membatalkan pengajuan, tidak menagih lagi dan tidak memotong jatah periode baru. Penyelesaian rilisan tetap per lagu ketika tayang terkonfirmasi. Pemulihan setelah periode berakhir perlu disejajarkan dengan ketentuan sementara/pengembalian yang telah dibahas agar hak pengganti dapat dipakai dan tidak otomatis menjadi saldo permanen; durasi pemulihan bulanan belum disahkan melalui rekomendasi ini.

Pemberian bulanan ini khusus usulan Token Rilisan paket. Manfaat WAMI/desain pada Pro dan calon Business tetap berupa kuota layanan langsung, tidak sekaligus menerbitkan Token Layanan untuk manfaat yang sama. Pemberian Token Layanan tersendiri dari paket/bonus masih perlu keputusan cakupan dan nilai. Cakupan jatah Express calon Studio perlu menjelaskan apakah memenuhi seluruh layanan atau hanya biaya percepatan agar tidak menggandakan manfaat/tagihan; hal itu belum diputuskan.

Pengaturan sumber/masa berlaku, jumlah per paket, kapasitas antrean, prorata/upgrades tanpa penerbitan ganda dan transisi manfaat lama perlu ditetapkan sebelum penerapan. Pelanggan lama mempertahankan ketentuan yang sudah dibayar sampai tanggal berakhir sesuai keputusan sebelumnya; tidak menyamakan jatah harian lama dengan jatah bulanan baru tanpa perhitungan/penjelasan. Tidak ada perubahan kode, saldo, pengajuan, pelanggan atau rilis.

## Tarif Token Rilisan dan simulasi jumlah paket — usulan 5 Oktober 2026

Pengguna meminta membahas kelanjutan pemberian bulanan: jumlah Token paket dan tarif layanan. Permintaan membahas belum menetapkan angka komersial, mengganti manfaat aktif atau memberi izin implementasi/rilis. Business tetap disimpan; jumlah dan kebijakan organisasinya tidak ditetapkan melalui simulasi ini.

Usulan acuan perhitungan meneruskan baseline prototype, untuk ditinjau terhadap harga rupiah dan biaya sebelum disahkan:

| Layanan | Total Token Rilisan per lagu | Rincian dalam simulasi |
| --- | --- | --- |
| Standard | 1 | Biaya dasar rilisan |
| Express | 2 | Dasar 1 dan tambahan percepatan 1 |
| MAX | 3 | Dasar 1 dan tambahan percepatan 2 |

Angka Express/MAX adalah total, tidak ditambahkan kembali pada tarif Standard. Tarif unit layanan yang sama diusulkan berlaku bagi semua paket; kapasitas/tanggal yang benar-benar dapat dipenuhi tetap harus diperiksa. Satu EP lima lagu dalam simulasi memerlukan Standard 5, Express 10 atau MAX 15 Token. Album sepuluh lagu memerlukan 10/20/30. Ketentuan pencadangan dan penyelesaian per lagu tetap mengikuti rancangan terdahulu.

Untuk melihat bentuk manfaat secara konkret, gunakan simulasi 10 Token Rilisan per periode bulanan untuk Studio dan 10 untuk Pro. Angka 10 dipilih untuk menguji contoh Album sepuluh lagu Standard, bukan hasil verifikasi kapasitas/biaya atau rekomendasi kuota final. Basic tidak mempunyai pemberian bulanan dari langganan dalam calon model ini; saldo pembelian/bonus yang sah tetap mempunyai haknya sendiri. Sepuluh Token setara sepuluh lagu Standard, lima Express atau tiga MAX dengan satu Token tersisa, sebelum manfaat percepatan tambahan. Studio dan Pro diusulkan mempunyai jatah rilisan setara pada tahap awal: nilai tambah Pro terutama berupa kuota pengurusan WAMI, set desain dan Kampanye Rilisan, dengan jumlah/cakupan yang masih perlu ditetapkan. Perbedaan Token antar-paket dapat ditinjau kembali bila pola pemakaian dan biaya mendukungnya; nama paket tidak otomatis menggandakan penerbitan Token.

Manfaat Express terbatas pada Studio perlu dihitung terpisah. Usulan cakupan: menanggung tambahan percepatan 1 Token per lagu pada model 1/2/3, sedangkan biaya dasar 1 Token tetap diambil dari saldo yang dipilih. Jumlah lagu yang mendapat manfaat belum ditetapkan. Satu unit manfaat berlaku per lagu, bukan otomatis seluruh EP/Album; tampilan ringkasan harus menjelaskan jumlah lagu yang ditanggung dan sisa Token yang dibayar sebelum pengajuan. Pemanfaatan sebagian kuota pada satu EP/Album tidak mengubah sebagian lagu menjadi layanan berbeda atau membebankan percepatan dua kali. Manfaat ini tidak diterbitkan sebagai Token Layanan atau saldo yang bisa dipakai ulang.

Nilai beli Token, harga rupiah Standard/Express/MAX dan diskon perlu dihitung bersama agar setiap jalur Token yang ditawarkan memang lebih murah menurut ketentuan pengguna. Rp35.000 yang pernah dibahas sebagai harga kredit lama bukan otomatis harga rupiah layanan baru atau kurs Token baru. Jangan mengunci kelipatan 1/2/3 bila setelah pemeriksaan ternyata tidak memenuhi perbandingan harga atau biaya pengerjaan; angka saat ini hanya acuan pembahasan.

Jumlah final membutuhkan jumlah pelanggan sasaran, penggunaan per pelanggan, biaya pekerjaan lengkap (termasuk tindak lanjut/revisi), kapasitas total serta beban WAMI/desain. Volume staf yang telah dicatat merupakan total pekerjaan bulanan dan tidak boleh dipakai sebagai pemakaian satu label. Uji beban maksimal dan rata-rata; Token yang dibeli tambahan juga menambah antrean. Kuota yang disepakati harus dapat dilayani, dengan estimasi/kapasitas yang dinyatakan sebelum pembayaran/pengajuan. Manfaat lama yang telah dibayar tetap mengikuti hak/tanggal berakhirnya; simulasi ini tidak menurunkan atau memigrasikan saldo pelanggan.

## Harga beli Token dan tarif rupiah pembanding — usulan 5 Oktober 2026

Pengguna meminta melanjutkan setelah simulasi tarif/jatah. Ini pembahasan harga untuk dinilai, belum pengesahan jumlah/harga, pengubahan unit lama atau izin implementasi/rilis. Pemeriksaan sumber menemukan dua acuan yang perlu dipertimbangkan bersama: repo-reference-v10/backend/routes/cms_defaults.py, bagian pricing, memuat Rp35.000 per lagu dan Rp200.000 paket Album. Test referensi test_iter71_ppr_tiered_pricing.py menerangkan Album memakai tarif paket, sedangkan Single/EP mengikuti jumlah lagu. Ini default/rancangan repo, bukan verifikasi harga database atau transaksi live. Prototype V12.0 memakai harga kredit Rp35.000 serta penawaran bundel contoh; penawaran prototype bukan otomatis harga komersial yang telah disahkan.

Benturan: bila tetap memakai Rp35.000 untuk harga satu Token Rilisan dan sepuluh Token untuk Album sepuluh lagu, biaya perolehan Rp350.000 melampaui tarif rupiah Album Rp200.000. Bahkan harga Token Rp30.000 masih menghasilkan Rp300.000 untuk sepuluh lagu. Ketentuan pembayaran Token selalu lebih murah tidak bisa dipenuhi hanya dengan diskon harga unit Single. Jangan menaikkan harga rupiah Album diam-diam untuk membuat perbandingan tampak hemat.

Usulan asisten: uji harga pembelian dasar Token Rilisan Rp30.000 per unit, dengan acuan rupiah Single Standard Rp35.000; mempertahankan bentuk tarif Single/EP Standard 1, Express 2, MAX 3 per lagu. Tarif rupiah Express Rp70.000 dan MAX Rp105.000 merupakan simulasi asisten mengikuti rasio 2/3, bukan harga yang ditemukan di repo atau keputusan operasional. Dengan simulasi tersebut, biaya membeli Token adalah Rp30.000/Rp60.000/Rp90.000 per lagu, selisih Rp5.000/Rp10.000/Rp15.000 (sekitar 14,29 persen).

Untuk mengakomodasi acuan Album, usulan baru yang perlu persetujuan pengguna adalah tarif layanan Album Standard khusus 6 Token Rilisan total (biaya perolehan Rp180.000), dibanding acuan rupiah Rp200.000, hemat Rp20.000 atau 10 persen. Ini usulan pengecualian Album terhadap rancangan satu Token Standard per lagu untuk semua rilisan yang dibahas sebelumnya; belum menggantikan aturan itu. Diskon melekat pada pesanan layanan Album dengan cakupan/jumlah lagu yang jelas, bukan saldo khusus yang diam-diam dapat membiayai Single murah, ataupun jenis Token baru. Cakupan kelayakan Album dan tarif percepatan Album masih perlu ditetapkan; jangan otomatis mengalikan tarif bundel dengan 2/3 sebagai janji harga. Tarif Single/EP dan tarif Album akhir harus diuji pada batas cakupan agar jenis rilisan tidak mudah dipilih hanya untuk menghindari biaya.

Pencadangan/penyelesaian Album tetap per lagu. Jika bundel disetujui, alokasi tiap lagu harus berasal dari total tarif pesanan yang benar-benar dibayar; tidak menagih kembali satu Token penuh per lagu atau mengembalikan tarif Single atas lagu yang dibayar dengan diskon Album. Contoh sepuluh lagu dan total enam Token menunjukkan kebutuhan alokasi pecahan/ketelitian pembukuan serta pembelian pas kebutuhan, bukan mengesahkan implementasinya. Kuota bulanan sepuluh Token sebelumnya tetap simulasi, dan manfaat jumlah lagu harus dihitung ulang bila tarif bundel dipilih.

Usulan harga pembelian dasar Token Layanan Rp10.000 per unit, tetap saldo/fungsi terpisah dari Token Rilisan tanpa konversi otomatis. Contoh WAMI dengan acuan rencana harga baru Rp100.000 per lagu di repo: 9 Token Layanan, biaya perolehan Rp90.000, selisih Rp10.000 atau 10 persen. Masukan staf mencatat harga WAMI sebelumnya Rp50.000 dan rencana Rp100.000 belum mempunyai transaksi web baru; ini harga jual, bukan bukti biaya. Pesanan/penawaran lama yang sah tidak dinaikkan surut. Harga Token Layanan, tarif WAMI dan layanan lain tetap usulan; hak WAMI yang termasuk paket memenuhi pesanan tanpa debit Token/rupiah kedua.

Pembelian diusulkan dapat pas jumlah kebutuhan, termasuk satu unit untuk Single, agar label tidak dipaksa membeli bundel besar demi satu pesanan. Kebutuhan pecahan bila diskon/pelepasan parsial dipilih perlu keputusan ketelitian unit dan minimum pembelian. Diskon pembelian massal belum ditambah; hemat dasar sudah berasal dari tarif pembayaran Token. Biaya yang dibebankan pada label harus mencakup biaya wajib pembayaran yang relevan sebelum menampilkan perbandingan; pembelian minimum/sisa saldo ditunjukkan terpisah. Harga dasar yang berubah hanya berlaku pada penawaran/pesanan baru sesuai tanggal efektif; pesanan diterima mempertahankan snapshot harga/cakupan. Saldo lama membutuhkan pemetaan hak, sumber, nilai dan masa berlaku yang telah diparkir, tidak otomatis berkurang atau diganti dengan harga simulasi ini.

Kelayakan harga harus diperiksa terhadap biaya kerja lengkap, biaya langsung dan biaya pembayaran yang berlaku. Selisih 10–14,29 persen adalah perhitungan simulasi, bukan bukti keuntungan atau kapasitas staf. Harga paket Studio/Pro/Business, jumlah manfaat akhir, penukaran saldo dan transisi belum diselesaikan pada turn ini. Titik keputusan berikut yang perlu dinilai adalah mempertahankan tarif layanan Album khusus, karena mengubah biaya Token, jumlah lagu yang dapat memakai manfaat bulanan dan cara pemulihan parsial.


### Token diparkir; rilis prototype V12.1 — 5 Oktober 2026

Pengguna tidak menyetujui usulan harga terakhir dan meminta memarkir pembahasan Token. Angka harga, jumlah manfaat, konversi, tarif bundel Album, serta dua saldo Token tidak diterapkan. Proposal sebelumnya tetap merupakan riwayat diskusi, bukan kebijakan yang disetujui. Perilaku kredit, harga dan hak lama pada V12.0 menjadi baseline.

Permintaan merasakan rilis terbaru dilaksanakan sebagai prototype V12.1: pemantauan dana dan katalog, tindak lanjut data label lama, serta Rencana dan Kampanye Rilisan. Paket Basic/Studio/Pro/Business adalah arah nama dan manfaat yang telah disepakati; angka dan kebijakan komersial yang belum final tidak dijadikan penawaran baru. Business rinci dan emblem tetap diparkir. Rilis ini tidak melakukan migrasi atau transaksi produksi.
