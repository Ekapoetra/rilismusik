import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Landmark, ShieldCheck } from "lucide-react";
import { api, formatApiError } from "@/api/client";

const PENDING = ["pending_admin_approval", "pending_label_approval"];
const BankRow = ({ label, value }) => <div className="flex justify-between gap-4 py-1.5 text-sm"><span className="text-zinc-500">{label}</span><span className="text-right font-semibold">{value || "—"}</span></div>;

export const BankChangePanel = ({ labelId, bank, canFinance, onChanged }) => {
  const [requests, setRequests] = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ bank_name: "", account_number: "", account_holder_name: "", reason: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(async () => {
    if (!canFinance) return;
    const { data } = await api.get(`/admin/labels/${labelId}/bank-change-requests`);
    setRequests(data || []);
  }, [canFinance, labelId]);
  useEffect(() => { load().catch((err) => setError(formatApiError(err.response?.data?.detail))); }, [load]);
  const pending = useMemo(() => requests.find((item) => PENDING.includes(item.status)), [requests]);

  if (!canFinance || !bank) return null;
  const begin = () => { setForm({ bank_name: bank.bank_name || "", account_number: bank.account_number || "", account_holder_name: bank.account_holder_name || "", reason: "" }); setEditing(true); };
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try { await api.post(`/admin/labels/${labelId}/bank-change-request`, form); setEditing(false); setMessage("Permintaan dikirim ke label untuk persetujuan."); await load(); }
    catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  const review = async (action) => {
    setBusy(true); setError(""); setMessage("");
    try { await api.post(`/admin/bank-account-change-requests/${pending.id}/action`, { action }); setMessage(action === "approve" ? "Perubahan rekening disetujui." : "Perubahan rekening ditolak."); await load(); await onChanged(); }
    catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return <section className="rm-card p-5 space-y-4" data-testid="admin-bank-change-panel">
    <div className="flex items-center justify-between gap-3"><h3 className="font-display font-bold text-lg flex items-center gap-2"><Landmark className="w-5 h-5" /> Perubahan Rekening</h3>{!pending && !editing && <button className="rm-btn-ghost text-sm" onClick={begin} data-testid="admin-bank-change-open-button">Ajukan ke Label</button>}</div>
    {error && <div role="alert" className="text-sm text-red-300" data-testid="admin-bank-change-error">{error}</div>}{message && <div className="text-sm text-emerald-300" data-testid="admin-bank-change-success">{message}</div>}
    {pending && <div className="rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-4" data-testid={`admin-bank-change-request-${pending.id}`}><div className="flex items-center gap-2 text-sm font-bold text-amber-200"><ShieldCheck className="w-4 h-4" /> {pending.status === "pending_admin_approval" ? "Persetujuan admin diperlukan" : "Menunggu persetujuan label"}</div><div className="mt-2"><BankRow label="Bank baru" value={pending.proposed_bank?.bank_name} /><BankRow label="Nomor baru" value={pending.proposed_bank?.account_number} /><BankRow label="Atas nama" value={pending.proposed_bank?.account_holder_name} /></div>{pending.status === "pending_admin_approval" && <div className="mt-3 flex gap-2"><button className="rm-btn-primary text-sm" disabled={busy} onClick={() => review("approve")} data-testid="admin-bank-change-approve-button">Setujui</button><button className="rm-btn-ghost text-sm text-red-300" disabled={busy} onClick={() => review("reject")} data-testid="admin-bank-change-reject-button">Tolak</button></div>}</div>}
    {editing && <form className="grid md:grid-cols-2 gap-3" onSubmit={submit}><Field label="Nama Bank"><input className="rm-input" value={form.bank_name} onChange={(e) => setForm({ ...form, bank_name: e.target.value })} required data-testid="admin-bank-change-name-input" /></Field><Field label="Nomor Rekening"><input className="rm-input" value={form.account_number} onChange={(e) => setForm({ ...form, account_number: e.target.value })} required data-testid="admin-bank-change-number-input" /></Field><Field label="Atas Nama"><input className="rm-input" value={form.account_holder_name} onChange={(e) => setForm({ ...form, account_holder_name: e.target.value })} required data-testid="admin-bank-change-holder-input" /></Field><Field label="Alasan"><input className="rm-input" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} data-testid="admin-bank-change-reason-input" /></Field><div className="md:col-span-2 flex justify-end gap-2"><button type="button" className="rm-btn-ghost" onClick={() => setEditing(false)} data-testid="admin-bank-change-cancel-button">Batal</button><button className="rm-btn-primary" disabled={busy} data-testid="admin-bank-change-submit-button">Kirim ke Label</button></div></form>}
  </section>;
};

const Field = ({ label, children }) => <div><label className="rm-label">{label}</label>{children}</div>;