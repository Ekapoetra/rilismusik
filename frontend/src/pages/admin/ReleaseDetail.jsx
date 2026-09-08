import React, { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, CreditCard } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";
import { ReleaseMetadataView } from "@/components/releases/ReleaseMetadataView";
import { AdminReleaseWorkflow } from "./releases/AdminReleaseWorkflow";
import { useAuth } from "@/api/AuthContext";
import { WhatsAppFollowUpButton } from "@/components/releases/WhatsAppFollowUpButton";
import { AdminDeleteReleaseButton } from "@/components/releases/AdminDeleteReleaseButton";

export default function AdminReleaseDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const [release, setRelease] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    setError("");
    try { const { data } = await api.get(`/releases/${id}`); setRelease(data); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail) || "Gagal memuat detail rilisan."); }
  }, [id]);
  useEffect(() => { setRelease(null); load(); }, [load]);
  const canMutate = hasPermission("releases.review");

  return (
    <div className="min-w-0 max-w-7xl space-y-8 pb-28" data-testid="admin-release-detail-page">
      <Link to="/admin/releases" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white" data-testid="admin-release-back-link"><ArrowLeft className="h-4 w-4" /> Manajemen Rilisan</Link>
      {error && <div className="rounded-md bg-red-500/10 px-4 py-3 text-sm text-red-300" role="alert" data-testid="admin-release-error">{error}</div>}
      {!release ? (!error && <div className="text-zinc-500" data-testid="admin-release-detail-loading">Memuat detail rilisan…</div>) : <>
        <header className="flex flex-col gap-4 border-b border-white/10 pb-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="break-all text-xs font-bold uppercase text-zinc-500" data-testid="admin-release-detail-reference">{release.release_type} · {release.id}</div>
            <h1 className="mt-1 break-words font-display text-4xl font-extrabold tracking-normal" data-testid="admin-release-detail-title">{release.release_title}</h1>
            <p className="mt-2 break-words text-sm text-zinc-400" data-testid="admin-release-detail-artist-label">{release.artist_name} · {release.label_name_snapshot}</p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-3">
            <WhatsAppFollowUpButton release={release} />
            <span data-testid="admin-release-detail-status"><StatusBadge status={release.status} /></span>
            <AdminDeleteReleaseButton release={release} onDeleted={() => navigate("/admin/releases", { replace: true })} />
          </div>
        </header>
        {message && <div className="rounded-md bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300" role="status" data-testid="admin-release-success">{message}</div>}
        {release.admin_note && <div className="border-l-2 border-amber-400 bg-amber-500/10 px-4 py-3 text-sm text-amber-100" data-testid="admin-release-current-note"><strong>Catatan terakhir:</strong> {release.admin_note}</div>}
        {release.selected_addons?.length > 0 && <section className="border-y border-white/10 py-5" data-testid="admin-release-addons">
          <h2 className="mb-3 font-display text-lg font-bold">Layanan Tambahan</h2>
          {release.selected_addons.map((item) => <div className="flex justify-between py-2 text-sm" key={item.id} data-testid={`admin-release-addon-${item.id}`}><span>{item.name}</span><strong>Rp {Number(item.amount || 0).toLocaleString("id-ID")}</strong></div>)}
        </section>}
        {release.payment && <section className="flex flex-wrap items-center justify-between gap-4 border border-white/10 p-4" data-testid="admin-release-payment">
          <div className="flex min-w-0 items-center gap-3"><CreditCard className="h-5 w-5 shrink-0 text-zinc-500" /><div className="min-w-0"><div className="break-all font-bold">Invoice {release.payment.id}</div><div className="text-xs text-zinc-500">{release.payment.status} · Rp {Number(release.payment.amount || 0).toLocaleString("id-ID")}</div></div></div>
        </section>}
        <ReleaseMetadataView release={release} />
        {canMutate ? <AdminReleaseWorkflow release={release} onUpdated={load} setMessage={setMessage} setError={setError} /> : <div className="border border-white/10 px-4 py-3 text-sm text-zinc-400" data-testid="admin-release-readonly-notice">Akses baca-saja. Tindakan alur kerja memerlukan izin Review dan ubah status.</div>}
      </>}
    </div>
  );
}