# Paket backend penuh — belum dipasang pada hosting

Pilihan pengguna: buka setelah fitur lengkap siap, bukan buka hanya untuk
membaca data. Production masih maintenance. Paket ini tidak mengubah
`vercel.json`, production branch, domain, atau environment hosting.

## Mengapa preview belum sama dengan production

`backend/vercel_app.py` hanya menerima mode preview dan memblokir perubahan
data. Impor/rebuild/audit royalti memakai `asyncio.create_task`; scheduler
lama berjalan di dalam proses API. Upload audio memakai multipart ke API.
Membuka pembatasan saja tidak memindahkan pekerjaan itu ke sistem yang tahan
penghentian Function. FastAPI pada Vercel dijalankan sebagai Function dengan
batas durasi dan ukuran payload; file audio besar perlu jalur langsung ke
storage. Alternatif full Vercel memerlukan migrasi job ke queue/workflow dan
jalur unggahan tersebut, bukan sekadar mengganti environment.

Jalur kompatibilitas yang disiapkan di sini: frontend tetap Vercel, backend
lama berjalan pada **satu container/proses yang terus menyala**. Ini memberi
scheduler/recovery dan pekerjaan panjang runtime yang sesuai dengan kode
yang ada. Ini belum membuktikan semua recovery idempotent setelah crash;
restart saat pemrosesan harus diuji sebelum cutover. Jangan autoscale atau
jalankan dua backend production yang sama selama scheduler belum dipisah.

## Berkas yang siap ditinjau

- `backend/Dockerfile.production`: API penuh melalui `server:app`, satu worker.
- `backend/scripts/start_production.py`: pemeriksaan format konfigurasi;
  gagal sebelum server mulai jika konfigurasi wajib belum lengkap.
- `backend/tests/test_production_configuration.py`: pemeriksaan launcher tanpa
  mengakses database, pembayaran, email atau storage pengguna.

Build dari root repository:

```sh
docker build -f backend/Dockerfile.production -t rilismusik-api .
```

Image belum dibangun atau dipublikasikan oleh sesi ini. `.dockerignore`
mencegah file environment, unggahan lokal dan cache ikut image. Pasang volume
persisten pada `/data`; `UPLOAD_DIR=/data/uploads`. Set port sesuai hosting,
HTTPS ingress, restart policy, dan **satu replica**. Mengatur nama direktori
tidak otomatis membuat volume persisten.

## Konfigurasi pada hosting backend

Masukkan rahasia langsung di hosting. Jangan salin nilainya ke GitHub/chat.
Gunakan `MONGO_URL` Atlas sendiri, `DB_NAME=rilismusik`, JWT lama, SMTP/pengirim,
R2 lama, `XENDIT_SECRET_KEY`, `XENDIT_RETURN_URL_BASE` dan `FRONTEND_URL`.
Return URL harus sama dengan frontend final. `XENDIT_ALLOW_MOCK_PAY=false`.
Jika webhook diaktifkan, isi verification token dan arahkan callback ke backend
final. Dua Google Client ID serta Authorized JavaScript origins tetap perlu
konfigurasi akun Google; login password tidak bergantung pada Google.

`RILISMUSIK_DEPLOYMENT_MODE=production` hanya untuk runtime container ini;
jangan menggantinya pada deployment Function preview. Jalankan pemeriksaan:

```sh
python backend/scripts/start_production.py --check
```

Pemeriksaan ini hanya format dan kelengkapan, bukan ping layanan eksternal.

## Yang masih diperlukan sebelum pembukaan

Belum tersedia akun/alamat hosting backend penuh untuk dipasang. Setelah
hosting dipilih, perlu sambungkan routing frontend/API pada domain yang sama
atau konfigurasi origin/cookies yang benar. Uji unggahan WAV besar melalui
backend/storage tanpa melalui batas payload Function. Jangan menggunakan
proxy Function Vercel sebagai solusi untuk audio besar.

Dengan akun uji, verifikasi login admin/label, upload dan baca ulang cover/audio,
email, pembuatan invoice dan status pembayaran, request withdraw beserta
riwayat dan bank snapshot, serta satu job background sampai selesai. Jangan
mengirim pembayaran/pencairan nyata hanya untuk smoke test. Pastikan migrasi
source dibekukan agar tidak ada perubahan sesudah ekspor yang terlewat.

Sebelum cutover: verifikasi indeks dan jumlah koleksi live, cegah scheduler
lama dari dua host menulis database yang sama, siapkan rollback deployment,
dan konfigurasi domain/callback layanan final. Jadwal membuka akses hanya
dipasang setelah runtime dan alur tersebut terverifikasi; perubahan branch
yang dijadwalkan tidak menjamin Vercel selesai build tepat pada detiknya.

Referensi:
- https://vercel.com/docs/frameworks/backend/fastapi
- https://vercel.com/docs/functions/limitations
- https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel
