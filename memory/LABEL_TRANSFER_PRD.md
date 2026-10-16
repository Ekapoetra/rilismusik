# Pindah / Ganti Nama Label (Label Transfer)

Kasus: di Believe pelanggan memindahkan rilisan dari satu label ke label lain
(contoh Pelpendo → Elfnon). Rilis Musik harus mengikuti: semua tampil di bawah
satu nama, laporan atas nama lama tetap dikenali, saldo ikut pindah.

## Keputusan user (2026-10)
- Fleksibel: ganti nama, gabung semua rilisan, atau pilih rilisan.
- Perpindahan normal selalu dalam **akun yang sama**.
- Label **dijual** ke akun lain dimungkinkan, dengan aturan lebih ketat.
- Saldo yang belum ditarik **ikut pindah** (untuk penjualan: pilihan eksplisit, default tetap di penjual).
- Pelanggan mengajukan sendiri dari dashboard label; admin juga bisa menginput langsung.

## Mode
| Mode | Label tujuan | Rilisan | Label asal setelahnya |
|---|---|---|---|
| `rename` | — (nama baru) | tetap (label sama) | nama lama jadi alias |
| `merge` | label lain di akun yang sama | semua | ditandai `merged_into_label_id`, namanya dialihkan ke tujuan |
| `releases` | label lain di akun yang sama | dipilih | tetap aktif |
| `sale` | label di akun lain | semua / dipilih | tetap milik penjual |

## Aturan uang
- Saldo = baris royalti pending/available setelah `last_withdrawn_period` + ledger penyesuaian − withdraw aktif.
- Yang dipindah: baris royalti **belum ditarik** (draft/pending/available, bukan legacy, periode > cutoff asal) milik katalog yang dipindah. Mode `merge` memindah semua baris label asal.
- Baris yang periodenya ≤ cutoff label tujuan tetap dipindah (riwayat menyatu), tetapi nilainya dikreditkan lewat ledger penyesuaian (`source=LABEL_TRANSFER`) karena FIFO tujuan tidak lagi menghitung periode itu. Jika baris konflik masih draft/pending (import belum dana diterima), transfer ditolak sampai import selesai.
- Mode `merge` juga memindah saldo penyesuaian (Inject Saldo) yang belum terpakai: debit di asal, kredit di tujuan.
- Penjualan (`sale`): baris periode ≥ `effective_period` selalu ke pembeli; periode sebelumnya hanya pindah jika `carry_balance=true`. Import berikutnya untuk lagu yang dijual: periode < efektif → penjual, ≥ efektif → pembeli.
- Riwayat yang sudah ditarik, withdraw, pembayaran, tiket tetap di label asal.
- Prasyarat: tidak ada withdraw aktif di kedua label, tidak ada hitung ulang royalti berjalan, tidak ada import royalti yang sedang diproses/publish/terima dana.

## Pencocokan import royalti
- Nama label Believe dicocokkan ke nama utama, lalu alias (`label_name_aliases`), lalu label yang digabung dialihkan ke tujuannya. Mencegah pembuatan label placeholder baru untuk nama lama/baru.

## Izin & persetujuan
- Pelanggan (pemilik akun): ajukan `rename` / `merge` / `releases` dari dashboard.
- Admin `labels.manage`: input pengajuan atas nama pelanggan.
- `labels.transfer` (default Super Admin): terapkan langsung tanpa persetujuan.
- `labels.transfer.approve` (default Super Admin, dapat didelegasikan): setujui/tolak; tidak boleh menyetujui pengajuan sendiri kecuali punya `labels.transfer`.
- `sale`: hanya admin yang menginput, wajib alasan + referensi dokumen, **hanya Super Admin selain pengaju** yang bisa menyetujui. Kedua pemilik akun diberi notifikasi.
- Persetujuan mewajibkan konfirmasi bahwa perpindahan di Believe sudah berhasil.

## Kode
- `backend/routes/label_transfer_service.py` (validasi, rencana, penerapan), `backend/routes/label_transfers.py` (endpoint).
- `backend/routes/royalty.py` import: alias + routing periode penjualan.
- Frontend: kartu dashboard label, panel detail label admin, halaman `/admin/label-transfers`.
