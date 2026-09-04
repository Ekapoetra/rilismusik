import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CreditCard } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import StatusBadge from "@/components/shared/StatusBadge";
import { ReleaseMetadataView } from "@/components/releases/ReleaseMetadataView";
import { AdminReleaseWorkflow } from "./releases/AdminReleaseWorkflow";
import { useAuth } from "@/api/AuthContext";
import { WhatsAppFollowUpButton } from "@/components/releases/WhatsAppFollowUpButton";

export default function AdminReleaseDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [release, setRelease] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    try { const { data } = await api.get(`/releases/${id}`); setRelease(data); }
    catch (requestError) { setError(formatApiError(requestError.response?.data?.detail)); }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  if (!release) return <div className="text-zinc-500" data-testid="admin-release-detail-loading">Memuat detail rilisan…</div>;
  const canMutate = ["super_admin", "admin_release"].includes(user?.role);
  return <div className="max-w-7xl space-y-8 pb-28"><Link to="/admin/releases" className="inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white" data-testid="admin-release-back-link"><ArrowLeft className="h-4 w-4" /> Manajemen Rilisan</Link><header className="flex flex-col gap-4 border-b border-white/10 pb-6 sm:flex-row sm:items-end sm:justify-between"><div><div className="text-xs font-bold uppercase text-zinc-500">{release.release_type} · {release.id}</div><h1 className="mt-1 font-display text-4xl font-extrabold tracking-normal" data-testid="admin-release-detail-title">{release.release_title}</h1><p className="mt-2 text-sm text-zinc-400">{release.artist_name} · {release.label_name_snapshot}</p></div><div className="flex flex-wrap items-center gap-3"><WhatsAppFollowUpButton release={release} /><StatusBadge status={release.status} /></div></header>{message && <div className="rounded-md bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300" role="status" data-testid="admin-release-success">{message}</div>}{error && <div className="rounded-md bg-red-500/10 px-4 py-3 text-sm text-red-300" role="alert" data-testid="admin-release-error">{error}</div>}{release.admin_note && <div className="border-l-2 border-amber-400 bg-amber-500/10 px-4 py-3 text-sm text-amber-100" data-testid="admin-release-current-note"><strong>Catatan terakhir:</strong> {release.admin_note}</div>}{release.selected_addons?.length > 0 && <section className="border-y border-white/10 py-5" data-testid="admin-release-addons"><h2 className="mb-3 font-display text-lg font-bold">Layanan Tambahan</h2>{release.selected_addons.map((item) => <div className="flex justify-between py-2 text-sm" key={item.id}><span>{item.name}</span><strong>Rp {Number(item.amount || 0).toLocaleString("id-ID")}</strong></div>)}</section>}{release.payment && <section className="flex flex-wrap items-center justify-between gap-4 border border-white/10 p-4" data-testid="admin-release-payment"><div className="flex items-center gap-3"><CreditCard className="h-5 w-5 text-zinc-500" /><div><div className="font-bold">Invoice {release.payment.id}</div><div className="text-xs text-zinc-500">{release.payment.status} · Rp {Number(release.payment.amount || 0).toLocaleString("id-ID")}</div></div></div></section>}<ReleaseMetadataView release={release} />{canMutate ? <AdminReleaseWorkflow release={release} onUpdated={load} setMessage={setMessage} setError={setError} /> : <div className="border border-white/10 px-4 py-3 text-sm text-zinc-400" data-testid="admin-release-readonly-notice">Akses baca-saja. Tindakan alur kerja hanya tersedia untuk Admin Rilisan dan Super Admin.</div>}</div>;
}