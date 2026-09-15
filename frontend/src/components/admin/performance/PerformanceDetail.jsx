import React from "react";
import { Gauge, Clock, Layers, ShieldCheck, TrendingUp, CalendarCheck, Info } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { CATEGORY_COLOR, CONFIDENCE_LABEL, CONFIDENCE_COLOR, scoreColor, catName } from "@/pages/admin/perfHelpers";

const COMPONENT_META = {
  achievement: { icon: TrendingUp, id: "Pencapaian", en: "Achievement" },
  timeliness: { icon: Clock, id: "Ketepatan Waktu", en: "Timeliness" },
  complexity: { icon: Layers, id: "Kompleksitas", en: "Complexity" },
  quality: { icon: ShieldCheck, id: "Kualitas", en: "Quality" },
};

const ATT_META = {
  PRESENT: ["Hadir", "Present", "text-emerald-300"], LATE: ["Terlambat", "Late", "text-amber-300"],
  ABSENT: ["Tidak Hadir", "Absent", "text-red-300"], LEAVE: ["Cuti", "Leave", "text-sky-300"],
  HOLIDAY: ["Libur", "Holiday", "text-zinc-400"], NOT_RECORDED: ["Belum Tercatat", "Not Recorded", "text-zinc-500"],
};

export function PerformanceDetail({ data }) {
  const { t, locale } = useAppPreferences();
  if (!data) return <p className="text-sm text-zinc-500">{t("Memuat…")}</p>;
  const score = data.overall_score;
  const conf = data.confidence || "insufficient";

  return (
    <div className="space-y-5" data-testid="performance-detail">
      {/* Overall score */}
      <div className="flex flex-wrap items-center gap-5 rounded-xl border border-white/10 bg-white/[0.02] p-5">
        <div className="text-center">
          <div className={`font-display text-5xl font-extrabold tabular-nums ${scoreColor(score)}`} data-testid="perf-overall-score">
            {score === null || score === undefined ? "—" : score}
          </div>
          <div className="mt-1 text-[11px] uppercase tracking-widest text-zinc-500">{t("Skor Keseluruhan")}</div>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            {data.category
              ? <span className={`rounded-full border px-3 py-1 text-xs font-bold ${CATEGORY_COLOR[data.category.key] || ""}`} data-testid="perf-category">{catName(data.category, locale)}</span>
              : <span className="rounded-full border border-white/10 px-3 py-1 text-xs font-semibold text-zinc-500">{t("Data belum cukup")}</span>}
            <span className={`text-xs font-semibold ${CONFIDENCE_COLOR[conf]}`} data-testid="perf-confidence">
              {t("Keyakinan")}: {t(CONFIDENCE_LABEL[conf]?.[0] || conf)}
            </span>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            <span data-testid="perf-completed"><span className="font-bold tabular-nums">{data.completed_count}</span> <span className="text-zinc-500">{t("pekerjaan selesai")}</span></span>
            <span data-testid="perf-weighted"><span className="font-bold tabular-nums">{data.weighted_output}</span> <span className="text-zinc-500">{t("output berbobot")}</span></span>
          </div>
          <p className="flex items-start gap-1.5 text-[11px] text-zinc-500"><Info className="mt-0.5 h-3 w-3 shrink-0" />{t("Skor dinormalisasi dari komponen yang datanya tersedia. Absensi ditampilkan terpisah dan tidak masuk skor.")}</p>
        </div>
      </div>

      {/* Component breakdown */}
      <div>
        <h4 className="mb-2 flex items-center gap-1.5 text-sm font-bold"><Gauge className="h-4 w-4 text-pink-300" />{t("Rincian Komponen")}</h4>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {Object.entries(data.components || {}).map(([key, c]) => {
            const M = COMPONENT_META[key]; const Ico = M?.icon || Gauge;
            const available = c.score !== null && c.score !== undefined;
            return (
              <div key={key} className="rounded-lg border border-white/10 bg-white/[0.02] p-3" data-testid={`perf-component-${key}`}>
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-xs font-semibold text-zinc-300"><Ico className="h-3.5 w-3.5 text-zinc-400" />{t(locale === "en" ? M?.en : M?.id) || key}</span>
                  <span className="text-[10px] text-zinc-500">×{c.weight}</span>
                </div>
                <div className={`mt-2 font-display text-2xl font-extrabold tabular-nums ${available ? scoreColor(c.score) : "text-zinc-600"}`}>
                  {available ? c.score : t("Tidak Tersedia")}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Output by work type */}
      <div>
        <h4 className="mb-2 flex items-center gap-1.5 text-sm font-bold"><Layers className="h-4 w-4 text-pink-300" />{t("Output per Jenis Pekerjaan")}</h4>
        {(data.by_type || []).length === 0 ? (
          <p className="rounded-lg border border-white/10 py-6 text-center text-xs text-zinc-500">{t("Belum ada pekerjaan selesai pada periode ini.")}</p>
        ) : (
          <div className="overflow-hidden rounded-lg border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-[11px] uppercase text-zinc-500"><tr><th className="px-3 py-2">{t("Jenis")}</th><th className="px-3 py-2 text-right">{t("Jumlah")}</th><th className="px-3 py-2 text-right">{t("Bobot")}</th><th className="px-3 py-2 text-right">{t("Berbobot")}</th></tr></thead>
              <tbody>
                {data.by_type.map((r) => (
                  <tr key={r.work_type} className="border-t border-white/5" data-testid={`perf-bytype-${r.work_type}`}>
                    <td className="px-3 py-2">{locale === "en" ? r.label_en : r.label_id}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{r.count}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-500">{r.weight}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-semibold">{(r.count * r.weight).toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Timeliness + Work timing */}
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
          <h4 className="flex items-center gap-1.5 text-sm font-bold"><Clock className="h-4 w-4 text-pink-300" />{t("Ketepatan Waktu")}</h4>
          <div className="mt-2 flex gap-4 text-sm">
            <span className="text-emerald-300">{t("Tepat Waktu")}: <b className="tabular-nums">{data.timeliness?.on_time ?? 0}</b></span>
            <span className="text-amber-300">{t("Terlambat")}: <b className="tabular-nums">{data.timeliness?.late ?? 0}</b></span>
          </div>
          <div className="mt-1 text-xs text-zinc-500">{t("On-time")}: {data.timeliness?.on_time_pct === null || data.timeliness?.on_time_pct === undefined ? t("Tidak Tersedia") : `${data.timeliness.on_time_pct}%`}</div>
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-4">
          <h4 className="flex items-center gap-1.5 text-sm font-bold"><TrendingUp className="h-4 w-4 text-pink-300" />{t("Waktu Kerja")}</h4>
          <div className="mt-2 space-y-1 text-xs">
            <div>{t("Waktu Antre")}: <span className="text-zinc-500">{t("Tidak Tersedia")}</span></div>
            <div>{t("Waktu Proses")}: <span className="text-zinc-500">{t("Tidak Tersedia")}</span></div>
            <div>{t("Waktu Penyelesaian")}: <b className="tabular-nums">{data.work_timing?.resolution_time_hours === null || data.work_timing?.resolution_time_hours === undefined ? t("Tidak Tersedia") : `${data.work_timing.resolution_time_hours} ${t("jam")}`}</b></div>
          </div>
        </div>
      </div>

      {/* Achievement entries */}
      {(data.achievement?.entries || []).length > 0 && (
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-sm font-bold"><TrendingUp className="h-4 w-4 text-pink-300" />{t("Pencapaian Target")}</h4>
          <div className="overflow-hidden rounded-lg border border-white/10">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-[11px] uppercase text-zinc-500"><tr><th className="px-3 py-2">{t("Jenis")}</th><th className="px-3 py-2 text-right">{t("Aktual")}</th><th className="px-3 py-2 text-right">{t("Target")}</th><th className="px-3 py-2 text-right">{t("Pencapaian")}</th></tr></thead>
              <tbody>
                {data.achievement.entries.map((e) => (
                  <tr key={e.work_type} className="border-t border-white/5">
                    <td className="px-3 py-2">{e.work_type}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{e.actual}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-zinc-500">{e.target}</td>
                    <td className={`px-3 py-2 text-right tabular-nums font-semibold ${scoreColor(Math.min(100, e.achievement_pct))}`}>{e.achievement_pct}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Attendance (separate, not scored) */}
      {data.attendance && (
        <div>
          <h4 className="mb-2 flex items-center gap-1.5 text-sm font-bold"><CalendarCheck className="h-4 w-4 text-pink-300" />{t("Indikator Absensi")} <span className="text-[10px] font-normal text-zinc-500">({t("terpisah dari skor")})</span></h4>
          <div className="flex flex-wrap gap-3">
            {Object.entries(ATT_META).map(([k, m]) => (
              <div key={k} className="rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-center" data-testid={`perf-att-${k}`}>
                <div className={`font-display text-lg font-extrabold tabular-nums ${m[2]}`}>{data.attendance[k] ?? 0}</div>
                <div className="text-[10px] text-zinc-500">{t(locale === "en" ? m[1] : m[0])}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
