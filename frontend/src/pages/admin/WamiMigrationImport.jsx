import React, { useRef, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { UploadCloud, CheckCircle2, AlertTriangle, HelpCircle, FileSpreadsheet, Sparkles, Search } from "lucide-react";

const STATUS_META = {
  matched: { label: "Cocok", cls: "bg-emerald-500/15 text-emerald-300", icon: CheckCircle2 },
  multi: { label: "Cocok ganda — pilih", cls: "bg-amber-500/15 text-amber-300", icon: HelpCircle },
  not_found: { label: "Tidak ditemukan", cls: "bg-zinc-500/15 text-zinc-400", icon: Search },
};

function candLabel(c) {
  const bits = [c.release_title, c.track_title].filter(Boolean).join(" — ");
  const extra = [c.primary_artist, c.label_name, c.track_performers].filter(Boolean).join(" · ");
  return extra ? `${bits}  ·  ${extra}` : bits;
}

export default function WamiMigrationImport() {
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [applying, setApplying] = useState(false);
  const [preview, setPreview] = useState(null);
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [result, setResult] = useState(null);

  const analyze = async () => {
    if (!file) return;
    setBusy(true); setErr(""); setResult(null); setPreview(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post("/wami/migration/preview", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setPreview(data);
      setRows(data.rows || []);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail) || "Gagal menganalisis file"); }
    finally { setBusy(false); }
  };

  const setSelection = (rowIdx, trackId) => {
    setRows((prev) => prev.map((r) => (r.row === rowIdx ? { ...r, selected_track_id: trackId || null } : r)));
  };

  const readyItems = rows.filter((r) => r.selected_track_id).map((r) => {
    const cand = (r.candidates || []).find((c) => c.track_id === r.selected_track_id) || {};
    return { track_id: r.selected_track_id, release_id: cand.release_id, title: r.title, ...r.wami };
  });

  const apply = async () => {
    if (!readyItems.length) return;
    setApplying(true); setErr(""); setResult(null);
    try {
      const { data } = await api.post("/wami/migration/apply", { items: readyItems, filename: preview?.filename });
      setResult(data);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail) || "Gagal menerapkan data"); }
    finally { setApplying(false); }
  };

  const S = preview?.summary || {};

  return (
    <div className="space-y-5" data-testid="wami-migration-import">
      <div className="rm-card p-5">
        <div className="flex items-center gap-2 text-sm font-bold"><FileSpreadsheet className="h-5 w-5 text-[#FF1F8E]" /> Impor Data WAMI (Migrasi)</div>
        <p className="mt-1 text-xs text-zinc-400">Unggah file Excel (.xlsx) berisi kolom Title, ISWC, Contributors, Original Publishers, Performers, BMAT ID, Internal ID. Sistem mencocokkan Title dengan lagu/rilisan terdaftar, lalu Anda tinjau sebelum menerapkan.</p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <input ref={fileRef} type="file" accept=".xlsx" className="hidden" onChange={(e) => { setFile(e.target.files?.[0] || null); setPreview(null); setResult(null); }} data-testid="wami-migration-file-input" />
          <button className="rm-btn-ghost inline-flex items-center gap-2" onClick={() => fileRef.current?.click()} data-testid="wami-migration-choose-file"><UploadCloud className="h-4 w-4" /> {file ? file.name : "Pilih file .xlsx"}</button>
          <button className="rm-btn-primary inline-flex items-center gap-2" disabled={!file || busy} onClick={analyze} data-testid="wami-migration-analyze"><Search className="h-4 w-4" /> {busy ? "Menganalisis…" : "Analisis & Cocokkan"}</button>
        </div>
        {err && <div className="mt-3 rounded-lg bg-red-500/15 px-3 py-2 text-sm text-red-300" data-testid="wami-migration-error"><AlertTriangle className="mr-1 inline h-4 w-4" />{err}</div>}
      </div>

      {result && <div className="rm-card border border-emerald-500/30 bg-emerald-500/[0.06] p-5" data-testid="wami-migration-result">
        <div className="flex items-center gap-2 text-sm font-bold text-emerald-300"><CheckCircle2 className="h-5 w-5" /> Berhasil diterapkan</div>
        <p className="mt-1 text-sm text-emerald-200/90">{result.applied} lagu ditandai WAMI pada {result.releases} rilisan. Badge “Terdaftar di WAMI” kini tampil di Manajemen Rilisan.</p>
      </div>}

      {preview && <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5" data-testid="wami-migration-summary">
          {[["Total baris", S.total, "text-zinc-200"], ["Cocok", S.matched, "text-emerald-300"], ["Cocok ganda", S.multi, "text-amber-300"], ["Tidak ditemukan", S.not_found, "text-zinc-400"], ["Perkiraan (fuzzy)", S.fuzzy, "text-indigo-300"]].map(([l, v, c]) => (
            <div key={l} className="rm-card p-3"><div className="text-[10px] uppercase tracking-widest text-zinc-500">{l}</div><div className={`font-display text-2xl font-extrabold ${c}`}>{v || 0}</div></div>
          ))}
        </div>
        <div className="flex items-center justify-between">
          <div className="text-xs text-zinc-400">Siap diterapkan: <strong className="text-white">{readyItems.length}</strong> lagu</div>
          <button className="rm-btn-primary inline-flex items-center gap-2" disabled={!readyItems.length || applying} onClick={apply} data-testid="wami-migration-apply"><Sparkles className="h-4 w-4" /> {applying ? "Menerapkan…" : `Terapkan ${readyItems.length} data`}</button>
        </div>
        <div className="rm-card overflow-hidden">
          <div className="hidden grid-cols-12 gap-2 border-b border-white/5 bg-white/[0.03] px-4 py-2.5 text-[10px] font-bold uppercase tracking-widest text-zinc-500 md:grid">
            <div className="col-span-3">Title (Excel)</div><div className="col-span-2">WAMI</div><div className="col-span-2">Status</div><div className="col-span-5">Rilisan Tujuan</div>
          </div>
          {rows.map((r) => {
            const meta = STATUS_META[r.status] || STATUS_META.not_found;
            const Icon = meta.icon;
            return (
              <div key={r.row} className="grid grid-cols-12 items-center gap-2 border-b border-white/5 px-4 py-3 text-sm last:border-0" data-testid={`wami-migration-row-${r.row}`}>
                <div className="col-span-12 md:col-span-3"><div className="font-semibold">{r.title}</div>{r.match_type === "fuzzy" && <span className="text-[10px] font-bold text-indigo-300">≈ perkiraan mirip</span>}</div>
                <div className="col-span-12 text-[11px] text-zinc-400 md:col-span-2"><div>ISWC: {r.wami.iswc || "—"}</div><div>BMAT: {r.wami.bmat_id || "—"}</div></div>
                <div className="col-span-6 md:col-span-2"><span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-bold ${meta.cls}`}><Icon className="h-3 w-3" /> {meta.label}</span></div>
                <div className="col-span-6 md:col-span-5">
                  {r.status === "not_found" ? <span className="text-xs text-zinc-500">Tidak ada rilisan yang cocok — dilewati</span> : (
                    <select className="rm-input text-xs" value={r.selected_track_id || ""} onChange={(e) => setSelection(r.row, e.target.value)} data-testid={`wami-migration-select-${r.row}`}>
                      <option value="">— Jangan terapkan —</option>
                      {(r.candidates || []).map((c) => <option key={c.track_id} value={c.track_id} className="bg-zinc-900">{candLabel(c)}{c.already_wami ? " (sudah WAMI)" : ""}</option>)}
                    </select>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>}
    </div>
  );
}
