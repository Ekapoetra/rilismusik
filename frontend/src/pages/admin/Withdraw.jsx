import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError, fileUrl } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { Banknote, CheckCircle, XCircle, UploadCloud, History, Scale, PenLine, Pencil } from "lucide-react";
import WithdrawImportPanel from "./WithdrawImportPanel";
import BalanceAuditPanel from "./BalanceAuditPanel";
import { ManualLegacyWithdrawPanel } from "@/components/admin/ManualLegacyWithdrawPanel";
import { LegacyWithdrawEditDialog } from "@/components/admin/LegacyWithdrawEditDialog";
import { FinancialPeriodOverview, jakartaPeriod, monthLabel } from "@/components/admin/FinancialPeriodOverview";

function fmtIDR(n) { return new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0); }
function fmtAmount(w) { return fmtIDR(w.amount_idr); }

const STATUS_PILL = {
  requested: "bg-amber-500/15 text-amber-300",
  approved: "bg-sky-500/15 text-sky-300",
  rejected: "bg-red-500/15 text-red-300",
  paid: "bg-emerald-500/15 text-emerald-300",
};

export default function AdminWithdraw() {
  const { user: me } = useAuth();
  const [items, setItems] = useState([]);
  const [importOpen, setImportOpen] = useState(false);
  const [auditOpen, setAuditOpen] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [status, setStatus] = useState("");
  const [window, setWindow] = useState(null);
  const [open, setOpen] = useState(null); // selected wd for action
  const [action, setAction] = useState("");
  const [form, setForm] = useState({ note: "", payment_reference: "", payment_proof_url: "" });
  const [busy, setBusy] = useState(false);
  const [legacyEdit, setLegacyEdit] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [reportPeriod, setReportPeriod] = useState(jakartaPeriod);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [listResponse, summaryResponse] = await Promise.all([
        api.get("/withdraw/admin", { params: { status: status || undefined, ...reportPeriod } }),
        api.get("/withdraw/admin/summary", { params: reportPeriod }),
      ]);
      setItems(listResponse.data); setSummary(summaryResponse.data);
    } catch (error) { setErr(formatApiError(error.response?.data?.detail)); }
    finally { setLoading(false); }
  }, [status, reportPeriod]);
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

      {summary && <FinancialPeriodOverview
        title="Arus Dana Withdrawal"
        description={`Pengajuan dan pencairan pada ${monthLabel(reportPeriod.month, reportPeriod.year)}.`}
        year={reportPeriod.year} month={reportPeriod.month} years={summary.available_years}
        onYearChange={(year) => setReportPeriod((current) => ({ ...current, year }))}
        onMonthChange={(month) => setReportPeriod((current) => ({ ...current, month }))}
        metrics={[
          { key: "outgoing", label: "Dana Keluar", amount: summary.outgoing.amount_idr, count: summary.outgoing.count, yearAmount: summary.year_total.outgoing_idr, colorClass: "text-rose-300", barClass: "bg-rose-400" },
          { key: "pending", label: "Dana Tertunda", amount: summary.pending.amount_idr, count: summary.pending.count, yearAmount: summary.year_total.pending_idr, colorClass: "text-amber-300", barClass: "bg-amber-400" },
        ]}
        monthly={summary.monthly.map((row) => ({ ...row, outgoing: row.outgoing_idr, pending: row.pending_idr }))}
        testIdPrefix="admin-withdraw-cashflow"
      />}

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
        {loading && <div className="text-xs text-zinc-400" role="status" data-testid="admin-withdraw-period-loading">Memuat periode…</div>}
        {["super_admin", "admin_finance"].includes(me?.role) && <button className="rm-btn-ghost text-sm flex items-center gap-2 ml-auto" onClick={() => { setAuditOpen((value) => !value); setImportOpen(false); setManualOpen(false); }} data-testid="admin-balance-audit-toggle"><Scale className="w-4 h-4" /> {auditOpen ? "Tutup Audit Saldo" : "Audit Saldo Label"}</button>}
        {["super_admin", "admin_finance"].includes(me?.role) && <button className="rm-btn-ghost text-sm flex items-center gap-2" onClick={() => { setManualOpen((value) => !value); setAuditOpen(false); setImportOpen(false); }} data-testid="admin-manual-legacy-withdraw-toggle"><PenLine className="w-4 h-4" /> {manualOpen ? "Tutup Input Manual" : "Tambah Riwayat Manual"}</button>}
        {me?.role === "super_admin" && (
          <button
            className="rm-btn-ghost text-sm flex items-center gap-2"
            onClick={() => { setImportOpen((s) => !s); setAuditOpen(false); setManualOpen(false); }}
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

      {manualOpen && ["super_admin", "admin_finance"].includes(me?.role) && (
        <div className="rm-card p-5"><h3 className="font-display font-bold text-lg tracking-tight mb-4">Tambah Riwayat Withdraw Legacy</h3><ManualLegacyWithdrawPanel onComplete={load} /></div>
      )}

      <div className="rm-card overflow-hidden" aria-busy={loading}>
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Jumlah</div>
          <div className="col-span-3">Rekening</div>
          <div className="col-span-2">Tanggal Request</div>
          <div className="col-span-1">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? <div className="p-10 text-center text-zinc-500 text-sm" data-testid="admin-withdraw-empty">{loading ? "Memuat withdrawal…" : "Belum ada withdraw."}</div> : items.map((w) => (
          <div key={w.id} className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0" data-testid={`admin-withdraw-row-${w.id}`}>
            <div className="col-span-12 md:col-span-3 flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-amber-500/15 text-amber-300 grid place-items-center"><Banknote className="w-4 h-4" /></div>
              <div className="min-w-0">
                <div className="font-semibold text-sm truncate" data-testid={`admin-withdraw-label-${w.id}`}>{w.label_name || w.label_id}</div>
              </div>
            </div>
            <div className="col-span-6 md:col-span-2 font-display font-extrabold tracking-tight" data-testid={`admin-withdraw-amount-${w.id}`}>{fmtAmount(w)}{w.legacy_import && <span className="ml-1.5 px-1.5 py-0.5 rounded text-[9px] font-bold bg-violet-500/15 text-violet-300 align-middle" data-testid={`admin-withdraw-legacy-badge-${w.id}`}>LEGACY</span>}</div>
            <div className="col-span-6 md:col-span-3 text-xs">{w.bank_snapshot?.bank_name || "—"}<br/><span className="text-zinc-500">{w.bank_snapshot?.account_number} • {w.bank_snapshot?.account_holder_name}</span></div>
            <div className="col-span-6 md:col-span-2 text-xs"><div>{w.request_date?.slice(0, 10) || "—"}</div>{w.paid_date && <div className="text-zinc-500">Cair {w.paid_date.slice(0, 10)}</div>}{w.legacy_import && (w.period_from || w.period_to) && <div className="text-violet-300 mt-1" data-testid={`admin-withdraw-period-${w.id}`}>{w.period_from || "…"} → {w.period_to || "…"}</div>}</div>
            <div className="col-span-6 md:col-span-1"><span data-testid={`admin-withdraw-status-${w.id}`} className={`px-2 py-1 rounded-full text-[10px] font-bold capitalize ${STATUS_PILL[w.status] || "bg-white/[0.06] text-zinc-400"}`}>{w.status}</span></div>
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
              {w.legacy_editable && ["super_admin", "admin_finance"].includes(me?.role) && <button type="button" title="Edit bulan laporan legacy" className="rounded-md p-1.5 text-violet-300 transition-colors hover:bg-violet-500/15" onClick={() => setLegacyEdit(w)} data-testid={`admin-withdraw-legacy-edit-${w.id}`}><Pencil className="h-4 w-4" /></button>}
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
      <LegacyWithdrawEditDialog withdrawal={legacyEdit} onClose={() => setLegacyEdit(null)} onComplete={async (result) => { setMsg(`Bulan laporan legacy diperbarui ke ${result.new_period_to}. Saldo tersedia kini ${fmtIDR(result.balance_available_idr)}.`); await load(); }} />
    </div>
  );
}
