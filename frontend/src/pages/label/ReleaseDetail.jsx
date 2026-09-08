import React, { useCallback, useEffect, useState } from "react";
import { useParams, Link, useSearchParams, useNavigate } from "react-router-dom";
import { api, formatApiError, fileUrl } from "@/api/client";
import { openXenditCheckout, pollPaymentUntilTerminal } from "@/api/payments";
import StatusBadge from "@/components/shared/StatusBadge";
import { CreditCard, Disc3, Music, Download, Trash2 } from "lucide-react";
import { toast } from "@/components/ui/sonner";
import { ReleaseMetadataView } from "@/components/releases/ReleaseMetadataView";

export default function ReleaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [invoice, setInvoice] = useState(null);
  const [paying, setPaying] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/releases/${id}`);
      setData(data);
      if (data.payment_id && data.payment_status === "pending") {
        const inv = await api.get(`/label/invoices`);
        setInvoice(inv.data.find((i) => i.id === data.payment_id) || null);
      } else { setInvoice(null); }
    } catch (e) { setErr(formatApiError(e.response?.data?.detail) || "Gagal memuat"); }
  }, [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const paymentId = searchParams.get("payment_id");
    if (!paymentId) return;
    let active = true;
    setPaying(true);
    pollPaymentUntilTerminal(paymentId, null, 75)
      .then(async () => { if (active) { setSearchParams({}); await load(); } })
      .catch((e) => active && setErr(formatApiError(e.response?.data?.detail || e.message)))
      .finally(() => active && setPaying(false));
    return () => { active = false; };
  }, [searchParams, setSearchParams, load]);

  const pay = async () => {
    if (!invoice) return;
    setPaying(true);
    try {
      await openXenditCheckout(invoice.id);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail || e.message)); }
    finally { setPaying(false); }
  };
  const downloadCopyright = async () => {
    setErr("");
    try {
      const response = await api.get(`/releases/${id}/copyright-letter`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data); const anchor = document.createElement("a");
      anchor.href = url; anchor.download = `Surat-Hak-Cipta-${data.release_title}.pdf`; anchor.click(); URL.revokeObjectURL(url);
    } catch (error) { setErr(formatApiError(error.response?.data?.detail) || "Gagal membuat surat hak cipta"); }
  };

  const deleteRelease = async () => {
    if (!window.confirm(`Hapus rilisan “${data.release_title}”? Tindakan ini tidak dapat dibatalkan.`)) return;
    setDeleting(true);
    try {
      await api.delete(`/releases/${id}`);
      toast.success("Rilisan dihapus.");
      navigate("/label/releases");
    } catch (error) { setErr(formatApiError(error.response?.data?.detail) || "Gagal menghapus rilisan"); }
    finally { setDeleting(false); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;

  return (
    <div className="space-y-5 max-w-5xl">
      <Link to="/label/releases" className="text-sm text-zinc-400 hover:rm-gradient-text">← Daftar Rilisan</Link>

      <div className="flex items-start justify-between gap-5 flex-wrap">
        <div className="flex gap-4 items-start">
          {data.cover_url ? (
            <img src={fileUrl(data.cover_url)} alt="cover" className="w-28 h-28 rounded-2xl object-cover" />
          ) : (
            <div className="w-28 h-28 rounded-2xl bg-gradient-to-br from-[#FF4FA8] to-[#A24EFF] grid place-items-center text-white"><Disc3 className="w-8 h-8" /></div>
          )}
          <div>
            <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">{data.release_type}</div>
            <h1 className="font-display text-3xl font-extrabold tracking-tighter">{data.release_title}</h1>
            <div className="text-zinc-400 mt-1">{data.artist_name} • Rilis {data.release_date}</div>
            <div className="mt-2"><StatusBadge status={data.status} /></div>
          </div>
        </div>
        {(data.status === "draft" || data.status === "need_revision") && (
          <Link to={`/label/releases/${data.id}/edit`} className="rm-btn-ghost" data-testid="release-detail-edit-button">Edit</Link>
        )}
        {["draft", "rejected"].includes(data.status) && (
          <button type="button" onClick={deleteRelease} disabled={deleting} className="rm-btn-ghost flex items-center gap-2 text-red-300 hover:text-red-200 disabled:opacity-40" data-testid="release-detail-delete-button"><Trash2 className="w-4 h-4" /> {deleting ? "Menghapus…" : "Hapus Rilisan"}</button>
        )}
        {["approved", "delivered", "live"].includes(data.status) && <button type="button" className="rm-btn-ghost flex items-center gap-2" onClick={downloadCopyright} data-testid="release-detail-copyright-download"><Download className="w-4 h-4" /> Surat Hak Cipta</button>}
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm border border-red-100">{err}</div>}

      {/* Awaiting payment block */}
      {data.payment_status === "not_generated" && (
        <div className="rounded-lg border border-sky-500/30 bg-sky-500/10 p-5 text-sm text-sky-200" data-testid="release-detail-awaiting-admin-approval">
          Rilisan menunggu review admin. Invoice biaya dasar dan layanan tambahan dibuat setelah metadata dinyatakan valid.
        </div>
      )}
      {data.payment_status === "pending" && invoice && (
        <div className="rm-glass-strong rounded-3xl p-6 border border-amber-200/60">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/100/20 text-amber-300 grid place-items-center"><CreditCard className="w-5 h-5" /></div>
            <div>
              <div className="font-display font-bold text-lg">Menunggu Pembayaran</div>
              <div className="text-sm text-zinc-400">Invoice gabungan Rp {(invoice.amount).toLocaleString("id-ID")} via checkout Xendit.</div>
            </div>
          </div>
          <div className="text-xs text-zinc-500 mb-3">Invoice: {invoice.xendit_invoice_id}</div>
          {invoice.line_items?.length > 0 && <div className="mb-4 divide-y divide-white/5 rounded-lg border border-white/10 px-3" data-testid="release-detail-invoice-lines">{invoice.line_items.map((item) => <div key={item.reference_id} className="flex justify-between gap-4 py-2 text-xs"><span className="text-zinc-400">{item.name}</span><span>Rp {Number(item.amount || 0).toLocaleString("id-ID")}</span></div>)}</div>}
          <button className="rm-btn-primary" onClick={pay} disabled={paying} data-testid="release-detail-xendit-pay">
            {paying ? "Mengonfirmasi…" : "Bayar via Xendit"}
          </button>
          <div className="text-[11px] text-zinc-600 mt-2">Status pembayaran dikonfirmasi langsung ke Xendit setelah Anda kembali.</div>
        </div>
      )}
      {data.status === "paid" && <div className="rounded-md border border-emerald-500/30 bg-emerald-500/10 p-5 text-sm text-emerald-200" data-testid="release-detail-payment-confirmed">Pembayaran sudah dikonfirmasi. Admin akan menyetujui dan melanjutkan distribusi ke Believe.</div>}

      {data.admin_note && (
        <div className="rounded-2xl bg-yellow-500/15 text-yellow-200 px-4 py-3 text-sm border border-yellow-100">
          <b>Catatan Admin:</b> {data.admin_note}
        </div>
      )}

      <ReleaseMetadataView release={data} />
    </div>
  );
}

