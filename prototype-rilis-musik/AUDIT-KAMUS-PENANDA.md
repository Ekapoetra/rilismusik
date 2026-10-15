# Audit Kamus Penanda (Standar & Penanda) — v1.1 dev.12

Observasi atas halaman **Standar & Penanda → Kamus Penanda** (50 baris, 10 kelompok) ditambah
tabel yang mengulanginya (Standar Tiket Bantuan, Standar layanan tambahan, Standar Transaksi),
dibandingkan dengan pemakaian nyata chip di Dashboard, Pekerjaan Saya, dan Label.
Tujuan: satu kamus yang **berfungsi sebagai sumber kebenaran**, kata yang konsisten, warna yang
bisa ditebak, dan tampilan yang sama persis dengan pil/chip baru.

Status tiap usulan: **U** = ubah, **K** = kembangkan, **H** = hapus/gabung. Belum ada yang diterapkan;
yang sudah jalan di dev.9 ditandai ✔.

## 1. Fungsi & struktur

| # | Temuan | Usulan |
|---|---|---|
| F1 | Dua jenis hal dicampur dalam satu tabel: **status objek** (penarikan, royalti, WAMI, tiket, transaksi — satu objek selalu tepat di satu status) dan **penanda kondisi** (Baru/Prioritas/Lewat tenggat/Perlu tindak lanjut, akses, aktivitas — bisa menumpuk di atas status). | **U** Pisahkan menjadi dua bagian: *Status per modul* dan *Penanda kondisi* (overlay). Penanda kondisi dijelaskan sebagai "muncul di samping status, bisa lebih dari satu". |
| F2 | Baris penanda kondisi tidak menampilkan chip-nya (hanya teks tebal + kode `work.new`); pembaca tidak melihat wujud penanda yang dimaksud. Kode internal tampil ke pengguna. | **U** Tampilkan chip sungguhan; kode dipindah ke `title`/tooltip untuk pengembang. |
| F3 | Dua kelompok bernama hampir sama: "Kondisi pekerjaan" dan "KONDISI PEKERJAAN & TENGGAT" (kapital semua). Isi yang kedua (Pencairan terlambat, Sebagian tayang) sebenarnya milik Penarikan dan Rilisan. | **H** Gabungkan: pindahkan dua baris itu ke modulnya; hapus kelompok huruf kapital. |
| F4 | Istilah yang sama dipakai dengan makna berbeda: "Menunggu pembayaran" ×4 (penarikan, WAMI, layanan, transaksi), "Menunggu pemeriksaan" ×3, "Selesai" ×3, "Perlu tindak lanjut" ×2 (pekerjaan vs transaksi). | **U** Satu istilah = satu makna. Bila modul butuh makna lain, pakai kata lain (lihat §2). |
| F5 | "Diajukan" muncul dua kali dengan warna berbeda (biru di Kamus, netral di Standar Tiket). | ✔ dev.9 memaksa biru; **H** tabel Standar Tiket digabung ke Kamus (kolom "Langkah berikutnya"). |
| F6 | Tidak ada legenda arti warna; pembaca harus menebak bahwa biru = menunggu, oranye = perlu tindakan, dst. | **K** Legenda 5 nada di atas tabel, memakai chip kaca yang sama dengan daftar. |
| F7 | 50 baris tanpa saringan atau pencarian. | **K** Chip saringan per modul + kotak cari (pola yang sama dengan Kotak Masuk). |
| F8 | Tabel Standar Tiket/Transaksi/Layanan mengulang status dengan kalimat lain; dua sumber kebenaran. | **H** Satu tabel; kolom tambahan "Siapa bertindak" dan "Langkah berikutnya". |

## 2. Kata

| # | Temuan | Usulan |
|---|---|---|
| K1 | Kapitalisasi tidak konsisten: "Dalam Penanganan", "Perlu Tanggapan Label", "Menunggu Distributor" (Title Case) vs "Menunggu pemeriksaan" (sentence case). | **U** Sentence case untuk semua. |
| K2 | Tiga kata untuk "terlambat": *Lewat tenggat* (pekerjaan), *Pencairan terlambat* (penarikan), *Lewat estimasi* (layanan). | **U** "Lewat tenggat" untuk tahap kerja; "Lewat jatuh tempo" untuk uang; "Lewat estimasi" dihapus (pakai Lewat tenggat). |
| K3 | "Koreksi memerlukan penyelesaian" (29 huruf) tidak muat di chip. | **U** "Koreksi tertunda" — maknanya tetap "perlu keputusan petugas". |
| K4 | "Lama tidak beraktivitas" (23 huruf), "Persiapan pendaftaran", "Pemeriksaan berlangsung", "Menunggu pencocokan" terlalu panjang untuk chip di daftar padat. | **U** "Tidak aktif", "Persiapan", "Sedang diperiksa", "Belum dicocokkan". |
| K5 | "Menunggu pembayaran" dipakai untuk 4 hal. | **U** Penarikan: "Menunggu transfer"; WAMI/Layanan: "Belum dibayar"; Transaksi: "Belum dibayar". |
| K6 | "Perlu tindak lanjut" (penanda pekerjaan) vs "Perlu tindak lanjut" (transaksi). | **U** Transaksi → "Pembelian belum terpenuhi" / "Pemeriksaan terbuka" (dua kondisi berbeda, dua kata). |
| K7 | "Ditunda" (penarikan, *on hold*) vs "Ditangguhkan" (akses, *suspended*) mudah tertukar. | **U** Penarikan → "Tertahan"; "Ditangguhkan" tetap untuk akses. |
| K8 | Padanan Inggris: "In Handling" bukan istilah lazim. | **U** "In progress"; "Needs label response" sentence case. |
| K9 | "Baru" dideskripsikan "diterima dan belum ditangani" — sama dengan "Diajukan" (tiket). | **H** Satu istilah untuk antrean awal: "Baru". |

## 3. Warna indikator

Aturan yang sudah berjalan sejak dev.9 (dan dipakai Dashboard):

| Nada | Arti | Contoh |
|---|---|---|
| Biru | sedang berjalan / menunggu antrean, sistem, atau pihak ketiga | Menunggu pemeriksaan, Diterbitkan, Menunggu WAMI |
| Oranye | **perlu tindakan manusia** (label atau petugas) sebelum proses bisa lanjut | Prioritas, Perlu perbaikan, Perlu peninjauan |
| Merah | batas waktu terlampaui atau akses dihentikan | Lewat tenggat, Lewat jatuh tempo, Ditangguhkan |
| Hijau | selesai / terkonfirmasi | Dibayarkan, Selesai, Terkonfirmasi, Aktif |
| Netral | ditutup, kedaluwarsa, tidak aktif, normal (tidak perlu perhatian) | Ditutup, Kedaluwarsa, Normal, Nonoperasional |

Baris yang melanggar aturan itu:

| # | Penanda | Sekarang | Usulan | Alasan |
|---|---|---|---|---|
| W1 | Baru, Diajukan | netral | biru ✔ (dev.9) | antrean, bukan status akhir |
| W2 | Normal / Dibatasi / Ditangguhkan (halaman Label) | kuning lain, tanpa titik | netral / oranye / merah ✔ (dev.9) | masuk sistem penanda yang sama |
| W3 | Menunggu tanggapan (layanan) | biru | **oranye** | label harus menjawab — tindakan manusia |
| W4 | Lengkapi bahan (layanan) | biru | **oranye** | label harus mengirim bahan |
| W5 | Koreksi pembayaran (penarikan) | biru | **oranye** | transfer ulang ditahan sampai petugas memutuskan |
| W6 | Belum aktif (aktivitas) | — (tanpa chip) | biru | calon/prospek, masih mungkin aktif |
| W7 | Ditangguhkan | merah hanya di Label | merah di mana pun | akses dihentikan = merah |
| W8 | Merah untuk hal lain | — | **dilarang** | merah hanya untuk batas waktu & penghentian akses, agar tetap bermakna |

## 4. Penyesuaian dengan pil/chip baru

- Chip kaca (titik + rim berwarna, teks netral) saat ini hanya aktif di Dashboard. Setelah disetujui,
  cakupannya dinaikkan ke seluruh `.status111` — termasuk tabel Kamus — supaya kamus menunjukkan
  **wujud yang sama persis** dengan yang dilihat pengguna di daftar.
- Lebar chip dibatasi ±22 huruf (lihat K3–K4); label lebih panjang dipotong dengan elipsis dan judul penuh di tooltip.
- Legenda 5 nada (§3) ditampilkan sebagai lima chip kaca di atas tabel.
- Penanda kondisi (Baru/Prioritas/Lewat tenggat/Perlu tindak lanjut) ditampilkan bersebelahan dengan status contoh, seperti di daftar pekerjaan ("Penarikan · Tepian Musik · *Menunggu pemeriksaan* · *Lewat tenggat*").

## 5. Ringkasan: ubah / kembangkan / hapus

- **Ubah (U):** sentence case; 8 penggantian kata (K2–K8); 3 perubahan warna (W3–W5); kode internal ke tooltip.
- **Kembangkan (K):** legenda nada; saringan modul + pencarian; kolom "Siapa bertindak" & "Langkah berikutnya"; chip kaca di kamus.
- **Hapus/gabung (H):** kelompok huruf kapital; tabel Standar Tiket/Transaksi/Layanan sebagai pengulang; "Diajukan" (pakai "Baru"); "Lewat estimasi".

Butuh keputusan pemilik sebelum diterapkan: K5 (kata pengganti "Menunggu pembayaran"), K7 ("Tertahan"), W3–W5 (tiga warna), dan apakah legenda + saringan dibuat sekarang (dev.13) atau setelah Chat Center matang.
