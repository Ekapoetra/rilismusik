import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError, fileUrl } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { Banknote, CheckCircle, XCircle, UploadCloud, History, Scale } from "lucide-react";
import WithdrawImportPanel from "./WithdrawImportPanel";
import BalanceAuditPanel from "./BalanceAuditPanel";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtAmount(w) { return fmtIDR(w.amount_idr); }

const STATUS_PILL = {
  requested: "bg-amber-500/100/15 text-amber-300",
  approved: "bg-sky-500/15 text-sky-300",
  rejected: "bg-red-500/15 text-red-300",
  paid: "bg-emerald-500/15 text-emerald-300",
};

export default function AdminWithdraw() {
  const { user: me } = useAuth();
  const [items, setItems] = useState([]);
  const [importOpen, setImportOpen] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
  const [status, setStatus] = useState("");
  const [window, setWindow] = useState(null);
  const [open, setOpen] = useState(null); // selected wd for action
  const [action, setAction] = useState("");
  const [form, setForm] = useState({ note: "", payment_reference: "", payment_proof_url: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const { data } = await api.get("/withdraw/admin", { params: { status: status || undefined } });
    setItems(data);
  }, [status]);
  useEffect(() => { load(); api.get("/withdraw/window").then(r => setWindow(r.data)); }, [load]);

  const submitAction = async () => {
    setBusy(true); setErr(""); setMsg("");
    try {
      await api.post(`/withdraw/admin/${open.id}/action`, { action, ...form });
      setMsg(`Aksi ${action} berhasil.`);
      setOpen(null); setAction(""); setForm({ note: "", payment_reference: "", payment_proof_url: "" });
      load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const uploadProof = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await api.post("/withdraw/admin/upload-proof", fd, { headers: { "Content-Type": "multipart/form-data" } });
    setForm((f) => ({ ...f, payment_proof_url: data.url }));
  };

  return (
    <div className="space-y-5">
      <div>
        <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Finance</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Withdraw Management</h1>
        {window && <p className="text-sm text-zinc-400 mt-1">Hari ke-{window.day} (Asia/Jakarta) — {window.message}</p>}
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm" data-testid="admin-withdraw-error">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm" data-testid="admin-withdraw-message">{msg}</div>}

      <div className="rm-card p-4 flex flex-wrap gap-3 items-end">
        <div className="min-w-[200px]">
          <label className="rm-label">Status</label>
          <select className="rm-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="admin-withdraw-status-filter">
            <option value="">Semua</option>
            <option value="requested">Requested</option>
            <option value="approved">Approved</option>
            <option value="paid">Paid</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
        {["super_admin", "admin_finance"].includes(me?.role) && <button className="rm-btn-ghost text-sm flex items-center gap-2 ml-auto" onClick={() => { setAuditOpen((value) => !value); setImportOpen(false); }} data-testid="admin-balance-audit-toggle"><Scale className="w-4 h-4" /> {auditOpen ? "Tutup Audit Saldo" : "Audit Saldo Label"}</button>}
        {me?.role === "super_admin" && (
          <button
            className="rm-btn-ghost text-sm flex items-center gap-2"
            onClick={() => { setImportOpen((s) => !s); setAuditOpen(false); }}
            data-testid="admin-withdraw-import-toggle"
          >
            <History className="w-4 h-4" /> {importOpen ? "Tutup Import Riwayat" : "Import Riwayat Penarikan (CSV)"}
          </button>
        )}
      </div>

      {importOpen && me?.role === "super_admin" && (
        <div className="rm-card p-5">
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Import Riwayat Penarikan</h3>
          <WithdrawImportPanel />
        </div>
      )}

      {auditOpen && ["super_admin", "admin_finance"].includes(me?.role) && (
        <div className="rm-card p-5"><BalanceAuditPanel /></div>
      )}

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Jumlah</div>
          <div className="col-span-3">Rekening</div>
          <div className="col-span-2">Tanggal Request</div>
          <div className="col-span-1">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-10 text-center text-zinc-500 text-sm">Belum ada withdraw.</div> : items.map((w) => (
          <div key={w.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0">
            <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-amber-500/100/15 text-amber-300 grid place-items-center"><Banknote className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-semibold text-sm truncate">{w.label_name || w.label_id}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-2 font-display font-extrabold tracking-tight">{fmtAmount(w)}{w.legacy_import && <span className="ml-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-violet-500/15 text-violet-300 align-middle">LEGACY</span>}</div>
            <div className="col-span-6 md:col-span-3 text-xs">{w.bank_snapshot?.bank_name || "—"}<br/><span className="text-zinc-500">{w.bank_snapshot?.account_number} • {w.bank_snapshot?.account_holder_name}</span></div>
            <div className="col-span-6 md:col-span-2 text-xs">{w.request_date?.slice(0, 10)}</div>
            <div className="col-span-6 md:col-span-1"><span className={`px-2 py-1 rounded-full text-[10px] font-bold capitalize ${STATUS_PILL[w.status] || "bg-white/[0.06] text-zinc-400"}`}>{w.status}</span></div>
            <div className="col-span-12 md:col-span-1 text-right">
              {w.status === "requested" && (
                <div className="flex gap-1 justify-end">
                  <button title="Approve" className="text-emerald-300 hover:bg-emerald-50 rounded-lg p-1.5" onClick={() => { setOpen(w); setAction("approve"); }} data-testid={`admin-withdraw-approve-${w.id}`}><CheckCircle className="w-4 h-4" /></button>
                  <button title="Reject" className="text-red-600 hover:bg-red-50 rounded-lg p-1.5" onClick={() => { setOpen(w); setAction("reject"); }} data-testid={`admin-withdraw-reject-${w.id}`}><XCircle className="w-4 h-4" /></button>
                </div>
              )}
              {w.status === "approved" && (
                <button className="rm-btn-primary text-xs" onClick={() => { setOpen(w); setAction("mark_paid"); }} data-testid={`admin-withdraw-pay-${w.id}`}>Mark Paid</button>
              )}
              {w.status === "paid" && w.payment_proof_url && <a href={fileUrl(w.payment_proof_url)} target="_blank" rel="noreferrer" className="text-xs rm-gradient-text font-semibold">Bukti →</a>}
            </div>
          </div>
        ))}
      </div>

      {open && action && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4" onClick={() => setOpen(null)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <h3 className="font-display font-extrabold text-xl tracking-tighter capitalize">{action.replace("_", " ")} Withdraw</h3>
            <div className="text-sm text-zinc-400">{open.label_name} • {fmtAmount(open)}</div>
            {action === "mark_paid" && (
              <>
                <div>
                  <label className="rm-label">Bukti Pembayaran (PDF/JPG/PNG)</label>
                  <label className="rm-btn-ghost cursor-pointer flex items-center gap-2 w-fit">
                    <UploadCloud className="w-4 h-4" /> {form.payment_proof_url ? "Ganti file" : "Upload bukti"}
                    <input type="file" accept=".jpg,.jpeg,.png,.pdf" hidden onChange={(e) => uploadProof(e.target.files?.[0])} data-testid="admin-withdraw-proof-upload" />
                  </label>
                  {form.payment_proof_url && <div className="text-xs text-emerald-300 mt-1">✓ {form.payment_proof_url.split("/").pop()}</div>}
                </div>
                <div>
                  <label className="rm-label">Referensi Pembayaran</label>
                  <input className="rm-input" value={form.payment_reference} onChange={(e) => setForm({ ...form, payment_reference: e.target.value })} placeholder="TRX-2026-001" data-testid="admin-withdraw-reference" />
                </div>
              </>
            )}
            <div>
              <label className="rm-label">Catatan {action === "reject" && "(alasan reject)"}</label>
              <textarea className="rm-input min-h-[80px]" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} data-testid="admin-withdraw-note" />
            </div>
            <div className="flex justify-end gap-2">
              <button className="rm-btn-ghost" onClick={() => { setOpen(null); setAction(""); }}>Batal</button>
              <button className="rm-btn-primary" disabled={busy} onClick={submitAction} data-testid="admin-withdraw-action-submit">{busy ? "Memproses…" : "Konfirmasi"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
