import React, { useState, useRef } from "react";
import { Upload, Download, FileText, Users, Music2, ListMusic, Wallet, AlertCircle, CheckCircle2, Clock, UserCheck, UserX } from "lucide-react";
import { api } from "@/api/client";
import { useEffect } from "react";

const TABS = [
  { id: "labels", label: "Labels", icon: Users, endpoint: "labels", desc: "Import data label lama (5-6 ribu). user_id=null, status=legacy_unclaimed." },
  { id: "releases", label: "Releases", icon: Music2, endpoint: "releases", desc: "Import katalog rilisan lama (imported_legacy=true)." },
  { id: "tracks", label: "Tracks", icon: ListMusic, endpoint: "tracks", desc: "Import master tracks per release. Audio file URL optional." },
  { id: "withdraws", label: "Withdraws", icon: Wallet, endpoint: "withdraws", desc: "Import histori withdraw 2021-sekarang. Tidak trigger notifikasi atau mutasi saldo." },
  { id: "claims", label: "Claims", icon: UserCheck, endpoint: null, desc: "Resolve permintaan label claim akun lama. Link ke legacy label_id atau reject." },
];

export default function AdminMigrate() {
  const params = new URLSearchParams(window.location.search);
  const initialTab = params.get("tab") || "labels";
  const [tab, setTab] = useState(TABS.find(t => t.id === initialTab) ? initialTab : "labels");
  const cfg = TABS.find(t => t.id === tab);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Migrasi Data</h1>
        <p className="text-sm text-zinc-400 mt-1">Bulk import data lama (royalti, label, releases, tracks, withdraw). <b>Super Admin only.</b></p>
      </div>

      <div className="flex flex-wrap gap-2 border-b border-white/5 pb-3">
        {TABS.map(t => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              data-testid={`admin-migrate-tab-${t.id}`}
              onClick={() => setTab(t.id)}
              className={`rm-pill flex items-center gap-2 px-4 py-2 text-sm ${tab === t.id ? "bg-white/10 border-white/20 text-white" : "text-zinc-400 hover:text-white"}`}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="rm-card p-5">
        <div className="text-sm text-zinc-400 mb-4 flex items-start gap-2">
          <FileText className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <span>{cfg.desc}</span>
        </div>

        {cfg.endpoint ? (
          <CsvImportPanel kind={cfg.endpoint} />
        ) : (
          <ClaimsPanel />
        )}
      </div>
    </div>
  );
}

function CsvImportPanel({ kind }) {
  const [file, setFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const inputRef = useRef(null);

  const downloadTemplate = async () => {
    const res = await api.get(`/admin/migrate/template/${kind}`, { responseType: "blob" });
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const a = document.createElement("a");
    a.href = url; a.download = `template_${kind}.csv`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const downloadReport = () => {
    if (!result?.report) return;
    const headers = Object.keys(result.report[0]);
    const csv = [
      headers.join(","),
      ...result.report.map(r => headers.map(h => JSON.stringify(r[h] ?? "")).join(","))
    ].join("\n");
    const url = window.URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = `migrate_${kind}_report.csv`; a.click();
    window.URL.revokeObjectURL(url);
  };

  const submit = async () => {
    if (!file) {
      setErr("Pilih file CSV terlebih dahulu");
      return;
    }
    setErr(""); setResult(null); setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("dry_run", dryRun ? "true" : "false");
      const { data } = await api.post(`/admin/migrate/${kind}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(data);
    } catch (e) {
      setErr(e.response?.data?.detail || "Upload gagal");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={downloadTemplate}
          className="rm-btn-secondary text-xs flex items-center gap-2"
          data-testid={`admin-migrate-${kind}-template`}
        >
          <Download className="w-3.5 h-3.5" /> Download Template
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null); setErr(""); }}
          className="text-xs text-zinc-300 file:rm-btn-secondary file:mr-3 file:px-3 file:py-1.5 file:border-0 file:cursor-pointer"
          data-testid={`admin-migrate-${kind}-file`}
        />
        <label className="text-xs text-zinc-400 flex items-center gap-2 cursor-pointer ml-auto">
          <input
            type="checkbox"
            checked={dryRun}
            onChange={(e) => setDryRun(e.target.checked)}
            className="accent-[#FF1F8E]"
            data-testid={`admin-migrate-${kind}-dryrun`}
          />
          Dry-run (preview saja)
        </label>
        <button
          onClick={submit}
          disabled={!file || loading}
          className="rm-btn-primary text-xs flex items-center gap-2"
          data-testid={`admin-migrate-${kind}-submit`}
        >
          <Upload className="w-3.5 h-3.5" />
          {loading ? "Memproses…" : dryRun ? "Preview Dry-run" : "Import Sekarang"}
        </button>
      </div>

      {err && (
        <div className="rounded-2xl bg-red-500/15 text-red-300 px-4 py-3 text-sm flex items-start gap-2">
          <AlertCircle className="w-4 h-4 mt-0.5" /> <span>{String(err)}</span>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Stat label="Total Baris" value={result.total_rows} color="text-zinc-200" />
            <Stat label="Inserted" value={result.inserted} color="text-emerald-300" />
            <Stat label="Skipped" value={result.skipped ?? 0} color="text-amber-300" />
            <Stat label="Errors" value={result.errors} color="text-red-300" />
          </div>
          {result.dry_run && (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-xs px-3 py-2 flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" /> Ini adalah <b>dry-run</b> — data BELUM disimpan. Untik commit, uncheck dry-run lalu submit lagi.
            </div>
          )}
          <div className="flex justify-between items-center">
            <div className="text-xs text-zinc-500">Menampilkan {Math.min(result.report.length, 20)} dari {result.report.length} baris report.</div>
            <button onClick={downloadReport} className="rm-btn-secondary text-xs flex items-center gap-2">
              <Download className="w-3.5 h-3.5" /> Download Report CSV
            </button>
          </div>
          <div className="overflow-x-auto rounded-2xl border border-white/5">
            <table className="w-full text-xs">
              <thead className="bg-white/[0.03] text-zinc-400">
                <tr>
                  <th className="px-3 py-2 text-left">Row</th>
                  <th className="px-3 py-2 text-left">Status</th>
                  <th className="px-3 py-2 text-left">Detail</th>
                  <th className="px-3 py-2 text-left">Reason</th>
                </tr>
              </thead>
              <tbody>
                {result.report.slice(0, 20).map((r, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="px-3 py-2 text-zinc-500">{r.row}</td>
                    <td className="px-3 py-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        r.status === "OK" ? "bg-emerald-500/15 text-emerald-300" :
                        r.status === "SKIPPED" ? "bg-amber-500/15 text-amber-300" :
                        "bg-red-500/15 text-red-300"
                      }`}>
                        {r.status === "OK" ? <CheckCircle2 className="inline w-3 h-3 mr-0.5" /> :
                          r.status === "SKIPPED" ? <Clock className="inline w-3 h-3 mr-0.5" /> :
                          <AlertCircle className="inline w-3 h-3 mr-0.5" />}
                        {r.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-zinc-200">{r.label_name || r.release_title || r.track_title}</td>
                    <td className="px-3 py-2 text-zinc-500">{r.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div className="rounded-2xl border border-white/5 bg-white/[0.02] p-3">
      <div className="text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{label}</div>
      <div className={`text-xl font-bold mt-1 ${color}`}>{value ?? 0}</div>
    </div>
  );
}

function ClaimsPanel() {
  const [claims, setClaims] = useState([]);
  const [search, setSearch] = useState("");
  const [unclaimed, setUnclaimed] = useState([]);
  const [activeClaim, setActiveClaim] = useState(null);
  const [loading, setLoading] = useState(false);

  const reload = async () => {
    const { data } = await api.get("/admin/migrate/claims");
    setClaims(data);
  };
  useEffect(() => { reload(); }, []);

  const openLink = async (claim) => {
    setActiveClaim(claim);
    const { data } = await api.get(`/admin/migrate/labels/unclaimed?q=${encodeURIComponent(claim.claim_legacy_name || "")}`);
    setUnclaimed(data);
    setSearch(claim.claim_legacy_name || "");
  };
  const searchAgain = async () => {
    const { data } = await api.get(`/admin/migrate/labels/unclaimed?q=${encodeURIComponent(search)}`);
    setUnclaimed(data);
  };
  const doLink = async (legacy) => {
    setLoading(true);
    try {
      await api.post(`/admin/migrate/claims/${activeClaim.id}/link/${legacy.id}`);
      setActiveClaim(null); setUnclaimed([]); await reload();
    } catch (e) {
      alert(e.response?.data?.detail || "Link gagal");
    } finally { setLoading(false); }
  };
  const doReject = async (claim) => {
    const reason = window.prompt("Alasan reject?", "Data tidak cocok");
    if (reason === null) return;
    const fd = new FormData(); fd.append("reason", reason);
    await api.post(`/admin/migrate/claims/${claim.id}/reject`, fd, { headers: { "Content-Type": "multipart/form-data" } });
    await reload();
  };

  return (
    <div className="space-y-5">
      <div className="text-xs text-zinc-400">
        Total pending claims: <b className="text-zinc-200">{claims.length}</b>
      </div>

      {claims.length === 0 ? (
        <div className="text-center text-zinc-500 py-10 text-sm">
          <UserCheck className="w-8 h-8 mx-auto mb-2 opacity-50" />
          Belum ada permintaan claim akun lama.
        </div>
      ) : (
        <div className="space-y-3">
          {claims.map((c) => (
            <div key={c.id} className="rounded-2xl border border-white/5 bg-white/[0.02] p-4 flex flex-wrap items-start justify-between gap-3" data-testid={`admin-claim-${c.id}`}>
              <div className="text-sm space-y-1">
                <div className="font-semibold">{c.name} <span className="text-zinc-500 text-xs">· {c.email}</span></div>
                <div className="text-xs text-zinc-400">
                  Klaim sebagai: <b className="text-zinc-200">{c.claim_legacy_name}</b>
                </div>
                <div className="text-xs text-zinc-500">
                  Nama baru: {c.claim_label_name_new} · WA: {c.claim_whatsapp}
                </div>
                <div className="text-[10px] text-zinc-600">Diajukan: {c.claim_requested_at?.slice(0, 16)?.replace("T", " ")}</div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => openLink(c)}
                  className="rm-btn-primary text-xs flex items-center gap-2"
                  data-testid={`admin-claim-link-${c.id}`}
                >
                  <UserCheck className="w-3.5 h-3.5" /> Link
                </button>
                <button
                  onClick={() => doReject(c)}
                  className="rm-btn-secondary text-xs flex items-center gap-2 text-red-300"
                  data-testid={`admin-claim-reject-${c.id}`}
                >
                  <UserX className="w-3.5 h-3.5" /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeClaim && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="rm-card max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="text-lg font-bold">Link ke Legacy Label</div>
                <div className="text-xs text-zinc-400 mt-1">
                  Klaimer: <b>{activeClaim.email}</b> mengaku punya label <b className="text-zinc-200">{activeClaim.claim_legacy_name}</b>
                </div>
              </div>
              <button onClick={() => { setActiveClaim(null); setUnclaimed([]); }} className="text-zinc-400 hover:text-white text-xl">×</button>
            </div>
            <div className="flex gap-2 mb-3">
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="rm-input flex-1"
                placeholder="Cari nama label lama…"
              />
              <button onClick={searchAgain} className="rm-btn-secondary text-xs px-4">Cari</button>
            </div>
            <div className="space-y-2">
              {unclaimed.length === 0 && (
                <div className="text-center text-zinc-500 text-sm py-6">Tidak ditemukan legacy label unclaimed.</div>
              )}
              {unclaimed.map((lab) => (
                <div key={lab.id} className="rounded-xl border border-white/5 bg-white/[0.02] p-3 flex items-center justify-between gap-3">
                  <div className="text-sm">
                    <div className="font-semibold">{lab.label_name}</div>
                    <div className="text-xs text-zinc-500">{lab.city || "—"} · PIC: {lab.pic_name || "—"} · {lab.subscription_tier || "no sub"}</div>
                  </div>
                  <button
                    onClick={() => doLink(lab)}
                    disabled={loading}
                    className="rm-btn-primary text-xs"
                    data-testid={`admin-claim-link-confirm-${lab.id}`}
                  >
                    Link
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
