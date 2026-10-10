import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cog, RefreshCw, Send, Trash2, History, ScrollText, LayoutTemplate } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";

const AREAS = [
  ["content", "Konten Landing"],
  ["procedures", "Prosedur Operasional"],
  ["token", "Token"],
];
const KIND_LABEL = {
  "draft-save": "Simpan draf", "draft-discard": "Buang draf",
  "draft-restore": "Pulihkan versi", publish: "Terbitkan", "direct-publish": "Terbit langsung (CMS)",
};
const PROCEDURE_FIELDS = [
  ["subscription_reminder_days", "Pengingat langganan (hari sebelum berakhir)", "list", "30, 7, 3, 1"],
  ["contract_reminder_days", "Pengingat kontrak (hari sebelum berakhir)", "list", "30, 7, 1"],
  ["payment_pending_reminder_hours", "Pengingat invoice tertunda (jam sejak dibuat)", "list", "72, 24"],
  ["withdraw_min_idr", "Minimum penarikan (Rp)", "int", "1000000"],
  ["daily_release_limit", "Batas rilisan per hari per label", "int", "7"],
];

const fmt = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso
    : new Intl.DateTimeFormat("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d).replace(".", ":") + " WIB";
};
const parseList = (raw) => raw.split(/[,\s]+/).filter(Boolean).map(Number);
const QUOTA_LABELS = {
  pay_per_release: "Pay Per Release", annual_normal: "Annual Normal",
  annual_vip: "Annual VIP", multi_label: "Multi Label",
};
const fmtIDR = (n) => new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(n || 0);

export default function AdminSystem() {
  const [area, setArea] = useState("content");
  const [state, setState] = useState(null); // {published, draft, version, ...}
  const [audit, setAudit] = useState([]);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [publishNote, setPublishNote] = useState("");
  const [showPublish, setShowPublish] = useState(false);
  const [procDraft, setProcDraft] = useState(null); // editable procedures value
  const [tokDraft, setTokDraft] = useState(null); // editable token value
  const [newCostKey, setNewCostKey] = useState("");

  const load = useCallback(async (a = area) => {
    setErr("");
    try {
      const [{ data: detail }, { data: log }] = await Promise.all([
        api.get(`/admin/system/${a}`), api.get(`/admin/system/${a}/audit`),
      ]);
      setState(detail);
      setAudit(log.entries || []);
      if (a === "procedures") setProcDraft(detail.draft || detail.published);
      if (a === "token") setTokDraft(detail.draft || detail.published);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
  }, [area]);
  useEffect(() => { load(area); }, [area, load]);

  const act = async (kind, payload) => {
    setBusy(true);
    try {
      const { data } = await api.post(`/admin/system/${area}/${kind}`, payload);
      setState(data);
      if (area === "procedures") setProcDraft(data.draft || data.published);
      if (area === "token") setTokDraft(data.draft || data.published);
      const { data: log } = await api.get(`/admin/system/${area}/audit`);
      setAudit(log.entries || []);
      return true;
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
      if (e.response?.status === 409) await load();
      return false;
    } finally { setBusy(false); }
  };

  const saveDraft = (value) => act("draft", { value, version: state.version, draft_version: state.draft_version });
  const discard = () => act("discard", { version: state.version, draft_version: state.draft_version });
  const restore = (id) => act("restore", { history_id: id, version: state.version, draft_version: state.draft_version });
  const publish = async () => {
    if (!publishNote.trim()) { toast.error("Catatan penerapan wajib diisi"); return; }
    const ok = await act("publish", { note: publishNote.trim(), version: state.version, draft_version: state.draft_version });
    if (ok) { setShowPublish(false); setPublishNote(""); toast.success("Versi baru diterbitkan."); }
  };

  const procValue = () => {
    const v = {};
    for (const [key, , kind] of PROCEDURE_FIELDS) {
      const raw = procDraft?.[key];
      v[key] = kind === "list" ? parseList(String(raw ?? "").replace(/^\[|\]$/g, "")) : Number(raw);
    }
    return v;
  };
  const procDisplay = (v) => Array.isArray(v) ? v.join(", ") : String(v ?? "");

  const tokValue = () => ({
    price_idr: Number(tokDraft?.price_idr) || 0,
    daily_quota: Object.fromEntries(
      Object.entries(tokDraft?.daily_quota || {}).map(([k, v]) => [k, Number(v) || 0])),
    service_costs: Object.fromEntries(
      Object.entries(tokDraft?.service_costs || {}).map(([k, v]) => [k, Number(v) || 0])),
  });
  const setTok = (path, key, val) => setTokDraft((d) => ({
    ...(d || {}), [path]: { ...((d || {})[path] || {}), [key]: val },
  }));

  return (
    <div className="space-y-6" data-testid="admin-system-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Sistem</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><Cog className="h-6 w-6 text-sky-400" /> Pengaturan Sistem</h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">Konfigurasi bervesi: ubah sebagai draf, tinjau, lalu terbitkan. Setiap perubahan tercatat di audit dan dapat dipulihkan dari riwayat.</p>
        </div>
        <button className="rm-btn-ghost" onClick={() => load()} disabled={busy}><RefreshCw className="h-4 w-4" /> Muat ulang</button>
      </header>

      <div className="flex flex-wrap gap-2 border-b border-white/10">
        {AREAS.map(([id, labelText]) => (
          <button key={id} onClick={() => setArea(id)}
            className={`px-4 py-2 text-sm font-bold rounded-t-xl ${area === id ? "bg-[#14111E] border border-white/10 border-b-[#14111E] rm-gradient-text" : "text-zinc-500 hover:text-white"}`}
            data-testid={`system-area-${id}`}>{labelText}</button>
        ))}
      </div>

      {err && <div className="rounded-2xl bg-red-500/15 px-4 py-3 text-sm text-red-300">{err}</div>}
      {!state ? <div className="text-zinc-500">Memuat…</div> : (
        <>
          <section className="rm-card flex flex-wrap items-center justify-between gap-4 p-5">
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <div><div className="text-xs uppercase tracking-widest text-zinc-500">Versi terbit</div><div className="text-xl font-extrabold">v{state.version}</div></div>
              <div><div className="text-xs uppercase tracking-widest text-zinc-500">Diterapkan</div><div>{fmt(state.applied_at)}</div></div>
              <div><div className="text-xs uppercase tracking-widest text-zinc-500">Catatan</div><div className="max-w-xs truncate text-zinc-300">{state.note || "—"}</div></div>
              <div>
                <div className="text-xs uppercase tracking-widest text-zinc-500">Draf</div>
                {state.has_draft
                  ? <span className="rounded-full border border-amber-400/40 bg-amber-500/10 px-2 py-0.5 text-xs font-bold text-amber-300">Ada draf</span>
                  : <span className="text-zinc-500">Kosong</span>}
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {state.has_draft && <>
                <button className="rm-btn-ghost" onClick={discard} disabled={busy}><Trash2 className="h-4 w-4" /> Buang Draf</button>
                <button className="rm-btn-primary" onClick={() => setShowPublish(true)} disabled={busy}><Send className="h-4 w-4" /> Terbitkan</button>
              </>}
            </div>
          </section>

          {area === "token" ? (
            <section className="rm-card space-y-4 p-5" data-testid="system-token-editor">
              <h2 className="text-base font-bold">Rel pembayaran token</h2>
              <p className="text-sm text-zinc-400">
                Token adalah opsi pembayaran kedua — Rupiah tetap tawaran utama di semua checkout.
                Kuota harian berasal dari paket berbayar dan reset tiap hari (WIB); token yang dibeli tidak pernah hangus.
              </p>
              <label className="block space-y-1 text-sm max-w-xs">
                <span className="text-zinc-400">Harga jual per token (Rp)</span>
                <input className="rm-input w-full" type="number" min="25000" max="1000000"
                  value={tokDraft?.price_idr ?? ""}
                  onChange={(e) => setTokDraft((d) => ({ ...(d || {}), price_idr: e.target.value }))}
                  data-testid="token-price-input" />
              </label>
              <div>
                <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-2">Kuota harian per paket</div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {Object.keys(QUOTA_LABELS).map((tier) => (
                    <label key={tier} className="space-y-1 text-sm">
                      <span className="text-zinc-400">{QUOTA_LABELS[tier]}</span>
                      <input className="rm-input w-full" type="number" min="0" max="100"
                        value={tokDraft?.daily_quota?.[tier] ?? 0}
                        onChange={(e) => setTok("daily_quota", tier, e.target.value)}
                        data-testid={`quota-${tier}`} />
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold mb-2">Biaya layanan (token)</div>
                <div className="space-y-2">
                  {Object.entries(tokDraft?.service_costs || {}).map(([key, val]) => (
                    <div key={key} className="flex items-center gap-2">
                      <code className="text-xs text-zinc-400 w-44 truncate">{key}</code>
                      <input className="rm-input w-24" type="number" min="0" max="500"
                        value={val}
                        onChange={(e) => setTok("service_costs", key, e.target.value)}
                        data-testid={`cost-${key}`} />
                      <span className="text-xs text-zinc-500">token • ≈ {fmtIDR((Number(val) || 0) * (Number(tokDraft?.price_idr) || 0))}</span>
                      <button className="text-xs text-red-400 hover:text-red-300"
                        onClick={() => setTokDraft((d) => {
                          const costs = { ...(d?.service_costs || {}) };
                          delete costs[key];
                          return { ...(d || {}), service_costs: costs };
                        })}>hapus</button>
                    </div>
                  ))}
                </div>
                <div className="mt-2 flex items-center gap-2">
                  <input className="rm-input w-56" placeholder="kunci layanan, mis. cover"
                    value={newCostKey} onChange={(e) => setNewCostKey(e.target.value)}
                    data-testid="token-new-cost-key" />
                  <button className="rm-btn-ghost text-xs" disabled={!newCostKey.trim()}
                    onClick={() => { setTok("service_costs", newCostKey.trim(), 1); setNewCostKey(""); }}
                    data-testid="token-add-cost">+ Tambah layanan</button>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="rm-btn-primary" disabled={busy || !tokDraft}
                  onClick={() => saveDraft(tokValue())}
                  data-testid="token-save-draft">Simpan sebagai Draf</button>
                {state.has_draft
                  ? <span className="self-center text-xs text-amber-300">Menyimpan menimpa draf yang ada</span>
                  : null}
              </div>
            </section>
          ) : area === "content" ? (
            <section className="rm-card space-y-3 p-5 text-sm">
              <h2 className="flex items-center gap-2 text-base font-bold"><LayoutTemplate className="h-4 w-4 text-zinc-400" /> Konten landing page</h2>
              <p className="text-zinc-400">
                Area ini membungkus Landing Page CMS. Halaman publik selalu membaca versi <em>terbit</em> —
                draf tidak pernah tampil sebelum diterbitkan. Super Admin dapat membuka editor dan menyimpan
                perubahan sebagai <strong>draf</strong> (bukan terbit langsung) dari halaman CMS.
              </p>
              {state.has_draft
                ? <p className="rounded-xl border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-amber-200">Draf menunggu ditinjau. Buka editor CMS untuk mengubahnya, atau terbitkan/buang dari sini.</p>
                : <p className="text-zinc-500">Belum ada draf. Simpan draf dari editor CMS untuk menyiapkan perubahan bertahap.</p>}
              <Link to="/admin/cms" className="rm-btn-ghost inline-flex items-center gap-2">Buka Editor CMS</Link>
            </section>
          ) : (
            <section className="rm-card space-y-4 p-5">
              <h2 className="text-base font-bold">Prosedur operasional</h2>
              <p className="text-sm text-zinc-400">Konsumsi langsung oleh penjadwal, penarikan, dan batas unggah. Daftar nilai dipisah koma.</p>
              <div className="grid gap-4 sm:grid-cols-2">
                {PROCEDURE_FIELDS.map(([key, labelText, kind, ph]) => (
                  <label key={key} className="space-y-1 text-sm">
                    <span className="text-zinc-400">{labelText}</span>
                    <input className="rm-input w-full" placeholder={ph}
                      value={procDisplay(procDraft?.[key])}
                      onChange={(e) => setProcDraft((d) => ({ ...(d || {}), [key]: kind === "list" ? e.target.value : e.target.value }))} />
                  </label>
                ))}
              </div>
              <div className="flex flex-wrap gap-2">
                <button className="rm-btn-primary" disabled={busy || !procDraft}
                  onClick={() => saveDraft(procValue())}>Simpan sebagai Draf</button>
                {state.has_draft
                  ? <span className="self-center text-xs text-amber-300">Menyimpan menimpa draf yang ada</span>
                  : null}
              </div>
            </section>
          )}

          <section className="rm-card space-y-3 p-5">
            <h2 className="flex items-center gap-2 text-base font-bold"><History className="h-4 w-4 text-zinc-400" /> Riwayat versi</h2>
            {!state.history?.length ? <p className="text-sm text-zinc-500">Belum ada riwayat — versi awal akan tercatat pada penerbitan pertama.</p> : (
              <div className="divide-y divide-white/5 text-sm">
                {state.history.map((h) => (
                  <div key={h.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <div><span className="font-bold">v{h.version}</span><span className="ml-3 text-zinc-400">{fmt(h.at)}</span><span className="ml-3 text-zinc-500">{h.note || "—"}</span></div>
                    <button className="rm-btn-ghost text-xs" disabled={busy} onClick={() => restore(h.id)}>Pulihkan sebagai draf</button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="rm-card space-y-3 p-5">
            <h2 className="flex items-center gap-2 text-base font-bold"><ScrollText className="h-4 w-4 text-zinc-400" /> Audit</h2>
            {!audit.length ? <p className="text-sm text-zinc-500">Belum ada entri audit.</p> : (
              <div className="divide-y divide-white/5 text-sm">
                {audit.slice(0, 30).map((e) => (
                  <div key={e.id} className="py-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="font-mono text-xs text-zinc-500">{e.id}</span>
                      <span className="font-bold">{KIND_LABEL[e.kind] || e.kind}</span>
                      <span className="text-zinc-400">{fmt(e.at)}</span>
                      <span className="text-zinc-500">{e.note || ""}</span>
                    </div>
                    {e.diff?.length ? (
                      <details className="mt-1">
                        <summary className="cursor-pointer text-xs text-zinc-500 hover:text-zinc-300">{e.diff.length} perubahan</summary>
                        <ul className="mt-1 space-y-0.5 pl-4 text-xs text-zinc-400">
                          {e.diff.slice(0, 20).map((d, i) => (
                            <li key={i}><span className="text-zinc-300">{d.field}</span>: {JSON.stringify(d.before)} → {JSON.stringify(d.after)}</li>
                          ))}
                        </ul>
                      </details>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {showPublish && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setShowPublish(false)}>
          <div className="rm-card w-full max-w-md space-y-4 p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold">Terbitkan versi baru</h3>
            <p className="text-sm text-zinc-400">Versi terbit saat ini dipindahkan ke riwayat dan dapat dipulihkan. Catatan wajib diisi untuk audit.</p>
            <textarea className="rm-input min-h-[80px] w-full" placeholder="Catatan penerapan (wajib)"
              value={publishNote} onChange={(e) => setPublishNote(e.target.value)} />
            <div className="flex justify-end gap-2">
              <button className="rm-btn-ghost" onClick={() => setShowPublish(false)}>Batal</button>
              <button className="rm-btn-primary" onClick={publish} disabled={busy}>Terbitkan</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
