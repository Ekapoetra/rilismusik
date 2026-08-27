import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { UserPlus, Copy, FileSpreadsheet, X } from "lucide-react";
import { useAuth } from "@/api/AuthContext";

export default function AdminLabels() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [creating, setCreating] = useState(null);  // label being processed
  const [created, setCreated] = useState(null);   // success result with plaintext password

  const load = useCallback(async () => {
    const { data } = await api.get("/admin/labels", { params: { q: q || undefined, status: status || undefined } });
    setItems(data);
  }, [q, status]);
  useEffect(() => { load(); }, [load]);

  const onCreated = () => {
    setCreating(null);
    load();
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Operations</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Label Management</h1>
        </div>
        {["super_admin", "admin_finance"].includes(user?.role) && <Link to="/admin/labels/rate-import" className="rm-btn-primary flex items-center gap-2" data-testid="admin-label-rate-import-link"><FileSpreadsheet className="w-4 h-4" /> Impor Rate</Link>}
      </div>
      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="rm-label">Cari Label</label>
          <input className="rm-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} placeholder="Nama label…" data-testid="admin-labels-search" />
        </div>
        <div className="min-w-[180px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-labels-status">
            <option value="">Semua</option>
            <option value="active">Active</option>
            <option value="legacy_unclaimed">Legacy / Unclaimed</option>
            <option value="suspended">Suspended</option>
            <option value="blacklisted">Blacklisted</option>
          </select>
        </div>
        <button className="rm-btn-ghost" onClick={load} data-testid="admin-labels-filter">Filter</button>
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-4">Label</div>
          <div className="col-span-3">Email</div>
          <div className="col-span-2">Tipe</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm">Belum ada label.</div> : items.map((l) => {
          const unclaimed = !l.user_id || l.account_status === "legacy_unclaimed";
          return (
            <div key={l.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]" data-testid={`admin-label-row-${l.id}`}>
              <div className="col-span-12 md:col-span-4">
                <div className="font-semibold flex items-center gap-2">
                  {l.label_name}
                  {unclaimed && (
                    <span className="px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 text-[10px] font-bold uppercase tracking-wider">Unclaimed</span>
                  )}
                  {l.auto_created_from && (
                    <span className="px-2 py-0.5 rounded-full bg-violet-500/15 text-violet-300 text-[10px] font-bold uppercase tracking-wider" title={`Auto-created from royalty import ${l.auto_created_from?.slice(0, 8)}`}>From CSV</span>
                  )}
                </div>
                <div className="text-xs text-zinc-500">{l.pic_name || "—"}</div>
              </div>
              <div className="col-span-6 md:col-span-3 text-sm truncate">{l.email || <span className="text-zinc-600 italic">tidak ada</span>}</div>
              <div className="col-span-6 md:col-span-2 text-sm capitalize">{l.payment_type?.replace(/_/g, " ") || "—"}</div>
              <div className="col-span-6 md:col-span-2">
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${
                  l.account_status === "active" ? "bg-emerald-500/15 text-emerald-300"
                  : l.account_status === "legacy_unclaimed" ? "bg-amber-500/15 text-amber-300"
                  : l.account_status === "suspended" ? "bg-amber-500/15 text-amber-300"
                  : "bg-red-500/15 text-red-300"
                }`}>{(l.account_status || "—").replace(/_/g, " ")}</span>
              </div>
              <div className="col-span-6 md:col-span-1 text-right space-y-1">
                <Link to={`/admin/labels/${l.id}`} className="block text-sm font-semibold rm-gradient-text" data-testid={`admin-label-detail-${l.id}`}>Detail →</Link>
                {unclaimed && (
                  <button
                    onClick={() => setCreating(l)}
                    className="text-xs text-amber-300 hover:text-amber-200 flex items-center gap-1 ml-auto"
                    data-testid={`admin-label-create-account-${l.id}`}
                  >
                    <UserPlus className="w-3 h-3" /> Buatkan Akun
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {creating && (
        <CreateAccountModal
          label={creating}
          onClose={() => setCreating(null)}
          onSuccess={(res) => { setCreated(res); onCreated(); }}
        />
      )}
      {created && <CredentialsModal data={created} onClose={() => setCreated(null)} />}
    </div>
  );
}

function CreateAccountModal({ label, onClose, onSuccess }) {
  const [form, setForm] = useState({
    email: label.email || "",
    pic_name: label.pic_name || "",
    whatsapp: label.whatsapp || "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setLoading(true);
    try {
      const fd = new FormData();
      fd.append("email", form.email);
      if (form.pic_name) fd.append("pic_name", form.pic_name);
      if (form.whatsapp) fd.append("whatsapp", form.whatsapp);
      if (form.password) fd.append("password", form.password);
      const { data } = await api.post(`/admin/labels/${label.id}/create-account`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      onSuccess(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Gagal membuat akun");
    } finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <form onSubmit={submit} className="rm-card max-w-md w-full p-6" data-testid="admin-create-account-modal">
        <div className="flex justify-between items-start mb-4">
          <div>
            <div className="text-lg font-bold">Buatkan Akun untuk Label</div>
            <div className="text-xs text-zinc-400 mt-1"><b>{label.label_name}</b></div>
          </div>
          <button type="button" onClick={onClose} className="text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="rm-label">Email <span className="text-red-400">*</span></label>
            <input required type="email" className="rm-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="admin-create-email" />
          </div>
          <div>
            <label className="rm-label">Nama PIC</label>
            <input className="rm-input" value={form.pic_name} onChange={(e) => setForm({ ...form, pic_name: e.target.value })} placeholder="Default: nama label" />
          </div>
          <div>
            <label className="rm-label">WhatsApp</label>
            <input className="rm-input" value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} placeholder="081xxx" />
          </div>
          <div>
            <label className="rm-label">Password (kosongkan untuk auto-generate)</label>
            <input type="text" className="rm-input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="Min 8 karakter — atau biarkan kosong" />
          </div>
        </div>
        {err && <div className="text-sm text-red-300 bg-red-500/10 rounded-xl px-3 py-2 mt-3">{err}</div>}
        <div className="flex gap-2 mt-5">
          <button type="button" onClick={onClose} className="rm-btn-ghost flex-1">Batal</button>
          <button type="submit" disabled={loading} className="rm-btn-primary flex-1" data-testid="admin-create-account-submit">
            {loading ? "Memproses…" : "Buat Akun"}
          </button>
        </div>
      </form>
    </div>
  );
}

function CredentialsModal({ data, onClose }) {
  const copy = () => navigator.clipboard.writeText(`Email: ${data.email}\nPassword: ${data.password}`);
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
      <div className="rm-card max-w-md w-full p-6" data-testid="admin-credentials-modal">
        <div className="text-lg font-bold text-emerald-300 mb-1">✓ Akun berhasil dibuat</div>
        <div className="text-xs text-zinc-400 mb-4">Label: <b>{data.label_name}</b></div>
        <div className="rounded-xl bg-amber-500/10 border border-amber-500/30 px-3 py-2 text-xs text-amber-200 mb-4">
          ⚠️ {data.warning}
        </div>
        <div className="space-y-2 text-sm">
          <div className="rounded-xl bg-white/[0.03] border border-white/5 px-3 py-2">
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Email</div>
            <div className="font-mono">{data.email}</div>
          </div>
          <div className="rounded-xl bg-white/[0.03] border border-white/5 px-3 py-2">
            <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">Password</div>
            <div className="font-mono select-all">{data.password}</div>
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={copy} className="rm-btn-ghost flex-1 flex items-center justify-center gap-2"><Copy className="w-4 h-4" /> Salin</button>
          <button onClick={onClose} className="rm-btn-primary flex-1" data-testid="admin-credentials-close">Sudah Saya Salin</button>
        </div>
      </div>
    </div>
  );
}
