# Optimasi dashboard Rilis Musik

Branch: `codex/dashboard-performance`, berbasis Google login commit `4ffcf88`.
Branch ini sudah mencakup persiapan Google login; PR optimasi ditumpuk di atas
`codex/google-login-vercel`. Production maintenance tetap aktif.

## Perubahan

| Temuan audit | Implementasi |
| --- | --- |
| Antrean pekerjaan lambat | Satu snapshot untuk My Work/Team Monitor, discovery dibatasi dua operasi bersamaan, insert/complete batch 500, skip pekerjaan yang sudah terbuka, atribusi aktor dibaca batch. |
| Rekonsiliasi bersamaan | Lease MongoDB dengan `_id` unik pada `performance_state`, expiry 90 detik, batas proses 45 detik, stamp sukses setelah selesai, pelepasan pada gagal. Lease pulih setelah instance berhenti. |
| Request analitik/KYC berulang | KYC dibagi lewat provider layout; grafik enam bulan memakai hasil analitik utama ketika rentang sama. Shared request hanya selama in-flight, dibedakan akun/label/filter dan direset pada login/logout. Tidak menyimpan cache angka finansial setelah request selesai. |
| Saldo dihitung dua kali | Dashboard mengembalikan snapshot otoritatif sebagai data awal hook saldo. Refresh berikutnya tetap memanggil helper otoritatif, tanpa mengubah formula pencairan. |
| Lima rilisan mengambil 500 | Parameter server `limit=5&include_revenue=false`; pengayaan hanya lima rilisan dan rollup pendapatan tidak dijalankan. Default daftar penuh tetap 500 dan rollup tetap aktif. |
| Query berurutan | Independent read groups dibatasi dua operasi, kegagalan membatalkan grup. Count rilisan label dan funnel memakai satu hasil agregasi status. |
| Polling bertumpuk | Hook polling mencegah overlap, berhenti pada tab tersembunyi, refresh ketika tab kembali aktif, dan mempertahankan nilai terakhir saat gagal. Chat tidak memuat direktori saat tertutup. |
| Pengulangan KPI/progress | Dashboard metrics dapat melewati uang yang sudah diminta kartu mandiri. Ringkasan kerja memakai daftar in-progress yang sama di frontend. |
| UI menampilkan nol/selesai sebelum data | Loading dan error eksplisit; helper metrics mengembalikan kegagalan jika query gagal, bukan nol palsu. |
| Semua halaman di bundle awal | 61 halaman memakai React.lazy/Suspense; role preview juga dimuat terpisah. Route, permission guard, fitur dan URL tetap. |
| Pengukuran belum tersedia | Header Server-Timing, log durasi dengan route template, skrip pembandingan, pemeriksaan indeks dan explain terbatas. |

## Batas rekonsiliasi

Rekonsiliasi masih berjalan sinkron secara terbatas ketika snapshot perlu
diperbarui. Reader lain dapat membaca snapshot tersimpan dengan indikator
`synchronizing`. Tidak ada `asyncio.create_task` yang ditinggal setelah response.
Cron server lama tetap dapat memakai fungsi yang sama, dengan lease yang sama.
Mode preview tetap menonaktifkan worker/cron. Memindahkan seluruh sinkronisasi
ke worker durable memerlukan layanan worker/queue production yang belum dipilih.
Batch/lease memperbaiki jalur saat ini tanpa membuat pekerjaan background Vercel
yang dapat hilang ketika instance berhenti.

## Verifikasi

Tes offline membandingkan respons finansial, analitik admin (cache/live),
ringkasan label, dan scope pekerjaan dengan snapshot kode sebelum optimasi.
Fixtures mencakup status pending/available/withdrawn, legacy_settled, cutoff,
adjustment dan reservasi, serta label berbeda. Lease diuji saat concurrent,
expiry, failure, dan reopen pekerjaan; sejarah dan atribusi tetap dipertahankan.
Mongomock bukan Atlas: hasil ini tidak membuktikan execution plan atau kecepatan
jaringan live. CI juga menjalankan tes frontend, auth Google, preview dan build.

## Pengujian live setelah deployment Preview

Gunakan dua preview yang menunjuk database dan region yang sama. Environment
sama seperti Google login, termasuk `RILISMUSIK_DEPLOYMENT_MODE=preview` dan dua
Client ID Google. Jangan mengubah production branch/promote deployment ini.

1. Login super admin lalu buka `/api/admin/performance-check`. Hasil memuat
   metadata indeks koleksi target, ukuran pool utama, dan region runtime Vercel.
2. Tambahkan `?include_explain=true` untuk sample explain work/monthly analytics;
   `&label_id=<ID_LABEL>` menambah sample royalty label. Masing-masing dibatasi
   1500 ms dan 20 dokumen; hasil hanya statistik, bukan dokumen/isi royalti.
3. Sample find bukan benchmark agregasi lengkap. Sebelum menambah indeks besar,
   periksa explain agregasi representatif di Atlas (label kecil/besar,
   periode latest/enam bulan, artist revenue, work dan monthly analytics).
4. Verifikasi region cluster dari Atlas. Endpoint tidak menebak lokasi Atlas
   dari hostname dan tidak otomatis memindahkan region/menaikkan pool.
5. Jika indeks impor monthly hilang, pertimbangkan pola builder yang sudah ada:
   `(period, dim)`, `(dim, revenue_idr desc)`, `(dim, key, period)`, sesuai hasil
   explain. Work sekarang dibaca dengan status=open; verifikasi kebutuhan
   indeks status/work_type. Jangan membuat unique dedupe sebelum memeriksa
   history reopen dan duplikasi yang sudah ada.
6. Catat API browser Network/Server-Timing saat pertama buka, reload dan setelah
   idle. Lakukan pada akun label kecil/besar dan multi-label. Pencairan/submit/
   upload tetap dibatasi preview; jangan pakai perubahan saldo tersimpan untuk
   menggantikan angka otoritatif.

Skrip lokal (password diminta tersembunyi, tidak disimpan):

```bash
python3 backend/scripts/measure_preview.py --url https://ALAMAT-PREVIEW --role admin
python3 backend/scripts/measure_preview.py --url https://ALAMAT-PREVIEW --role label
```

Untuk preview lama tambahkan `--baseline`. Simpan stdout JSON untuk perbandingan;
skrip hanya mencatat route/status/durasi, tidak mencatat isi respons, password,
cookie atau token. Login/logout merupakan satu-satunya write yang diperlukan.
Jangan gunakan bila preview sedang berada di protection/login wall Vercel;
buka/izinkan akses pengujian preview dahulu melalui pengaturan pemilik project.

## Status yang belum dibuktikan

Tidak ada akses langsung ke Atlas/Vercel management pada sesi pengerjaan ini.
Indeks aktual, region Atlas, explain agregasi finansial lengkap, durasi cold/warm
live dan kesetaraan seluruh data riil masih perlu verifikasi lewat preview.
Tidak ada indeks besar yang dibuat, cluster dipindahkan, atau pool diubah
berdasarkan dugaan. Tidak ada janji loading menjadi jumlah detik tertentu.

## Referensi

- https://www.mongodb.com/docs/manual/core/write-operations-atomicity/
- https://www.mongodb.com/docs/manual/reference/method/db.collection.bulkWrite/
- https://react.dev/reference/react/lazy
- https://vercel.com/docs/functions/configuring-functions/region
