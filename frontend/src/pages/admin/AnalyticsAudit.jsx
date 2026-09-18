import React, { useState } from "react";
import { ShieldCheck, RefreshCw, AlertTriangle, Copy, Layers } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";

const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);
const cls = (n) => (n === 0 ? "text-emerald-400" : "text-amber-400");

export default function AnalyticsAudit() {
  const now = new Date();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (from) qs.set("period_from", from);
      if (to) qs.set("period_to", to);
      const r = await api.get(`/admin/analytics/audit${qs.toString() ? `?${qs}` : ""}`);
      setData(r.data);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail || e.message));
    } finally {
      setLoading(false);
    }
  };

  const totalDiff = (data?.periods || []).reduce((s, p) => s + Math.abs(p.diff_cache_vs_eligible_idr), 0);

  return (
    <div className="space-y-6" data-testid="analytics-audit-page">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 font-display text-2xl font-extrabold"><ShieldCheck className="h-6 w-6 text-fuchsia-400" /> Audit Konsistensi Analytics Royalti</h1>
          <p className="mt-1 text-sm text-zinc-400">Read-only. Membandingkan data mentah vs baris layak (kanonik) vs cache, per <b>Bulan Laporan</b>. Tidak mengubah/menghapus data apa pun.</p>
        </div>
      </div>

      <div className="rm-glass flex flex-wrap items-end gap-3 rounded-2xl p-4">
        <label className="text-xs font-semibold text-zinc-400">Dari periode (YYYY-MM)<input value={from} onChange={(e) => setFrom(e.target.value)} placeholder="2026-04" className="rm-input mt-1 block w-36" data-testid="audit-from" /></label>
        <label className="text-xs font-semibold text-zinc-400">Sampai periode (YYYY-MM)<input value={to} onChange={(e) => setTo(e.target.value)} placeholder="2026-07" className="rm-input mt-1 block w-36" data-testid="audit-to" /></label>
        <button onClick={run} disabled={loading} className="rm-btn-primary inline-flex items-center gap-2" data-testid="audit-run"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />{loading ? "Menghitung…" : "Jalankan Audit"}</button>
      </div>

      {data && (
        <>
          <div className="rm-glass rounded-2xl p-4 text-sm">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
              <span className={`font-bold ${cls(totalDiff)}`}>{totalDiff === 0 ? "✓ Cache konsisten dengan definisi kanonik" : `⚠ Total selisih cache vs eligible: ${fmtIDR(totalDiff)}`}</span>
              <span className="text-zinc-500">Kanonik: match_status ∈ [matched, manually_matched] · status ∈ [pending, available, withdrawn] · bukan staging</span>
            </div>
            {totalDiff !== 0 && <p className="mt-2 text-xs text-amber-300/80">Jika ada selisih, jalankan "Hitung Ulang Analitik" di halaman Analitik agar cache dibangun ulang dengan definisi terbaru.</p>}
          </div>

          <div className="rm-glass overflow-auto rounded-2xl p-4" data-testid="audit-periods">
            <div className="mb-2 text-sm font-bold">Rekonsiliasi per Bulan Laporan</div>
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase text-zinc-500">
                <th className="py-1">Periode</th><th className="text-right">Raw (semua)</th><th className="text-right">Eligible (kanonik)</th><th className="text-right">Cache</th><th className="text-right">Selisih Cache↔Eligible</th><th className="text-right">Import</th>
              </tr></thead>
              <tbody>
                {data.periods.map((p) => (
                  <React.Fragment key={p.period}>
                    <tr className="border-t border-white/5" data-testid={`audit-period-${p.period}`}>
                      <td className="py-2 font-semibold">{p.period}{p.import_count > 1 && <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-sky-500/15 px-2 py-0.5 text-[10px] font-bold text-sky-300"><Layers className="h-3 w-3" />{p.import_count} import</span>}</td>
                      <td className="text-right tabular-nums text-zinc-400">{fmtIDR(p.raw_idr)}<div className="text-[10px] text-zinc-600">{p.raw_lines} baris</div></td>
                      <td className="text-right tabular-nums font-semibold">{fmtIDR(p.eligible_idr)}<div className="text-[10px] text-zinc-600">{p.eligible_lines} baris</div></td>
                      <td className="text-right tabular-nums">{fmtIDR(p.cache_idr)}</td>
                      <td className={`text-right tabular-nums font-bold ${cls(p.diff_cache_vs_eligible_idr)}`}>{fmtIDR(p.diff_cache_vs_eligible_idr)}</td>
                      <td className="text-right tabular-nums text-zinc-400">{p.import_count}</td>
                    </tr>
                    {p.imports.filter((it) => it.lines > 0).map((it) => (
                      <tr key={it.import_id} className="text-xs text-zinc-500">
                        <td className="py-0.5 pl-4">↳ {it.filename || "(tanpa nama)"} <span className="text-zinc-600">· {it.import_status}</span></td>
                        <td className="text-right">{it.lines} baris</td>
                        <td className="text-right">{it.eligible_lines} layak</td>
                        <td className="text-right tabular-nums">{fmtIDR(it.eligible_idr)}</td>
                        <td colSpan={2}></td>
                      </tr>
                    ))}
                  </React.Fragment>
                ))}
                {!data.periods.length && <tr><td colSpan={6} className="py-3 text-zinc-500">Tidak ada data pada rentang ini.</td></tr>}
              </tbody>
            </table>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rm-glass rounded-2xl p-4" data-testid="audit-overlaps">
              <div className="mb-2 flex items-center gap-2 text-sm font-bold"><Layers className="h-4 w-4 text-sky-400" /> Bulan dengan Overlap Import ({data.overlaps.length})</div>
              <p className="mb-2 text-xs text-zinc-500">Bulan laporan yang datanya berasal dari lebih dari satu file import. Belum tentu duplikat — bisa transaksi baru yang valid.</p>
              {data.overlaps.map((o) => (
                <div key={o.period} className="border-b border-white/5 py-2 text-sm last:border-0">
                  <div className="font-semibold">{o.period} — {o.import_count} import</div>
                  {o.imports.map((it) => <div key={it.import_id} className="text-xs text-zinc-500">↳ {it.filename || "(tanpa nama)"} · {it.eligible_lines} baris · {fmtIDR(it.eligible_idr)}</div>)}
                </div>
              ))}
              {!data.overlaps.length && <p className="text-sm text-zinc-500">Tidak ada overlap.</p>}
            </div>

            <div className="rm-glass rounded-2xl p-4" data-testid="audit-duplicates">
              <div className="mb-2 flex items-center gap-2 text-sm font-bold"><Copy className="h-4 w-4 text-amber-400" /> Dugaan Baris Duplikat ({data.duplicate_suspects.length})</div>
              <p className="mb-2 text-xs text-zinc-500">Baris identik (periode, platform, negara, ISRC, tipe, qty, revenue) yang muncul di <b>import berbeda</b>. Hanya indikasi — perlu diverifikasi sebelum tindakan apa pun.</p>
              <div className="max-h-96 overflow-auto">
                {data.duplicate_suspects.map((d, i) => (
                  <div key={i} className="border-b border-white/5 py-2 text-xs last:border-0">
                    <div className="flex items-center justify-between"><span className="font-semibold text-amber-300">{d.period} · {d.platform} · {d.country}</span><span className="tabular-nums font-bold">{fmtIDR(d.idr)}</span></div>
                    <div className="text-zinc-500">ISRC {d.isrc || "—"} · qty {d.quantity} · €{d.revenue_eur} · muncul {d.count}× di {d.import_ids.length} import</div>
                  </div>
                ))}
                {!data.duplicate_suspects.length && <p className="text-sm text-zinc-500">Tidak ada dugaan duplikat.</p>}
              </div>
            </div>
          </div>

          <div className="rm-glass rounded-2xl p-4 text-xs text-zinc-500" data-testid="audit-note">
            <div className="flex items-start gap-2"><AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-amber-400" /><span>{data.note}</span></div>
          </div>
        </>
      )}
    </div>
  );
}
