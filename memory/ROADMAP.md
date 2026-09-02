# RILIS MUSIK — Prioritized Roadmap

## P0 — Production rollout
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
- Link remaining CMS settings dynamically across all landing sections.
- Move FastAPI deprecated `on_event` startup/shutdown hooks to lifespan handlers.
- Add background job notification deep-links by exact job kind instead of the generic migration page.
- Add an optional daily operations digest for failed imports, failed emails, and pending approvals.

## Completed in current cycle
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