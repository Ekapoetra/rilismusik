# Analisis menu Pemantauan Keuangan — v1.1 dev.19

Catatan untuk perbaikan desain berikutnya. **Belum ada yang diubah**; fiturnya sudah tersedia.
Diamati pada prototype (Super Admin, 1440 px) untuk 7 tab: Pemantauan Dana, Kewajiban Royalti,
Perkembangan Katalog, Rekonsiliasi Kas, Kredit, Tarif Khusus, Bonus Kredit.

| Tab | Tinggi halaman | Isi utama | Masalah paling terasa |
|---|---|---|---|
| Pemantauan Dana | ±2.700 px | 4 kartu + tabel 19 baris | baris 80 px, kolom "Dana >365 hari" berisi "Belum diketahui" di semua baris |
| Kewajiban Royalti | ±2.600 px | 4 kartu, grafik, tabel, umur, daftar label | angka tidak cocok dengan Pemantauan Dana; grafik & tabel mengulang data yang sama |
| Perkembangan Katalog | ±2.300 px | tabel 21 baris | kolom "Perbandingan" mengulang kalimat yang sama di setiap baris |
| Rekonsiliasi Kas | ±1.200 px | 4 kartu bernilai Rp 0 + panel kosong | halaman terasa rusak saat belum ada data |
| Kredit | ±1.800 px | tabel 25 baris | lebih cocok di Manajemen Label daripada di keuangan |
| Tarif Khusus / Bonus Kredit | ±1.000 px | tabel kosong | "Belum ada catatan." tanpa ajakan memulai |

## 1. Struktur & navigasi
1. **Tujuh tab sejajar mencampur tiga jenis pekerjaan**: pemantauan uang (Dana, Kewajiban, Kas),
   analitik (Katalog), dan pengaturan (Kredit, Tarif Khusus, Bonus Kredit).
   *Usulan:* tiga kelompok — **Dana & kewajiban** · **Kas** · **Katalog**; pindahkan Kredit, Tarif Khusus
   dan Bonus Kredit ke Pengaturan Platform atau ke detail label.
2. **Pemantauan Dana dan Kewajiban Royalti tumpang tindih**: keduanya menjawab "berapa hak label yang
   belum dicairkan", dengan sumber berbeda (Rp 74,5 jt vs Rp 32,4 jt). Dua angka berbeda untuk pertanyaan
   yang sama merusak kepercayaan.
   *Usulan:* satu halaman **Dana & kewajiban** dengan satu sumber angka (buku besar), lalu tampilan:
   ringkasan → per laporan bulanan → per label.
3. **Pemilih "Sumber data" (saldo awal label lama / buku besar berjalan) diulang di beberapa tab.**
   *Usulan:* jadikan satu pemilih global di kepala halaman, atau hilangkan setelah migrasi saldo lama selesai.
4. **Judul dan tab diletakkan di tengah**, berbeda dari halaman lain yang rata kiri.

## 2. Kepadatan & keterbacaan
1. **Tabel tanpa batas**: Dana, Katalog dan Kredit menampilkan semua label sekaligus (halaman 1.800–2.700 px).
   Dengan ±1.800 label nyata ini tidak bisa dipakai. *Usulan:* paginasi 25 baris, urutkan per kolom,
   kolom pertama lengket, baris 52–56 px.
2. **Kolom tanpa informasi**: "Dana >365 hari = Belum diketahui" (Dana) dan "Data belum sebanding · Perlu
   dua periode…" (Katalog) di setiap baris. *Usulan:* sembunyikan kolomnya dan ganti dengan satu pita
   keterangan di atas tabel sampai datanya tersedia.
3. **Kalimat penjelas panjang di bawah kartu** ("Tiga kartu terakhir adalah bagian dari hak label…").
   *Usulan:* pindahkan ke tooltip (i) atau satu baris kecil yang bisa dibuka.
4. **Tombol panah di setiap baris** menambah 20+ tombol per halaman. *Usulan:* seluruh baris bisa diklik,
   panah hanya muncul saat hover.

## 3. Status kosong
- Rekonsiliasi Kas menampilkan empat kartu "Rp 0" dan panel abu kosong; Tarif Khusus & Bonus Kredit hanya
  "Belum ada catatan." *Usulan:* status kosong yang menjelaskan **apa yang terjadi bila diisi** dan satu
  tombol utama (mis. "Catat posisi kas pertama", "Tambah tarif khusus").

## 4. Kewajiban Royalti (tab baru dev.18)
1. Empat kartu ringkas tingginya tidak seragam; kartu pertama terlalu ramai (angka + delta + kalimat).
2. Grafik batang dan tabel per laporan memuat angka yang sama → pilih satu sebagai tampilan utama
   (grafik), tabel sebagai rincian yang bisa dibuka.
3. Kolom "Umur saldo" dan daftar label memakai warna oranye/merah yang belum mengikuti aturan Kamus
   Penanda (merah hanya untuk batas waktu & penghentian akses).
4. Daftar label mencampur "siap cair" dan "di bawah ambang" dengan status yang panjang; tombol
   "Kirim pengingat" sebaiknya juga tersedia massal ("Ingatkan 17 label").
5. Angka rekap bulanan & umur saldo masih data pratinjau; di aplikasi asli harus dihitung dari
   unggahan laporan royalti dan buku besar penarikan (satu sumber dengan Pemantauan Dana).

## 5. Data & aplikasi asli (untuk PHASE2)
- Kewajiban per laporan butuh snapshot per periode: saldo per label saat laporan diunggah, pengajuan
  s.d. tgl 14, pembayaran s.d. tgl 20 — disimpan sekali per periode (bukan dihitung ulang dari 3 juta baris
  royalti setiap kali halaman dibuka).
- Umur saldo butuh tanggal sumber per kredit royalti (saat ini "Belum diketahui" untuk saldo lama).

## Urutan perbaikan yang disarankan
1. Satukan Pemantauan Dana + Kewajiban Royalti (satu sumber angka).
2. Paginasi & kepadatan tabel untuk semua tab.
3. Pindahkan Kredit / Tarif Khusus / Bonus Kredit keluar dari Pemantauan Keuangan.
4. Status kosong Rekonsiliasi Kas, Tarif Khusus, Bonus Kredit.
5. Rapikan tata letak kepala halaman (rata kiri, pemilih sumber global).
