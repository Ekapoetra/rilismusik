import React, { useEffect, useState } from "react";
import { Search } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { RoyaltyAdjustmentPanel } from "@/components/admin/royalty-adjustments/RoyaltyAdjustmentPanel";

export default function RoyaltyAdjustments() {
  const [q, setQ] = useState("");
  const [labels, setLabels] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      try { const { data } = await api.get("/royalty/admin/adjustments/labels", { params: { q } }); if (active) { setLabels(data); setError(""); } }
      catch (e) { if (active) setError(formatApiError(e.response?.data?.detail) || "Daftar label belum dapat dimuat."); }
      finally { if (active) setLoading(false); }
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [q]);
  return <div className="max-w-6xl space-y-7" data-testid="royalty-adjustments-page">
    <header><div className="text-xs uppercase text-zinc-500">Royalti · Rekonsiliasi Legacy</div><h1 className="mt-2 font-display text-4xl font-bold">Inject Saldo</h1></header>
    <section className="space-y-3" data-testid="adjustment-label-picker">
      <label htmlFor="adjustment-label-search" className="inline-flex items-center gap-2 text-sm text-zinc-400"><Search className="h-4 w-4" /> Pilih Label</label>
      <input id="adjustment-label-search" data-testid="adjustment-label-search" className="rm-input w-full max-w-lg" type="search" placeholder="Cari nama label…" value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="flex max-h-48 flex-wrap gap-2 overflow-y-auto" data-testid="adjustment-label-results">{labels.map((label) => <button key={label.id} type="button" className={`max-w-full break-words rounded-md border px-3 py-2 text-sm transition-colors ${selected?.id === label.id ? "border-emerald-400/50 bg-emerald-400/10 text-emerald-200" : "border-white/10 text-zinc-400 hover:border-white/30 hover:text-white"}`} aria-pressed={selected?.id === label.id} onClick={() => setSelected(label)} data-testid={`adjustment-select-label-${label.id}`}>{label.label_name}</button>)}</div>
      {loading && <p className="text-xs text-zinc-500" data-testid="adjustment-label-loading">Mencari label…</p>}
      {!loading && labels.length === 0 && <p className="text-sm text-zinc-500" data-testid="adjustment-label-empty">Label tidak ditemukan.</p>}
      {error && <p role="alert" className="text-sm text-red-300" data-testid="adjustment-label-error">{error}</p>}
    </section>
    {selected && <><h2 className="break-words text-lg font-bold" data-testid="adjustment-selected-label">{selected.label_name}</h2><RoyaltyAdjustmentPanel key={selected.id} label={selected} onChanged={() => {}} /></>}
  </div>;
}