import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { LabelDetailCards, LabelDetailModals } from "@/components/admin/LabelDetailView";
import { BankChangePanel } from "@/components/admin/BankChangePanel";
import BalanceAuditPanel from "./BalanceAuditPanel";
import { Scale } from "lucide-react";
import { RoyaltyAdjustmentPanel } from "@/components/admin/royalty-adjustments/RoyaltyAdjustmentPanel";
import { RateChangePanel } from "@/components/admin/RateChangePanel";
import { SensitiveRequestsPanel } from "@/components/admin/SensitiveRequestsPanel";
import { celebrateWork } from "@/lib/completionFeedback";

export default function AdminLabelDetail() {
  const { id } = useParams();
  const { hasPermission, user } = useAuth();
  const [data, setData] = useState(null);
  const [blacklistOpen, setBlacklistOpen] = useState(false);
  const [blacklistReason, setBlacklistReason] = useState("");
  const [revokeOpen, setRevokeOpen] = useState(false);
  const [revokeReason, setRevokeReason] = useState("");
  const [revokeCascade, setRevokeCascade] = useState(false);
  const [emailOpen, setEmailOpen] = useState(false);
  const [newEmail, setNewEmail] = useState("");
  const [emailNotify, setEmailNotify] = useState(true);
  const [emailReason, setEmailReason] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [balanceAuditOpen, setBalanceAuditOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    const response = await api.get(`/admin/labels/${id}`);
    setData(response.data);
  }, [id]);

  useEffect(() => { load().catch((error) => setErr(formatApiError(error.response?.data?.detail))); }, [load]);
  const canFinance = hasPermission("labels.bank") || hasPermission("royalty.manage");
  const canRateDirect = hasPermission("labels.rate");
  const canRateRequest = hasPermission("labels.rate.request");
  const canRateApprove = hasPermission("labels.rate.approve");
  const canRateView = hasPermission("labels.rate.request.view");
  const canBlacklist = hasPermission("labels.manage");
  const canBlacklistDirect = hasPermission("labels.blacklist");
  const canBlacklistRequest = hasPermission("labels.blacklist.request");
  const canBlacklistView = hasPermission("labels.blacklist.request.view");
  const canBlacklistApprove = hasPermission("labels.blacklist.approve");
  const canPackageDirect = hasPermission("labels.package");
  const canPackageRequest = hasPermission("labels.package.request");
  const canPackageView = hasPermission("labels.package.request.view");
  const canPackageApprove = hasPermission("labels.package.approve");
  const canAccounts = hasPermission("labels.accounts");
  const canEmailDirect = hasPermission("labels.email");
  const canEmailApprove = hasPermission("labels.email.approve");
  const approvePermission = { blacklist: canBlacklistApprove, package: canPackageApprove, email: canEmailApprove };
  // Email changes need a second admin unless the approver may change emails directly.
  const canApproveRequest = (req) => Boolean(approvePermission[req.action_type])
    && !(req.action_type === "email" && req.requested_by === user?.id && !canEmailDirect);

  const runAction = async (action, success) => {
    setErr(""); setMsg("");
    try { await action(); await load(); setMsg(success); }
    catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  const setStatus = (status) => runAction(() => api.patch(`/admin/labels/${id}`, { account_status: status }), `Status diubah ke ${status}`);
  const verifyBank = () => runAction(async () => { await api.post(`/withdraw/admin/verify-bank/${id}`); celebrateWork("bank_verification"); }, "Rekening diverifikasi.");
  const unblacklist = () => {
    if (canBlacklistDirect) {
      if (window.confirm("Lepas blacklist label ini?")) runAction(() => api.post(`/admin/labels/${id}/unblacklist`), "Blacklist dilepas. Label dapat login kembali.");
    } else {
      const reason = window.prompt("Alasan pengajuan lepas blacklist (opsional):") ?? "";
      runAction(() => api.post(`/admin/labels/${id}/blacklist-request`, { action: "unblacklist", reason }), "Permintaan lepas blacklist dikirim untuk persetujuan Super Admin.");
      setRefreshKey((k) => k + 1);
    }
  };

  const blacklist = async (event) => {
    event.preventDefault();
    if (canBlacklistDirect) {
      await runAction(() => api.post(`/admin/labels/${id}/blacklist`, { reason: blacklistReason }), "Label di-blacklist. Login akan ditolak.");
    } else {
      await runAction(() => api.post(`/admin/labels/${id}/blacklist-request`, { action: "blacklist", reason: blacklistReason }), "Permintaan blacklist dikirim untuk persetujuan Super Admin.");
      setRefreshKey((k) => k + 1);
    }
    setBlacklistOpen(false); setBlacklistReason("");
  };

  const revokeAccount = async (event) => {
    event.preventDefault(); setErr(""); setMsg("");
    try {
      const form = new FormData(); form.append("cascade_artists", String(revokeCascade)); form.append("reason", revokeReason);
      const response = await api.post(`/admin/labels/${id}/revoke-account`, form, { headers: { "Content-Type": "multipart/form-data" } });
      setRevokeOpen(false); setRevokeReason(""); setRevokeCascade(false); await load();
      setMsg(`Akses akun ${response.data.revoked_email || ""} dicabut. ${response.data.artists_disabled || 0} artist sub-account dinonaktifkan.`);
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
  };

  const closeEmail = () => { setEmailOpen(false); setNewEmail(""); setEmailReason(""); };
  const changeEmail = async (event) => {
    event.preventDefault(); setErr(""); setMsg(""); setEmailBusy(true);
    const email = newEmail.trim().toLowerCase();
    const reason = emailReason.trim();
    try {
      if (canEmailDirect) {
        const form = new FormData(); form.append("new_email", email); form.append("notify", String(emailNotify)); form.append("reason", reason);
        const response = await api.post(`/admin/labels/${id}/change-email`, form, { headers: { "Content-Type": "multipart/form-data" } });
        closeEmail(); await load();
        setMsg(`Email diubah dari ${response.data.old_email} → ${response.data.new_email}. Sesi login lama terputus.`);
      } else {
        const response = await api.post(`/admin/labels/${id}/email-change-request`, { new_email: email, notify: emailNotify, reason });
        closeEmail(); setRefreshKey((k) => k + 1);
        setMsg(`Permintaan ganti email ${response.data.reference_id || ""} dikirim. Email berubah setelah disetujui Super Admin atau admin penyetuju.`);
      }
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
    finally { setEmailBusy(false); }
  };

  if (!data) return <div className="text-zinc-500">Memuat…</div>;
  const label = data.label;
  const isBlacklisted = label.account_status === "blacklisted";
  const permissions = { canFinance, canBlacklist, canBlacklistDirect, canBlacklistRequest, isBlacklisted, canPackage: canPackageDirect, canPackageRequest, canAccounts };
  const actions = { setStatus, unblacklist, verifyBank, openBlacklist: () => setBlacklistOpen(true), openEmail: () => setEmailOpen(true), openRevoke: () => setRevokeOpen(true) };
  const modals = {
    revoke: { open: revokeOpen, close: () => setRevokeOpen(false), submit: revokeAccount, reason: revokeReason, setReason: setRevokeReason, cascade: revokeCascade, setCascade: setRevokeCascade },
    email: { open: emailOpen, close: closeEmail, submit: changeEmail, value: newEmail, setValue: setNewEmail, notify: emailNotify, setNotify: setEmailNotify, reason: emailReason, setReason: setEmailReason, direct: canEmailDirect, busy: emailBusy },
    blacklist: { open: blacklistOpen, close: () => setBlacklistOpen(false), submit: blacklist, reason: blacklistReason, setReason: setBlacklistReason },
  };

  return <div className="space-y-5">
    <Link to="/admin/labels" className="text-sm text-zinc-400 hover:rm-gradient-text">← Label Management</Link>
    <div className="flex items-center gap-3 flex-wrap"><h1 className="font-display text-3xl font-extrabold tracking-tighter">{label.label_name}</h1>{isBlacklisted && <span className="rm-badge bg-red-500/20 text-red-300">BLACKLISTED</span>}</div>
    {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm">{err}</div>}{msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm">{msg}</div>}
    {isBlacklisted && label.blacklist_reason && <div className="rounded-2xl bg-red-500/10 border border-red-500/20 p-4 text-sm"><div className="text-xs font-bold uppercase tracking-widest text-red-300 mb-1">Alasan Blacklist</div><div className="text-red-100">{label.blacklist_reason}</div></div>}
    <LabelDetailCards data={data} permissions={permissions} actions={actions} onChanged={load} onPackageChanged={() => { load(); setRefreshKey((k) => k + 1); }} />
    {(canRateDirect || canRateRequest || canRateView || canRateApprove) && <RateChangePanel labelId={id} label={label} perms={{ direct: canRateDirect, request: canRateRequest && !canRateDirect, approve: canRateApprove, view: canRateView }} onChanged={load} />}
    <SensitiveRequestsPanel labelId={id} canView={canBlacklistView || canPackageView || canAccounts || canEmailApprove} canApprove={canApproveRequest} onChanged={load} refreshKey={refreshKey} />
    {hasPermission("royalty.manage") && <RoyaltyAdjustmentPanel label={label} onChanged={load} />}
    {canFinance && <section className="border-y border-white/10 py-5" data-testid="admin-label-balance-adjustment-section"><div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="font-display text-lg font-bold">Kesesuaian Saldo Royalti</h2><p className="mt-1 text-sm text-zinc-400">Preview perhitungan ulang setelah cutoff tanpa menyentuh withdrawal web.</p></div><button type="button" className={balanceAuditOpen ? "rm-btn-primary inline-flex items-center gap-2" : "rm-btn-ghost inline-flex items-center gap-2"} onClick={() => setBalanceAuditOpen((value) => !value)} data-testid="admin-label-balance-audit-toggle"><Scale className="h-4 w-4" /> {balanceAuditOpen ? "Tutup Penyesuaian" : "Audit & Sesuaikan Saldo"}</button></div>{balanceAuditOpen && <div className="mt-5" data-testid="admin-label-balance-audit-content"><BalanceAuditPanel label={label} onComplete={load} /></div>}</section>}
    <BankChangePanel labelId={id} bank={data.bank_account} canFinance={canFinance} onChanged={load} />
    <LabelDetailModals data={data} modals={modals} />
  </div>;
}