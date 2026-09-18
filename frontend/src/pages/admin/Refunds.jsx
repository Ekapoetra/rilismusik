import React, { useCallback, useEffect, useState } from "react";
import { RotateCcw, AlertTriangle, CheckCircle2, Trash2, XCircle } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

const idr = (n) => "Rp " + Number(n || 0).toLocaleString("id-ID");
const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString("id-ID", { day: "2-digit", month: "short", year: "numeric" }) : "—");

export default function Refunds() {
  const { t } = useAppPreferences();
  const [tab, setTab] = useState("pending");
  const [data, setData] = useState({ items: [], total_idr: 0, count: 0 });
  const [err, setErr] = useState("");
  const [target, setTarget] = useState(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setErr("");
    try { const { data } = await api.get(`/admin/refunds/${tab}`); setData(data); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [tab]);
  useEffect(() => { load(); }, [load]);

  const submit = async () => {
    if (note.trim().length < 3) { toast.error(t("Catatan/nomor referensi transfer wajib diisi.")); return; }
    setSaving(true);
    try {
      await api.post(`/admin/refunds/${target.payment_id}/mark-refunded`, { note });
      toast.success(t("Pembayaran ditandai sudah direfund."));
      setTarget(null); setNote(""); await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const statusBadge = (s) => s === "deleted"
    ? <span className="inline-flex items-center gap-1 rounded-full border border-zinc-500/40 bg-zinc-500/10 px-2 py-0.5 text-[11px] font-bold text-zinc-300"><Trash2 className="h-3 w-3" />{t("Dihapus")}</span>
    : s === "rejected"
    ? <span className="inline-flex items-center gap-1 rounded-full border border-red-400/30 bg-red-500/10 px-2 py-0.5 text-[11px] font-bold text-red-300"><XCircle className="h-3 w-3" />{t("Ditolak")}</span>
    : <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-zinc-400">{s}</span>;

  return (
    <div className="space-y-6" data-testid="refunds-page">
      <header className="border-b border-white/10 pb-5">
        <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Keuangan")}</div>
        <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><RotateCcw className="h-6 w-6 text-pink-400" />{t("Refund Pembayaran")}</h1>
        <p className="mt-2 text-sm text-zinc-400">{t("Pembayaran lunas untuk rilisan yang ditolak atau sudah dihapus. Transfer manual ke label, lalu tandai sudah direfund di sini (pencatatan status).")}</p>
      </header>

      <div className="flex items-center gap-2">
        <button onClick={() => setTab("pending")} className={`rounded-full px-4 py-1.5 text-sm font-semibold ${tab === "pending" ? "bg-pink-500/15 text-pink-300" : "text-zinc-500 hover:text-white"}`} data-testid="refunds-tab-pending">{t("Perlu Refund")}</button>
        <button onClick={() => setTab("history")} className={`rounded-full px-4 py-1.5 text-sm font-semibold ${tab === "history" ? "bg-pink-500/15 text-pink-300" : "text-zinc-500 hover:text-white"}`} data-testid="refunds-tab-history">{t("Riwayat")}</button>
        <span className="ml-auto text-sm text-zinc-400">{data.count} {t("pembayaran")} · <b className="text-white">{idr(data.total_idr)}</b></span>
      </div>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="refunds-error">{err}</div>}

      <div className="overflow-x-auto rounded-lg border border-white/10" data-testid="refunds-table">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-left text-[11px] uppercase text-zinc-500">
            <tr>
              <th className="px-4 py-3">{t("Label")}</th><th className="px-4 py-3">{t("Rilisan")}</th>
              <th className="px-4 py-3">{t("Status Rilisan")}</th><th className="px-4 py-3 text-right">{t("Nominal")}</th>
              <th className="px-4 py-3">{t("Tanggal Bayar")}</th><th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {data.items.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-zinc-500">
                {tab === "pending"
                  ? <span className="inline-flex items-center gap-2 text-emerald-300"><CheckCircle2 className="h-4 w-4" />{t("Tidak ada pembayaran yatim. Semua bersih.")}</span>
                  : t("Belum ada riwayat refund.")}
              </td></tr>
            ) : data.items.map((it) => (
              <tr key={it.payment_id} className="border-t border-white/5" data-testid={`refund-row-${it.payment_id}`}>
                <td className="px-4 py-3 font-semibold">{it.label_name}</td>
                <td className="px-4 py-3 text-zinc-300">{it.release_title}<span className="ml-2 text-[10px] uppercase text-zinc-600">{it.type}</span></td>
                <td className="px-4 py-3">{statusBadge(it.release_status)}</td>
                <td className="px-4 py-3 text-right font-bold tabular-nums">{idr(it.amount_idr)}</td>
                <td className="px-4 py-3 text-zinc-400">{fmt(it.paid_at)}</td>
                <td className="px-4 py-3 text-right">
                  {tab === "pending"
                    ? <button onClick={() => { setTarget(it); setNote(""); }} className="rm-btn text-xs" data-testid={`refund-mark-${it.payment_id}`}>{t("Tandai Direfund")}</button>
                    : <span className="text-[11px] text-emerald-300" title={it.refund_note}><CheckCircle2 className="mr-1 inline h-3.5 w-3.5" />{fmt(it.refunded_at)} · {it.refunded_by_name}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={!!target} onOpenChange={(o) => !o && setTarget(null)}>
        <DialogContent className="ui-menu max-w-md rounded-lg" data-testid="refund-dialog">
          <DialogHeader><DialogTitle>{t("Tandai Sudah Direfund")}</DialogTitle></DialogHeader>
          {target && (
            <div className="space-y-4">
              <div className="rounded-lg border border-amber-400/30 bg-amber-500/[0.06] p-3 text-sm">
                <div className="flex items-center gap-2 font-bold text-amber-300"><AlertTriangle className="h-4 w-4" />{t("Konfirmasi transfer manual")}</div>
                <p className="mt-1 text-zinc-300">{t("Pastikan Anda sudah mentransfer")} <b>{idr(target.amount_idr)}</b> {t("ke")} <b>{target.label_name}</b>. {t("Tindakan ini hanya mencatat status refund, tidak mengirim uang otomatis.")}</p>
              </div>
              <label className="block text-sm text-zinc-400">{t("Catatan / No. referensi transfer")} <span className="text-red-400">*</span>
                <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3} className="rm-input mt-1 w-full" placeholder={t("mis. Transfer BCA ref 8829911 tgl 15/06")} data-testid="refund-note" />
              </label>
            </div>
          )}
          <DialogFooter>
            <button onClick={() => setTarget(null)} className="rm-btn-ghost text-sm" data-testid="refund-cancel">{t("Batal")}</button>
            <button onClick={submit} disabled={saving} className="rm-btn text-sm" data-testid="refund-confirm">{saving ? t("Menyimpan…") : t("Konfirmasi Refund")}</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
