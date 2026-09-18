import React, { useState } from "react";
import { Scale, RefreshCw, CheckCircle2, AlertTriangle, Wallet } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const idr = (n) => (n === null || n === undefined ? "—" : "Rp " + Number(n).toLocaleString("id-ID"));
const firstOfMonth = () => new Date().toISOString().slice(0, 8) + "01";
const today = () => new Date().toISOString().slice(0, 10);

export default function XenditReconciliation() {
  const { t } = useAppPreferences();
  const [from, setFrom] = useState(firstOfMonth());
  const [to, setTo] = useState(today());
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true); setErr(""); setData(null);
    try { const { data } = await api.get("/admin/xendit/reconciliation", { params: { date_from: from, date_to: to } }); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  };

  const xOk = data?.xendit?.available;

  return (
    <div className="space-y-6" data-testid="xendit-recon-page">
      <header className="border-b border-white/10 pb-5">
        <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Keuangan")}</div>
        <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><Scale className="h-6 w-6 text-pink-400" />{t("Rekonsiliasi Xendit")}</h1>
        <p className="mt-2 text-sm text-zinc-400">{t("Bandingkan saldo & penerimaan pembayaran di Xendit dengan pembayaran lunas di sistem, untuk mendeteksi selisih.")}</p>
      </header>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm text-zinc-400">{t("Dari")}<input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="rm-input mt-1 block py-1.5" data-testid="recon-from" /></label>
        <label className="text-sm text-zinc-400">{t("Sampai")}<input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="rm-input mt-1 block py-1.5" data-testid="recon-to" /></label>
        <button onClick={run} disabled={loading} className="rm-btn inline-flex items-center gap-2 text-sm" data-testid="recon-run"><RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />{t("Hitung Rekonsiliasi")}</button>
      </div>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="recon-error">{err}</div>}

      {data && (
        <div className="space-y-5" data-testid="recon-result">
          {!xOk && (
            <div className="rounded-lg border border-amber-400/40 bg-amber-500/[0.06] p-4 text-sm text-amber-200" data-testid="recon-xendit-unavailable">
              <div className="flex items-center gap-2 font-bold text-amber-300"><AlertTriangle className="h-4 w-4" />{t("Data Xendit tidak tersedia")}</div>
              <p className="mt-1">{t("Kode")}: {data.xendit?.error_code || "—"} · {data.xendit?.message || t("Periksa akses/scope API Xendit (Balance & Transaction Read).")}</p>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="recon-card-balance">
              <div className="flex items-center gap-1.5 text-xs text-zinc-500"><Wallet className="h-3.5 w-3.5" />{t("Saldo Kas Xendit")}</div>
              <div className="mt-1 font-display text-2xl font-extrabold tabular-nums">{xOk ? idr(data.xendit.balance_cash) : "—"}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="recon-card-xendit-in">
              <div className="text-xs text-zinc-500">{t("Penerimaan Xendit (bruto)")}</div>
              <div className="mt-1 font-display text-2xl font-extrabold tabular-nums">{xOk ? idr(data.xendit.payment_in_gross) : "—"}</div>
              <div className="mt-0.5 text-[11px] text-zinc-500">{xOk ? `${data.xendit.count} ${t("transaksi")} · ${t("neto")} ${idr(data.xendit.payment_in_net)}` : ""}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4" data-testid="recon-card-system">
              <div className="text-xs text-zinc-500">{t("Pembayaran Lunas (sistem)")}</div>
              <div className="mt-1 font-display text-2xl font-extrabold tabular-nums">{idr(data.system.paid_total_idr)}</div>
              <div className="mt-0.5 text-[11px] text-zinc-500">{data.system.count} {t("pembayaran")}</div>
            </div>
            <div className={`rounded-xl border p-4 ${data.matched === null ? "border-white/10 bg-white/[0.02]" : data.matched ? "border-emerald-400/30 bg-emerald-500/[0.06]" : "border-red-400/30 bg-red-500/[0.06]"}`} data-testid="recon-card-variance">
              <div className="text-xs text-zinc-500">{t("Selisih")}</div>
              <div className={`mt-1 font-display text-2xl font-extrabold tabular-nums ${data.matched === null ? "" : data.matched ? "text-emerald-300" : "text-red-300"}`}>{xOk ? idr(data.variance_idr) : "—"}</div>
              <div className="mt-1 text-[11px] font-semibold">
                {data.matched === null ? <span className="text-zinc-500">{t("Tidak dapat dihitung")}</span>
                  : data.matched ? <span className="inline-flex items-center gap-1 text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" />{t("Sesuai")}</span>
                  : <span className="inline-flex items-center gap-1 text-red-300"><AlertTriangle className="h-3.5 w-3.5" />{t("Ada selisih")}</span>}
              </div>
            </div>
          </div>
          <p className="text-[11px] text-zinc-500">{t("Selisih = Penerimaan Xendit (bruto) − Pembayaran lunas di sistem, untuk rentang tanggal yang sama (WIB). Biaya/pajak/refund dapat menyebabkan selisih pada saldo kas; gunakan Balance Report Xendit untuk audit ledger penuh.")}</p>
        </div>
      )}
    </div>
  );
}
