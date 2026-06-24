import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { ADMIN_USER } from "@/constants/testIds";
import { Plus, X, Shield } from "lucide-react";

const ROLES = [
  { v: "super_admin", l: "Super Admin" },
  { v: "admin_release", l: "Admin Release" },
  { v: "admin_finance", l: "Admin Finance" },
  { v: "admin_support", l: "Admin Support" },
  { v: "admin_content", l: "Admin Content/CMS" },
];

export default function AdminUsers() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "admin_release" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const { data } = await api.get("/admin/admin-users");
    setItems(data);
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setSaving(true);
    try {
      await api.post("/admin/admin-users", form);
      setOpen(false);
      setForm({ name: "", email: "", password: "", role: "admin_release" });
      await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Access Control</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Admin Users</h1>
        </div>
        <button className="rm-btn-primary flex items-center gap-2" onClick={() => setOpen(true)} data-testid={ADMIN_USER.addButton}>
          <Plus className="w-4 h-4" /> Tambah Admin
        </button>
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-4">Nama</div>
          <div className="col-span-4">Email</div>
          <div className="col-span-3">Role</div>
          <div className="col-span-1">Status</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm">Belum ada admin user.</div> : items.map((u) => (
          <div key={u.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0">
            <div className="col-span-12 md:col-span-4 flex items-center gap-2"><Shield className="w-4 h-4 text-zinc-600" />{u.name}</div>
            <div className="col-span-6 md:col-span-4 text-sm truncate">{u.email}</div>
            <div className="col-span-3 md:col-span-3 text-sm capitalize">{u.role.replace(/_/g, " ")}</div>
            <div className="col-span-3 md:col-span-1 text-xs capitalize">{u.status}</div>
          </div>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4" onClick={() => setOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Tambah Admin User</h3>
              <button type="button" onClick={() => setOpen(false)}><X className="w-5 h-5" /></button>
            </div>
            <div>
              <label className="rm-label">Nama</label>
              <input data-testid={ADMIN_USER.nameInput} className="rm-input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div>
              <label className="rm-label">Email</label>
              <input data-testid={ADMIN_USER.emailInput} type="email" className="rm-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
            <div>
              <label className="rm-label">Password</label>
              <input data-testid={ADMIN_USER.passwordInput} type="text" className="rm-input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} />
            </div>
            <div>
              <label className="rm-label">Role</label>
              <select data-testid={ADMIN_USER.roleSelect} className="rm-input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r.v} value={r.v}>{r.l}</option>)}
              </select>
            </div>
            {err && <div className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{err}</div>}
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
              <button className="rm-btn-primary" disabled={saving} data-testid={ADMIN_USER.saveButton}>{saving ? "Menyimpan…" : "Simpan"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
