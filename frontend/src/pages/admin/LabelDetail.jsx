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
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [revokeReason, setRevokeReason] = useState("");
  const [revokeCascade, setRevokeCascade] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailNotify, setEmailNotify] = useState(true);
  const [subTier, setSubTier] = useState("pay_per_release");
  const [subExpiry, setSubExpiry] = useState("");
  const [subSaving, setSubSaving] = useState(false);
  const [royaltySaving, setRoyaltySaving] = useState(false);
  const [recalcJob, setRecalcJob] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const { data } = await api.get(`/admin/labels/${id}`);
    setData(data);
    setRoyalty(String(data.label.royalty_percentage_default ?? 60));
    const l = data.label;
    setSubTier(l.payment_type === "annual_subscription" ? (l.subscription_tier || "annual_normal") : "pay_per_release");
    setSubExpiry(l.subscription_expires_at ? l.subscription_expires_at.slice(0, 10) : "");
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
    setRoyaltySaving(true);
    try {
      const { data: updated } = await api.patch(`/admin/labels/${id}`, { royalty_percentage_default: parseFloat(royalty), royalty_change_reason: reason });
      await load();
      const jobId = updated.royalty_recalculation_job_id;
      if (!jobId) {
        setMsg("Persentase royalti tersimpan; tidak ada perubahan nilai yang perlu dihitung ulang.");
        return;
      }
      setMsg("Persentase tersimpan. Royalti belum ditarik sedang dihitung ulang tanpa fee tambahan.");
      for (let attempt = 0; attempt < 180; attempt += 1) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        const { data: job } = await api.get(`/admin/migrate/jobs/${jobId}`);
        setRecalcJob(job);
        if (job.status === "done") {
          const result = job.result || {};
          setMsg(`Hitung ulang selesai: ${(result.lines_recalculated || 0).toLocaleString("id-ID")} baris diperbarui.`);
          await load();
          break;
        }
        if (job.status === "error") {
          setErr(job.error_message || "Hitung ulang royalti gagal.");
          break;
        }
      }
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setRoyaltySaving(false); }
  };

  const saveSubscription = async () => {
    setErr(""); setMsg("");
    if (subTier !== "pay_per_release" && !subExpiry) {
      setErr("Isi tanggal masa berlaku untuk paket tahunan.");
      return;
    }
    setSubSaving(true);
    try {
      const payload = subTier === "pay_per_release"
        ? { payment_type: "pay_per_release" }
        : { subscription_tier: subTier, subscription_expires_at: subExpiry };
      await api.patch(`/admin/labels/${id}`, payload);
      await load();
      setMsg("Paket langganan diperbarui.");
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setSubSaving(false); }
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

  const revokeAccount = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      const fd = new FormData();
      fd.append("cascade_artists", revokeCascade ? "true" : "false");
      fd.append("reason", revokeReason);
      const { data: res } = await api.post(`/admin/labels/${id}/revoke-account`, fd);
      setRevokeOpen(false);
      setRevokeReason("");
      setRevokeCascade(false);
      await load();
      setMsg(
        `Akses akun ${res.revoked_email || ""} dicabut. ` +
        (res.artists_disabled > 0 ? `${res.artists_disabled} artist sub-account ikut dinonaktifkan. ` : "") +
        "Anda bisa buat akun baru dengan email lain via 'Buat Akun'."
      );
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
  };

  const changeEmail = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    try {
      const fd = new FormData();
      fd.append("new_email", newEmail.trim().toLowerCase());
      fd.append("notify", emailNotify ? "true" : "false");
      const { data: res } = await api.post(`/admin/labels/${id}/change-email`, fd);
      setEmailOpen(false);
      setNewEmail("");
      await load();
      setMsg(
        `Email diubah dari ${res.old_email} → ${res.new_email}. ` +
        (emailNotify ? `Notifikasi terkirim ke email ${res.notify_sent?.old ? "lama" : ""}${res.notify_sent?.old && res.notify_sent?.new ? " & " : ""}${res.notify_sent?.new ? "baru" : ""}. ` : "") +
        "Sesi login label terputus, harus login ulang."
      );
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
          <Row k="Paket" v={l.payment_type === "annual_subscription" ? (l.subscription_tier === "annual_vip" ? "Annual VIP" : "Annual Normal") : "Pay Per Release"} />
          <Row k="Subscription" v={l.subscription_status} />
          <Row k="Masa Berlaku" v={l.subscription_expires_at ? new Date(l.subscription_expires_at).toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" }) : "—"} />
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
          {/* Phase 25 — Account lifecycle */}
          {l.user_id && (
            <div className="pt-3 border-t border-white/5 space-y-2">
              <div className="text-[11px] uppercase tracking-widest font-bold text-zinc-500">Akun Login</div>
              <div className="text-xs text-zinc-400">Email aktif: <span className="font-mono text-zinc-200">{l.email || "—"}</span></div>
              <div className="flex gap-2 flex-wrap">
                <button
                  className="rm-btn-ghost text-xs flex items-center gap-1"
                  onClick={() => setEmailOpen(true)}
                  data-testid="admin-label-change-email"
                >
                  Ganti Email
                </button>
                <button
                  className="rm-btn-ghost text-xs text-amber-300 hover:text-amber-200 flex items-center gap-1"
                  onClick={() => setRevokeOpen(true)}
                  data-testid="admin-label-revoke-account"
                >
                  Cabut Akses
                </button>
              </div>
              <div className="text-[10px] text-zinc-500 leading-relaxed">
                Cabut akses akan menonaktifkan login tanpa menghapus data label/royalti. Akun baru bisa dibuat ulang dengan email lain.
              </div>
            </div>
          )}
          {!l.user_id && l.previous_account_email && (
            <div className="pt-3 border-t border-white/5 text-xs">
              <div className="text-amber-300">Akun login dicabut sebelumnya.</div>
              <div className="text-zinc-500 mt-0.5">Mantan email: <span className="font-mono">{l.previous_account_email}</span></div>
              <div className="text-zinc-500">Gunakan tombol &quot;Buat Akun&quot; di halaman Label Management untuk akun baru.</div>
            </div>
          )}
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
              <button className="rm-btn-primary text-sm" onClick={setRoyaltyPct} disabled={royaltySaving} data-testid="admin-label-royalty-save">{royaltySaving ? "Menghitung ulang…" : "Simpan Royalti"}</button>
              {recalcJob && (
                <div className="text-xs text-sky-300" data-testid="admin-label-royalty-recalculation-status">
                  Status: {recalcJob.status === "processing" ? "memproses" : recalcJob.status} • {(recalcJob.progress_lines_done || 0).toLocaleString("id-ID")} / {(recalcJob.progress_lines_total || 0).toLocaleString("id-ID")} baris
                </div>
              )}
              <div className="text-[11px] text-zinc-500">Persentase diterapkan langsung pada pendapatan dasar. Semua royalti yang belum withdrawn dihitung ulang; royalti settled tetap dibekukan.</div>
            </div>
          )}
        </div>
        {/* Phase 30 — Paket & Langganan manual edit */}
        {canFinance && (
          <div className="rm-card p-5 space-y-3" data-testid="admin-label-subscription-card">
            <h3 className="font-display font-bold tracking-tight text-lg">Paket &amp; Langganan</h3>
            <div>
              <label className="rm-label">Paket</label>
              <select
                className="rm-input"
                value={subTier}
                onChange={(e) => setSubTier(e.target.value)}
                data-testid="admin-label-sub-tier-select"
              >
                <option value="pay_per_release">Pay Per Release (Rp 35.000 / rilis)</option>
                <option value="annual_normal">Annual Normal (Rp 350.000 / tahun)</option>
                <option value="annual_vip">Annual VIP (Rp 500.000 / tahun — FREE WAMI)</option>
              </select>
            </div>
            {subTier !== "pay_per_release" && (
              <div>
                <label className="rm-label">Masa Berlaku Sampai</label>
                <input
                  className="rm-input"
                  type="date"
                  value={subExpiry}
                  onChange={(e) => setSubExpiry(e.target.value)}
                  data-testid="admin-label-sub-expiry-input"
                />
                <div className="text-[11px] text-zinc-500 mt-1">Langganan otomatis aktif jika tanggal di masa depan, expired jika sudah lewat.</div>
              </div>
            )}
            <button
              className="rm-btn-primary text-sm"
              onClick={saveSubscription}
              disabled={subSaving}
              data-testid="admin-label-sub-save"
            >
              {subSaving ? "Menyimpan…" : "Simpan Paket"}
            </button>
            <div className="text-[11px] text-zinc-500">
              Pindah ke Pay Per Release akan menonaktifkan langganan &amp; menghapus masa berlaku. Annual VIP aktif = WAMI gratis untuk label ini.
            </div>
          </div>
        )}
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

      {/* Phase 25 — Revoke account modal */}
      {revokeOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setRevokeOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={revokeAccount} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4 border border-amber-500/30" data-testid="admin-label-revoke-modal">
            <h3 className="font-display font-extrabold text-xl tracking-tighter text-amber-200">Cabut Akses Akun</h3>
            <div className="text-sm text-zinc-300 space-y-2">
              <p>
                Email login <b className="text-zinc-100">{l.email}</b> akan dinonaktifkan. Semua sesi terputus & login ditolak.
              </p>
              <p className="text-amber-300/90 text-xs">
                Data label, artist, rilisan, kontrak, dan royalti TIDAK dihapus. Anda bisa membuat akun baru dengan email lain via &quot;Buat Akun&quot; di Label Management.
              </p>
            </div>
            <div>
              <label className="rm-label">Alasan (opsional)</label>
              <input
                className="rm-input"
                value={revokeReason}
                onChange={(e) => setRevokeReason(e.target.value)}
                placeholder="Misal: ganti PIC, pergantian email, dll"
                data-testid="admin-label-revoke-reason"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
              <input
                type="checkbox"
                checked={revokeCascade}
                onChange={(e) => setRevokeCascade(e.target.checked)}
                data-testid="admin-label-revoke-cascade"
                className="rm-checkbox"
              />
              <span>Ikut nonaktifkan {data.artists_count || 0} artist sub-account label ini</span>
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setRevokeOpen(false)}>Batal</button>
              <button
                className="rm-btn-primary bg-gradient-to-r from-amber-500 to-orange-600"
                data-testid="admin-label-revoke-submit"
              >
                Cabut Akses
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Phase 25 — Change email modal */}
      {emailOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setEmailOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={changeEmail} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4 border border-sky-500/30" data-testid="admin-label-email-modal">
            <h3 className="font-display font-extrabold text-xl tracking-tighter text-sky-200">Ganti Email Akun</h3>
            <div className="text-sm text-zinc-300">
              Email akun login <b>{l.label_name}</b> akan diubah. Sesi login lama otomatis terputus — label harus login ulang dengan email baru.
            </div>
            <div>
              <label className="rm-label">Email Lama</label>
              <input className="rm-input opacity-70" disabled value={l.email || ""} />
            </div>
            <div>
              <label className="rm-label">Email Baru</label>
              <input
                className="rm-input"
                type="email"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="email@baru.com"
                data-testid="admin-label-new-email"
                required
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
              <input
                type="checkbox"
                checked={emailNotify}
                onChange={(e) => setEmailNotify(e.target.checked)}
                data-testid="admin-label-email-notify"
                className="rm-checkbox"
              />
              <span>Kirim notifikasi otomatis ke email lama & baru</span>
            </label>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setEmailOpen(false)}>Batal</button>
              <button
                className="rm-btn-primary bg-gradient-to-r from-sky-500 to-cyan-600"
                disabled={!newEmail || !newEmail.includes("@")}
                data-testid="admin-label-email-submit"
              >
                Ganti Email
              </button>
            </div>
          </form>
        </div>
      )}

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
