import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Landmark, Pencil, ShieldCheck } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { BANK_ACCOUNT } from "@/constants/testIds";

const EMPTY = { bank_name: "", account_number: "", account_holder_name: "", reason: "" };
const PENDING = ["pending_admin_approval", "pending_label_approval"];

const BankRow = ({ label, value }) => (
  <div className="flex justify-between gap-4 border-b border-white/5 py-2 text-sm last:border-0">
    <span className="text-zinc-500">{label}</span><span className="text-right font-semibold">{value || "—"}</span>
  </div>
);

export const BankAccountPanel = () => {
  const [bank, setBank] = useState(null);
  const [requests, setRequests] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    const [bankResponse, requestResponse] = await Promise.all([
      api.get("/label/bank-account"), api.get("/label/bank-account/change-requests"),
    ]);
    setBank(bankResponse.data);
    setRequests(requestResponse.data || []);
  }, []);

  useEffect(() => { load().catch((err) => setError(formatApiError(err.response?.data?.detail))); }, [load]);
  const pending = useMemo(() => requests.find((item) => PENDING.includes(item.status)), [requests]);

  const openForm = () => {
    setForm({
      bank_name: bank?.bank_name || "",
      account_number: bank?.account_number || "",
      account_holder_name: bank?.account_holder_name || "",
      reason: "",
    });
    setEditing(true); setError(""); setMessage("");
  };

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(""); setMessage("");
    try {
      if (bank) {
        await api.post("/label/bank-account/change-request", form);
        setMessage("Permintaan perubahan dikirim. Rekening lama tetap aktif sampai disetujui admin.");
      } else {
        await api.post("/label/bank-account", form);
        setMessage("Rekening disimpan dan menunggu verifikasi admin.");
      }
      setEditing(false); await load();
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const review = async (action) => {
    setBusy(true); setError(""); setMessage("");
    try {
      await api.post(`/label/bank-account/change-requests/${pending.id}/action`, { action });
      setMessage(action === "approve" ? "Perubahan rekening admin telah Anda setujui." : "Perubahan rekening admin telah ditolak.");
      await load();
    } catch (err) { setError(formatApiError(err.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <section className="rm-card p-6 space-y-4" data-testid={BANK_ACCOUNT.panel}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-display font-bold text-lg"><Landmark className="w-5 h-5" /> Rekening Bank</div>
        {bank && !pending && !editing && <button type="button" className="rm-btn-ghost text-sm flex items-center gap-2" onClick={openForm} data-testid={BANK_ACCOUNT.changeButton}><Pencil className="w-4 h-4" /> Ajukan Perubahan</button>}
      </div>
      {error && <div role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-300" data-testid="bank-account-error-alert">{error}</div>}
      {message && <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300" data-testid="bank-account-success-alert">{message}</div>}

      {bank && !editing && <div><BankRow label="Nama Bank" value={bank.bank_name} /><BankRow label="Nomor Rekening" value={bank.account_number} /><BankRow label="Atas Nama" value={bank.account_holder_name} /><BankRow label="Status Verifikasi" value={bank.verified_status} /></div>}

      {pending && !editing && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/[0.06] p-4" data-testid={`bank-account-request-${pending.id}`}>
          <div className="flex items-center gap-2 text-sm font-bold text-amber-200"><ShieldCheck className="w-4 h-4" /> {pending.status === "pending_label_approval" ? "Persetujuan Anda diperlukan" : "Menunggu persetujuan admin"}</div>
          <div className="mt-3"><BankRow label="Bank baru" value={pending.proposed_bank?.bank_name} /><BankRow label="Nomor baru" value={pending.proposed_bank?.account_number} /><BankRow label="Atas nama" value={pending.proposed_bank?.account_holder_name} /></div>
          {pending.status === "pending_label_approval" && <div className="mt-4 flex gap-2"><button className="rm-btn-primary text-sm" disabled={busy} onClick={() => review("approve")} data-testid={BANK_ACCOUNT.approveButton}>Setujui</button><button className="rm-btn-ghost text-sm text-red-300" disabled={busy} onClick={() => review("reject")} data-testid={BANK_ACCOUNT.rejectButton}>Tolak</button></div>}
        </div>
      )}

      {(!bank || editing) && (
        <form className="grid gap-3 md:grid-cols-2" onSubmit={submit}>
          <Field label="Nama Bank"><input className="rm-input" value={form.bank_name} onChange={(event) => setForm({ ...form, bank_name: event.target.value })} required data-testid={BANK_ACCOUNT.bankNameInput} /></Field>
          <Field label="Nomor Rekening"><input className="rm-input" value={form.account_number} onChange={(event) => setForm({ ...form, account_number: event.target.value })} required data-testid={BANK_ACCOUNT.accountNumberInput} /></Field>
          <Field label="Atas Nama"><input className="rm-input" value={form.account_holder_name} onChange={(event) => setForm({ ...form, account_holder_name: event.target.value })} required data-testid={BANK_ACCOUNT.holderInput} /></Field>
          {bank && <Field label="Alasan Perubahan"><input className="rm-input" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} data-testid={BANK_ACCOUNT.reasonInput} /></Field>}
          <div className="md:col-span-2 flex justify-end gap-2">{editing && <button type="button" className="rm-btn-ghost" onClick={() => setEditing(false)} data-testid="bank-account-cancel-button">Batal</button>}<button className="rm-btn-primary" disabled={busy} data-testid={BANK_ACCOUNT.submitButton}>{busy ? "Menyimpan…" : bank ? "Kirim Permintaan" : "Submit Rekening"}</button></div>
        </form>
      )}
    </section>
  );
};

const Field = ({ label, children }) => <div><label className="rm-label">{label}</label>{children}</div>;