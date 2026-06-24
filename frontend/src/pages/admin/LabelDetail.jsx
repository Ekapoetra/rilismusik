import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";

export default function AdminLabelDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [royalty, setRoyalty] = useState("");
  const [reason, setReason] = useState("");
  const [blacklistOpen, setBlacklistOpen] = useState(false);
  const [blacklistReason, setBlacklistReason] = useState("");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const { data } = await api.get(`/admin/labels/${id}`);
    setData(data);
    setRoyalty(String(data.label.royalty_percentage_default ?? 60));
  };
  useEffect(() => { load(); }, [id]);

  const canFinance = user?.role === "super_admin" || user?.role === "admin_finance";
  const canBlacklist = user?.role === "super_admin";

  const setStatus = async (s) => {
    setErr(""); setMsg("");
    try {
      await api.patch(`/admin/labels/${id}`, { account_status: s });
      await load();
      setMsg(`Status diubah ke ${s}`);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  };

  const setRoyaltyPct = async () => {
    setErr(""); setMsg("");
    try {
      await api.patch(`/admin/labels/${id}`, { royalty_percentage_default: parseFloat(royalty), royalty_change_reason: reason });
      await load();
      setMsg("Persentase royalti diperbarui.");
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  };

  const verifyBank = async () => {
    setErr(""); setMsg("");
    try {
      await api.post(`/withdraw/admin/verify-bank/${id}`);
      await load();
      setMsg("Rekening diverifikasi.");
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  };

  const blacklist = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      await api.post(`/admin/labels/${id}/blacklist`, { reason: blacklistReason });
      setBlacklistOpen(false);
      setBlacklistReason("");
      await load();
      setMsg("Label di-blacklist. Login akan ditolak.");
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
  };

  const unblacklist = async () => {
    if (!window.confirm("Lepas blacklist label ini?")) return;
    setErr(""); setMsg("");
    try {
      await api.post(`/admin/labels/${id}/unblacklist`);
      await load();
      setMsg("Blacklist dilepas. Label dapat login kembali.");
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const l = data.label;
  const isBlacklisted = l.account_status === "blacklisted";

  return (
    <div className="space-y-5">
      <Link to="/admin/labels" className="text-sm text-zinc-400 hover:rm-gradient-text">← Label Management</Link>
      <div className="flex items-center gap-3 flex-wrap">
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">{l.label_name}</h1>
        {isBlacklisted && (
          <span className="rm-badge" style={{ background: "rgba(239,68,68,0.2)", color: "#FCA5A5" }}>
            <span className="rm-badge-dot" style={{ background: "#EF4444" }} />
            BLACKLISTED
          </span>
        )}
      </div>
      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}

      {isBlacklisted && l.blacklist_reason && (
        <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-4 text-sm">
          <div className="text-xs font-bold uppercase tracking-widest text-red-300 mb-1">Alasan Blacklist</div>
          <div className="text-red-100">{l.blacklist_reason}</div>
          {l.blacklisted_at && <div className="text-xs text-red-200/60 mt-1">Diblacklist pada {new Date(l.blacklisted_at).toLocaleString("id-ID")}</div>}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="rm-card p-5 space-y-2">
          <h3 className="font-display font-bold tracking-tight text-lg">Info Label</h3>
          <Row k="Penanggung Jawab" v={l.pic_name} />
          <Row k="Email" v={l.email} />
          <Row k="WhatsApp" v={l.whatsapp} />
          <Row k="Tipe" v={l.label_type} />
          <Row k="Subscription" v={l.subscription_status} />
          <Row k="Kontrak" v={l.contract_status} />
          <Row k="Status Akun" v={l.account_status} />
          <Row k="Royalti %" v={l.royalty_percentage_default + "%"} />
          <Row k="Created" v={l.created_at?.slice(0, 10)} />
        </div>
        <div className="rm-card p-5 space-y-3">
          <h3 className="font-display font-bold tracking-tight text-lg">Aksi</h3>
          <div className="flex gap-2 flex-wrap">
            <button className="rm-btn-ghost text-sm" onClick={() => setStatus("active")} data-testid="admin-label-activate" disabled={isBlacklisted}>Aktifkan</button>
            <button className="rm-btn-ghost text-sm" onClick={() => setStatus("suspended")} data-testid="admin-label-suspend" disabled={isBlacklisted}>Suspend</button>
            {canBlacklist && !isBlacklisted && (
              <button className="rm-btn-ghost text-sm text-red-300 hover:text-red-200" onClick={() => setBlacklistOpen(true)} data-testid="admin-label-blacklist">Blacklist…</button>
            )}
            {canBlacklist && isBlacklisted && (
              <button className="rm-btn-ghost text-sm text-emerald-300 hover:text-emerald-200" onClick={unblacklist} data-testid="admin-label-unblacklist">Lepas Blacklist</button>
            )}
          </div>
          {canFinance && (
            <div className="pt-3 border-t border-white/5 space-y-3">
              <div>
                <label className="rm-label">Bagian Royalti Label (%)</label>
                <input className="rm-input" type="number" min="0" max="100" value={royalty} onChange={(e) => setRoyalty(e.target.value)} data-testid="admin-label-royalty-input" />
              </div>
              <div>
                <label className="rm-label">Alasan Perubahan</label>
                <input className="rm-input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Misal: review tahunan" data-testid="admin-label-royalty-reason" />
              </div>
              <button className="rm-btn-primary text-sm" onClick={setRoyaltyPct} data-testid="admin-label-royalty-save">Simpan Royalti</button>
              <div className="text-[11px] text-zinc-500">Perubahan berlaku mulai bulan berjalan. Histori disimpan otomatis.</div>
            </div>
          )}
        </div>
        <div className="rm-card p-5 space-y-2">
          <h3 className="font-display font-bold tracking-tight text-lg">Rekening</h3>
          {data.bank_account ? (
            <>
              <Row k="Bank" v={data.bank_account.bank_name} />
              <Row k="Nomor" v={data.bank_account.account_number} />
              <Row k="Atas Nama" v={data.bank_account.account_holder_name} />
              <Row k="Verifikasi" v={data.bank_account.verified_status} />
              {canFinance && data.bank_account.verified_status !== "verified" && (
                <button className="rm-btn-primary text-sm mt-2" onClick={verifyBank} data-testid="admin-label-verify-bank">Verifikasi Rekening</button>
              )}
            </>
          ) : <div className="text-sm text-zinc-500">Label belum input rekening.</div>}
        </div>
        <div className="rm-card p-5 space-y-2">
          <h3 className="font-display font-bold tracking-tight text-lg">Statistik</h3>
          <Row k="Artist" v={data.artists_count} />
          <Row k="Rilisan" v={data.releases_count} />
          <Row k="Saldo Tersedia" v={"Rp " + (l.balance_available_idr || 0).toLocaleString("id-ID")} />
          <Row k="Saldo Pending" v={"Rp " + (l.balance_pending_idr || 0).toLocaleString("id-ID")} />
        </div>
      </div>

      {/* Blacklist modal */}
      {blacklistOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setBlacklistOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={blacklist} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4 border border-red-500/30">
            <h3 className="font-display font-extrabold text-xl tracking-tighter text-red-200">Blacklist Label</h3>
            <div className="text-sm text-zinc-300">
              Label <b>{l.label_name}</b> akan di-blacklist. Login akan ditolak dengan alasan yang Anda input. Semua rilisan & saldo tetap ada tapi tidak bisa diakses.
            </div>
            <div>
              <label className="rm-label">Alasan Blacklist</label>
              <textarea
                className="rm-input min-h-[100px]"
                value={blacklistReason}
                onChange={(e) => setBlacklistReason(e.target.value)}
                placeholder="Misal: terbukti melakukan plagiasi konten…"
                data-testid="admin-label-blacklist-reason"
                required
                minLength={3}
              />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setBlacklistOpen(false)}>Batal</button>
              <button className="rm-btn-primary bg-gradient-to-r from-red-500 to-rose-600" disabled={blacklistReason.length < 3} data-testid="admin-label-blacklist-submit">Blacklist</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
function Row({ k, v }) { return <div className="flex justify-between text-sm py-1.5 border-b border-white/5 last:border-0"><span className="text-zinc-500">{k}</span><span className="font-semibold capitalize">{v ?? "—"}</span></div>; }
