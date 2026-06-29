import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api/client";
import StatusBadge, { STATUS_LABELS } from "@/components/shared/StatusBadge";
import { Calendar, TrendingUp } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtInt(n) { return Number(n || 0).toLocaleString("id-ID"); }
function fmtPeriod(p) {
  if (!p || p.length !== 7) return "—";
  const [y, m] = p.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  return `${months[parseInt(m, 10) - 1] || m} ${y}`;
}

export default function AdminReleases() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [periods, setPeriods] = useState([]);
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [sortBy, setSortBy] = useState("revenue"); // revenue | date

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (status) params.status = status;
      if (q) params.q = q;
      if (periodFrom) params.period_from = periodFrom;
      if (periodTo) params.period_to = periodTo;
      const { data } = await api.get("/admin/releases", { params });
      if (sortBy === "revenue") data.sort((a, b) => (b.revenue_idr || 0) - (a.revenue_idr || 0));
      setItems(data);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/admin/analytics/periods");
        setPeriods(data.periods || []);
      } catch (_) { /* ignore cold cache */ }
    })();
    load();
  }, []);
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [status, periodFrom, periodTo, sortBy]);

  const totalRev = items.reduce((s, r) => s + (r.revenue_idr || 0), 0);

  return (
    <div className="space-y-5" data-testid="admin-releases-page">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Release Operations</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Release Management</h1>
        <p className="text-sm text-zinc-400 mt-1">Total revenue & bulan laporan aktif dihitung dari <span className="text-zinc-200">royalty_lines</span>.</p>
      </div>

      <div className="rm-card p-4 grid md:grid-cols-6 gap-3 items-end">
        <div className="md:col-span-2">
          <label className="rm-label">Cari Judul</label>
          <input className="rm-input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && load()} data-testid="admin-releases-search" />
        </div>
        <div>
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-releases-status">
            <option value="">Semua</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
        <div>
          <label className="rm-label flex items-center gap-1.5"><Calendar className="w-3 h-3" /> Dari</label>
          <select className="rm-input" value={periodFrom} onChange={(e) => setPeriodFrom(e.target.value)} data-testid="admin-releases-period-from">
            <option value="">— Semua —</option>
            {periods.map(p => <option key={p} value={p}>{fmtPeriod(p)}</option>)}
          </select>
        </div>
        <div>
          <label className="rm-label flex items-center gap-1.5"><Calendar className="w-3 h-3" /> Sampai</label>
          <select className="rm-input" value={periodTo} onChange={(e) => setPeriodTo(e.target.value)} data-testid="admin-releases-period-to">
            <option value="">— Semua —</option>
            {periods.map(p => <option key={p} value={p}>{fmtPeriod(p)}</option>)}
          </select>
        </div>
        <div>
          <label className="rm-label">Sort</label>
          <select className="rm-input" value={sortBy} onChange={(e) => setSortBy(e.target.value)} data-testid="admin-releases-sort">
            <option value="revenue">Revenue tertinggi</option>
            <option value="date">Tanggal rilis</option>
          </select>
        </div>
      </div>

      {(items.length > 0 || totalRev > 0) && (
        <div className="rm-card p-4 flex items-center justify-between flex-wrap gap-2">
          <div className="text-sm text-zinc-400 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>{fmtInt(items.length)} rilisan · Total revenue: <b className="text-emerald-300">{fmtIDR(totalRev)}</b></span>
          </div>
          {periodFrom && periodTo && (
            <div className="text-xs text-zinc-500">Range: {fmtPeriod(periodFrom)} – {fmtPeriod(periodTo)}</div>
          )}
        </div>
      )}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 gap-3 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Rilisan</div>
          <div className="col-span-2">Label</div>
          <div className="col-span-2">Release Date</div>
          <div className="col-span-2 text-right">Revenue</div>
          <div className="col-span-2">Aktif Terakhir</div>
          <div className="col-span-1 text-right">Status</div>
        </div>
        {items.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 text-sm">{loading ? "Memuat…" : "Tidak ada rilisan."}</div>
        ) : items.map((r) => (
          <Link to={`/admin/releases/${r.id}`} key={r.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition" data-testid={`admin-release-row-${r.id}`}>
            <div className="col-span-12 md:col-span-3">
              <div className="font-semibold truncate">{r.release_title}</div>
              <div className="text-xs text-zinc-500 truncate">{r.artist_name} • {r.release_type}</div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm truncate">{r.label_name || "—"}</div>
            <div className="col-span-6 md:col-span-2 text-sm">{r.release_date || "—"}</div>
            <div className="col-span-6 md:col-span-2 text-right">
              <div className={`font-mono font-bold ${r.revenue_idr > 0 ? "text-emerald-300" : "text-zinc-600"}`}>{fmtIDR(r.revenue_idr)}</div>
              <div className="text-[10px] text-zinc-500">{fmtInt(r.royalty_lines_count)} baris</div>
            </div>
            <div className="col-span-6 md:col-span-2 text-xs">
              {r.last_active_period ? (
                <>
                  <div className="text-zinc-300">{fmtPeriod(r.last_active_period)}</div>
                  {r.first_active_period && r.first_active_period !== r.last_active_period && (
                    <div className="text-[10px] text-zinc-500">dari {fmtPeriod(r.first_active_period)}</div>
                  )}
                </>
              ) : <span className="text-zinc-600">—</span>}
            </div>
            <div className="col-span-6 md:col-span-1 text-right"><StatusBadge status={r.status} /></div>
          </Link>
        ))}
      </div>
    </div>
  );
}
