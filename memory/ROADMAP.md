# RILIS MUSIK — Prioritized Roadmap

## P0 — Production rollout
- Redeploy Phase 68 lalu validasi satu artis lama tanpa sosial, satu artis tersimpan multi-link, satu artis baru dari submit, snapshot admin, dan template WhatsApp pada setiap transisi status.
- Redeploy Phase 67 lalu cek pencarian nama label lintas periode di Admin Withdraw serta rendering logo/fallback pada Admin Label Management, Dashboard, dan Profil label.
- Redeploy Phase 66 lalu verifikasi satu akun label legacy: isi profil/rekening/kontrak/logo, unggah KTP, review melalui Super Admin/Admin Support, dan pastikan fitur inti baru terbuka setelah approve.
- Pastikan bucket R2 production tetap privat untuk prefix `kyc-private/`; akses KTP harus melalui endpoint pemilik/reviewer dan `/api/files/kyc-private/*` wajib 404.
- Redeploy Phase 65 lalu uji satu draft SINGLE dan satu EP pada akun internal: metadata, exact cover/WAV validation, revision edit, PPR invoice email/notifikasi, payment sandbox, Deliver to Believe, UPC/ISRC, Live, dan Takedown.
- Setelah redeploy Phase 64: buka Label Management → 24migo → Audit & Sesuaikan Saldo → Preview. Pastikan cutoff Mei 2026, periode Juni–Juli, persentase 35%, dan target sekitar Rp5.117.660 sebelum commit. Setelah commit, audit ulang harus `Sesuai` dan withdrawal web tidak berubah.
- Redeploy Phase 63 lalu cocokkan satu bulan pemasukan Xendit dengan invoice paid, satu bulan Dana Keluar/Tertunda dengan histori Withdraw, dan verifikasi urutan default Release Management.
- Redeploy Phase 62 lalu pilih satu withdrawal legacy yang cutoff-nya diketahui. Review preview saldo/baris sebelum commit, verifikasi saldo label sesudahnya, dan pastikan withdrawal web tidak menampilkan tombol edit.
- Redeploy Phase 61, lalu verifikasi satu pembayaran nyata bernominal kecil: metode pembayaran terbaca, label menerima receipt, admin menerima notifikasi, dan kartu tindak lanjut muncul bila layanannya memerlukan aksi.
- Redeploy Phase 60, lalu uji satu file kecil terlebih dahulu melalui Royalty Detail → Ganti File Import. Periksa preview per label sebelum mengetik `GANTI DATA`.
- Gunakan Audit File Ganda sebelum mengganti file yang dicurigai duplikat; commit penggantian menghapus import lama permanen dan hanya Super Admin yang dapat menjalankannya.
- Redeploy Phase 59 lalu buka Royalty Import → Audit File Ganda → Mulai Audit. Kirim hasil pasangan `MEI 2026.csv` vs `Mei 2022.csv` sebelum tindakan data apa pun.
- Jangan menghapus atau mengarsipkan duplikat sebelum dampak saldo aktif dan riwayat pembayaran selesai direview.
- Redeploy Phase 58 diagnostic-only, lalu jangan menjalankan audit/commit. Main agent akan membaca endpoint diagnosis F - Audio secara read-only dan menentukan akar masalah berdasarkan status/periode nyata.
- Redeploy Phase 57. Audit baru membandingkan status setiap baris dengan status induk laporan dan akan menemukan draft/pending yang tertinggal pada laporan yang sudah diterima.
- Setelah deploy, Audit Ulang F - Audio harus menampilkan data salah status atau perubahan perkiraan saldo. Jangan commit bila tetap nol; gunakan hasil itu sebagai bukti untuk investigasi data lebih lanjut.
- Redeploy Phase 56. Audit ulang harus mendeteksi F - Audio yang pasca-Januari masih bertanda sudah dibayar walau statusnya bukan withdrawn.
- Setelah deploy, jalankan Audit Ulang → cari `F - Audio` → pastikan kolom Royalti Salah Status tidak nol → jalankan koreksi → Audit Ulang lagi hingga nol dan verifikasi saldo terhadap Rp1.253.286.
- Redeploy perbaikan stale-job terbaru. Pekerjaan global lama yang berhenti di 70/1.720 sejak 23 Agustus akan ditutup otomatis saat commit audit berikutnya.
- Setelah deploy, klik Audit Ulang sebelum koreksi agar hasil sementara memakai data terbaru; tidak perlu menunggu pekerjaan lama tersebut.
- Redeploy Phase 55 global orphan-withdrawn audit/recovery. Perubahan tidak menyentuh saldo production sebelum Admin Finance/Super Admin menjalankan commit eksplisit.
- Setelah deploy, buka Withdraw → Audit Saldo Label, jalankan preview global, cari `F - Audio`, lalu pastikan orphan `withdrawn` setelah cutoff efektif Januari 2026 muncul sebelum commit.
- Review semua label berstatus `Riwayat belum lengkap`; label dengan paid withdrawal tanpa `period_to` sengaja diblokir dan harus diperbaiki manual sebelum pemulihan.
- Setelah commit audit yang sudah direview, jalankan Audit Ulang dan verifikasi F - Audio tidak lagi memiliki orphan, pending = Rp0, serta saldo available sesuai perhitungan Feb–Jul.
- Redeploy Phase 54 immediately to remove the `/api/admin/labels` 524 timeout and restore visible Label Management rows.
- After deploy, wait for the background balance snapshot to finish, then verify KSO list/detail parity.
- Redeploy the Label Management balance parity fix; production currently still displays the stale stored balance until redeploy.
- Post-deploy, verify KSO Music Distribution list balance equals its detail withdrawable balance.
- Redeploy preview auth frontend/backend so production receives Google Login, improved password reset, and merge-safe R2 CORS startup behavior.
- After redeploy, perform one real Google login using an already-registered label email and verify both apex/`www` callback paths.
- Retry the latest royalty CSV upload from production `www`; the shared bucket preflight is already repaired.
- Redeploy current preview code so production mendapat perbaikan login apex/`www` dan konfigurasi official Hostinger mailbox.
- Redeploy juga membawa fitur Admin Withdraw → Tambah Riwayat Manual Legacy.
- Redeploy juga membawa kolom Rupiah `Saldo Available` pada daftar Label Management.
- Redeploy membawa default sort saldo terbesar, pilihan sort label/email/saldo, dan kolom bulan withdraw terakhir.
- Redeploy membawa breakdown Admin Dashboard: Total Bagian Label, Sudah Withdraw, dan Belum Withdraw.
- Redeploy membawa pencarian label server-side agar seluruh label production dapat ditemukan, termasuk label lama di luar 1.000 hasil awal.
- Setelah redeploy, smoke test login/me/refresh pada `https://rilismusik.com` dan `https://www.rilismusik.com` dari Windows dan macOS.
- Run one controlled production release-submission email and one manually triggered monthly summary, then confirm Hostinger delivery logs.
- Run a controlled user acceptance pass for multi-device auth, bank approval, PPR invoice, and PDF download.

## P1 — Product follow-up
- Add Admin Finance UI for monthly email delivery status/retry (backend status endpoint already exists).
- Add explicit bank-change history timeline and cancellation before approval.
- Add bulk download/archive for generated copyright letters.
- Add migration/report for legacy PPR releases whose invoices were created before the new post-approval flow.

## P2 — Quality & operations
- Tambahkan fingerprint/checksum saat upload royalty CSV ke R2 agar file duplikat ditolak sebelum masuk proses import.
- Link remaining CMS settings dynamically across all landing sections.
- Move FastAPI deprecated `on_event` startup/shutdown hooks to lifespan handlers.
- Add background job notification deep-links by exact job kind instead of the generic migration page.
- Add an optional daily operations digest for failed imports, failed emails, and pending approvals.

## Completed in current cycle
- Phase 68 menambahkan identitas sosial wajib artis, reusable artist profile dari submission, snapshot sosial admin, WhatsApp follow-up status-aware, dan lokalisasi workflow rilisan.
- Phase 67 menambahkan pencarian withdrawal lintas seluruh periode berdasarkan nama label serta identitas logo/fallback konsisten di tiga area utama.
- Phase 66 menambahkan mandatory KYC seluruh label, checklist profil, logo/KTP R2 privat, reviewer queue, approve/reject, dashboard counter, backend feature gate, dan frontend blurred lockout.
- Phase 65 menambahkan complete release metadata wizard, strict asset validation, revision-safe editing, full Admin detail, role-safe workflow actions, conditional Annual/PPR state machine, invoice notification, Believe delivery, UPC/ISRC Live gate, Reject, dan Takedown.
- Phase 64 menambahkan scoped per-label reconciliation dengan exact active-rate projection, mandatory preview, post-cutoff status recovery, web-withdraw protection, dan reusable Label Detail workflow.
- Phase 63 menambahkan release operational-priority ordering, pemasukan Xendit bulanan/tahunan, serta ringkasan dan filter arus dana Withdraw.
- Phase 62 menambahkan guarded edit bulan laporan terakhir untuk legacy withdrawal, mandatory preview, background commit, direct-web immutability, rekonsiliasi saldo/status line, dan audit revision.
- Phase 60 menambahkan selected-file replacement: upload R2 staging, mandatory preview, hard-delete lama setelah commit, adjustment paid history, recalculation active withdrawal, resume/idempotency, dan refresh saldo/analytics.
- Phase 59 menambahkan audit file ganda background yang hanya membaca data, membandingkan periode, menghitung dampak label/saldo/riwayat, dan memperjelas total file multi-periode pada UI.
- Phase 57 menyelaraskan draft/pending berdasarkan status induk laporan, memperbaiki alur Dana Diterima agar selalu memproses keduanya, dan menjaga draft pada laporan yang belum diterbitkan.
- Phase 56 memulihkan penanda `legacy_settled=true` yang salah pada status draft/pending/available setelah batas tarik, mempertahankan status asli, dan menghitung ulang bagian label.
- Phase 55 mendeteksi withdrawn orphan setelah cutoff paid untuk seluruh label, memblokir riwayat ambigu, memulihkan baris secara guarded, menghitung ulang rate terkini, dan memperbarui snapshot saldo.
- RCA production F - Audio membuktikan formula 50% benar; sumber selisih adalah komposisi royalty lines aktif/withdrawn dan stored pending negatif, bukan potongan tambahan.
- Label Management available balance now uses the same live source-of-truth computation as Label Detail.
- Password reset email hardening, existing-label Google Login, and production R2 apex/`www` CORS repair.
- Manual legacy withdraw dengan amount otomatis, background settlement, rekonsiliasi saldo, dan label visibility guard.
- Multi-device JWT sessions and global revocation.
- Login password visibility.
- Safe admin deletion/restoration and `admin_marketing` access.
- Two-sided bank-account approval.
- Expanded release metadata and submission notifications.
- Post-approval combined PPR invoice.
- Content ID YouTube link.
- Add-on edit/delete/archive.
- Copyright PDF with CMS signature/stamp.
- Monthly royalty emails and background completion notifications.