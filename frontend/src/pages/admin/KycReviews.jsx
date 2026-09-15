import React, { useCallback, useEffect, useState } from "react";
import { BadgeCheck, Clock3, Search, ShieldCheck } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { KycReviewDetail } from "@/components/admin/KycReviewDetail";
import { useAuth } from "@/api/AuthContext";

const FILTERS = [{ value: "pending_review", label: "Menunggu" }, { value: "rejected", label: "Ditolak" }, { value: "verified", label: "Terverifikasi" }, { value: "", label: "Semua" }];

export default function KycReviews() {
  const { hasPermission, user } = useAuth();
  const [status, setStatus] = useState("pending_review");
  const [items, setItems] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadQueue = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const { data } = await api.get("/admin/kyc", { params: { status } });
      setItems(data || []);
      setSelectedId((current) => (data || []).some((item) => item.label_id === current) ? current : data?.[0]?.label_id || null);
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setLoading(false); }
  }, [status]);

  const loadDetail = useCallback(async () => {
    if (!selectedId) { setDetail(null); return; }
    try { const { data } = await api.get(`/admin/kyc/${selectedId}`); setDetail(data); }
    catch (err) { setError(formatApiError(err.response?.data?.detail)); }
  }, [selectedId]);

  useEffect(() => { loadQueue(); }, [loadQueue]);
  useEffect(() => { loadDetail(); }, [loadDetail]);
  const reviewed = async () => { await loadQueue(); await loadDetail(); };

  return <div className="space-y-7" data-testid="admin-kyc-page">
    <header className="flex flex-col gap-4 border-b border-white/10 pb-6 lg:flex-row lg:items-end lg:justify-between"><div><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Identity Operations</div><h1 className="mt-1 font-display text-4xl font-extrabold">Review Verifikasi Akun</h1><p className="mt-2 text-sm text-zinc-400">Verifikasi identitas penanggung jawab tanpa mengekspos dokumen ke URL publik.</p></div><div className="flex flex-wrap gap-2" data-testid="admin-kyc-status-filters">{FILTERS.map((filter) => <button key={filter.value || "all"} type="button" onClick={() => setStatus(filter.value)} className={`rounded-md border px-4 py-2 text-sm font-semibold transition-colors ${status === filter.value ? "border-white/30 bg-white text-black" : "border-white/10 bg-white/[0.03] text-zinc-400 hover:bg-white/[0.07] hover:text-white"}`} data-testid={`admin-kyc-filter-${filter.value || "all"}`}>{filter.label}</button>)}</div></header>
    {error && <div role="alert" className="rounded-lg border border-red-400/30 bg-red-400/10 p-4 text-sm text-red-200" data-testid="admin-kyc-page-error">{error}</div>}
    <div className="grid min-h-[560px] gap-8 xl:grid-cols-[340px_minmax(0,1fr)]">
      <aside className="border-y border-white/10 py-3" data-testid="admin-kyc-queue">
        <div className="flex items-center justify-between px-2 py-3"><span className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><Search className="h-4 w-4" /> Pengajuan</span><strong className="font-mono text-sm" data-testid="admin-kyc-queue-count">{items.length}</strong></div>
        {loading && <div className="px-2 py-8 text-sm text-zinc-500" data-testid="admin-kyc-loading">Memuat antrean…</div>}
        {!loading && items.length === 0 && <div className="px-2 py-8 text-sm text-zinc-500" data-testid="admin-kyc-empty-queue">Tidak ada pengajuan pada status ini.</div>}
        <div className="rm-stagger space-y-2">{items.map((item) => <button key={item.id} type="button" onClick={() => setSelectedId(item.label_id)} className={`w-full rounded-lg border p-4 text-left transition-colors rm-fade-up ${selectedId === item.label_id ? "border-white/25 bg-white/[0.08]" : "border-transparent bg-white/[0.025] hover:border-white/10 hover:bg-white/[0.05]"}`} data-testid={`admin-kyc-queue-item-${item.label_id}`}><div className="flex items-start justify-between gap-3"><div><div className="font-display font-bold text-white">{item.label_name}</div><div className="mt-1 text-xs text-zinc-500">{item.pic_name || item.email}</div></div>{item.status === "verified" ? <BadgeCheck className="h-4 w-4 text-emerald-300" /> : item.status === "pending_review" ? <Clock3 className="h-4 w-4 text-amber-300" /> : <ShieldCheck className="h-4 w-4 text-red-300" />}</div><div className="mt-3 text-[11px] uppercase tracking-widest text-zinc-600">{item.uploaded_at?.slice(0, 10)}</div></button>)}</div>
      </aside>
      <KycReviewDetail detail={detail} onReviewed={reviewed} canReview={user?.role === "super_admin"} />
      {detail && user?.role !== "super_admin" && <p className="mt-3 text-center text-xs text-amber-300" data-testid="admin-kyc-super-only-note">Hanya Super Admin yang dapat memproses verifikasi akun.</p>}
    </div>
  </div>;
}