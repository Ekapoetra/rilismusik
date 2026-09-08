import React, { useCallback, useEffect, useState } from "react";
import { Plus, RefreshCw, ChevronLeft, ChevronRight } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { AdjustmentDialog, formatIDR } from "./AdjustmentDialog";
import { AdjustmentHistory } from "./AdjustmentHistory";

export const RoyaltyAdjustmentPanel = ({ label, onChanged }) => {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState({ items: [], total: 0 });
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const base = `/royalty/admin/adjustments/labels/${label.id}`;
  const load = useCallback(async () => {
    setLoading(true); setError("");
    try { const [s, h] = await Promise.all([api.get(`${base}/summary`), api.get(base, { params: { q, status: status || undefined, page, limit: 5 } })]); setSummary(s.data); setHistory(h.data); }
    catch (e) { setError(formatApiError(e.response?.data?.detail) || "Data penyesuaian belum dapat dimuat."); }
    finally { setLoading(false); }
  }, [base, q, status, page]);
  useEffect(() => { const timer = setTimeout(load, 200); return () => clearTimeout(timer); }, [load]);
  const changed = () => { load(); Promise.resolve(onChanged()).catch(() => {}); };
  const sources = summary?.legacy_period_to ? [["legacy", `Believe Legacy · s/d ${summary.legacy_period_to}`, summary.believe_legacy_idr], ["new", "Royalti baru · setelah batas legacy", summary.new_royalty_idr]] : [["unclassified", "Believe CSV · batas legacy belum ditetapkan", summary?.unclassified_csv_idr]];
  return <section className="space-y-5 border-y border-white/10 py-6" data-testid="royalty-adjustment-panel">
    <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-display text-lg font-bold">Penyesuaian Saldo Royalti</h2><div className="flex items-center gap-2"><button type="button" title="Muat ulang saldo" aria-label="Muat ulang saldo" onClick={load} disabled={loading} className="rm-btn-ghost p-2 disabled:opacity-40" data-testid="adjustment-refresh"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /></button><button type="button" disabled={!summary || summary.has_active_withdraw} aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)} className="rm-btn-primary inline-flex items-center gap-2 disabled:opacity-40" data-testid="adjustment-open"><Plus className="h-4 w-4" /> Inject Saldo</button></div></div>
    {error && <p role="alert" className="text-sm text-red-300" data-testid="adjustment-panel-error">{error}</p>}
    {summary && <>
      <div className="grid gap-6 lg:grid-cols-2"><div className="min-w-0"><div className="text-xs text-zinc-500">Saldo tersedia</div><div className="mt-2 break-words font-display text-3xl font-bold text-emerald-300" data-testid="adjustment-available-balance">{formatIDR(summary.balance_available_idr)}</div>{summary.has_active_withdraw && <p className="mt-3 text-sm text-amber-300" data-testid="adjustment-withdraw-lock">Penyesuaian terkunci selama penarikan diproses.</p>}</div><dl className="space-y-3 text-sm">{[...sources, ["manual", "Penyesuaian admin · belum ditarik", summary.admin_adjustment_idr], ["reserved", "Direservasi untuk penarikan", -summary.withdraw_reserved_idr]].map(([key, title, amount]) => <div key={key} className="flex flex-wrap justify-between gap-2"><dt className="text-zinc-400">{title}</dt><dd className="font-mono" data-testid={`adjustment-source-${key}`}>{formatIDR(amount)}</dd></div>)}</dl></div>
      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-5"><h3 className="text-sm font-semibold">Riwayat Penyesuaian</h3><div className="flex w-full flex-wrap gap-2 sm:w-auto"><input type="search" className="rm-input min-w-0 flex-1 text-sm" placeholder="Cari referensi, alasan, admin…" aria-label="Cari riwayat penyesuaian" value={q} onChange={(e) => { setQ(e.target.value); setPage(1); }} data-testid="adjustment-history-search" /><select className="rm-input text-sm" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Status penyesuaian" data-testid="adjustment-history-status-filter"><option value="">Semua status</option><option value="active">Aktif</option><option value="voided">Dibatalkan</option></select></div></div>
      <AdjustmentHistory items={history.items} labelId={label.id} onChanged={changed} />
      <div className="flex items-center justify-between gap-3 text-xs text-zinc-500"><span data-testid="adjustment-history-total">{history.total} penyesuaian · Halaman {page}</span><div className="flex gap-2"><button type="button" disabled={loading || page <= 1} className="p-2 transition-colors hover:text-white disabled:opacity-30" onClick={() => setPage(page - 1)} aria-label="Halaman sebelumnya" data-testid="adjustment-history-prev"><ChevronLeft className="h-4 w-4" /></button><button type="button" disabled={loading || page * 5 >= history.total} className="p-2 transition-colors hover:text-white disabled:opacity-30" onClick={() => setPage(page + 1)} aria-label="Halaman selanjutnya" data-testid="adjustment-history-next"><ChevronRight className="h-4 w-4" /></button></div></div>
    </>}
    {open && <AdjustmentDialog label={label} boundary={summary?.legacy_period_to} onClose={() => setOpen(false)} onChanged={changed} />}
  </section>;
};