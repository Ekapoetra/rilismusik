import React, { useCallback, useEffect, useState } from "react";
import { Pencil, Plus, Trash2, UserCog, ShieldX, Ban } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { AdminUserDialog } from "@/components/admin/access/AdminUserDialog";
import { ADMIN_USER } from "@/constants/testIds";
import { toast } from "@/components/ui/sonner";

export default function AdminUsers() {
  const { user, hasPermission } = useAuth();
  const [items, setItems] = useState([]); const [roles, setRoles] = useState([]);
  const [dialog, setDialog] = useState(undefined); const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [showDisabled, setShowDisabled] = useState(false);
  const [selected, setSelected] = useState(new Set());
  const canManage = hasPermission("access.users.manage");

  const load = useCallback(async () => {
    try {
      const [usersRes, rolesRes] = await Promise.all([api.get(`/admin/admin-users?include_disabled=${showDisabled}`), api.get("/admin/access/role-options")]);
      setItems(usersRes.data || []); setRoles(rolesRes.data || []); setSelected(new Set());
    } catch (e) { setError(formatApiError(e.response?.data?.detail)); }
  }, [showDisabled]);
  useEffect(() => { load(); }, [load]);

  const save = async (form) => { setSaving(true); setError(""); try { if (dialog?.id) await api.patch(`/admin/admin-users/${dialog.id}`, { name: form.name, admin_role_id: form.admin_role_id, status: form.status, password: form.password || undefined }); else await api.post("/admin/admin-users", { name: form.name, email: form.email, password: form.password, admin_role_id: form.admin_role_id }); setDialog(undefined); await load(); toast.success("Pengguna admin berhasil disimpan."); } catch (e) { setError(formatApiError(e.response?.data?.detail)); } finally { setSaving(false); } };
  const remove = async (admin) => { if (!window.confirm(`Nonaktifkan akun ${admin.name}? Akun tidak bisa login tetapi datanya tetap tersimpan.`)) return; try { await api.delete(`/admin/admin-users/${admin.id}`); await load(); toast.success("Akun admin dinonaktifkan."); } catch (e) { setError(formatApiError(e.response?.data?.detail)); } };
  const purge = async (admin) => { if (!window.confirm(`HAPUS PERMANEN akun ${admin.name}? Tindakan ini tidak bisa dibatalkan dan menghapus seluruh data terkait.`)) return; try { await api.delete(`/admin/admin-users/${admin.id}?permanent=true`); await load(); toast.success("Akun dihapus permanen."); } catch (e) { setError(formatApiError(e.response?.data?.detail)); } };
  const bulkPurge = async () => { const ids = [...selected]; if (ids.length === 0) return; if (!window.confirm(`HAPUS PERMANEN ${ids.length} akun terpilih? Tindakan ini tidak bisa dibatalkan.`)) return; try { const { data } = await api.post("/admin/admin-users/bulk-delete", { user_ids: ids }); await load(); toast.success(`${data.purged.length} akun dihapus permanen${data.skipped.length ? `, ${data.skipped.length} dilewati` : ""}.`); } catch (e) { setError(formatApiError(e.response?.data?.detail)); } };
  const toggleSel = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n; });

  return <div className="space-y-7" data-testid="admin-users-page">
    <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-6">
      <div><div className="text-xs font-bold uppercase text-zinc-500">Kontrol Akses</div><h1 className="mt-1 font-display text-4xl font-extrabold">Pengguna Admin</h1><p className="mt-2 text-sm text-zinc-400">Ubah nama, role kustom, status, dan akses login admin.</p></div>
      {canManage && <button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={() => setDialog(null)} data-testid={ADMIN_USER.addButton}><Plus className="h-4 w-4" /> Tambah Admin</button>}
    </header>
    {error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-500/10 p-3 text-sm text-red-200" data-testid="admin-users-error">{error}</div>}

    <div className="flex flex-wrap items-center justify-between gap-3">
      <label className="flex items-center gap-2 text-sm text-zinc-400"><input type="checkbox" checked={showDisabled} onChange={(e) => setShowDisabled(e.target.checked)} className="accent-[#FF1F8E]" data-testid="admin-users-show-disabled" /> Tampilkan akun nonaktif</label>
      {canManage && selected.size > 0 && <button type="button" onClick={bulkPurge} className="inline-flex items-center gap-2 rounded-md bg-red-500/15 px-3 py-2 text-sm font-bold text-red-300 hover:bg-red-500/25" data-testid="admin-users-bulk-purge"><ShieldX className="h-4 w-4" /> Hapus permanen ({selected.size})</button>}
    </div>

    <div className="divide-y divide-white/10 border-y border-white/10" data-testid="admin-users-list">{items.map((admin) => {
      const disabled = admin.status === "disabled" || admin.status === "suspended";
      return <article className="grid gap-4 py-5 md:grid-cols-[auto_minmax(0,1.5fr)_minmax(0,1fr)_120px_auto] md:items-center" key={admin.id} data-testid={`admin-user-row-${admin.id}`}>
        <div className="flex items-center">{canManage && admin.id !== user?.id ? <input type="checkbox" checked={selected.has(admin.id)} onChange={() => toggleSel(admin.id)} className="h-4 w-4 accent-[#FF1F8E]" data-testid={`admin-user-select-${admin.id}`} /> : <span className="w-4" />}</div>
        <div className="flex min-w-0 items-center gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-white/[0.05] text-zinc-400"><UserCog className="h-4 w-4" /></span><div className="min-w-0"><div className="truncate font-bold" data-testid={`admin-user-name-${admin.id}`} translate="no">{admin.name}</div><div className="truncate text-xs text-zinc-500" data-testid={`admin-user-email-${admin.id}`} translate="no">{admin.email}</div></div></div>
        <div><div className="text-[10px] font-bold uppercase text-zinc-600">Role</div><div className="mt-1 text-sm text-zinc-300" data-testid={`admin-user-role-${admin.id}`} translate="no">{admin.role_name || admin.role}</div></div>
        <span className={`text-xs font-bold ${admin.status === "active" ? "text-emerald-300" : "text-amber-300"}`} data-testid={`admin-user-status-${admin.id}`}>{admin.status === "active" ? "Aktif" : disabled ? "Nonaktif" : "Ditangguhkan"}</span>
        {canManage && <div className="flex justify-end gap-1">
          {!disabled && <button type="button" title="Edit pengguna" onClick={() => setDialog(admin)} className="rounded-md p-2 text-zinc-400 hover:bg-white/5 hover:text-white" data-testid={`admin-user-edit-${admin.id}`}><Pencil className="h-4 w-4" /></button>}
          {!disabled && <button type="button" title="Nonaktifkan pengguna" onClick={() => remove(admin)} disabled={admin.id === user?.id} className="rounded-md p-2 text-amber-300 hover:bg-amber-500/10 disabled:opacity-25" data-testid={`admin-user-delete-${admin.id}`}><Ban className="h-4 w-4" /></button>}
          <button type="button" title="Hapus permanen" onClick={() => purge(admin)} disabled={admin.id === user?.id} className="rounded-md p-2 text-red-300 hover:bg-red-500/10 disabled:opacity-25" data-testid={`admin-user-purge-${admin.id}`}><Trash2 className="h-4 w-4" /></button>
        </div>}
      </article>;
    })}</div>
    {dialog !== undefined && <AdminUserDialog user={dialog} roles={roles} onClose={() => setDialog(undefined)} onSave={save} saving={saving} />}
  </div>;
}
