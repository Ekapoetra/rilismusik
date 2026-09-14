import React, { useEffect, useState } from "react";
import { Save, Trash2 } from "lucide-react";
import { api } from "@/api/client";
import { PermissionMatrix } from "./PermissionMatrix";
import { RoleValidationPanel } from "./RoleValidationPanel";
import { RoleBehaviorPreview } from "./RoleBehaviorPreview";

export const RoleEditor = ({ role, modules, onSave, onDelete, saving, readOnly = false }) => {
  const [form, setForm] = useState(role);
  const [warnings, setWarnings] = useState([]);
  const [preview, setPreview] = useState(null);
  const [checking, setChecking] = useState(false);
  useEffect(() => { setForm(role ? { ...role, permissions: [...(role.permissions || [])] } : null); }, [role]);

  const perms = form?.permissions || [];
  const active = form?.active !== false;
  const permsKey = perms.slice().sort().join(",");
  useEffect(() => {
    if (!form) return;
    let cancelled = false;
    setChecking(true);
    const handle = setTimeout(async () => {
      try {
        const [v, p] = await Promise.all([
          api.post("/admin/access/validate", { permissions: perms, active }),
          api.post("/admin/access/preview", { permissions: perms, active }),
        ]);
        if (!cancelled) { setWarnings(v.data.warnings || []); setPreview(p.data); }
      } catch (_e) { /* non-fatal */ }
      finally { if (!cancelled) setChecking(false); }
    }, 350);
    return () => { cancelled = true; clearTimeout(handle); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [permsKey, active, form?.id]);

  if (!form) return <div className="py-16 text-center text-sm text-zinc-500">Pilih role untuk melihat izin.</div>;
  return <form onSubmit={(event) => { event.preventDefault(); if (!readOnly) onSave(form); }} className="min-w-0 space-y-7" data-testid="admin-role-editor">
    <header className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0"><div className="text-xs font-bold uppercase text-zinc-500">{form.builtin ? "Role Bawaan" : form.id ? "Role Kustom" : "Role Baru"}</div><h2 className="mt-1 break-words font-display text-2xl font-extrabold" data-testid="admin-role-current-name" translate="no">{form.name || "Role tanpa nama"}</h2>{form.key === "super_admin" && <p className="mt-2 text-xs text-amber-300">Super Admin selalu memiliki akses penuh sebagai proteksi sistem.</p>}</div>{form.id && !form.builtin && !readOnly && <button type="button" onClick={() => onDelete(form)} className="inline-flex items-center gap-2 rounded-md border border-red-400/30 px-3 py-2 text-xs font-bold text-red-300 hover:bg-red-500/10" data-testid="admin-role-delete-button"><Trash2 className="h-3.5 w-3.5" /> Hapus Role</button>}</header>
    <div className="grid gap-4 md:grid-cols-2"><label><span className="rm-label">Nama Role</span><input className="rm-input" value={form.name || ""} disabled={readOnly} onChange={(event) => setForm({ ...form, name: event.target.value })} required data-testid="admin-role-name-input" /></label><label><span className="rm-label">Status</span><select className="rm-input" value={form.active === false ? "inactive" : "active"} disabled={readOnly || form.key === "super_admin"} onChange={(event) => setForm({ ...form, active: event.target.value === "active" })} data-testid="admin-role-status-select"><option value="active">Aktif</option><option value="inactive">Nonaktif</option></select></label><label className="md:col-span-2"><span className="rm-label">Deskripsi</span><textarea className="rm-input min-h-20 resize-y" value={form.description || ""} disabled={readOnly} onChange={(event) => setForm({ ...form, description: event.target.value })} data-testid="admin-role-description-input" /></label></div>
    <PermissionMatrix modules={modules} permissions={form.permissions || []} onChange={(permissions) => setForm({ ...form, permissions })} readOnly={readOnly} />
    <RoleValidationPanel warnings={warnings} loading={checking} />
    <RoleBehaviorPreview preview={preview} loading={checking} active={active} />
    {!readOnly && <div className="sticky bottom-4 flex justify-end border border-white/10 bg-[var(--ui-surface)] p-4 shadow-xl"><button type="submit" className="rm-btn-primary inline-flex items-center gap-2" disabled={saving || !form.name?.trim()} data-testid="admin-role-save-button"><Save className="h-4 w-4" />{saving ? "Menyimpan…" : "Simpan Role"}</button></div>}
  </form>;
};
