import React from "react";
import { Layers, RefreshCw } from "lucide-react";
import { useSubmissionQuota } from "@/hooks/useSubmissionQuota";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const SubmissionQuotaView = ({ state, prefix }) => {
  const { t } = useAppPreferences(); const { quota, error, reload } = state;
  return <section className="flex flex-wrap items-center justify-between gap-3 border-y border-white/10 py-4" data-testid={`${prefix}-quota`}>
    <div className="flex min-w-0 items-center gap-3"><Layers className="h-5 w-5 shrink-0 text-pink-400" /><div><h2 className="text-sm font-semibold">{t("Kuota Rilisan Harian")}</h2><p className="text-xs text-zinc-500" data-testid={`${prefix}-quota-reset`}>{t("Reset setiap 00.00 WIB")}</p></div></div>
    {error ? <div className="flex items-center gap-2 text-xs text-amber-400" role="alert" data-testid={`${prefix}-quota-error`}>{t("Kuota belum dapat dimuat")}<button type="button" onClick={reload} title={t("Coba lagi")} aria-label={t("Coba lagi")} data-testid={`${prefix}-quota-retry`}><RefreshCw className="h-4 w-4" /></button></div> : quota ? <div className="text-right"><div className="text-sm"><strong data-testid={`${prefix}-quota-used`}>{quota.used}/{quota.limit}</strong> <span className="text-zinc-500">{t("rilisan terkirim hari ini")}</span></div><div className="mt-1 flex flex-wrap justify-end gap-x-3 text-xs"><span className={quota.remaining ? "text-emerald-400" : "text-amber-400"} data-testid={`${prefix}-quota-remaining`}>{t("Sisa")}: {quota.remaining}</span>{quota.pending > 0 && <span className="text-zinc-500" data-testid={`${prefix}-quota-pending`}>{quota.pending} {t("sedang diproses")}</span>}{quota.already_counted && <span className="text-zinc-500" data-testid={`${prefix}-quota-counted`}>{t("Rilisan ini sudah dihitung hari ini")}</span>}</div></div> : <span className="text-xs text-zinc-500" data-testid={`${prefix}-quota-loading`}>{t("Memuat…")}</span>}
  </section>;
};

export const SubmissionQuota = ({ prefix = "label-releases" }) => {
  const state = useSubmissionQuota();
  return <SubmissionQuotaView state={state} prefix={prefix} />;
};