# Management Label — dasar pembahasan V10

Pemeriksaan sumber: 22 September 2026. Repo referensi HEAD 6929bf25a56579d5ac81ed9def38a183665d7863. Temuan berasal dari pembacaan kode; bukan konfirmasi insiden pada layanan produksi. Tidak ada perubahan repo atau pemanggilan tindakan pada layanan produksi.

## Temuan dan konsekuensi rancangan

1. **Cakupan pencabutan akun pada multi-label.** `backend/routes/admin_label_service.py`, fungsi `revoke_label_account`, menonaktifkan user milik label yang dipilih lalu melepas hubungan label tersebut. `backend/routes/multi_label_merge.py` menghubungkan beberapa label kepada satu primary user. Akibat yang perlu diuji: mencabut akun dari satu anak dapat menonaktifkan login bersama. Pisahkan pembatasan label, pelepasan hubungan pengelola, dan penonaktifan seluruh akun. Tampilkan cakupan dampak sebelum tindakan.

2. **KYC dan label aktif belum menggunakan pemilihan yang sama.** `backend/routes/kyc_service.py`, `ensure_label_kyc`, memanggil `compute_kyc_state` tanpa label eksplisit; fungsi tersebut mengambil satu label berdasarkan user_id. `backend/routes/deps.py`, `get_label_by_user`, memilih label operasional berdasarkan active_label_id. Pemeriksaan persyaratan berisiko memakai label berbeda dari sasaran pekerjaan. KYC harus diperiksa sesuai sasaran tindakan; persyaratan akun/master dinilai terpisah. KYC administrasi juga harus tetap terpisah dari centang reputasi otomatis yang direncanakan.

3. **Label belum diklaim dan akses pernah dicabut tampak sama.** `frontend/src/pages/admin/Labels.jsx` menandai label tanpa user_id sebagai Unclaimed. Pencabutan akses menghasilkan no_account; filter daftar belum menyediakan kondisi tersebut. Riwayat dan penyebab harus dipertahankan agar label impor belum diklaim tidak disamakan dengan akun yang pernah dicabut.

4. **Identitas paket tidak konsisten.** Daftar pada `Labels.jsx` memetakan annual_subscription non-VIP menjadi Annual; `LabelDetailView.jsx` memetakannya menjadi Annual Normal. Multi-label dapat mendapat nama paket yang keliru pada dua tampilan. Gunakan satu pemetaan identitas paket; Flex/Go/Pro/Business tetap rancangan, bukan penetapan manfaat dan harga final.

5. **Paket berakhir belum mengikuti kesepakatan baru.** `backend/routes/entitlements.py` mengembalikan manfaat pay_per_release ketika paket tahunan tidak aktif. `backend/routes/releases.py`, `submit_release`, menggunakan manfaat tersebut untuk memilih alur bayar per rilisan. Rancangan yang disepakati membutuhkan identitas paket tetap tersimpan dan pengiriman baru/penambahan label dibatasi karena paket berakhir, dengan tindakan Perpanjang paket. Pembaruan paket hanya menghapus pembatasan karena paket, bukan pembatasan lain.

6. **Dua jalur perubahan paket berbeda.** Parser tanggal di `admin_label_service.py` memakai akhir hari UTC; layanan khusus `label_package_service.py` memakai akhir hari WIB. Tanggal yang sama dapat berbeda tujuh jam. Layanan khusus sudah mempunyai pemeriksaan revisi dan riwayat perubahan; jalur pembaruan umum belum memakai perlindungan yang sama. Satukan aturan, zona waktu, pemeriksaan perubahan bersamaan, dan pencatatan pada semua jalur.

7. **Daftar belum menjamin seluruh label dapat dijangkau.** `backend/routes/admin.py`, `admin_list_labels`, mengambil maksimum 1.000 label atau 200 hasil pencarian, tanpa metadata total/paginasi pada respons. Pencarian hanya nama label. Di atas batas tersebut daftar bukan inventaris lengkap. Tambahkan halaman dan total yang jelas serta pencarian identitas yang relevan. Jumlah label produksi belum diperiksa.

8. **Tampilan KYC dapat berbeda dari kondisi efektif.** Daftar memakai kyc_status tersimpan, sementara kyc_service menghitung ulang kelengkapan persyaratan dan dapat mengubah hasil menjadi needs_update. Semua tampilan harus merujuk pada definisi status yang sama; jangan mengartikan kyc_status sebagai centang reputasi.

9. **Fondasi royalti sudah tersedia.** `admin_get_label` di `backend/routes/admin.py` menghitung ringkasan royalti, pembayaran, saldo, dan penyesuaian. Pencabutan akses tidak menghapus katalog atau royalti. Gunakan fondasi ini untuk pemantauan nonoperasional dan pemisahan liabilitas. Daftar memakai saldo tersimpan dan pembaruan latar belakang, sedangkan detail menghitung snapshot; perbedaan kesegaran data harus jelas. Klasifikasi lebih dari satu tahun tanpa kegiatan membutuhkan definisi kegiatan relevan, bukan sekadar login atau royalti masuk.

10. **Penggabungan multi-label perlu pengamanan lanjutan.** `multi_label_merge.py` melakukan beberapa perubahan berurutan, sekaligus mengaktifkan paket multi-label selama 365 hari. Kegagalan ditandai failed dengan arahan recovery; tidak terlihat rollback menyeluruh pada alur ini. Pisahkan hubungan pengelolaan dari pemberian manfaat paket; tetapkan pemulihan aman untuk penggabungan parsial. Jangan menetapkan verifikasi master hanya dari lamanya akun atau paketnya.

## Arah UX untuk dibahas

- Satu baris utama mewakili satu label. Akun pengelola/master adalah hubungan yang terlihat, bukan pengganti identitas label.
- Nama, centang reputasi, nama paket, dan emblem mengikuti makna masing-masing. Sisa langganan berada di detail sesuai keputusan pengguna.
- Akses dan aktivitas memiliki kolom berbeda. Penyebab akses dapat lebih dari satu; label ringkas tidak boleh menghapus penyebab lainnya.
- Rincian memperlihatkan pengelola, persyaratan administrasi, alasan pembatasan, paket, serta tautan ke katalog dan royalti. Tindakan mengikuti objek dan kewenangan.
- Label nonoperasional yang masih menghasilkan royalti tetap tercatat, dengan pemantauan khusus Super Admin dan liabilitas terpisah. Klasifikasi nonoperasional tidak menghapus hak/saldo atau otomatis mengubahnya menjadi pendapatan platform.
- Centang reputasi otomatis memerlukan data aktivitas yang dapat dipercaya, masa bergabung yang benar, dan pemeriksaan hubungan master-anak. Jangan memakai tanggal impor sebagai masa bergabung tanpa validasi.

## Batas tahap ini

Ini dasar diskusi dan daftar celah, bukan implementasi V10. Paket/harga, konfigurasi KPI staff, dan ambang reputasi rinci belum ditetapkan ulang. Detail risiko lanjutan disimpan di sini agar pembahasan pengguna tetap terarah.
