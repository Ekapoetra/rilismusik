import React, { useCallback, useEffect, useState } from "react";
import { TrendingUp } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { PerformanceDetail } from "@/components/admin/performance/PerformanceDetail";

const thisMonth = () => new Date().toISOString().slice(0, 7);

export default function MyPerformance() {
  const { t } = useAppPreferences();
  const [period, setPeriod] = useState(thisMonth());
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true); setErr("");
    try { const { data } = await api.get("/admin/performance/me", { params: { period } }); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  }, [period]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-6" data-testid="my-performance-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Kinerja")}</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><TrendingUp className="h-6 w-6 text-pink-400" />{t("Performa Saya")}</h1>
          <p className="mt-2 text-sm text-zinc-400">{t("Ringkasan kinerja Anda dari pekerjaan yang diselesaikan. Transparan dan dapat ditelusuri.")}</p>
        </div>
        <label className="flex items-center gap-2 text-sm text-zinc-400">{t("Periode")}
          <input type="month" value={period} onChange={(e) => setPeriod(e.target.value)} className="rm-input py-1.5" data-testid="my-performance-period" />
        </label>
      </header>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="my-performance-error">{err}</div>}
      {loading ? <p className="text-sm text-zinc-500">{t("Memuat…")}</p>
        : data && data.is_staff === false ? (
          <div className="rounded-lg border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="my-performance-not-staff">
            {t("Super Admin tidak dinilai sebagai staf.")}
          </div>
        ) : data ? (
          <>
            {data.period_state === "finalized" && (
              <div className="rounded-md border border-indigo-400/30 bg-indigo-500/10 px-4 py-2 text-xs font-semibold text-indigo-200" data-testid="my-performance-finalized">
                {t("Periode ini sudah difinalisasi — nilai menggunakan konfigurasi yang berlaku saat finalisasi.")}
              </div>
            )}
            <PerformanceDetail data={data} />
          </>
        ) : null}
    </div>
  );
}
