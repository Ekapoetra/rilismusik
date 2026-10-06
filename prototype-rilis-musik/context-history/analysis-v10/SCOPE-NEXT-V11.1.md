# Cakupan rancangan V11.1

Status: siap menjadi acuan rilis setelah dialog. Pengguna menjawab "Oke silahkan.." terhadap langkah memastikan cakupan rilis, bukan perintah eksplisit mengimplementasikan atau merilis. Jangan mengubah prototype atau server sampai pengguna meminta eksekusi/rilis.
Baseline: prototype-v11.0, versi berikutnya V11.1. Versi lama dipertahankan; sources/ dan repo-reference-v10 read-only.

## 1. Layanan Tambahan lintas akun

- Label: Pesanan Saya dan Pilihan Layanan, akses kontekstual dari rilisan ke pesanan yang sama.
- Admin: antrean, penanganan, kelengkapan, hasil, revisi dan tindak lanjut. Super Admin: alur yang sama plus katalog dan keputusan penyelesaian.
- Satuan disepakati: WAMI per lagu (tetap menu WAMI yang ada), konten gambar per set desain, visualizer per lagu, smart link per rilisan.
- Metadata katalog dipakai ulang; bahan pengganti khusus pesanan tidak mengubah rilisan.
- Harga/benefit/cakupan/estimasi/revisi disimpan pada pesanan diterima. Katalog baru tidak mengubah pesanan lama.
- Unggah draft hasil berbeda dari Kirim hasil; hasil mempunyai versi. Label menerima atau mengirim revisi; kesalahan petugas tidak mengurangi jatah revisi.
- Jalur bahan kurang, terlambat, di luar cakupan, label diam, layanan tidak terpenuhi dan pengembalian mengikuti analysis-v10/ADDON-SERVICES-DISCUSSION.md. Pengingat tanpa batal/selesai otomatis.
- Pekerjaan, pembayaran dan pengembalian dipisahkan. Cegah aksi/pembayaran/pengembalian ganda, duplikasi kerja dan akses data akun lain.
- Semua penanda baru masuk Standar & Penanda. Atensi tindakan mengikuti desain compact statis V10.9, tanpa menghidupkan animasi yang dicabut.

## 2. Panel kanan global

Terapkan struktur referensi codex-clipboard-28e2c11c-f64d-4814-a4d1-4ac0e64b9067.png ke panel detail dari kanan di semua menu/peran yang memilikinya. Header, identitas, ringkasan, perkembangan bila relevan, hasil/kebutuhan tindakan, timeline, catatan sesuai akses. Gunakan komponen bersama dan DNA tampilan; tidak menyalin fitur komunikasi/persentase palsu. Jaga posisi scroll halaman asal, tema, ukuran responsif dan akses sentuh.

## 3. Grafik global

Terapkan bahasa visual referensi codex-clipboard-3d826793-d6a5-4d61-bfec-80c355c2207d.png: hirarki judul/periode, garis/batang halus sesuai data, sorotan, tooltip bebas potong, ringkasan berbasis data bila tepat, animasi masuk/transisi tenang, reduced motion dan sentuhan iPad. Pertahankan tipe grafik jika perlu untuk komposisi/perbandingan, warna semantik dan perhitungan. Tidak menyamakan semua grafik menjadi tren merah atau menciptakan kesimpulan sebab perubahan.

## Ditunda secara eksplisit

- Pemisahan saldo/transaksi Kredit Rilisan dan Kredit Layanan, nilai, kelayakan sumber, konversi dan hak kredit lama. Dua desain koin tetap konsep, bukan saldo aktif baru. Pembayaran layanan menggunakan rupiah/benefit sebagai baseline sampai aturan kredit layanan disepakati.
- Harga/format/estimasi/jatah revisi/jumlah benefit yang belum terkonfirmasi hanya data contoh yang jelas, bukan kebijakan final. Gunakan data repo bila benar-benar tersedia; jangan mengarang harga seolah harga sekarang.
- Dokumen/formulir final WAMI menunggu staf; tidak membuka ulang atau menduplikasi menu WAMI.
- Fitur/kebijakan lain yang sebelumnya diparkir tetap ditunda.

## Syarat penutupan implementasi kelak

Satu rilis utuh, nomor unik V11.1; audit alur tiga peran, reload/draft, duplikasi, penanganan dan hasil/revisi, kepemilikan dan catatan internal, pembayaran/pengembalian lokal, ketentuan pesanan lama. Audit semua lokasi panel/grafik agar pembaruan global tidak parsial; uji terang/gelap, desktop/tablet, tooltip dan animasi. Studio menempatkan kondisi versi terbaru paling atas, otomatis memilih akun. Regresi V11.0, Royalti, Penarikan dan Rilisan sesuai perubahan. Artefak mandiri/panduan dan LAN diperbarui hanya setelah izin rilis; tidak mengklaim backend/pembayaran nyata atau pengujian iPad Safari fisik.

## V11.1 — implementasi dan rilis yang diizinkan

29 September 2026: pengguna meminta langsung mengerjakan dan merilis. Cakupan di atas diterapkan pada prototype-v11.1, bersama empat koreksi UI baru: tema otomatis tersembunyi dengan slider dua posisi, Platform/Staff ringkas, hierarki teks, dan indikator pekerjaan satu ukuran tanpa pulse. Lihat README-V11.1.md dan SCOPE-V11.1.md untuk implementasi dan batasnya. Keputusan harga/benefit final serta pemisahan fungsi kredit tetap diparkir.
