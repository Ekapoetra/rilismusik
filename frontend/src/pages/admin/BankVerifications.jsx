import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Landmark, ShieldCheck, ArrowRight, RefreshCw, CheckCircle2, CheckSquare, Square, Wrench } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { celebrateWork } from "@/lib/completionFeedback";
import { BankSelect } from "@/components/shared/BankSelect";

const Row = ({ label, value, strong }) => (
  <div className="flex justify-between gap-4 py-1 text-sm">
    <span className="text-zinc-500">{label}</span>
    <span className={`text-right ${strong ? "font-semibold text-white" : "text-zinc-300"}`}>{value || "—"}</span>
  </div>
);

export default function BankVerifications() {
  const [tab, setTab] = useState("inputs");
  const [inputs, setInputs] = useState([]);
  const [changes, setChanges] = useState([]);
  const [unmapped, setUnmapped] = useState([]);
  const [choice, setChoice] = useState({});
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setErr("");
    try {
      const [inp, chg] = await Promise.all([
        api.get("/admin/bank-verifications/pending-inputs"),
        api.get("/admin/bank-verifications"),
      ]);
      setInputs(inp.data?.items || []);
      setChanges(chg.data || []);
      try { const um = await api.get("/admin/bank-verifications/unmapped"); setUnmapped(um.data?.items || []); } catch { setUnmapped([]); }
      setSelected([]); setChoice({});
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  // Default to whichever tab has work.
  useEffect(() => { if (!loading) setTab(inputs.length === 0 && changes.length > 0 ? "changes" : "inputs"); }, [loading]); // eslint-disable-line

  const review = async (item, action) => {
    setBusyId(item.id);
    try {
      await api.post(`/admin/bank-verifications/${item.id}/action`, { action });
      if (action === "approve") { celebrateWork("bank_verification"); }
      else { toast.success("Pengajuan rekening ditolak."); }
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusyId(null); }
  };

  const toggle = (labelId) => setSelected((s) => s.includes(labelId) ? s.filter((x) => x !== labelId) : [...s, labelId]);
  const allSelected = inputs.length > 0 && selected.length === inputs.length;
  const toggleAll = () => setSelected(allSelected ? [] : inputs.map((i) => i.label_id));

  const verifyInputs = async (labelIds) => {
    if (labelIds.length === 0) { toast.error("Pilih minimal satu rekening"); return; }
    setBulkBusy(true);
    try {
      const { data } = await api.post("/admin/bank-verifications/bulk-verify-inputs", { label_ids: labelIds });
      celebrateWork("bank_verification");
      toast.success(`${data.verified} rekening diverifikasi${data.skipped ? ` · ${data.skipped} dilewati` : ""}.`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBulkBusy(false); }
  };

  const fixBank = async (bankId) => {
    const value = choice[bankId];
    if (!value) { toast.error("Pilih bank yang benar dulu"); return; }
    setBusyId(bankId);
    try {
      await api.post(`/admin/bank-verifications/${bankId}/set-bank`, { bank_value: value });
      toast.success("Nama bank dibetulkan.");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusyId(null); }
  };

  const TabBtn = ({ id, children, count }) => (
    <button onClick={() => setTab(id)} className={`rounded-full px-4 py-1.5 text-sm font-semibold ${tab === id ? "bg-pink-500/15 text-pink-300" : "text-zinc-500 hover:text-white"}`} data-testid={`bank-verif-tab-${id}`}>
      {children}{count > 0 && <span className="ml-1.5 rounded-full bg-white/10 px-1.5 text-[11px]">{count}</span>}
    </button>
  );

  return (
    <div className="space-y-6" data-testid="admin-bank-verifications-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Operasional</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><Landmark className="h-6 w-6 text-pink-400" /> Verifikasi Rekening</h1>
          <p className="mt-2 text-sm text-zinc-400">Verifikasi rekening yang baru diinput label saat daftar, serta pengajuan perubahan rekening. Rekening baru bisa diverifikasi secara massal.</p>
        </div>
        <button type="button" onClick={load} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="bank-verif-refresh"><RefreshCw className="h-4 w-4" /> Muat ulang</button>
      </header>

      <div className="flex items-center gap-2">
        <TabBtn id="inputs" count={inputs.length}>Rekening Baru</TabBtn>
        <TabBtn id="changes" count={changes.length}>Perubahan Rekening</TabBtn>
        <TabBtn id="unmapped" count={unmapped.length}>Perlu Dibetulkan</TabBtn>
      </div>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="bank-verif-error">{err}</div>}
      {loading && <p className="text-sm text-zinc-500" data-testid="bank-verif-loading">Memuat…</p>}

      {/* First-time bank inputs — bulk verifiable */}
      {!loading && tab === "inputs" && (
        inputs.length === 0 ? (
          <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="bank-inputs-empty">Tidak ada input rekening baru yang menunggu. Semua beres 🎉</div>
        ) : (
          <div className="space-y-3" data-testid="bank-inputs-section">
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-white/10 bg-white/[0.02] px-4 py-3">
              <button onClick={toggleAll} className="inline-flex items-center gap-2 text-sm font-semibold text-zinc-300 hover:text-white" data-testid="bank-inputs-select-all">
                {allSelected ? <CheckSquare className="h-4 w-4 text-pink-300" /> : <Square className="h-4 w-4" />}
                {allSelected ? "Batalkan semua" : "Pilih semua"}
              </button>
              <span className="text-sm text-zinc-500">{selected.length} dipilih</span>
              <button onClick={() => verifyInputs(selected)} disabled={bulkBusy || selected.length === 0} className="rm-btn-primary ml-auto inline-flex items-center gap-2 text-sm disabled:opacity-40" data-testid="bank-inputs-bulk-verify">
                <CheckCircle2 className="h-4 w-4" />{bulkBusy ? "Memproses…" : `Verifikasi Terpilih (${selected.length})`}
              </button>
            </div>
            <div className="overflow-x-auto rounded-lg border border-white/10">
              <table className="w-full text-sm">
                <thead className="bg-white/5 text-left text-[11px] uppercase text-zinc-500">
                  <tr>
                    <th className="px-3 py-3 w-10"></th>
                    <th className="px-3 py-3">Label</th><th className="px-3 py-3">Bank</th>
                    <th className="px-3 py-3">Nomor</th><th className="px-3 py-3">Atas Nama</th>
                    <th className="px-3 py-3">KYC</th><th className="px-3 py-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {inputs.map((it) => (
                    <tr key={it.id} className={`border-t border-white/5 ${selected.includes(it.label_id) ? "bg-pink-500/[0.06]" : ""}`} data-testid={`bank-input-row-${it.label_id}`}>
                      <td className="px-3 py-2">
                        <button onClick={() => toggle(it.label_id)} data-testid={`bank-input-check-${it.label_id}`}>
                          {selected.includes(it.label_id) ? <CheckSquare className="h-4 w-4 text-pink-300" /> : <Square className="h-4 w-4 text-zinc-500" />}
                        </button>
                      </td>
                      <td className="px-3 py-2">
                        <Link to={`/admin/labels/${it.label_id}`} className="font-semibold text-white hover:text-pink-200">{it.label_name}</Link>
                        {it.pic_name && <div className="text-[11px] text-zinc-500">{it.pic_name}</div>}
                      </td>
                      <td className="px-3 py-2 text-zinc-300">{it.bank_name || "—"}</td>
                      <td className="px-3 py-2 tabular-nums text-zinc-300">{it.account_number || "—"}</td>
                      <td className="px-3 py-2 text-zinc-300">{it.account_holder_name || "—"}</td>
                      <td className="px-3 py-2"><span className="text-[11px] text-zinc-400">{it.kyc_status || "—"}</span></td>
                      <td className="px-3 py-2 text-right">
                        <button onClick={() => verifyInputs([it.label_id])} disabled={bulkBusy} className="rm-btn text-xs" data-testid={`bank-input-verify-${it.label_id}`}>Verifikasi</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}

      {/* Unmapped bank names — fix via dropdown */}
      {!loading && tab === "unmapped" && (
        unmapped.length === 0 ? (
          <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="bank-unmapped-empty">Semua nama bank sudah terpetakan dengan benar 🎉</div>
        ) : (
          <div className="space-y-3" data-testid="bank-unmapped-section">
            <div className="rounded-lg border border-amber-400/30 bg-amber-500/[0.06] px-4 py-3 text-sm text-amber-200">
              <span className="inline-flex items-center gap-2 font-semibold"><Wrench className="h-4 w-4" /> {unmapped.length} rekening dengan nama bank tidak dikenal. Pilih bank yang benar lalu simpan.</span>
            </div>
            <div className="overflow-x-auto rounded-lg border border-white/10">
              <table className="w-full text-sm">
                <thead className="bg-white/5 text-left text-[11px] uppercase text-zinc-500">
                  <tr>
                    <th className="px-3 py-3">Label</th><th className="px-3 py-3">Nama Bank Tersimpan</th>
                    <th className="px-3 py-3">Nomor</th><th className="px-3 py-3">Atas Nama</th>
                    <th className="px-3 py-3 w-72">Bank yang Benar</th><th className="px-3 py-3 text-right">Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {unmapped.map((it) => (
                    <tr key={it.id} className="border-t border-white/5" data-testid={`bank-unmapped-row-${it.id}`}>
                      <td className="px-3 py-2">
                        <Link to={`/admin/labels/${it.label_id}`} className="font-semibold text-white hover:text-pink-200">{it.label_name}</Link>
                      </td>
                      <td className="px-3 py-2 text-amber-300">{it.bank_name || "—"}</td>
                      <td className="px-3 py-2 tabular-nums text-zinc-300">{it.account_number || "—"}</td>
                      <td className="px-3 py-2 text-zinc-300">{it.account_holder_name || "—"}</td>
                      <td className="px-3 py-2">
                        <BankSelect value={choice[it.id] || ""} onChange={(value) => setChoice((c) => ({ ...c, [it.id]: value }))} testid={`bank-unmapped-select-${it.id}`} />
                      </td>
                      <td className="px-3 py-2 text-right">
                        <button onClick={() => fixBank(it.id)} disabled={busyId === it.id || !choice[it.id]} className="rm-btn text-xs disabled:opacity-40" data-testid={`bank-unmapped-save-${it.id}`}>{busyId === it.id ? "…" : "Simpan"}</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}

      {/* Bank change requests — individual approve/reject with old vs new */}
      {!loading && tab === "changes" && (
        changes.length === 0 ? (
          <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="bank-verif-empty">Tidak ada pengajuan perubahan rekening. Semua beres 🎉</div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2" data-testid="bank-verif-grid">
            {changes.map((item) => (
              <section key={item.id} className="rm-card space-y-4 p-5" data-testid={`bank-verif-card-${item.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2 text-sm font-bold text-amber-200"><ShieldCheck className="h-4 w-4" /> Persetujuan admin diperlukan</div>
                    <h3 className="mt-1 font-display text-lg font-bold">{item.label_name || "Label"}</h3>
                    <div className="text-xs text-zinc-500">Diajukan {(item.created_at || "").replace("T", " ").slice(0, 16)}{item.requested_by_name ? ` · oleh ${item.requested_by_name}` : ""}</div>
                  </div>
                  <Link to={`/admin/labels/${item.label_id}`} className="inline-flex items-center gap-1 text-xs font-bold text-pink-300 hover:text-pink-200" data-testid={`bank-verif-open-label-${item.id}`}>Buka label <ArrowRight className="h-3.5 w-3.5" /></Link>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                    <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-zinc-500">Rekening saat ini</div>
                    <Row label="Bank" value={item.current_bank?.bank_name} />
                    <Row label="Nomor" value={item.current_bank?.account_number} />
                    <Row label="Atas nama" value={item.current_bank?.account_holder_name} />
                  </div>
                  <div className="rounded-lg border border-emerald-400/30 bg-emerald-400/[0.05] p-3">
                    <div className="mb-1 text-[11px] font-bold uppercase tracking-wider text-emerald-300">Rekening baru diajukan</div>
                    <Row label="Bank" value={item.proposed_bank?.bank_name} strong />
                    <Row label="Nomor" value={item.proposed_bank?.account_number} strong />
                    <Row label="Atas nama" value={item.proposed_bank?.account_holder_name} strong />
                  </div>
                </div>
                {item.reason && <div className="rounded-md bg-white/[0.03] px-3 py-2 text-sm text-zinc-400"><span className="text-zinc-500">Alasan: </span>{item.reason}</div>}
                <div className="flex gap-2">
                  <button className="rm-btn-primary text-sm" disabled={busyId === item.id} onClick={() => review(item, "approve")} data-testid={`bank-verif-approve-${item.id}`}>{busyId === item.id ? "Memproses…" : "Setujui & Verifikasi"}</button>
                  <button className="rm-btn-ghost text-sm text-red-300" disabled={busyId === item.id} onClick={() => review(item, "reject")} data-testid={`bank-verif-reject-${item.id}`}>Tolak</button>
                </div>
              </section>
            ))}
          </div>
        )
      )}
    </div>
  );
}
