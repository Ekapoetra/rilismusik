import React, { useEffect, useState } from "react";
import { api, formatApiError, fileUrl } from "@/api/client";
import { Banknote, CheckCircle, XCircle, UploadCloud } from "lucide-react";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }

const STATUS_PILL = {
  requested: "bg-amber-50 text-amber-700",
  approved: "bg-sky-50 text-sky-700",
  rejected: "bg-red-50 text-red-700",
  paid: "bg-emerald-50 text-emerald-700",
};

export default function AdminWithdraw() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("");
  const [window, setWindow] = useState(null);
  const [open, setOpen] = useState(null); // selected wd for action
  const [action, setAction] = useState("");
  const [form, setForm] = useState({ note: "", payment_reference: "", payment_proof_url: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    const { data } = await api.get("/withdraw/admin", { params: { status: status || undefined } });
    setItems(data);
  };
  useEffect(() => { load(); api.get("/withdraw/window").then(r => setWindow(r.data)); /* eslint-disable-next-line */ }, [status]);

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
        <div className="text-xs uppercase tracking-widest text-slate-500 font-bold">Finance</div>
        <h1 className="font-display text-3xl font-extrabold tracking-tighter">Withdraw Management</h1>
        {window && <p className="text-sm text-slate-600 mt-1">Hari ke-{window.day} (Asia/Jakarta) — {window.message}</p>}
      </div>

      {err && <div className="rounded-2xl bg-red-50 text-red-700 px-4 py-3 text-sm">{err}</div>}
      {msg && <div className="rounded-2xl bg-emerald-50 text-emerald-700 px-4 py-3 text-sm">{msg}</div>}

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
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-slate-500 bg-slate-50/60 border-b border-slate-100">
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Jumlah</div>
          <div className="col-span-3">Rekening</div>
          <div className="col-span-2">Tanggal Request</div>
          <div className="col-span-1">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-10 text-center text-slate-500 text-sm">Belum ada withdraw.</div> : items.map((w) => (
          <div key={w.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-slate-50 last:border-0">
            <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 grid place-items-center"><Banknote className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-semibold text-sm truncate">{w.label_name || w.label_id}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-2 font-display font-extrabold tracking-tight">{fmtIDR(w.amount_idr)}</div>
            <div className="col-span-6 md:col-span-3 text-xs">{w.bank_snapshot?.bank_name || "—"}<br/><span className="text-slate-500">{w.bank_snapshot?.account_number} • {w.bank_snapshot?.account_holder_name}</span></div>
            <div className="col-span-6 md:col-span-2 text-xs">{w.request_date?.slice(0, 10)}</div>
            <div className="col-span-6 md:col-span-1"><span className={`px-2 py-1 rounded-full text-[10px] font-bold capitalize ${STATUS_PILL[w.status] || "bg-slate-100 text-slate-600"}`}>{w.status}</span></div>
            <div className="col-span-12 md:col-span-1 text-right">
              {w.status === "requested" && (
                <div className="flex gap-1 justify-end">
                  <button title="Approve" className="text-emerald-600 hover:bg-emerald-50 rounded-lg p-1.5" onClick={() => { setOpen(w); setAction("approve"); }} data-testid={`admin-withdraw-approve-${w.id}`}><CheckCircle className="w-4 h-4" /></button>
                  <button title="Reject" className="text-red-600 hover:bg-red-50 rounded-lg p-1.5" onClick={() => { setOpen(w); setAction("reject"); }} data-testid={`admin-withdraw-reject-${w.id}`}><XCircle className="w-4 h-4" /></button>
                </div>
              )}
              {w.status === "approved" && (
                <button className="rm-btn-primary text-xs" onClick={() => { setOpen(w); setAction("mark_paid"); }} data-testid={`admin-withdraw-pay-${w.id}`}>Mark Paid</button>
              )}
              {w.status === "paid" && w.payment_proof_url && <a href={fileUrl(w.payment_proof_url)} target="_blank" rel="noreferrer" className="text-xs text-[#FF3B30] font-semibold">Bukti →</a>}
            </div>
          </div>
        ))}
      </div>

      {open && action && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4" onClick={() => setOpen(null)}>
          <div onClick={(e) => e.stopPropagation()} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <h3 className="font-display font-extrabold text-xl tracking-tighter capitalize">{action.replace("_", " ")} Withdraw</h3>
            <div className="text-sm text-slate-600">{open.label_name} • {fmtIDR(open.amount_idr)}</div>
            {action === "mark_paid" && (
              <>
                <div>
                  <label className="rm-label">Bukti Pembayaran (PDF/JPG/PNG)</label>
                  <label className="rm-btn-ghost cursor-pointer flex items-center gap-2 w-fit">
                    <UploadCloud className="w-4 h-4" /> {form.payment_proof_url ? "Ganti file" : "Upload bukti"}
                    <input type="file" accept=".jpg,.jpeg,.png,.pdf" hidden onChange={(e) => uploadProof(e.target.files?.[0])} data-testid="admin-withdraw-proof-upload" />
                  </label>
                  {form.payment_proof_url && <div className="text-xs text-emerald-700 mt-1">✓ {form.payment_proof_url.split("/").pop()}</div>}
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
