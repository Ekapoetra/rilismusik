import React, { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import { UserPlus, Copy, FileSpreadsheet, X, RefreshCw, AlertCircle } from "lucide-react";
import { useAuth } from "@/api/AuthContext";

const fmtIDR = (value) => new Intl.NumberFormat("id-ID", {
  style: "currency", currency: "IDR", maximumFractionDigits: 0,
}).format(Number(value || 0));
const fmtPeriod = (period) => {
  if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(period || "")) return period || "Belum pernah WD";
  return new Intl.DateTimeFormat("id-ID", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${period}-01T00:00:00Z`));
};

export default function AdminLabels() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("balance_desc");
  const [creating, setCreating] = useState(null);  // label being processed
  const [created, setCreated] = useState(null);   // success result with plaintext password
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [balanceSync, setBalanceSync] = useState(null);
  const loadRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [sortBy, sortDir] = sort.split("_");
      const { data } = await api.get("/admin/labels", { params: { q: q || undefined, status: status || undefined, sort_by: sortBy, sort_dir: sortDir } });
      setItems(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Daftar label gagal dimuat. Silakan coba lagi.");
    } finally { setLoading(false); }
  }, [q, status, sort]);
  loadRef.current = load;
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    let timer;
    const check = async () => {
      try {
        const { data } = await api.get("/admin/labels/balance-refresh/status");
        setBalanceSync(data);
        if (data.status === "running") timer = setTimeout(check, 3000);
        else if (data.status === "done") loadRef.current?.();
      } catch { setBalanceSync(null); }
    };
    api.post("/admin/labels/balance-refresh").then(({ data }) => {
      setBalanceSync(data);
      if (data.status === "running" || data.queued) timer = setTimeout(check, 1500);
    }).catch(() => {});
    return () => { if (timer) clearTimeout(timer); };
  }, []);

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
        <div className="min-w-[230px]">
          <label className="rm-label">Urutan</label>
          <select className="rm-input" value={sort} onChange={(e) => setSort(e.target.value)} data-testid="admin-labels-sort">
            <option value="balance_desc">Saldo terbesar → terkecil</option>
            <option value="balance_asc">Saldo terkecil → terbesar</option>
            <option value="label_asc">Label A → Z</option>
            <option value="label_desc">Label Z → A</option>
            <option value="email_asc">Email A → Z</option>
            <option value="email_desc">Email Z → A</option>
          </select>
        </div>
        <button className="rm-btn-ghost" onClick={load} data-testid="admin-labels-filter">Filter</button>
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300" data-testid="admin-labels-error"><AlertCircle className="mr-2 inline h-4 w-4" />{error}</div>}
      {balanceSync?.status === "running" && <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 px-4 py-3 text-sm text-sky-200" data-testid="admin-labels-balance-sync"><RefreshCw className="mr-2 inline h-4 w-4 animate-spin" />Menyelaraskan saldo label di background. Daftar tetap dapat digunakan.</div>}
      {balanceSync?.status === "error" && <div role="alert" className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200" data-testid="admin-labels-balance-sync-error"><AlertCircle className="mr-2 inline h-4 w-4" />Sinkronisasi saldo gagal. Daftar tetap tersedia; coba buka ulang halaman atau jalankan Audit Saldo.</div>}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Email</div>
          <div className="col-span-1">Tipe</div>
          <div className="col-span-1">Status</div>
          <div className="col-span-2 text-right" data-testid="admin-labels-available-balance-header">Saldo Available</div>
          <div className="col-span-2 text-right" data-testid="admin-labels-last-withdraw-header">Withdraw Terakhir</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {loading ? <div className="p-8 text-center text-zinc-500 text-sm" data-testid="admin-labels-loading">Memuat label…</div> : items.length === 0 ? <div className="p-8 text-center text-zinc-500 text-sm" data-testid="admin-labels-empty">Belum ada label yang sesuai filter.</div> : items.map((l) => {
          const unclaimed = !l.user_id || l.account_status === "legacy_unclaimed";
          return (
            <div key={l.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02]" data-testid={`admin-label-row-${l.id}`}>
              <div className="col-span-12 md:col-span-3">
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
              <div className="col-span-6 md:col-span-2 text-sm truncate">{l.email || <span className="text-zinc-600 italic">tidak ada</span>}</div>
              <div className="col-span-6 md:col-span-1 text-sm capitalize truncate">{l.payment_type?.replace(/_/g, " ") || "—"}</div>
              <div className="col-span-4 md:col-span-1">
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold capitalize ${
                  l.account_status === "active" ? "bg-emerald-500/15 text-emerald-300"
                  : l.account_status === "legacy_unclaimed" ? "bg-amber-500/15 text-amber-300"
                  : l.account_status === "suspended" ? "bg-amber-500/15 text-amber-300"
                  : "bg-red-500/15 text-red-300"
                }`}>{(l.account_status || "—").replace(/_/g, " ")}</span>
              </div>
              <div className="col-span-4 md:col-span-2 text-right" data-testid={`admin-label-available-balance-${l.id}`}>
                <div className="text-[10px] uppercase tracking-widest text-zinc-500 md:hidden">Saldo Available</div>
                <div className="font-display font-bold tabular-nums text-emerald-300">{fmtIDR(l.balance_available_idr)}</div>
                <div className="text-[10px] text-zinc-600">belum withdrawn</div>
              </div>
              <div className="col-span-4 md:col-span-2 text-right" data-testid={`admin-label-last-withdraw-${l.id}`}>
                <div className="text-[10px] uppercase tracking-widest text-zinc-500 md:hidden">Withdraw Terakhir</div>
                <div className={`text-sm font-semibold ${l.last_withdrawn_period ? "text-zinc-200" : "text-zinc-500"}`}>{fmtPeriod(l.last_withdrawn_period)}</div>
                {l.last_withdrawn_period && <div className="text-[10px] font-mono text-zinc-600">{l.last_withdrawn_period}</div>}
              </div>
              <div className="col-span-4 md:col-span-1 text-right space-y-1">
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
