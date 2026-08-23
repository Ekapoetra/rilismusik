import React, { useCallback, useEffect, useState } from "react";
import { api, formatApiError, fileUrl } from "@/api/client";
import { FileSignature, Plus, Upload, Download, AlertTriangle, CheckCircle2, X, Calendar, Ban, RefreshCw, ChevronDown } from "lucide-react";

const STATUS_LABELS = {
  active: "Aktif",
  expiring_soon: "Akan Berakhir",
  expired: "Kadaluarsa",
  terminated: "Diakhiri",
};

const STATUS_STYLES = {
  active: { bg: "rgba(16,185,129,0.18)", color: "#6EE7B7", dot: "#10B981" },
  expiring_soon: { bg: "rgba(245,158,11,0.18)", color: "#FCD34D", dot: "#F59E0B" },
  expired: { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", dot: "#EF4444" },
  terminated: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#71717A" },
};

function StatusBadge({ status }) {
  const s = STATUS_STYLES[status] || STATUS_STYLES.active;
  return (
    <span className="rm-badge" style={{ background: s.bg, color: s.color }}>
      <span className="rm-badge-dot" style={{ background: s.dot }} />
      {STATUS_LABELS[status] || status}
    </span>
  );
}

export default function AdminContracts() {
  const [items, setItems] = useState([]);
  const [labels, setLabels] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [open, setOpen] = useState(false);
  const [terminateOpen, setTerminateOpen] = useState(null);  // contract being terminated
  const [extendOpen, setExtendOpen] = useState(null);        // contract being extended
  const [form, setForm] = useState({ label_id: "", start_date: "", end_date: "", notes: "", file_url: "", filename: "" });
  const [terminateReason, setTerminateReason] = useState("");
  const [extendData, setExtendData] = useState({ new_end_date: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    const params = statusFilter ? { status: statusFilter } : {};
    const { data } = await api.get("/contracts/admin", { params });
    setItems(data);
  }, [statusFilter]);
  const loadLabels = useCallback(async () => {
    const { data } = await api.get("/admin/labels");
    setLabels(data);
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadLabels(); }, [loadLabels]);

  const handlePdfUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true); setErr("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/contracts/admin/upload-pdf", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setForm((f) => ({ ...f, file_url: data.url, filename: data.filename }));
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setErr(""); setMsg("");
    if (!form.file_url) { setErr("Upload file PDF terlebih dahulu"); return; }
    setBusy(true);
    try {
      await api.post("/contracts/admin", form);
      setMsg("Kontrak berhasil dibuat.");
      setOpen(false);
      setForm({ label_id: "", start_date: "", end_date: "", notes: "", file_url: "", filename: "" });
      load();
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const submitTerminate = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api.post(`/contracts/admin/${terminateOpen.id}/terminate`, { reason: terminateReason });
      setMsg(`Kontrak ${terminateOpen.label_name} diakhiri.`);
      setTerminateOpen(null);
      setTerminateReason("");
      load();
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const submitExtend = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api.post(`/contracts/admin/${extendOpen.id}/extend`, extendData);
      setMsg(`Kontrak ${extendOpen.label_name} diperpanjang.`);
      setExtendOpen(null);
      setExtendData({ new_end_date: "", notes: "" });
      load();
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="space-y-5 max-w-7xl">
      <div className="flex flex-wrap justify-between items-end gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Legal</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Contracts</h1>
          <p className="text-sm text-zinc-400 mt-1">Kelola kontrak distribusi per label. Sistem otomatis menandai kontrak yang akan berakhir 30 hari ke depan.</p>
        </div>
        <button className="rm-btn-primary flex items-center gap-2" onClick={() => setOpen(true)} data-testid="admin-contract-new-button">
          <Plus className="w-4 h-4" /> Kontrak Baru
        </button>
      </div>

      {msg && <div className="rounded-2xl bg-emerald-500/15 text-emerald-300 px-4 py-3 text-sm flex items-center gap-2"><CheckCircle2 className="w-4 h-4" /> {msg}</div>}

      <div className="flex gap-2 flex-wrap">
        {["", "active", "expiring_soon", "expired", "terminated"].map((s) => (
          <button
            key={s || "all"}
            onClick={() => setStatusFilter(s)}
            className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest ${statusFilter === s ? "text-white" : "rm-glass text-zinc-400"}`}
            style={statusFilter === s ? { background: "linear-gradient(135deg, #FF1F8E, #A24EFF)" } : {}}
            data-testid={`admin-contract-filter-${s || "all"}`}
          >
            {s ? STATUS_LABELS[s] : "Semua"}
          </button>
        ))}
      </div>

      <div className="rm-card overflow-hidden">
        <div className="hidden md:grid grid-cols-12 px-5 py-3 text-[11px] uppercase tracking-widest font-bold text-zinc-500 bg-white/[0.03] border-b border-white/5">
          <div className="col-span-3">Label</div>
          <div className="col-span-2">Mulai</div>
          <div className="col-span-2">Berakhir</div>
          <div className="col-span-2">Sisa Hari</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-1 text-right">Aksi</div>
        </div>
        {items.length === 0 ? (
          <div className="p-10 text-center text-zinc-500 text-sm">
            <FileSignature className="w-8 h-8 mx-auto mb-3 text-zinc-700" />
            Belum ada kontrak. Klik &quot;Kontrak Baru&quot; untuk menambah.
          </div>
        ) : items.map((c) => (
          <div
            key={c.id}
            className="px-5 py-4 grid grid-cols-12 gap-3 items-center border-b border-white/5 last:border-0"
            data-testid={`admin-contract-row-${c.id}`}
          >
            <div className="col-span-12 md:col-span-3">
              <div className="font-semibold text-sm">{c.label_name}</div>
              <div className="text-xs text-zinc-500 truncate">{c.filename}</div>
            </div>
            <div className="col-span-6 md:col-span-2 text-sm">{c.start_date}</div>
            <div className="col-span-6 md:col-span-2 text-sm">{c.end_date}</div>
            <div className="col-span-6 md:col-span-2 text-sm">
              {c.effective_status === "terminated" ? <span className="text-zinc-500">—</span> :
                c.days_left !== null ? (
                  <span className={c.days_left < 0 ? "text-red-300" : c.days_left <= 30 ? "text-amber-300" : "text-zinc-300"}>
                    {c.days_left < 0 ? `${Math.abs(c.days_left)}h lewat` : `${c.days_left} hari`}
                  </span>
                ) : "—"}
            </div>
            <div className="col-span-6 md:col-span-2"><StatusBadge status={c.effective_status} /></div>
            <div className="col-span-12 md:col-span-1 flex justify-end gap-1">
              <a href={fileUrl(c.file_url)} target="_blank" rel="noreferrer" className="rm-btn-ghost p-2" title="Download PDF" data-testid={`admin-contract-download-${c.id}`}>
                <Download className="w-3.5 h-3.5" />
              </a>
              <ActionDropdown
                contract={c}
                onExtend={(con) => { setExtendOpen(con); setExtendData({ new_end_date: con.end_date, notes: "" }); }}
                onTerminate={(con) => { setTerminateOpen(con); setTerminateReason(""); }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* New Contract Modal */}
      {open && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4 overflow-y-auto" onClick={() => setOpen(false)}>
          <form
            onClick={(e) => e.stopPropagation()}
            onSubmit={submit}
            className="w-full max-w-lg rm-glass-strong rounded-[24px] p-6 space-y-4 my-8"
          >
            <div className="flex items-center justify-between">
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Kontrak Baru</h3>
              <button type="button" onClick={() => setOpen(false)} className="p-2 text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            {err && <div className="rounded-xl bg-red-500/15 text-red-300 px-3 py-2 text-sm flex items-center gap-2"><AlertTriangle className="w-4 h-4" /> {err}</div>}

            <div>
              <label className="rm-label">Label</label>
              <select
                className="rm-input"
                value={form.label_id}
                onChange={(e) => setForm({ ...form, label_id: e.target.value })}
                data-testid="admin-contract-label-select"
                required
              >
                <option value="">— Pilih label —</option>
                {labels.map((l) => (<option key={l.id} value={l.id}>{l.label_name}</option>))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="rm-label">Tanggal Mulai</label>
                <input type="date" className="rm-input" value={form.start_date} onChange={(e) => setForm({ ...form, start_date: e.target.value })} data-testid="admin-contract-start-date" required />
              </div>
              <div>
                <label className="rm-label">Tanggal Berakhir</label>
                <input type="date" className="rm-input" value={form.end_date} onChange={(e) => setForm({ ...form, end_date: e.target.value })} data-testid="admin-contract-end-date" required />
              </div>
            </div>

            <div>
              <label className="rm-label">Upload Kontrak (PDF)</label>
              <div className="flex items-center gap-3">
                <label className="rm-btn-ghost cursor-pointer flex items-center gap-2 text-sm">
                  <Upload className="w-4 h-4" /> Pilih PDF
                  <input type="file" className="hidden" accept=".pdf" onChange={handlePdfUpload} data-testid="admin-contract-pdf-input" />
                </label>
                {form.file_url && (
                  <span className="text-xs text-emerald-300 flex items-center gap-1 truncate"><CheckCircle2 className="w-3 h-3" /> {form.filename}</span>
                )}
              </div>
              <div className="text-[11px] text-zinc-500 mt-1">Hanya PDF.</div>
            </div>

            <div>
              <label className="rm-label">Catatan (opsional)</label>
              <textarea className="rm-input min-h-[70px]" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>

            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
              <button className="rm-btn-primary" disabled={busy} data-testid="admin-contract-submit">{busy ? "Menyimpan…" : "Simpan Kontrak"}</button>
            </div>
          </form>
        </div>
      )}

      {/* Terminate Modal */}
      {terminateOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setTerminateOpen(null)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submitTerminate} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4 border border-red-500/30">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-500/20 text-red-300 grid place-items-center"><Ban className="w-5 h-5" /></div>
              <h3 className="font-display font-extrabold text-xl tracking-tighter text-red-200">Akhiri Kontrak</h3>
            </div>
            <div className="text-sm text-zinc-300">Akhiri kontrak <b>{terminateOpen.label_name}</b>? Tindakan ini tidak bisa dibatalkan.</div>
            <div>
              <label className="rm-label">Alasan</label>
              <textarea className="rm-input min-h-[80px]" value={terminateReason} onChange={(e) => setTerminateReason(e.target.value)} data-testid="admin-contract-terminate-reason" required minLength={3} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setTerminateOpen(null)}>Batal</button>
              <button className="rm-btn-primary bg-gradient-to-r from-red-500 to-rose-600" disabled={busy} data-testid="admin-contract-terminate-submit">{busy ? "..." : "Akhiri Kontrak"}</button>
            </div>
          </form>
        </div>
      )}

      {/* Extend Modal */}
      {extendOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 grid place-items-center p-4" onClick={() => setExtendOpen(null)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submitExtend} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-300 grid place-items-center"><RefreshCw className="w-5 h-5" /></div>
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Perpanjang Kontrak</h3>
            </div>
            <div className="text-sm text-zinc-300">Perpanjang kontrak <b>{extendOpen.label_name}</b> (saat ini berakhir {extendOpen.end_date}).</div>
            <div>
              <label className="rm-label">Tanggal Berakhir Baru</label>
              <input type="date" className="rm-input" value={extendData.new_end_date} onChange={(e) => setExtendData({ ...extendData, new_end_date: e.target.value })} data-testid="admin-contract-extend-date" required />
            </div>
            <div>
              <label className="rm-label">Catatan (opsional)</label>
              <textarea className="rm-input min-h-[70px]" value={extendData.notes} onChange={(e) => setExtendData({ ...extendData, notes: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setExtendOpen(null)}>Batal</button>
              <button className="rm-btn-primary" disabled={busy} data-testid="admin-contract-extend-submit">{busy ? "..." : "Perpanjang"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

function ActionDropdown({ contract, onExtend, onTerminate }) {
  const [open, setOpen] = useState(false);
  const ref = React.useRef(null);
  React.useEffect(() => {
    const h = (e) => { if (open && ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, [open]);
  if (contract.effective_status === "terminated") return null;
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="rm-btn-ghost p-2"
        title="Aksi"
        data-testid={`admin-contract-actions-${contract.id}`}
      >
        <ChevronDown className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 w-48 rm-glass-strong rounded-xl shadow-2xl py-1 z-30 border border-white/5">
          <button onClick={() => { setOpen(false); onExtend(contract); }} className="w-full text-left text-sm px-3 py-2 hover:bg-white/5 flex items-center gap-2" data-testid={`admin-contract-extend-btn-${contract.id}`}>
            <RefreshCw className="w-3.5 h-3.5" /> Perpanjang
          </button>
          <button onClick={() => { setOpen(false); onTerminate(contract); }} className="w-full text-left text-sm px-3 py-2 hover:bg-white/5 text-red-300 flex items-center gap-2" data-testid={`admin-contract-terminate-btn-${contract.id}`}>
            <Ban className="w-3.5 h-3.5" /> Akhiri Kontrak
          </button>
        </div>
      )}
    </div>
  );
}
