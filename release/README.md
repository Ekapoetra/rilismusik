# Versi & catatan perubahan

Satu sumber untuk nomor versi (prototype + aplikasi asli) dan catatan perubahan
yang tampil di **Studio Pratinjau**.

| File | Isi |
|---|---|
| `release.json` | Versi yang sedang dikembangkan (`version`) dan versi produksi (`production`). |
| `changelog.json` | Catatan per versi, terbaru di atas. Versi teratas **harus** sama dengan `release.json`. |

Setelah mengubah salah satunya, jalankan:

```bash
node scripts/sync-release.cjs
```

Skrip ini memvalidasi isi lalu menulis `frontend/src/release.json`,
`prototype-rilis-musik/prototype-v13.0/release-data131.js` dan field `release` di
`prototype-current.json`. CI menjalankan `--check` dan gagal bila hasilnya belum
sinkron.

## Format versi (SemVer)

`MAYOR.MINOR.PATCH[-dev.N|-rc.N]`

- `1.1.0-dev.N`: build pengembangan ke-N di branch `prototype-node-api`. Tampil sebagai **v1.1 · dev N**.
- `1.1.0-rc.N`: kandidat rilis. Fitur sudah dikunci, tinggal uji akhir.
- `1.1.0`: rilis ke `main` (produksi). `1.1.1` dan seterusnya untuk perbaikan bug setelah rilis.
- `1.2.0-dev.1`: fitur berikutnya.

Naikkan `dev.N` per **kumpulan perubahan yang ditinjau pemilik**, bukan per commit.
Aplikasi asli memakai baris rilis (`APP_VERSION` = `1.1`) untuk popup Pembaruan,
sehingga member tidak diminta membaca ulang setiap build dev.

## Entri catatan

```json
{
  "id": "dev2-contoh",
  "status": "prototype | app | both",
  "where": { "role": "super | admin | label", "page": "labels9", "menu": { "id": "…", "en": "…" } },
  "title": { "id": "…", "en": "…" },
  "detail": { "id": "…", "en": "…" }
}
```

- `status`: `prototype` berarti hanya ada di rancangan, `app` berarti hanya ada di aplikasi asli, `both` berarti ada di keduanya.
- `where` diisi `null` untuk perubahan yang hanya ada di aplikasi asli. Entri ini tampil di Studio sebagai kartu info yang tidak bisa diklik.
- Menu **Pembaruan** di aplikasi asli (`frontend/src/pages/label/Updates.jsx`) adalah panduan terkurasi untuk label (keputusan D14), bukan log ini. Saat rilis, entri yang relevan untuk label ditulis ulang di sana.
