import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { formatReleaseDate } from "@/utils/releaseDate";
import StatusBadge, { STATUS_LABELS } from "@/components/shared/StatusBadge";
import { AdminDeleteReleaseButton } from "@/components/releases/AdminDeleteReleaseButton";
import { Calendar, TrendingUp } from "lucide-react";
import { ReleaseArtistCredits } from "@/components/releases/ReleaseArtistCredits";
import { ReleaseIsrcPanel, ReleaseIsrcToggle } from "@/components/releases/ReleaseIdentifiers";
import { ReleaseArtwork } from "@/components/releases/ReleaseArtwork";

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
  const [expandedIsrc, setExpandedIsrc] = useState(null);
  const [status, setStatus] = useState("");
  const [q, setQ] = useState("");
  const [periods, setPeriods] = useState([]);
  const [periodFrom, setPeriodFrom] = useState("");
  const [periodTo, setPeriodTo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sortBy, setSortBy] = useState("status"); // status | revenue | date

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (status) params.status = status;
      if (q) params.q = q;
      if (periodFrom) params.period_from = periodFrom;
      if (periodTo) params.period_to = periodTo;
      const { data } = await api.get("/admin/releases", { params });
      if (sortBy === "status") {
        const order = ["submitted", "awaiting_payment", "paid", "under_review", "need_revision", "approved", "delivered", "draft", "live"];
        const rank = Object.fromEntries(order.map((value, index) => [value, index]));
        data.sort((a, b) => String(b.submitted_at || b.updated_at || b.created_at || "").localeCompare(String(a.submitted_at || a.updated_at || a.created_at || "")));
        data.sort((a, b) => (rank[a.status] ?? order.length) - (rank[b.status] ?? order.length));
      } else if (sortBy === "revenue") data.sort((a, b) => (b.revenue_idr || 0) - (a.revenue_idr || 0));
      else data.sort((a, b) => String(b.release_date || b.created_at || "").localeCompare(String(a.release_date || a.created_at || "")));
      setItems(data);
    } catch (requestError) {
      setError(formatApiError(requestError.response?.data?.detail) || "Gagal memuat rilisan.");
    } finally { setLoading(false); }
  }, [status, q, periodFrom, periodTo, sortBy]);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/admin/analytics/periods");
        setPeriods(data.periods || []);
      } catch (error) {
        console.warn("Analytics periods unavailable; release list remains usable.", error);
      }
    })();
    load();
  }, [load]);

  const totalRev = items.reduce((s, r) => s + (r.revenue_idr || 0), 0);

  return (
    <div className="space-y-5" data-testid="admin-releases-page">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Operasional Rilisan</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Manajemen Rilisan</h1>
        <p className="text-sm text-zinc-400 mt-1">Total pendapatan dan bulan laporan aktif dihitung dari data royalti.</p>
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
          <label className="rm-label">Urutkan</label>
          <select className="rm-input" value={sortBy} onChange={(e) => setSortBy(e.target.value)} data-testid="admin-releases-sort">
            <option value="status">Prioritas status</option>
            <option value="revenue">Pendapatan tertinggi</option>
            <option value="date">Tanggal rilis</option>
          </select>
        </div>
      </div>

      {(items.length > 0 || totalRev > 0) && (
        <div className="rm-card p-4 flex items-center justify-between flex-wrap gap-2">
          <div className="text-sm text-zinc-400 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>{fmtInt(items.length)} rilisan · Total pendapatan: <b className="text-emerald-300">{fmtIDR(totalRev)}</b></span>
          </div>
          {periodFrom && periodTo && (
            <div className="text-xs text-zinc-500">Rentang: {fmtPeriod(periodFrom)} – {fmtPeriod(periodTo)}</div>
          )}
        </div>
      )}

      {error && <div role="alert" className="rounded-md bg-red-500/10 p-4 text-sm text-red-300" data-testid="admin-releases-error">{error}</div>}
      <div className="rm-card overflow-hidden">
        <div className="hidden xl:grid xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,.8fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,.8fr)_minmax(0,1.2fr)] gap-3 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div>Rilisan</div><div>Label</div><div data-testid="admin-releases-upc-header">UPC</div><div data-testid="admin-releases-isrc-header">ISRC</div>
          <div>Tanggal Rilis</div><div className="text-right">Pendapatan</div><div>Aktif Terakhir</div><div className="text-right">Status / Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-8 text-center text-zinc-500 text-sm">{loading ? "Memuat…" : "Tidak ada rilisan."}</div>
        ) : items.map((r) => (
          <div key={r.id} className="relative px-5 py-4 grid grid-cols-12 xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,.8fr)_minmax(0,1fr)_minmax(0,1fr)_minmax(0,.8fr)_minmax(0,1.2fr)] gap-3 items-center border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors" data-testid={`admin-release-row-${r.id}`}>
            <div className="min-w-0 col-span-12 xl:col-auto flex items-start gap-3">
              <ReleaseArtwork release={r} prefix="admin-list" onUpdated={(patch) => setItems((current) => current.map((item) => item.id === r.id ? { ...item, ...patch } : item))} />
              <div className="min-w-0">
              <Link to={`/admin/releases/${r.id}`} translate="no" className="block break-words font-semibold [overflow-wrap:anywhere] after:absolute after:inset-0 focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-white/50" data-testid={`admin-release-open-${r.id}`}>{r.release_title}</Link>
              <ReleaseArtistCredits release={r} prefix="admin-release" />
              <div className="mt-1 text-[10px] uppercase text-zinc-500" data-testid={`admin-release-type-${r.id}`}>{r.release_type}</div>
              </div>
            </div>
            <div className="col-span-12 min-w-0 break-words text-sm xl:col-auto" translate="no" data-testid={`admin-release-label-${r.id}`}>{r.label_name || "—"}</div>
            <div className="min-w-0 col-span-6 xl:col-auto"><div className="mb-1 text-[10px] text-zinc-500 xl:hidden">UPC</div><code className="break-all text-xs" translate="no" data-testid={`admin-release-upc-${r.id}`}>{r.upc || "—"}</code></div>
            <div className="min-w-0 col-span-6 xl:col-auto"><div className="mb-1 text-[10px] text-zinc-500 xl:hidden">ISRC</div><ReleaseIsrcToggle release={r} open={expandedIsrc === r.id} onToggle={() => setExpandedIsrc((value) => value === r.id ? null : r.id)} /></div>
            <div className="min-w-0 col-span-6 xl:col-auto text-sm break-words" data-testid={`admin-release-date-${r.id}`}>{formatReleaseDate(r.release_date)}</div>
            <div className="min-w-0 col-span-6 xl:col-auto text-right break-words">
              <div className={`font-mono font-bold ${r.revenue_idr > 0 ? "text-emerald-300" : "text-zinc-600"}`}>{fmtIDR(r.revenue_idr)}</div>
              <div className="text-[10px] text-zinc-500">{fmtInt(r.royalty_lines_count)} baris</div>
            </div>
            <div className="min-w-0 col-span-6 xl:col-auto text-xs">
              {r.last_active_period ? (
                <>
                  <div className="text-zinc-300">{fmtPeriod(r.last_active_period)}</div>
                  {r.first_active_period && r.first_active_period !== r.last_active_period && (
                    <div className="text-[10px] text-zinc-500">dari {fmtPeriod(r.first_active_period)}</div>
                  )}
                </>
              ) : <span className="text-zinc-600">—</span>}
            </div>
            <div className="min-w-0 col-span-6 xl:col-auto flex flex-wrap items-center justify-end gap-2" data-testid={`admin-release-status-actions-${r.id}`}>
              <span data-testid={`admin-release-status-${r.id}`}><StatusBadge status={r.status} /></span>
              <AdminDeleteReleaseButton release={r} compact onDeleted={(id) => setItems((current) => current.filter((item) => item.id !== id))} />
            </div>
            {expandedIsrc === r.id && <ReleaseIsrcPanel release={r} />}
          </div>
        ))}
      </div>
    </div>
  );
}
