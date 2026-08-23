import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, formatApiError } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { LabelDetailCards, LabelDetailModals } from "@/components/admin/LabelDetailView";

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

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

  const load = useCallback(async () => {
    const response = await api.get(`/admin/labels/${id}`);
    const label = response.data.label;
    setData(response.data);
    setRoyalty(String(label.royalty_percentage_default ?? 60));
    setSubTier(label.payment_type === "annual_subscription" ? (label.subscription_tier || "annual_normal") : "pay_per_release");
    setSubExpiry(label.subscription_expires_at?.slice(0, 10) || "");
  }, [id]);

  useEffect(() => { load().catch((error) => setErr(formatApiError(error.response?.data?.detail))); }, [load]);
  const canFinance = user?.role === "super_admin" || user?.role === "admin_finance";
  const canBlacklist = user?.role === "super_admin";

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

  const saveSubscription = async () => {
    if (subTier !== "pay_per_release" && !subExpiry) { setErr("Isi tanggal masa berlaku untuk paket tahunan."); return; }
    setSubSaving(true);
    const payload = subTier === "pay_per_release" ? { payment_type: "pay_per_release" } : { subscription_tier: subTier, subscription_expires_at: subExpiry };
    await runAction(() => api.patch(`/admin/labels/${id}`, payload), "Paket langganan diperbarui.");
    setSubSaving(false);
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
  const permissions = { canFinance, canBlacklist, isBlacklisted };
  const actions = { setStatus, unblacklist, verifyBank, openBlacklist: () => setBlacklistOpen(true), openEmail: () => setEmailOpen(true), openRevoke: () => setRevokeOpen(true) };
  const royaltyState = { royalty, setRoyalty, reason, setReason, save: setRoyaltyPct, saving: royaltySaving, recalcJob };
  const subscriptionState = { tier: subTier, setTier: setSubTier, expiry: subExpiry, setExpiry: setSubExpiry, save: saveSubscription, saving: subSaving };
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
    <LabelDetailCards data={data} permissions={permissions} actions={actions} royaltyState={royaltyState} subscriptionState={subscriptionState} />
    <LabelDetailModals data={data} modals={modals} />
  </div>;
}