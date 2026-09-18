# PRD — UI Settings: Compact Navigation (2026-06)

## Diterapkan
- Konsep **Group** baru pada navigasi (sebelumnya flat). Model: `admin_ui_settings.admin_navigation` kini punya `groups:[{id,labels{id,en},order}]` dan tiap item punya `group_id`.
- Registry: `DEFAULT_NAV_GROUPS` + `NAV_GROUP_MAP` di `admin_permission_service.py` (7 grup sesuai §21: work_center, distribution_ops, royalty_finance, services_support, team_access, personal, system). `ui_settings` dipindah top-level (default), tapi data lama yang punya parent tetap ikut grup parent.
- `_merge_default_nav` (admin_access.py): seed groups bila kosong, isi group_id yang hilang, dan **paksa subtab ikut grup parent** (agar valid untuk data lama).
- Endpoint: `GET /admin/navigation` & `GET /admin/ui-settings` kembalikan `groups`; `PUT /admin/ui-settings` validasi groups + group_id + subtab satu-level + subtab segrup dgn parent. Semua key wajib hadir (tidak ada remove menu — sesuai keputusan user; visibilitas ikut role).
- Model: `AdminNavGroupIn`, `AdminNavItemIn.group_id`, `AdminUiSettingsIn.groups`.
- Sidebar asli (`AdminLayout.AdminSidebarView`): render header grup (skip grup kosong), item per grup, subtab nested. Fallback flat bila groups kosong. `AdminNavigationContext` meneruskan `groups`.
- Editor `pages/admin/UiSettings.jsx` (rewrite): live preview (kiri, pakai AdminSidebarView), search, Tambah Group, kartu grup compact (rename inline, ••• pindah atas/bawah/hapus-jika-kosong, badge N menu), baris menu (drag handle, nama inline, EN helper read-only, selector Parent/Main Tab). DnD menu (dnd-kit) dalam & antar grup. Grup reorder via ••• (bukan drag). Bahasa Bawaan + SoundSettings dipertahankan di bawah.

## Keputusan user
- Grup di sidebar asli: YA (§21). EN: read-only, grup/menu baru mirror ID. TIDAK ada remove/add-picker menu. Pertahankan Bahasa Bawaan + Sound Settings.

## Verifikasi
- Backend: GET navigation/ui-settings kembalikan 7 groups + group_id; PUT round-trip 39 items OK (setelah fix subtab-ikut-grup-parent).
- Sidebar asli: 7 header grup tampil benar (screenshot).
- Editor: struktur, live preview, kartu grup, drag handle tampil; `input_value` menu = "Dashboard" (benar), save tersimpan.

## ⚠️ BELUM TUNTAS / perlu cek visual
- Kontras teks NAMA MENU di baris editor tampak tidak terlihat pada screenshot terkompresi (nilai benar, style `color:var(--ui-text)`+`WebkitTextFillColor` sudah ditambahkan). Perlu diverifikasi di browser resolusi penuh; bila masih pudar, ganti ke warna eksplisit sesuai tema (mis. class token teks utama admin) — nama grup sudah tampil normal dengan style sama.
- Group reorder via tombol ••• (AC-07 minta drag; belum drag). Bisa ditingkatkan ke drag bila diminta.
- Responsive/touch DnD dasar ada (TouchSensor); belum diuji di mobile.
