import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Landmark, ShieldCheck, ArrowRight, RefreshCw } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { celebrateWork } from "@/lib/completionFeedback";

const Row = ({ label, value, strong }) => (
  <div className="flex justify-between gap-4 py-1 text-sm">
    <span className="text-zinc-500">{label}</span>
    <span className={`text-right ${strong ? "font-semibold text-white" : "text-zinc-300"}`}>{value || "—"}</span>
  </div>
);

export default function BankVerifications() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setErr("");
    try { const { data } = await api.get("/admin/bank-verifications"); setItems(data || []); }
    catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const review = async (item, action) => {
    setBusyId(item.id);
    try {
      await api.post(`/admin/bank-verifications/${item.id}/action`, { action });
      if (action === "approve") { celebrateWork("bank_verification"); }
      else { toast.success("Pengajuan rekening ditolak."); }
      await load();
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally { setBusyId(null); }
  };

  return (
    <div className="space-y-6" data-testid="admin-bank-verifications-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Operasional</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><Landmark className="h-6 w-6 text-pink-400" /> Verifikasi Rekening</h1>
          <p className="mt-2 text-sm text-zinc-400">Pengajuan perubahan/verifikasi rekening label yang menunggu persetujuan admin. Tinjau detail di sini tanpa harus mencari per label.</p>
        </div>
        <button type="button" onClick={load} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="bank-verif-refresh"><RefreshCw className="h-4 w-4" /> Muat ulang</button>
      </header>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="bank-verif-error">{err}</div>}

      {loading ? (
        <p className="text-sm text-zinc-500" data-testid="bank-verif-loading">Memuat…</p>
      ) : items.length === 0 ? (
        <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="bank-verif-empty">Tidak ada pengajuan rekening yang menunggu. Semua beres 🎉</div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2" data-testid="bank-verif-grid">
          {items.map((item) => (
            <section key={item.id} className="rm-card space-y-4 p-5" data-testid={`bank-verif-card-${item.id}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2 text-sm font-bold text-amber-200"><ShieldCheck className="h-4 w-4" /> Persetujuan admin diperlukan</div>
                  <h3 className="mt-1 font-display text-lg font-bold">{item.label_name || "Label"}</h3>
                  <div className="text-xs text-zinc-500">Diajukan {(item.created_at || "").replace("T", " ").slice(0, 16)}{item.requested_by_name ? ` · oleh ${item.requested_by_name}` : ""}</div>
                </div>
                <Link to={`/admin/labels/${item.label_id}`} className="inline-flex items-center gap-1 text-xs font-bold text-pink-300 hover:text-pink-200" data-testid={`bank-verif-open-label-${item.id}`}>Buka label <ArrowRight className="h-3.5 w-3.5" /></Link>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-zinc-500">Rekening saat ini</div>
                  <Row label="Bank" value={item.current_bank?.bank_name} />
                  <Row label="Nomor" value={item.current_bank?.account_number} />
                  <Row label="Atas nama" value={item.current_bank?.account_holder_name} />
                </div>
                <div className="rounded-lg border border-emerald-400/30 bg-emerald-400/[0.05] p-3">
                  <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-emerald-300">Rekening baru diajukan</div>
                  <Row label="Bank" value={item.proposed_bank?.bank_name} strong />
                  <Row label="Nomor" value={item.proposed_bank?.account_number} strong />
                  <Row label="Atas nama" value={item.proposed_bank?.account_holder_name} strong />
                </div>
              </div>

              {item.reason && <div className="rounded-md bg-white/[0.03] px-3 py-2 text-sm text-zinc-400"><span className="text-zinc-500">Alasan: </span>{item.reason}</div>}

              <div className="flex gap-2">
                <button className="rm-btn-primary text-sm" disabled={busyId === item.id} onClick={() => review(item, "approve")} data-testid={`bank-verif-approve-${item.id}`}>{busyId === item.id ? "Memproses…" : "Setujui & Verifikasi"}</button>
                <button className="rm-btn-ghost text-sm text-red-300" disabled={busyId === item.id} onClick={() => review(item, "reject")} data-testid={`bank-verif-reject-${item.id}`}>Tolak</button>
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
