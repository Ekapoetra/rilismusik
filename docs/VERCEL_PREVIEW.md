# Deployment percobaan migrasi Rilis Musik

Konfigurasi ini menjalankan React dan FastAPI sebagai dua Vercel Services
dalam satu project. `/api` menuju Python, sedangkan halaman dan aset web
menuju frontend. Branch ini untuk uji migrasi, belum untuk pengalihan produksi.

## Pengaturan project

- Repository: `Ekapoetra/rilismusik`.
- Branch untuk import/deploy Vercel: `vercel-preview` (tanpa `/` pada nama branch).
- Branch PR pengembangan: `codex/vercel-preview`.
- Root Directory: akar repository, bukan `frontend` atau `backend`.
- Gunakan konfigurasi Services dari `vercel.json`. Build/install/output diatur
  per service; jangan menambahkan override build frontend di tingkat project.
- Jika project sudah terhubung ke repository ini, pilih branch percobaan
  untuk deployment, atau gunakan Preview Deployment yang dibuat untuk PR.

## Environment variables

Isi nilai rahasia langsung pada project Vercel, jangan di GitHub atau chat.
Untuk Preview Deployment, env harus tersedia pada lingkungan **Preview**.
Jika memakai project terpisah untuk pengujian dan deployment pertamanya
ditandai Production oleh Vercel, isi env pada lingkungan itu juga;
`RILISMUSIK_DEPLOYMENT_MODE=preview` tetap membatasi aplikasi untuk pengujian.

| Nama | Nilai / sumber |
| --- | --- |
| `MONGO_URL` | Connection string Atlas milik sendiri, memakai password baru. |
| `DB_NAME` | `rilismusik` |
| `RILISMUSIK_DEPLOYMENT_MODE` | `preview` |
| `JWT_SECRET` | Nilai backend yang sama dengan Emergent. |
| `FRONTEND_URL` | Alamat frontend percobaan, dengan `https://`, tanpa `/` terakhir. Jika tidak diisi, entrypoint memakai `VERCEL_URL` jika tersedia. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | Nilai layanan email yang sama. Kode membaca variabel ini saat import; `SMTP_PORT` harus berupa angka. |
| `SENDER_EMAIL`, `SENDER_NAME` | Nilai pengirim email yang sama. |
| `R2_ENDPOINT_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET` | Akses bucket lama agar audio, cover, dan dokumen yang sudah di R2 tetap terbaca. |
| `R2_PUBLIC_BASE_URL` | Opsional, hanya jika sebelumnya memakai domain CDN R2. |
| `GOOGLE_CLIENT_ID` | OAuth Client ID Google bertipe Web application. |
| `REACT_APP_GOOGLE_CLIENT_ID` | Client ID yang sama untuk tombol Google resmi; nilai ini bersifat publik. |

`UPLOAD_DIR` lama tidak dipakai oleh entrypoint Vercel. Direktori sementara
ditetapkan otomatis di `/tmp`; direktori ini bukan penyimpanan permanen.
`REACT_APP_BACKEND_URL` boleh kosong untuk konfigurasi satu domain ini:
frontend menggunakan `/api`. Tidak ada password/API key yang perlu diberi
awalan `REACT_APP_`.

Env Xendit bisa disiapkan untuk tahap berikutnya. Pembayaran dan webhook
dinonaktifkan pada preview melalui pembatasan permintaan yang mengubah data.
Nama yang benar-benar dibaca kode meliputi `XENDIT_SECRET_KEY`,
`XENDIT_API_URL`, `XENDIT_RETURN_URL_BASE`, `XENDIT_ALLOW_MOCK_PAY`,
`XENDIT_WEBHOOK_ENABLED`, dan `XENDIT_WEBHOOK_VERIFICATION_TOKEN`.
`XENDIT_RETURN_URL_BASE` harus mengikuti alamat frontend saat pembayaran
diaktifkan nanti. Login Google menggunakan Google Identity Services langsung;
lihat [panduan konfigurasi Google](GOOGLE_LOGIN_VERCEL.md).

## Koneksi Atlas dan pemeriksaan

Atlas harus mengizinkan koneksi dari jaringan Vercel. Akses IP komputer yang
dipakai saat impor saja belum mencakup Vercel. Konfigurasikan Network Access
sesuai IP keluar deployment sebelum menguji koneksi.

1. Buka `/api/health` pada alamat deployment; respons harus berisi `ok: true`.
   Endpoint ini hanya mengecek API, bukan koneksi database.
2. Login menggunakan akun lama dengan email dan password.
3. Sebagai super admin, buka `/api/admin/deployment-check` pada domain yang
   sama. Respons harus menunjukkan database `rilismusik`, koneksi berhasil,
   dan jumlah dokumen koleksi `users`, `labels`, `releases`, `royalty_lines`,
   `monthly_analytics`.
4. Cocokkan dashboard, daftar label, daftar rilisan, saldo dan riwayat dengan
   aplikasi lama. Periksa cover/audio yang diambil dari R2.

Preview mencegah pembayaran, pendaftaran, pengiriman email, unggahan,
perubahan data melalui endpoint, dan pemicu pekerjaan background.
Login/refresh tetap menulis sesi pada database salinan. Pembacaan tertentu
bisa memperbarui cache/metadata sesuai perilaku API lama, jadi ini bukan
jaminan database benar-benar read-only.

## Jika analitik atau pendapatan artis kosong

Ekspor ZIP yang diterima pada 1 Oktober 2026 berisi 160 koleksi dan 7.498.233
dokumen, tetapi tidak memuat koleksi aktif `royalty_lines` maupun
`monthly_analytics`. Sebanyak 7.274.925 dokumen berada pada 97 koleksi
`monthly_analytics_staging_*`; koleksi sementara itu bukan bukti bahwa data
royalti sumber sudah ikut dipindahkan.

`royalty_lines` menyimpan rincian royalti. `monthly_analytics` menyimpan
ringkasan yang dibaca analitik dan pendapatan artis. Ambil ekspor kedua
koleksi dari database lama dan cocokkan jumlah serta periode datanya sebelum
impor tambahan. Rebuild tidak dapat memulihkan rincian yang belum diimpor.
Jangan mengganti koleksi aktif dengan salah satu staging tanpa validasi
kelengkapan dan konsistensi dengan sumber.

Pada mode preview, cache miss tetap memakai pembacaan live yang sama tetapi
tidak menjadwalkan rebuild otomatis. Tombol Rebuild Cache masih dibatasi
karena pekerjaan tersebut harus dijalankan oleh worker yang sesuai pada
tahap migrasi berikutnya.

## Sebelum pengalihan produksi

Pekerjaan impor royalti, audit, penghitungan ulang, pemulihan pekerjaan, dan
scheduler lama harus dipindahkan ke worker/workflow yang tahan penghentian
Function, atau tetap dijalankan pada backend/server yang selalu aktif.
Jangan mengaktifkan APScheduler lama pada banyak instance Function.
File lokal lama yang tidak ada di R2 memerlukan migrasi terpisah. Ekspor JSON
tidak menyertakan file dan telah meratakan beberapa tipe BSON; pengujian
aplikasi diperlukan. Rekonsiliasi perubahan yang terjadi pada aplikasi lama
setelah ekspor sebelum mengalihkan domain dan webhook.

Referensi resmi:
- https://vercel.com/docs/services
- https://vercel.com/docs/services/routing
- https://vercel.com/docs/frameworks/backend/fastapi

## Validasi tanpa database produksi

CI pada branch ini menginstal dependensi runtime, mengimpor seluruh API,
menguji startup preview tanpa koneksi database/worker, pembatasan endpoint,
autentikasi pemeriksaan database, lalu membangun frontend React.

Untuk menjalankan smoke test lokal:

```sh
python -m pip install -r backend/requirements.txt
python -m unittest discover -s backend/tests -p test_vercel_preview.py -v
```
