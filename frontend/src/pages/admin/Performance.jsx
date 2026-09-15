import React, { useCallback, useEffect, useState } from "react";
import { Gauge, Lock, Unlock, ChevronRight } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { PerformanceDetail } from "@/components/admin/performance/PerformanceDetail";
import { CATEGORY_COLOR, CONFIDENCE_LABEL, CONFIDENCE_COLOR, scoreColor, catName } from "./perfHelpers";

const thisMonth = () => new Date().toISOString().slice(0, 7);

export default function Performance() {
  const { t, locale } = useAppPreferences();
  const [period, setPeriod] = useState(thisMonth());
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [detail, setDetail] = useState(null);
  const [detailData, setDetailData] = useState(null);

  const load = useCallback(async () => {
    setErr("");
    try { const { data } = await api.get("/admin/performance/overview", { params: { period } }); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [period]);
  useEffect(() => { load(); }, [load]);

  const openDetail = async (row) => {
    setDetail(row); setDetailData(null);
    try { const { data } = await api.get(`/admin/performance/staff/${row.user_id}`, { params: { period } }); setDetailData(data); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const periodAction = async (action) => {
    try { await api.post("/admin/performance/periods/action", { period, action });
      toast.success(action === "finalize" ? t("Periode difinalisasi.") : t("Periode dibuka kembali."));
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const finalized = data?.period_state === "finalized";

  return (
    <div className="space-y-6" data-testid="performance-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Kinerja")}</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><Gauge className="h-6 w-6 text-pink-400" />{t("Performa Tim")}</h1>
          <p className="mt-2 text-sm text-zinc-400">{t("Kinerja staf per periode dari data pekerjaan yang otoritatif. Klik baris untuk rincian.")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-zinc-400">{t("Periode")}
            <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} className="rm-input py-1.5" data-testid="performance-period" />
          </label>
          {data?.can_finalize && (finalized ? (
            <button onClick={() => periodAction("reopen")} className="rm-btn-ghost inline-flex items-center gap-1.5 text-sm" data-testid="performance-reopen"><Unlock className="h-4 w-4" />{t("Buka Periode")}</button>
          ) : (
            <button onClick={() => periodAction("finalize")} className="rm-btn-ghost inline-flex items-center gap-1.5 text-sm" data-testid="performance-finalize"><Lock className="h-4 w-4" />{t("Finalisasi Periode")}</button>
          ))}
        </div>
      </header>

      {finalized && <div className="rounded-md border border-indigo-400/30 bg-indigo-500/10 px-4 py-2 text-xs font-semibold text-indigo-200" data-testid="performance-finalized-banner">{t("Periode difinalisasi — konfigurasi dibekukan untuk periode ini.")}</div>}
      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="performance-error">{err}</div>}

      {data && (
        <div className="overflow-x-auto rounded-lg border border-white/10" data-testid="performance-table">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-left text-[11px] uppercase text-zinc-500">
              <tr>
                <th className="px-4 py-3">{t("Staf")}</th><th className="px-4 py-3">{t("Role")}</th>
                <th className="px-4 py-3 text-right">{t("Selesai")}</th><th className="px-4 py-3 text-right">{t("Output Berbobot")}</th>
                <th className="px-4 py-3 text-right">{t("On-time")}</th><th className="px-4 py-3 text-right">{t("Skor")}</th>
                <th className="px-4 py-3">{t("Kategori")}</th><th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {data.rows.length === 0 ? <tr><td colSpan={8} className="px-4 py-10 text-center text-zinc-500">{t("Tidak ada staf aktif.")}</td></tr> : data.rows.map((r) => (
                <tr key={r.user_id} onClick={() => openDetail(r)} className="cursor-pointer border-t border-white/5 hover:bg-white/[0.04]" data-testid={`performance-row-${r.user_id}`}>
                  <td className="px-4 py-3 font-semibold">{r.name}</td>
                  <td className="px-4 py-3 text-zinc-400">{r.role_name}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{r.completed_count}</td>
                  <td className="px-4 py-3 text-right tabular-nums">{r.weighted_output}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-zinc-400">{r.on_time_pct === null || r.on_time_pct === undefined ? "—" : `${r.on_time_pct}%`}</td>
                  <td className={`px-4 py-3 text-right font-display text-lg font-extrabold tabular-nums ${scoreColor(r.overall_score)}`}>{r.overall_score === null || r.overall_score === undefined ? "—" : r.overall_score}</td>
                  <td className="px-4 py-3">
                    {r.category ? <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-bold ${CATEGORY_COLOR[r.category.key] || ""}`}>{catName(r.category, locale)}</span> : <span className={`text-[11px] ${CONFIDENCE_COLOR[r.confidence]}`}>{t(CONFIDENCE_LABEL[r.confidence]?.[0] || r.confidence)}</span>}
                  </td>
                  <td className="px-4 py-3 text-zinc-600"><ChevronRight className="h-4 w-4" /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent className="ui-menu max-h-[92dvh] w-[calc(100%-2rem)] max-w-3xl overflow-y-auto rounded-lg" data-testid="performance-detail-dialog">
          <DialogHeader><DialogTitle>{detail?.name} · {period}</DialogTitle></DialogHeader>
          <PerformanceDetail data={detailData} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
