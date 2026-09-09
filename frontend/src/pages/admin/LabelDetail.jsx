import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { LabelDetailCards, LabelDetailModals } from "@/components/admin/LabelDetailView";
import { BankChangePanel } from "@/components/admin/BankChangePanel";
import BalanceAuditPanel from "./BalanceAuditPanel";
import { Scale } from "lucide-react";
import { RoyaltyAdjustmentPanel } from "@/components/admin/royalty-adjustments/RoyaltyAdjustmentPanel";

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

export default function AdminLabelDetail() {
  const { id } = useParams();
  const { hasPermission } = useAuth();
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
  const [royaltySaving, setRoyaltySaving] = useState(false);
  const [recalcJob, setRecalcJob] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [balanceAuditOpen, setBalanceAuditOpen] = useState(false);

  const load = useCallback(async () => {
    const response = await api.get(`/admin/labels/${id}`);
    const label = response.data.label;
    setData(response.data);
    setRoyalty(String(label.royalty_percentage_default ?? 60));
  }, [id]);

  useEffect(() => { load().catch((error) => setErr(formatApiError(error.response?.data?.detail))); }, [load]);
  const canFinance = hasPermission("labels.bank") || hasPermission("royalty.manage");
  const canRate = hasPermission("labels.rate");
  const canBlacklist = hasPermission("labels.manage");

  const runAction = async (action, success) => {
    setErr(""); setMsg("");
    try { await action(); await load(); setMsg(success); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  const setStatus = (status) => runAction(() => api.patch(`/admin/labels/${id}`, { account_status: status }), `Status diubah ke ${status}`);
  const verifyBank = () => runAction(() => api.post(`/withdraw/admin/verify-bank/${id}`), "Rekening diverifikasi.");
  const unblacklist = () => window.confirm("Lepas blacklist label ini?") && runAction(() => api.post(`/admin/labels/${id}/unblacklist`), "Blacklist dilepas. Label dapat login kembali.");

  const setRoyaltyPct = async () => {
    setErr(""); setMsg(""); setRoyaltySaving(true);
    try {
      const response = await api.patch(`/admin/labels/${id}`, { royalty_percentage_default: Number(royalty), royalty_change_reason: reason });
      const jobId = response.data.royalty_recalculation_job_id;
      await load();
      if (!jobId) { setMsg("Persentase royalti tersimpan; tidak ada nilai yang perlu dihitung ulang."); return; }
      setMsg("Persentase tersimpan. Royalti belum ditarik sedang dihitung ulang.");
      for (let attempt = 0; attempt < 180; attempt += 1) {
        await wait(2000);
        const jobResponse = await api.get(`/admin/migrate/jobs/${jobId}`);
        setRecalcJob(jobResponse.data);
        if (jobResponse.data.status === "done") {
          setMsg(`Hitung ulang selesai: ${(jobResponse.data.result?.lines_recalculated || 0).toLocaleString("id-ID")} baris diperbarui.`);
          await load(); break;
        }
        if (jobResponse.data.status === "error") { setErr(jobResponse.data.error_message || "Hitung ulang royalti gagal."); break; }
      }
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
    finally { setRoyaltySaving(false); }
  };

  const blacklist = async (event) => {
    event.preventDefault();
    await runAction(() => api.post(`/admin/labels/${id}/blacklist`, { reason: blacklistReason }), "Label di-blacklist. Login akan ditolak.");
    setBlacklistOpen(false); setBlacklistReason("");
  };

  const revokeAccount = async (event) => {
    event.preventDefault(); setErr(""); setMsg("");
    try {
      const form = new FormData(); form.append("cascade_artists", String(revokeCascade)); form.append("reason", revokeReason);
      const response = await api.post(`/admin/labels/${id}/revoke-account`, form);
      setRevokeOpen(false); setRevokeReason(""); setRevokeCascade(false); await load();
      setMsg(`Akses akun ${response.data.revoked_email || ""} dicabut. ${response.data.artists_disabled || 0} artist sub-account dinonaktifkan.`);
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  const changeEmail = async (event) => {
    event.preventDefault(); setErr(""); setMsg("");
    try {
      const form = new FormData(); form.append("new_email", newEmail.trim().toLowerCase()); form.append("notify", String(emailNotify));
      const response = await api.post(`/admin/labels/${id}/change-email`, form);
      setEmailOpen(false); setNewEmail(""); await load();
      setMsg(`Email diubah dari ${response.data.old_email} → ${response.data.new_email}. Sesi login lama terputus.`);
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const label = data.label;
  const isBlacklisted = label.account_status === "blacklisted";
  const permissions = { canFinance, canRate, canBlacklist, isBlacklisted, canPackage: hasPermission("labels.package"), canAccounts: hasPermission("labels.accounts") };
  const actions = { setStatus, unblacklist, verifyBank, openBlacklist: () => setBlacklistOpen(true), openEmail: () => setEmailOpen(true), openRevoke: () => setRevokeOpen(true) };
  const royaltyState = { royalty, setRoyalty, reason, setReason, save: setRoyaltyPct, saving: royaltySaving, recalcJob };
  const modals = {
    revoke: { open: revokeOpen, close: () => setRevokeOpen(false), submit: revokeAccount, reason: revokeReason, setReason: setRevokeReason, cascade: revokeCascade, setCascade: setRevokeCascade },
    email: { open: emailOpen, close: () => setEmailOpen(false), submit: changeEmail, value: newEmail, setValue: setNewEmail, notify: emailNotify, setNotify: setEmailNotify },
    blacklist: { open: blacklistOpen, close: () => setBlacklistOpen(false), submit: blacklist, reason: blacklistReason, setReason: setBlacklistReason },
  };

  return <div className="space-y-5">
    <Link to="/admin/labels" className="text-sm text-zinc-400 hover:rm-gradient-text">← Label Management</Link>
    <div className="flex items-center gap-3 flex-wrap"><h1 className="font-display text-3xl font-extrabold tracking-tighter">{label.label_name}</h1>{isBlacklisted && <span className="rm-badge bg-red-500/20 text-red-300">BLACKLISTED</span>}</div>
    {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}{msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}
    {isBlacklisted && label.blacklist_reason && <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-4 text-sm"><div className="text-xs font-bold uppercase tracking-widest text-red-300 mb-1">Alasan Blacklist</div><div className="text-red-100">{label.blacklist_reason}</div></div>}
    <LabelDetailCards data={data} permissions={permissions} actions={actions} royaltyState={royaltyState} onChanged={load} />
    {hasPermission("royalty.manage") && <RoyaltyAdjustmentPanel label={label} onChanged={load} />}
    {canFinance && <section className="border-y border-white/10 py-5" data-testid="admin-label-balance-adjustment-section"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-display text-lg font-bold">Kesesuaian Saldo Royalti</h2><p className="mt-1 text-sm text-zinc-400">Preview perhitungan ulang setelah cutoff tanpa menyentuh withdrawal web.</p></div><button type="button" className={balanceAuditOpen ? "rm-btn-primary inline-flex items-center gap-2" : "rm-btn-ghost inline-flex items-center gap-2"} onClick={() => setBalanceAuditOpen((value) => !value)} data-testid="admin-label-balance-audit-toggle"><Scale className="h-4 w-4" /> {balanceAuditOpen ? "Tutup Penyesuaian" : "Audit & Sesuaikan Saldo"}</button></div>{balanceAuditOpen && <div className="mt-5" data-testid="admin-label-balance-audit-content"><BalanceAuditPanel label={label} onComplete={load} /></div>}</section>}
    <BankChangePanel labelId={id} bank={data.bank_account} canFinance={canFinance} onChanged={load} />
    <LabelDetailModals data={data} modals={modals} />
  </div>;
}