import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { Upload, FileSpreadsheet, CheckCircle2, Banknote } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtEUR(n) { return new Intl.NumberFormat("en-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 2 }).format(n || 0); }

function todayPeriod() {
  const d = new Date();
  d.setMonth(d.getMonth() - 1);
  return d.toISOString().slice(0, 7);
}

export default function AdminRoyaltyImport() {
  const [imports, setImports] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ period: todayPeriod(), rate_eur_idr: 17500, file: null, note: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => { const { data } = await api.get("/royalty/admin/imports"); setImports(data); };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    if (!form.file) { setErr("File CSV wajib diupload"); return; }
    if (!form.period.match(/^\d{4}-\d{2}$/)) { setErr("Periode harus YYYY-MM"); return; }
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("period", form.period);
      fd.append("rate_eur_idr", form.rate_eur_idr);
      fd.append("note", form.note || "");
      fd.append("file", form.file);
      await api.post("/royalty/admin/imports", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setMsg("CSV diupload & diparse.");
      setOpen(false);
      setForm({ period: todayPeriod(), rate_eur_idr: 17500, file: null, note: "" });
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Finance</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Royalty Import</h1>
          <p className="text-sm text-slate-600 mt-1">Upload CSV Believe (EUR) + set kurs IDR per periode.</p>
        </div>
        <button className="rm-btn-primary flex items-center gap-2" onClick={() => setOpen(true)} data-testid="admin-royalty-upload-button">
          <Upload className="w-4 h-4" /> Upload CSV
        </button>
      </div>

      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">{msg}</div>}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-slate-500 bg-slate-50/60 border-b border-slate-100">
          <div className="col-span-2">Periode</div>
          <div className="col-span-2">Kurs</div>
          <div className="col-span-2">Revenue EUR</div>
          <div className="col-span-2">Bagian Label IDR</div>
          <div className="col-span-2">Lines (matched/total)</div>
          <div className="col-span-2">Status</div>
        </div>
        {imports.length === 0 ? <div className="p-10 text-center text-slate-500 text-sm">Belum ada import. Klik &quot;Upload CSV&quot; untuk mulai.</div> : imports.map((i) => (
          <Link key={i.id} to={`/admin/royalty/${i.id}`} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-slate-50 last:border-0 hover:bg-slate-50/40">
            <div className="col-span-12 md:col-span-2 flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 grid place-items-center"><FileSpreadsheet className="w-4 h-4" /></div>
              <div className="font-display font-bold">{i.period}</div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm">Rp {i.exchange_rate_eur_idr?.toLocaleString("id-ID")}/€</div>
            <div className="col-span-6 md:col-span-2 text-sm">{fmtEUR(i.total_revenue_eur)}</div>
            <div className="col-span-6 md:col-span-2 text-sm font-semibold">{fmtIDR(i.total_label_idr)}</div>
            <div className="col-span-6 md:col-span-2 text-xs"><span className="text-emerald-700 font-bold">{i.matched_lines}</span> / {i.total_lines} {i.unmatched_lines > 0 && <span className="text-amber-700"> ({i.unmatched_lines} unmatched)</span>}</div>
            <div className="col-span-12 md:col-span-2">
              <StatusBadge s={i.status} />
            </div>
          </Link>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4" onClick={() => setOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <h3 className="font-display font-extrabold text-xl tracking-tighter">Upload CSV Royalti</h3>
            <div>
              <label className="rm-label">Periode (YYYY-MM)</label>
              <input className="rm-input" value={form.period} onChange={(e) => setForm({ ...form, period: e.target.value })} placeholder="2026-05" data-testid="admin-royalty-period" required />
            </div>
            <div>
              <label className="rm-label">Kurs EUR → IDR</label>
              <input type="number" min="1000" step="0.01" className="rm-input" value={form.rate_eur_idr} onChange={(e) => setForm({ ...form, rate_eur_idr: parseFloat(e.target.value) })} data-testid="admin-royalty-rate" required />
              <div className="text-[11px] text-slate-500 mt-1">Kurs diinput manual per periode. Tidak bisa diubah setelah publish.</div>
            </div>
            <div>
              <label className="rm-label">File CSV Believe</label>
              <input type="file" accept=".csv,text/csv" className="rm-input" onChange={(e) => setForm({ ...form, file: e.target.files?.[0] || null })} data-testid="admin-royalty-file" />
              <div className="text-[11px] text-slate-500 mt-1">Auto-detect kolom ISRC, UPC, Title, Artist, Platform, Country, Quantity, Revenue (EUR).</div>
            </div>
            <div>
              <label className="rm-label">Catatan (opsional)</label>
              <input className="rm-input" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
              <button className="rm-btn-primary" disabled={busy} data-testid="admin-royalty-submit">{busy ? "Mengupload…" : "Upload & Parse"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ s }) {
  const map = {
    pending_review: { bg: "bg-amber-50", color: "text-amber-700", label: "Pending Review", icon: FileSpreadsheet },
    published: { bg: "bg-sky-50", color: "text-sky-700", label: "Published", icon: CheckCircle2 },
    dana_received: { bg: "bg-emerald-50", color: "text-emerald-700", label: "Dana Diterima", icon: Banknote },
  }[s] || { bg: "bg-slate-100", color: "text-slate-600", label: s };
  const Icon = map.icon;
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${map.bg} ${map.color}`}>{Icon && <Icon className="w-3 h-3" />}{map.label}</span>;
}
