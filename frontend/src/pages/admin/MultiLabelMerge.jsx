import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Layers, Search, ArrowRight, ArrowLeft, CheckCircle2, Users2, Building2, Wallet, ShieldCheck } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { useAuth } from "@/api/AuthContext";

const fmtIDR = (n) => "Rp " + Number(n || 0).toLocaleString("id-ID");
const PKG = { pay_per_release: "Pay Per Release", annual_normal: "Annual", annual_vip: "VIP", multi_label: "Multi Label" };
const STEPS = ["Pilih Label", "Akun Utama", "Penanggung Jawab", "Rekening", "Review"];

export default function MultiLabelMerge() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("labels.multi_label.manage");
  const [tab, setTab] = useState("accounts");
  return (
    <div className="space-y-6" data-testid="multi-label-page">
      <header className="flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-[#A24EFF]/30 to-[#4E7CFF]/20"><Layers className="h-5 w-5 text-[#C79BFF]" /></div>
        <div><h1 className="font-display text-2xl font-extrabold">Multi Label</h1><p className="text-sm text-zinc-400">Kelola akun Multi Label & gabungkan beberapa akun existing.</p></div>
      </header>
      <div className="flex gap-2">
        <button onClick={() => setTab("accounts")} className={`rounded-full px-4 py-1.5 text-sm font-semibold ${tab === "accounts" ? "bg-white/10 text-white" : "text-zinc-400"}`} data-testid="tab-accounts">Akun Multi Label</button>
        {canManage && <button onClick={() => setTab("wizard")} className={`rounded-full px-4 py-1.5 text-sm font-semibold ${tab === "wizard" ? "bg-white/10 text-white" : "text-zinc-400"}`} data-testid="tab-wizard">Gabungkan Akun</button>}
        <button onClick={() => setTab("requests")} className={`rounded-full px-4 py-1.5 text-sm font-semibold ${tab === "requests" ? "bg-white/10 text-white" : "text-zinc-400"}`} data-testid="tab-requests">Permintaan</button>
      </div>
      {tab === "accounts" && <AccountsList />}
      {tab === "wizard" && <MergeWizard onDone={() => setTab("accounts")} />}
      {tab === "requests" && <RequestsList canManage={canManage} />}
    </div>
  );
}

function RequestsList({ canManage }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => { api.get("/admin/multi-label/requests").then((r) => setRows(r.data.requests || [])).catch(() => {}).finally(() => setLoading(false)); }, []);
  useEffect(() => { load(); }, [load]);
  const handle = async (id) => { try { await api.post(`/admin/multi-label/requests/${id}/handle`); toast.success("Ditandai selesai."); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); } };
  if (loading) return <div className="text-sm text-zinc-500">Memuat…</div>;
  if (!rows.length) return <div className="rm-glass rounded-2xl p-8 text-center text-sm text-zinc-400" data-testid="ml-requests-empty">Belum ada permintaan Multi Label.</div>;
  return (
    <div className="space-y-2" data-testid="ml-requests-list">
      {rows.map((r) => (
        <div key={r.id} className="rm-glass flex flex-wrap items-center justify-between gap-3 rounded-2xl p-4" data-testid={`ml-request-${r.id}`}>
          <div className="min-w-0">
            <div className="text-sm font-semibold">{r.name} <span className="text-xs font-normal text-zinc-500">• {r.email} • {r.whatsapp}</span></div>
            {r.label_info && <div className="mt-0.5 text-xs text-zinc-400">Label: {r.label_info}</div>}
            {r.message && <div className="mt-0.5 text-xs text-zinc-500 italic">"{r.message}"</div>}
          </div>
          <div className="flex items-center gap-2">
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${r.status === "handled" ? "bg-emerald-500/15 text-emerald-300" : "bg-amber-500/15 text-amber-300"}`}>{r.status}</span>
            {canManage && r.status !== "handled" && <button onClick={() => handle(r.id)} className="rm-btn-ghost text-xs" data-testid={`ml-request-handle-${r.id}`}>Tandai selesai</button>}
          </div>
        </div>
      ))}
    </div>
  );
}

function AccountsList() {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { api.get("/admin/multi-label/accounts").then((r) => setAccounts(r.data.accounts || [])).catch(() => {}).finally(() => setLoading(false)); }, []);
  if (loading) return <div className="text-sm text-zinc-500">Memuat…</div>;
  if (!accounts.length) return <div className="rm-glass rounded-2xl p-8 text-center text-sm text-zinc-400" data-testid="ml-accounts-empty">Belum ada akun Multi Label.</div>;
  return (
    <div className="grid gap-4 md:grid-cols-2" data-testid="ml-accounts-list">
      {accounts.map((a) => (
        <div key={a.primary_user_id} className="rm-glass rounded-2xl p-5" data-testid={`ml-account-${a.primary_user_id}`}>
          <div className="flex items-center justify-between"><div className="text-sm font-bold">{a.primary_email}</div><span className="rounded-full bg-[#A24EFF]/20 px-2 py-0.5 text-[10px] font-bold uppercase text-[#C79BFF]">Multi Label</span></div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-zinc-400">
            <div><Users2 className="mr-1 inline h-3 w-3" />PIC: <span className="text-zinc-200">{a.responsible?.name || "—"}</span></div>
            <div><Wallet className="mr-1 inline h-3 w-3" />{a.payout_bank?.bank_name || "—"}</div>
            <div>Label: <span className="text-zinc-200">{a.label_count}</span></div>
            <div>Saldo: <span className="rm-gradient-text font-bold">{fmtIDR(a.aggregate_balance_idr)}</span></div>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">{a.labels.map((l) => <span key={l.id} className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-zinc-300">{l.label_name}</span>)}</div>
        </div>
      ))}
    </div>
  );
}

function MergeWizard({ onDone }) {
  const [step, setStep] = useState(0);
  const [q, setQ] = useState("");
  const [candidates, setCandidates] = useState([]);
  const [selected, setSelected] = useState({}); // label_id -> candidate
  const [primaryUserId, setPrimaryUserId] = useState("");
  const [pic, setPic] = useState({ responsible_name: "", responsible_email: "", responsible_whatsapp: "" });
  const [bankChoice, setBankChoice] = useState(""); // bank id or "new"
  const [newBank, setNewBank] = useState({ bank_name: "", account_number: "", account_holder_name: "" });
  const [preview, setPreview] = useState(null);
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);

  const search = useCallback(() => { api.get("/admin/multi-label/candidates", { params: { q } }).then((r) => setCandidates(r.data.candidates || [])).catch(() => {}); }, [q]);
  useEffect(() => { search(); }, [search]);

  const selectedList = useMemo(() => Object.values(selected), [selected]);
  const toggle = (c) => setSelected((prev) => { const n = { ...prev }; if (n[c.label_id]) delete n[c.label_id]; else n[c.label_id] = c; return n; });
  const ownerAccounts = useMemo(() => {
    const seen = {}; selectedList.forEach((c) => { if (c.user_id && !seen[c.user_id]) seen[c.user_id] = c; }); return Object.values(seen);
  }, [selectedList]);
  const banks = useMemo(() => selectedList.filter((c) => c.label_id), [selectedList]);

  const body = () => ({
    label_ids: selectedList.map((c) => c.label_id),
    primary_user_id: primaryUserId,
    ...pic,
    payout_bank_account_id: bankChoice && bankChoice !== "new" ? bankChoice : null,
    new_bank: bankChoice === "new" ? newBank : null,
  });

  const doValidate = async () => {
    setBusy(true);
    try {
      const r = await api.post("/admin/multi-label/merge/validate", body());
      setPreview(r.data.preview); setErrors(r.data.errors || []);
      setStep(4);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e.message)); }
    finally { setBusy(false); }
  };
  const doCommit = async () => {
    setBusy(true);
    try {
      await api.post("/admin/multi-label/merge/commit", { ...body(), confirm: true });
      toast.success("Merge berhasil. Akun Multi Label aktif.");
      onDone();
    } catch (e) {
      const d = e.response?.data?.detail;
      toast.error(typeof d === "object" ? (d.errors || []).join(", ") || "Merge gagal" : formatApiError(d || e.message));
    } finally { setBusy(false); }
  };

  const canNext = [selectedList.length >= 2, !!primaryUserId, pic.responsible_name && pic.responsible_email && pic.responsible_whatsapp, !!bankChoice && (bankChoice !== "new" || (newBank.bank_name && newBank.account_number && newBank.account_holder_name))][step];

  return (
    <div className="rm-glass rounded-2xl p-6" data-testid="merge-wizard">
      <div className="mb-6 flex flex-wrap items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s} className={`flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${i === step ? "bg-[#A24EFF]/25 text-[#C79BFF]" : i < step ? "text-emerald-400" : "text-zinc-500"}`}>
            {i < step ? <CheckCircle2 className="h-3.5 w-3.5" /> : <span className="grid h-4 w-4 place-items-center rounded-full border border-current text-[9px]">{i + 1}</span>}{s}
          </div>
        ))}
      </div>

      {step === 0 && (
        <div>
          <div className="relative mb-3"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-500" /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari nama label / email / PIC / ID" className="rm-input w-full pl-9" data-testid="merge-search" /></div>
          <div className="max-h-[380px] space-y-2 overflow-auto pr-1">
            {candidates.map((c) => {
              const disabled = c.already_merged;
              return (
                <label key={c.label_id} className={`flex items-center gap-3 rounded-xl border px-3 py-2 ${selected[c.label_id] ? "border-[#A24EFF]/50 bg-[#A24EFF]/10" : "border-white/10"} ${disabled ? "opacity-40" : "cursor-pointer"}`} data-testid={`merge-candidate-${c.label_id}`}>
                  <input type="checkbox" disabled={disabled} checked={!!selected[c.label_id]} onChange={() => toggle(c)} className="h-4 w-4 accent-[#A24EFF]" />
                  <div className="min-w-0 flex-1"><div className="truncate text-sm font-semibold">{c.label_name}</div><div className="truncate text-xs text-zinc-500">{c.email} • {PKG[c.package] || c.package}{c.already_merged ? " • sudah merged" : ""}</div></div>
                </label>
              );
            })}
          </div>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-2" data-testid="merge-primary">
          <p className="text-sm text-zinc-400">Pilih akun login utama untuk Multi Label.</p>
          {ownerAccounts.map((c) => (
            <label key={c.user_id} className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 cursor-pointer ${primaryUserId === c.user_id ? "border-[#A24EFF]/50 bg-[#A24EFF]/10" : "border-white/10"}`} data-testid={`merge-primary-${c.user_id}`}>
              <input type="radio" name="primary" checked={primaryUserId === c.user_id} onChange={() => { setPrimaryUserId(c.user_id); if (!pic.responsible_name) setPic({ responsible_name: c.pic_name || "", responsible_email: c.email || "", responsible_whatsapp: c.whatsapp || "" }); }} className="h-4 w-4 accent-[#A24EFF]" />
              <div><div className="text-sm font-semibold">{c.email}</div><div className="text-xs text-zinc-500">{c.label_name}</div></div>
            </label>
          ))}
        </div>
      )}

      {step === 2 && (
        <div className="grid max-w-lg gap-3" data-testid="merge-pic">
          <p className="text-sm text-zinc-400">Satu penanggung jawab untuk akun Multi Label.</p>
          <label className="text-xs font-semibold text-zinc-400">Nama<input value={pic.responsible_name} onChange={(e) => setPic({ ...pic, responsible_name: e.target.value })} className="rm-input mt-1 w-full" data-testid="merge-pic-name" /></label>
          <label className="text-xs font-semibold text-zinc-400">Email<input value={pic.responsible_email} onChange={(e) => setPic({ ...pic, responsible_email: e.target.value })} className="rm-input mt-1 w-full" data-testid="merge-pic-email" /></label>
          <label className="text-xs font-semibold text-zinc-400">WhatsApp<input value={pic.responsible_whatsapp} onChange={(e) => setPic({ ...pic, responsible_whatsapp: e.target.value })} className="rm-input mt-1 w-full" data-testid="merge-pic-wa" /></label>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-2" data-testid="merge-bank">
          <p className="text-sm text-zinc-400">Satu rekening pencairan untuk seluruh saldo gabungan.</p>
          {banks.map((c) => (
            <label key={`${c.label_id}-bank`} className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 cursor-pointer ${bankChoice === `${c.label_id}-bank` ? "border-[#A24EFF]/50 bg-[#A24EFF]/10" : "border-white/10"}`} data-testid={`merge-bank-${c.label_id}`}>
              <input type="radio" name="bank" checked={bankChoice === `${c.label_id}-bank`} onChange={() => setBankChoice(`${c.label_id}-bank`)} className="h-4 w-4 accent-[#A24EFF]" />
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <div className="text-sm">Rekening dari <span className="font-semibold">{c.label_name}</span></div>
            </label>
          ))}
          <label className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 cursor-pointer ${bankChoice === "new" ? "border-[#A24EFF]/50 bg-[#A24EFF]/10" : "border-white/10"}`} data-testid="merge-bank-new">
            <input type="radio" name="bank" checked={bankChoice === "new"} onChange={() => setBankChoice("new")} className="h-4 w-4 accent-[#A24EFF]" /> Tambahkan rekening baru (perlu verifikasi)
          </label>
          {bankChoice === "new" && (
            <div className="grid max-w-md gap-2 pl-6">
              <input placeholder="Nama Bank" value={newBank.bank_name} onChange={(e) => setNewBank({ ...newBank, bank_name: e.target.value })} className="rm-input w-full" data-testid="merge-newbank-name" />
              <input placeholder="Nomor Rekening" value={newBank.account_number} onChange={(e) => setNewBank({ ...newBank, account_number: e.target.value })} className="rm-input w-full" data-testid="merge-newbank-number" />
              <input placeholder="Nama Pemilik" value={newBank.account_holder_name} onChange={(e) => setNewBank({ ...newBank, account_holder_name: e.target.value })} className="rm-input w-full" data-testid="merge-newbank-holder" />
            </div>
          )}
        </div>
      )}

      {step === 4 && preview && (
        <div className="space-y-4" data-testid="merge-review">
          {errors.length > 0 && <div className="rounded-xl border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300" data-testid="merge-errors">{errors.join(" • ")}</div>}
          <div className="grid gap-3 md:grid-cols-2">
            <Info icon={Building2} label="Akun Utama" value={preview.primary_email} />
            <Info icon={Users2} label="Penanggung Jawab" value={preview.responsible.name} />
            <Info icon={Wallet} label="Rekening Pencairan" value={preview.payout_bank?.bank_name + (preview.payout_is_new ? " (baru, pending verifikasi)" : "")} />
            <Info icon={Layers} label="Jumlah Label" value={String(preview.label_count)} />
          </div>
          <div className="rounded-xl border border-white/10 p-3">
            <div className="mb-2 text-xs font-bold uppercase tracking-widest text-zinc-500">Label & Saldo Eligible</div>
            {preview.labels.map((l) => <div key={l.id} className="flex items-center justify-between border-b border-white/5 py-1.5 text-sm last:border-0"><span>{l.label_name} <span className="text-xs text-zinc-500">({PKG[l.package] || l.package}, cutoff {l.last_withdrawn_period || "—"})</span></span><span className="tabular-nums">{fmtIDR(l.available_idr)}</span></div>)}
          </div>
          <div className="flex items-center justify-between rounded-xl bg-[#A24EFF]/10 px-4 py-3"><span className="text-sm font-semibold">Total Saldo Gabungan</span><span className="font-display text-xl font-extrabold rm-gradient-text">{fmtIDR(preview.combined_balance_idr)}</span></div>
          <p className="text-xs text-zinc-500">Paket menjadi <b>Multi Label</b> ({fmtIDR(preview.price_idr)}/tahun). Akun lama akan diarsipkan (login dinonaktifkan). History tiap label tetap utuh.</p>
        </div>
      )}

      <div className="mt-6 flex items-center justify-between">
        <button onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0} className="rm-btn-ghost inline-flex items-center gap-2 disabled:opacity-30" data-testid="merge-back"><ArrowLeft className="h-4 w-4" /> Kembali</button>
        {step < 3 && <button onClick={() => setStep((s) => s + 1)} disabled={!canNext} className="rm-btn-primary inline-flex items-center gap-2 disabled:opacity-40" data-testid="merge-next">Lanjut <ArrowRight className="h-4 w-4" /></button>}
        {step === 3 && <button onClick={doValidate} disabled={!canNext || busy} className="rm-btn-primary inline-flex items-center gap-2 disabled:opacity-40" data-testid="merge-review-btn">Review <ArrowRight className="h-4 w-4" /></button>}
        {step === 4 && <button onClick={doCommit} disabled={busy || (errors && errors.length > 0)} className="rm-btn-primary inline-flex items-center gap-2 disabled:opacity-40" data-testid="merge-commit">Konfirmasi & Gabungkan</button>}
      </div>
    </div>
  );
}

function Info({ icon: Icon, label, value }) {
  return <div className="rounded-xl border border-white/10 p-3"><div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-zinc-500"><Icon className="h-3.5 w-3.5" />{label}</div><div className="mt-1 text-sm font-semibold">{value || "—"}</div></div>;
}
