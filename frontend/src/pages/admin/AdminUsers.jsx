import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { ADMIN_USER } from "@/constants/testIds";
import { Plus, X, Shield, AlertTriangle, Loader2 } from "lucide-react";

const ROLES = [
  { v: "super_admin", l: "Super Admin" },
  { v: "admin_release", l: "Admin Release" },
  { v: "admin_finance", l: "Admin Finance" },
  { v: "admin_support", l: "Admin Support" },
  { v: "admin_content", l: "Admin Content/CMS" },
];

export default function AdminUsers() {
  const { user: me } = useAuth();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "admin_release" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");
  // Danger zone — full data reset
  const [resetOpen, setResetOpen] = useState(false);
  const [resetConfirm, setResetConfirm] = useState("");
  const [resetDeleteFiles, setResetDeleteFiles] = useState(true);
  const [resetBusy, setResetBusy] = useState(false);
  const [resetErr, setResetErr] = useState("");
  const [resetReport, setResetReport] = useState(null);

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

  const submitReset = async (e) => {
    e.preventDefault();
    setResetErr("");
    setResetReport(null);
    setResetBusy(true);
    try {
      const fd = new FormData();
      fd.append("confirm", resetConfirm);
      fd.append("delete_r2_files", resetDeleteFiles ? "true" : "false");
      const { data } = await api.post("/admin/admin/danger/reset-all-data", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResetReport(data.report || {});
      setResetConfirm("");
    } catch (e) { setResetErr(formatApiError(e.response?.data?.detail)); }
    finally { setResetBusy(false); }
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

      {/* DANGER ZONE — Super Admin only */}
      {me?.role === "super_admin" && (
        <div className="rounded-[24px] border border-red-500/30 bg-red-500/[0.04] p-5 mt-12" data-testid="admin-danger-zone">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-red-500/15 text-red-300 grid place-items-center flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="text-xs uppercase tracking-widest text-red-300 font-bold">Danger Zone</div>
              <h2 className="font-display text-2xl font-extrabold tracking-tighter mt-1">Reset Semua Data</h2>
              <p className="text-sm text-zinc-400 mt-2 leading-relaxed">
                Menghapus <strong>SEMUA</strong> data bisnis: label, user (non-admin), rilisan, track, royalti, kontrak, withdraw, ticket, invoice, notifikasi, dan opsional file di R2.
                <br />
                <strong>Yang dipertahankan</strong>: admin users (super_admin & sub-admin), CMS landing settings, database indexes.
              </p>
              <button
                type="button"
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/15 hover:bg-red-500/25 text-red-200 border border-red-500/30 text-sm font-bold transition-colors"
                onClick={() => { setResetOpen(true); setResetReport(null); setResetErr(""); }}
                data-testid="admin-reset-open-btn"
              >
                <AlertTriangle className="w-4 h-4" /> Reset Semua Data
              </button>
            </div>
          </div>
        </div>
      )}

      {resetOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => !resetBusy && setResetOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submitReset} className="w-full max-w-lg rm-glass-strong rounded-[24px] p-6 space-y-4 border border-red-500/30">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-300" />
                <h3 className="font-display font-extrabold text-xl tracking-tighter text-red-200">Reset Semua Data</h3>
              </div>
              {!resetBusy && <button type="button" onClick={() => setResetOpen(false)}><X className="w-5 h-5" /></button>}
            </div>
            {!resetReport && (
              <>
                <div className="rounded-2xl bg-red-500/10 border border-red-500/30 px-4 py-3 text-sm text-red-200 leading-relaxed">
                  Aksi ini <strong>TIDAK BISA DIBATALKAN</strong>. Semua label, rilisan, royalti, dan file akan terhapus permanen.
                  Pastikan Anda sudah backup data penting.
                </div>
                <div>
                  <label className="rm-label">
                    Ketik <span className="font-mono text-red-300">RESET-ALL-DATA</span> untuk konfirmasi
                  </label>
                  <input
                    className="rm-input font-mono"
                    value={resetConfirm}
                    onChange={(e) => setResetConfirm(e.target.value)}
                    placeholder="RESET-ALL-DATA"
                    autoComplete="off"
                    data-testid="admin-reset-confirm-input"
                    required
                  />
                </div>
                <label className="flex items-start gap-3 text-sm text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={resetDeleteFiles}
                    onChange={(e) => setResetDeleteFiles(e.target.checked)}
                    className="mt-1"
                    data-testid="admin-reset-delete-files-checkbox"
                  />
                  <span>
                    Hapus juga <strong>semua file</strong> di Cloudflare R2 (cover, audio, contract PDF, dll). Centang jika ingin clean slate total.
                  </span>
                </label>
                {resetErr && <div className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 rounded-xl px-3 py-2">{resetErr}</div>}
                <div className="flex justify-end gap-2 pt-2">
                  <button type="button" className="rm-btn-ghost" onClick={() => setResetOpen(false)} disabled={resetBusy}>Batal</button>
                  <button
                    type="submit"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-500/80 hover:bg-red-500 text-white font-bold text-sm disabled:opacity-50"
                    disabled={resetBusy || resetConfirm !== "RESET-ALL-DATA"}
                    data-testid="admin-reset-submit-btn"
                  >
                    {resetBusy ? <><Loader2 className="w-4 h-4 animate-spin" /> Mereset…</> : "Konfirmasi Reset"}
                  </button>
                </div>
              </>
            )}
            {resetReport && (
              <div data-testid="admin-reset-report">
                <div className="rounded-2xl bg-emerald-500/10 border border-emerald-500/30 px-4 py-3 text-sm text-emerald-200 mb-3">
                  ✓ Reset selesai. Sistem sudah kembali ke kondisi awal (hanya admin & CMS yang dipertahankan).
                </div>
                <div className="text-xs font-mono bg-black/30 rounded-xl p-3 max-h-72 overflow-auto space-y-1">
                  {Object.entries(resetReport).map(([k, v]) => (
                    <div key={k} className="flex justify-between gap-2">
                      <span className="text-zinc-400">{k}</span>
                      <span className="text-emerald-300 font-bold">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))}
                </div>
                <div className="flex justify-end pt-3">
                  <button type="button" className="rm-btn-primary" onClick={() => { setResetOpen(false); window.location.reload(); }}>Reload Halaman</button>
                </div>
              </div>
            )}
          </form>
        </div>
      )}
    </div>
  );
}
