# Pemeliharaan sementara di Vercel

Branch `vercel-preview` menampilkan halaman pemeliharaan statis, termasuk untuk
URL dashboard, login, dan API. Deployment ini hanya menerbitkan
`maintenance-dist/index.html`; React, FastAPI, dan koneksi MongoDB tidak dijalankan.

Jadwal yang ditampilkan: **5 Oktober 2026 pukul 08.00 WIB**.
Jadwal ini merupakan pemberitahuan; halaman tidak membuka layanan secara otomatis.

Build: `node scripts/build-maintenance.cjs`.
Logo menggunakan aset asli `frontend/public/brand/logo-ui-light.png`.

Halaman menggunakan HTTP 503, `Retry-After` pada waktu tersebut, dan `no-store`.
Periksa respons dan tampilan deployment sebelum mempromosikannya ke production.

Untuk kembali ke aplikasi setelah migrasi dan pemeriksaan selesai, pulihkan
`vercel.json` dari commit aplikasi
`36a6fe2f1930f32a4e5b8660e65038436cc06d93` ke commit baru pada branch ini
(`git restore --source=36a6fe2f1930f32a4e5b8660e65038436cc06d93 -- vercel.json`).
Kode aplikasi dan database tidak diubah oleh halaman pemeliharaan.
Gunakan kembali konfigurasi preview saat verifikasi migrasi; deployment aplikasi
production penuh tetap memerlukan pemeriksaan data dan fitur produksi.
