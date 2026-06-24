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
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const { data } = await api.get(`/admin/labels/${id}`);
    setData(data);
    setRoyalty(String(data.label.royalty_percentage_default ?? 60));
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const canFinance = user?.role === "super_admin" || user?.role === "admin_finance";

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

  if (!data) return <div className="text-slate-500">Memuat…</div>;
  const l = data.label;

  return (
    <div className="space-y-5">
      <Link to="/admin/labels" className="text-sm text-slate-600 hover:text-[#FF3B30]">← Label Management</Link>
      <h1 className="font-display text-3xl font-extrabold tracking-tighter">{l.label_name}</h1>
      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">{msg}</div>}

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
            <button className="rm-btn-ghost text-sm" onClick={() => setStatus("active")} data-testid="admin-label-activate">Aktifkan</button>
            <button className="rm-btn-ghost text-sm" onClick={() => setStatus("suspended")} data-testid="admin-label-suspend">Suspend</button>
            <button className="rm-btn-ghost text-sm" onClick={() => setStatus("blacklisted")} data-testid="admin-label-blacklist">Blacklist</button>
          </div>
          {canFinance && (
            <div className="pt-3 border-t border-slate-100 space-y-3">
              <div>
                <label className="rm-label">Bagian Royalti Label (%)</label>
                <input className="rm-input" type="number" min="0" max="100" value={royalty} onChange={(e) => setRoyalty(e.target.value)} data-testid="admin-label-royalty-input" />
              </div>
              <div>
                <label className="rm-label">Alasan Perubahan</label>
                <input className="rm-input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Misal: review tahunan" data-testid="admin-label-royalty-reason" />
              </div>
              <button className="rm-btn-primary text-sm" onClick={setRoyaltyPct} data-testid="admin-label-royalty-save">Simpan Royalti</button>
              <div className="text-[11px] text-slate-500">Perubahan berlaku mulai bulan berjalan. Histori disimpan otomatis.</div>
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
          ) : <div className="text-sm text-slate-500">Label belum input rekening.</div>}
        </div>
        <div className="rm-card p-5 space-y-2">
          <h3 className="font-display font-bold tracking-tight text-lg">Statistik</h3>
          <Row k="Artist" v={data.artists_count} />
          <Row k="Rilisan" v={data.releases_count} />
          <Row k="Saldo Tersedia" v={"Rp " + (l.balance_available_idr || 0).toLocaleString("id-ID")} />
          <Row k="Saldo Pending" v={"Rp " + (l.balance_pending_idr || 0).toLocaleString("id-ID")} />
        </div>
      </div>
    </div>
  );
}
function Row({ k, v }) { return <div className="flex justify-between text-sm py-1.5 border-b border-slate-50 last:border-0"><span className="text-slate-500">{k}</span><span className="font-semibold capitalize">{v ?? "—"}</span></div>; }
