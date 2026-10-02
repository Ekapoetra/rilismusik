# Google login pada Vercel

Branch persiapan: `codex/google-login-vercel`, berbasis aplikasi preview commit `36a6fe2`.
Branch production yang menampilkan maintenance tidak diubah.

## 1. Environment Vercel

Buka project Rilis Musik → Settings → Environment Variables. Tambahkan dua
variabel berikut pada lingkungan **Preview** untuk pengujian:

| Nama | Nilai |
| --- | --- |
| `GOOGLE_CLIENT_ID` | OAuth Client ID milik Anda, berakhiran `.apps.googleusercontent.com`. |
| `REACT_APP_GOOGLE_CLIENT_ID` | Nilai Client ID yang sama persis. |

Client ID bersifat publik; ini bukan API key maupun Client Secret. Alur ini
memakai tombol Google Identity Services dan ID token, sehingga tidak
memerlukan `GOOGLE_CLIENT_SECRET` atau redirect URI backend. Jangan masukkan
Client Secret, password database, atau key rahasia pada variabel `REACT_APP_*`.

Tetap gunakan env database, JWT, R2, SMTP, dan `RILISMUSIK_DEPLOYMENT_MODE=preview`
yang sudah disiapkan. Variabel lama `REACT_APP_GOOGLE_AUTH_URL` dan
`EMERGENT_AUTH_SESSION_URL` tidak diperlukan oleh tombol baru.

Setelah menambahkan atau mengganti env, buat deployment baru dari branch ini.
Frontend membaca Client ID ketika build, sehingga deployment lama tidak
langsung menerima perubahan env.

## 2. Google Cloud / Google Auth Platform

1. Buka project yang memiliki Client ID → Google Auth Platform → Clients.
2. Pastikan jenis client adalah **Web application**.
3. Pada **Authorized JavaScript origins**, masukkan alamat yang benar-benar
   digunakan untuk membuka aplikasi, misalnya `https://rilismusik.vercel.app`
   serta hostname Preview yang dipakai menguji branch ini. Gunakan scheme dan
   hostname saja, tanpa `/login`, `/api`, path lain, atau slash terakhir.
4. Jika aplikasi juga dibuka dari domain sendiri atau alias `www`, tambahkan
   masing-masing origin tersebut. Wildcard hostname preview tidak didukung.
   Gunakan alias branch yang stabil agar tidak perlu mendaftarkan setiap URL
   commit baru. Jika Vercel Deployment Protection aktif, masuk ke preview dahulu.
5. Konfigurasikan Branding dengan nama Rilis Musik, support email, dan tautan
   homepage/privacy/terms yang benar. Tombol baru meminta identitas dasar saja,
   tidak meminta akses Gmail, Drive, atau YouTube.
6. Jika project Google masih berstatus **Testing**, tambahkan akun yang akan
   dipakai mencoba pada daftar test users. Sebelum dibuka untuk semua pelanggan,
   periksa Audience/publishing dan persyaratan verifikasi yang ditampilkan Google.

Metode popup/callback JavaScript ini tidak menggunakan `/auth/callback` atau
callback Emergent. Authorized redirect URIs untuk integrasi lain tidak perlu
 dihapus; tombol baru memakai Authorized JavaScript origins.

## 3. Pengujian

1. Deploy branch `codex/google-login-vercel` sebagai Preview. Root tetap akar
   repository dan konfigurasi Services tetap berasal dari `vercel.json`.
2. Buka `/login`. Tombol **Lanjutkan dengan Google** dan logo Google dirender
   oleh SDK resmi Google, bukan huruf G atau logo yang dibuat ulang.
3. Pilih akun Google dengan email akun label yang sudah ada di Rilis Musik.
4. Akun Gmail/Workspace yang terverifikasi dapat dicocokkan pertama kali dengan
   akun label yang sudah ada. Akun baru tidak otomatis dibuat.
5. Untuk akun Google beralamat email pihak ketiga, masuk dulu menggunakan
   password → **Profil & Rekening → Login dengan Google** → hubungkan akun
   dengan email yang sama. Setelah itu Google login memakai identitas Google
   yang stabil, bukan bergantung pada perubahan email.
6. Pastikan dashboard label terbuka, refresh halaman tetap login, logout bekerja,
   dan akun admin/nonaktif/merged/blacklisted tidak bisa masuk lewat tombol label.

Google login/link hanya menulis identitas dan sesi autentikasi. Fitur bisnis,
registrasi, pembayaran, unggahan, dan pekerjaan background tetap dibatasi mode
preview. Keberhasilan Google login belum menyatakan seluruh aplikasi siap
production atau pencairan siap diaktifkan.

## Penanganan kendala

| Gejala | Periksa |
| --- | --- |
| Tombol belum tersedia | Dua env Client ID terisi dan deployment sudah dibuild ulang. |
| Origin tidak diizinkan | Hostname pada address bar tercantum persis di Authorized JavaScript origins. |
| Popup kosong/tidak kembali | Header COOP dari konfigurasi Vercel sudah aktif; cek pemblokir popup atau ekstensi browser. |
| Sesi sudah berakhir/tidak cocok | Klik **Muat ulang tombol Google**. Challenge berlaku 10 menit; membuka beberapa tab login dapat mengganti challenge. |
| Diminta login password lebih dulu | Email pihak ketiga perlu dihubungkan dari akun yang sudah login. |
| Google login hanya untuk label terdaftar | Gunakan email label yang sudah ada. Akun admin tetap menggunakan login password. |

## Catatan implementasi

Backend memverifikasi signature, audience, issuer dan expiry melalui library
resmi `google-auth`. Nonce browser/cookie dan pemeriksaan same-origin melindungi
alur login; credential hanya dapat dipakai sekali melalui keunikan `_id` MongoDB,
termasuk saat bootstrap indeks preview dinonaktifkan. Binding disimpan pada
koleksi kecil `google_identities`, dan hash credential pada `google_auth_sessions`.
ID token asli tidak disimpan atau dicatat ke log. JWT aplikasi tetap disimpan
pada cookie Secure/HttpOnly seperti login password.

Sertifikat publik Google dicache sesuai TTL header respons agar login berikutnya
pada instance yang sama tidak selalu mengunduh sertifikat lagi. Ini mengurangi
panggilan provider; bukan janji durasi login tertentu atau perbaikan seluruh
loading dashboard.

Legacy endpoint Emergent di backend dipertahankan untuk kompatibilitas server
lama; frontend baru tidak memanggilnya dan mode preview tetap memblokirnya.

## Referensi resmi

- Setup dan JavaScript origins: https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid
- Verifikasi ID token/email authority: https://developers.google.com/identity/gsi/web/guides/verify-google-id-token
- Tombol dan branding: https://developers.google.com/identity/branding-guidelines
- Nonce dan renderButton: https://developers.google.com/identity/gsi/web/reference/js-reference
