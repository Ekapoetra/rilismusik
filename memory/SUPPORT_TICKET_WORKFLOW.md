# Support Ticket Label — Iteration 64

## Permintaan asli pengguna (2026-09-08)
Workflow Support Ticket label :
1. Takedown, saat pilih rilisan, otomatis menambahkan UPC dan ISRRC kedalam pengajuan, subject teriisi otomatis, deskripsi diwajibkan, alasan takedown ada 4 opsi : Revisi Metadata, Pindah Aggregator, Konfik Hak Cipta, Konfik Internal.
2. Edit Metadata, saat pilih rilisan, otomatis menambahkan UPC dan ISRRC kedalam pengajuan, informasi metadata baru, otomatis ter-load pada pengajuan, agar bisa diedit, alasan perubahan bebas isi, subject menyesuaikan, deskripsi dihapus, hanya alasan perubahan, lampiran tambahan (optional) tetap.
3. Pengajuan ContentID, saat pilih rilisan, otomatis menambahkan UPC dan ISRRC kedalam pengajuan, subject teriisi otomatis, deskirpsi tidak wajib, link video youtube bisa lebih dari 1, check list pernyataan lagu original tetap dipertahankan.
4. Cabut ContentID, saat pilih rilisan, otomatis menambahkan UPC dan ISRRC kedalam pengajuan, subject teriisi otomatis, deskirpsi tidak wajib, link video youtube bisa lebih dari 1, check list pernyataan lagu original tetap dipertahankan.
5. Hapus opsi : Masalah Royalti dan Lainnya.

Konfirmasi pengguna: "sudah sesuai" untuk seluruh kolom metadata existing, UPC + ISRC seluruh track, pengeditan sebagai pengajuan tiket (bukan langsung mengubah rilisan), serta mempertahankan keterbacaan tiket historis kategori yang dihapus.

## Implementasi
- Enam kategori tiket baru: takedown/edit_metadata/edit_audio/edit_cover/content_id_claim/content_id_release. `royalty_issue` dan `other` tetap dikenal untuk tiket historis tetapi tidak bisa dipakai membuat tiket baru.
- Empat kategori yang diminta memakai subjek otomatis kategori + judul rilisan. Backend menghasilkan subjek serta snapshot `upc`, `isrcs`, `release_tracks` dari sumber DB, bukan nilai identitas yang dikirim klien.
- UPC/ISRC yang belum tersedia ditampilkan jujur; tidak mengarang kode dan tidak memblokir pengajuan. UPC numerik legacy dinormalisasi ke string saat snapshot.
- Takedown: deskripsi wajib, pilihan alasan tepat empat (ejaan UI: Konflik Hak Cipta, Konflik Internal).
- Edit Metadata: judul, artist, genre, bahasa, copyright_line, p_line otomatis terisi; alasan bebas wajib; field deskripsi tidak dirender dan nilai API dikosongkan. Lampiran tetap opsional. Simpan original_metadata dan new_metadata lengkap untuk perbandingan admin/label; rilisan/track asli tidak diubah.
- Kedua Content ID: deskripsi opsional, satu atau beberapa URL video HTTPS (maksimal 20), tambah/hapus baris, pernyataan originalitas wajib. Server memvalidasi host/video ID dan menolak video duplikat lintas format URL; tidak memanggil YouTube API. `youtube_url` tunggal masih didukung untuk kompatibilitas.
- Komentar awal selalu bermakna: deskripsi, alasan perubahan, atau subjek otomatis bila deskripsi kosong.
- Detail label/admin menampilkan semua kode, semua link dan metadata sebelum/sesudah. Teks panjang aman pada layar sempit.
- Audio/cover dan upload attachment R2 existing dipertahankan; track penggantian audio harus milik rilisan yang dipilih.
- Akses admin menggunakan permission dinamis support.view/support.manage; view-only tidak bisa membalas/mengubah status/mengunggah lampiran. Catatan internal tidak dikembalikan melalui list/detail/cancel label.

## Referensi arsitektur
- `backend/models.py`: TicketCreateIn membatasi kategori baru; deskripsi/subjek bergantung workflow, `youtube_urls` ditambahkan.
- `backend/routes/ticket_workflow_service.py`: normalisasi, validasi kategori, snapshot sumber, URL video, response model pembuatan.
- `backend/routes/tickets.py`: endpoint existing, permission, komentar awal dan preservasi history.
- Frontend `components/label/tickets/`: konfigurasi bersama + kolom spesifik kategori.
- `components/label/SupportTicketModal.jsx`: dialog/form responsif, field wajib/opsional sesuai kategori.
- `pages/label/SupportTickets.jsx`: load sumber dengan cancellation guard, autofill dan submission.
- `components/shared/TicketReleaseIdentifiers.jsx`, `TicketRequestSummary.jsx`: rendering identik pada detail label/admin.

## Hasil verifikasi
- Backend final **10/10 passed**, XML `test_reports/pytest/iter64_final.xml`; build frontend dan kompilasi Python lulus.
- Tes aktual API/R2: kategori aktif/legacy, validasi takedown, metadata tanpa mutasi rilisan, upload lampiran nyata, kedua Content ID, ownership/noauth, internal note redaction, admin view-only.
- Browser tambahan utama: enam metadata terisi, switch A/B/A (termasuk kode kosong), metadata editable tanpa deskripsi + lampiran TXT nyata, before/after pada label/admin, sukses tetap muncul.
- Kedua Content ID terkirim via UI dengan dua URL, deskripsi kosong, checklist wajib; tambah/hapus baris URL dan rendering kedua link pada label/admin lulus.
- Responsif 320/768/1024/1440 lulus pada form; detail dengan alasan panjang tanpa spasi serta tampilan admin 320px aman. Sidebar admin memiliki transisi margin 300ms; tunggu selesai setelah resize sebelum menilai posisi screenshot.
- Demo PPR/VIP masih memiliki kelengkapan KYC/profil yang kurang; jangan mengubah data demo untuk testing. Dokumentasi kredensial sudah diperbarui; seluruh pengujian memakai fixture terverifikasi terisolasi.
- Fixture UI/backend, role, tiket/comments dan object upload yang direferensikan fixture dibersihkan; jumlah akun/label/tiket/role QA tersisa nol. Tidak ada API aplikasi MOCKED.
- Laporan final: `test_reports/iteration_64_followup.json` menutup kekurangan cakupan UI pada laporan awal Iter64.

## Catatan insiden data uji — transparansi
- Pada run pengujian awal, teardown yang dibuat testing agent memakai penghapusan notifikasi berdasarkan judul `iter64|Tiket` di database preview. Cakupan terlalu luas, sehingga notifikasi tiket di luar fixture dapat ikut terhapus; jumlah yang terhapus tidak dicatat dan tidak dapat dipastikan dari output.
- Main agent menginformasikan masalah ini kepada pengguna. Tidak ada penghapusan tiket/rilisan pengguna oleh query tersebut; dampak adalah notifikasi preview. Jangan mengklaim notifikasi lama sudah dipulihkan: tidak ada rekonstruksi/backup restoration yang dilakukan.
- Teardown sudah diganti ke ID tiket/user/role/file yang benar-benar dimiliki fixture. Added sentinel assertion membuktikan notifikasi di luar scope tidak ikut terhapus pada run final. Orphaned QA tickets dari teardown awal juga dibersihkan via label_id QA spesifik, bukan prefix ID tiket UUID yang keliru.
- Jangan menjalankan versi lama fixture/teardown atau mengadaptasi `test_phase3_tickets.py` tanpa menyesuaikan aturan baru dan meninjau scope cleanup.

## Berikutnya
- Verifikasi pengguna pada alur support label terbaru.
- Bila riwayat notifikasi preview lama perlu dipulihkan, perlu sumber backup valid; jangan membuat ulang status baca/timestamp secara perkiraan.
- P2 opsional: template balasan admin per jenis tiket.