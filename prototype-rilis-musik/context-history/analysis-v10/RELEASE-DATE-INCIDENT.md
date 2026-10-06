# Salah tanggal Believe dan finalisasi kredit

Kasus dari pengguna: staff memasukkan tanggal lebih lambat di Believe daripada tanggal permintaan web. Pengisian UPC/ISRC berhubungan dengan penandaan Tayang, padahal rilisan belum tayang dan kode disebut belum tersedia.

Temuan kode pada snapshot referensi (bukan pemeriksaan produksi): releases.py sudah memisahkan save_identifiers dari mark_live pada detail individual. MassGoLiveModal.jsx mengirim bulk-go-live lewat tombol Simpan & Tayangkan / Tayangkan Semua yang Lengkap. Mark_live individual memeriksa UPC/ISRC tetapi tidak menunjukkan persyaratan bukti tayang pada cabang tersebut. Deliver/mark_live/reschedule dapat menimpa release_date. Perlu menelusuri validasi massal sebelum implementasi.

Usulan koreksi rancangan, belum implementasi:
- Pisahkan tanggal permintaan label, tanggal yang dikonfirmasi dari Believe, dan waktu tayang aktual. Pertahankan riwayat perubahan, jangan menimpa permintaan awal agar tampak cocok.
- Kode katalog bukan bukti tayang. Simpan kode harus terpisah dari konfirmasi Tayang pada jalur individual dan massal.
- Kejadian salah input tanggal adalah masalah internal. Staff mengajukan koreksi ke Believe dan mencatat bukti/hasil, tanpa meminta label mengajukan ulang atau menerapkan tenggat revisi 24 jam.
- Kredit tetap dialokasikan selama pemulihan rilisan yang sama; tidak kedaluwarsa karena menunggu penanganan internal. Jika terlanjur dikonsumsi oleh status Live yang salah, koreksi ledger ke alokasi yang sama sekali saja, bukan sekaligus kembali tersedia.
- Jika koreksi tidak dapat memulihkan jadwal awal, sampaikan tanggal yang benar-benar dapat dipenuhi kepada label. Pembatalan setelah pengiriman menunggu kepastian dari distributor sebelum alokasi dilepas.
- Kegagalan final karena kesalahan internal perlu keputusan kompensasi terpisah; usulan kredit pengganti harian 48 jam dimulai saat kredit tersedia untuk digunakan, pembelian kembali tanpa kedaluwarsa. Jangan menyamakan pembatalan akibat kesalahan internal dengan pembatalan sukarela label.
- Untuk prototype: skenario salah tanggal, kode belum tersedia, Tayang keliru, koreksi berhasil, dan pembatalan terkonfirmasi. KPI belum diubah; simpan pelaku, waktu, penyebab, penanganan sebagai riwayat.
