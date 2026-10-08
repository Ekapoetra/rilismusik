import React, { useCallback, useEffect, useState } from "react";
import { Wrench, RefreshCw, Plus, Pencil, X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";

const MODULES = [
  ["all", "Seluruh sistem"], ["releases", "Rilisan"], ["payments", "Pembayaran"],
  ["royalty", "Royalti & penarikan"], ["tickets", "Tiket bantuan"], ["wami", "WAMI"],
  ["addons", "Layanan tambahan"], ["account", "Akun & aktivasi"],
];
const KINDS = [["scheduled", "Terjadwal"], ["emergency", "Darurat"]];
const MODES = [["info", "Pengumuman"], ["readonly", "Baca-saja"]];
const NOTIFY = [["none", "Tanpa pengumuman"], ["start", "Saat mulai"], ["1h", "1 jam sebelum"], ["24h", "24 jam sebelum"]];
const STATUS = { scheduled: "Terjadwal", active: "Berjalan", completed: "Selesai", cancelled: "Dibatalkan" };
const TONE = { active: "text-red-300 border-red-400/40 bg-red-500/10", scheduled: "text-sky-300 border-sky-400/40 bg-sky-500/10", completed: "text-zinc-400 border-white/10 bg-white/[0.04]", cancelled: "text-zinc-400 border-white/10 bg-white/[0.04]" };

const fmt = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : new Intl.DateTimeFormat("id-ID", { timeZone: "Asia/Jakarta", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d).replace(".", ":") + " WIB";
};
const toLocal = (iso) => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(d).replace(" ", "T");
};
const toIso = (local) => local ? new Date(local + ":00+07:00").toISOString() : "";
const label = (list, key) => (list.find(([k]) => k === key) || [])[1] || key;
const modsLabel = (mods) => mods.includes("all") ? "Seluruh sistem" : mods.map((m) => label(MODULES, m)).join(" · ");

const EMPTY = { title: "", kind: "scheduled", mode: "info", start_at: "", end_at: "", modules: [], message: "", notify: "start", note: "" };

export default function Maintenance() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState(null); // null | {id?, ...fields}
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setErr("");
    try {
      const { data } = await api.get("/admin/maintenance");
      setRows(data?.windows || []);
    } catch (e) { setErr(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openEditor = (w) => setEditing(w ? {
    id: w.id, title: w.title, kind: w.kind, mode: w.mode,
    start_at: toLocal(w.start_at), end_at: toLocal(w.end_at),
    modules: [...(w.modules || [])], message: w.message, notify: w.notify, note: w.note || "",
  } : { ...EMPTY });
  const set = (k, v) => setEditing((e) => ({ ...e, [k]: v }));
  const toggleModule = (m) => setEditing((e) => ({ ...e, modules: e.modules.includes(m) ? e.modules.filter((x) => x !== m) : [...e.modules, m] }));

  const save = async (ev) => {
    ev.preventDefault();
    if (!editing.modules.length) { toast.error("Pilih minimal satu modul terdampak"); return; }
    setBusy(true);
    const payload = { ...editing, start_at: toIso(editing.start_at), end_at: toIso(editing.end_at), note: editing.note || null };
    delete payload.id;
    try {
      if (editing.id) await api.patch(`/admin/maintenance/${editing.id}`, payload);
      else await api.post("/admin/maintenance", payload);
      toast.success(editing.id ? "Jadwal diperbarui." : "Jadwal dibuat.");
      setEditing(null);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const setStatus = async (w, status) => {
    setBusy(true);
    try {
      await api.post(`/admin/maintenance/${w.id}/status`, { status });
      toast.success(`Status: ${STATUS[status]}.`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const ordered = [...rows].sort((a, b) => ({ active: 0, scheduled: 1 }[a.effective_status] ?? 2) - ({ active: 0, scheduled: 1 }[b.effective_status] ?? 2) || new Date(a.start_at) - new Date(b.start_at));

  return (
    <div className="space-y-6" data-testid="admin-maintenance-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Sistem</div>
          <h1 className="mt-1 flex items-center gap-2 font-display text-3xl font-extrabold"><Wrench className="h-6 w-6 text-pink-400" /> Pemeliharaan</h1>
          <p className="mt-2 max-w-2xl text-sm text-zinc-400">Jadwalkan jeda layanan: rentang waktu, modul terdampak, dan pesan untuk member. Banner tampil sesuai waktu pengumuman yang dipilih.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={load} className="rm-btn-ghost inline-flex items-center gap-2 text-sm" data-testid="maint-refresh"><RefreshCw className="h-4 w-4" /> Muat ulang</button>
          <button type="button" onClick={() => openEditor(null)} className="rm-btn-primary inline-flex items-center gap-2 text-sm" data-testid="maint-new"><Plus className="h-4 w-4" /> Jadwalkan</button>
        </div>
      </header>

      {err && <div className="rounded-md bg-red-500/15 px-4 py-3 text-sm text-red-300" data-testid="maint-error">{err}</div>}
      {loading && <p className="text-sm text-zinc-500">Memuat…</p>}

      {!loading && ordered.length === 0 && (
        <div className="rounded-md border border-white/10 py-16 text-center text-sm text-zinc-500" data-testid="maint-empty">Belum ada jadwal pemeliharaan.</div>
      )}

      <div className="space-y-3">
        {ordered.map((w) => (
          <section key={w.id} className="rm-card p-4" data-testid={`maint-row-${w.id}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <strong>{w.title}</strong>
                  <span className={`rounded-full border px-2 py-0.5 text-[11px] font-bold ${TONE[w.effective_status] || TONE.completed}`} data-testid={`maint-status-${w.id}`}>{STATUS[w.effective_status] || w.effective_status}</span>
                  <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-zinc-400">{label(KINDS, w.kind)} · {w.mode === "readonly" ? "Baca-saja" : "Pengumuman"}</span>
                </div>
                <div className="mt-1 text-xs text-zinc-500">{fmt(w.start_at)} – {fmt(w.end_at)} · {modsLabel(w.modules)}</div>
                <p className="mt-1.5 text-sm text-zinc-400">{w.message}</p>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <button onClick={() => openEditor(w)} className="rm-btn inline-flex items-center gap-1.5 text-xs" data-testid={`maint-edit-${w.id}`}><Pencil className="h-3.5 w-3.5" /> Ubah</button>
                {w.effective_status === "scheduled" && <button onClick={() => setStatus(w, "active")} disabled={busy} className="rm-btn text-xs text-emerald-300" data-testid={`maint-activate-${w.id}`}>Mulai sekarang</button>}
                {["scheduled", "active"].includes(w.effective_status) && <button onClick={() => setStatus(w, "cancelled")} disabled={busy} className="rm-btn-ghost text-xs text-red-300" data-testid={`maint-cancel-${w.id}`}>Batalkan</button>}
                {w.effective_status === "active" && <button onClick={() => setStatus(w, "completed")} disabled={busy} className="rm-btn text-xs" data-testid={`maint-complete-${w.id}`}>Tandai selesai</button>}
                {["cancelled", "completed"].includes(w.effective_status) && <button onClick={() => setStatus(w, "scheduled")} disabled={busy} className="rm-btn-ghost text-xs" data-testid={`maint-reschedule-${w.id}`}>Jadwalkan ulang</button>}
              </div>
            </div>
          </section>
        ))}
      </div>

      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" data-testid="maint-editor">
          <form onSubmit={save} className="rm-card max-h-[90vh] w-full max-w-xl space-y-4 overflow-y-auto p-6">
            <div className="flex items-center justify-between">
              <h2 className="font-display text-xl font-bold">{editing.id ? "Ubah jadwal" : "Jadwal pemeliharaan baru"}</h2>
              <button type="button" onClick={() => setEditing(null)} className="ui-icon-button" aria-label="Tutup"><X className="h-4 w-4" /></button>
            </div>
            <label className="block text-sm">Judul pemeliharaan
              <input required maxLength={160} value={editing.title} onChange={(e) => set("title", e.target.value)} className="rm-input mt-1 w-full" data-testid="maint-f-title" />
            </label>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">Jenis
                <select value={editing.kind} onChange={(e) => set("kind", e.target.value)} className="rm-input mt-1 w-full">{KINDS.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>
              </label>
              <label className="block text-sm">Mode
                <select value={editing.mode} onChange={(e) => set("mode", e.target.value)} className="rm-input mt-1 w-full">{MODES.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>
              </label>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="block text-sm">Mulai · WIB
                <input required type="datetime-local" value={editing.start_at} onChange={(e) => set("start_at", e.target.value)} className="rm-input mt-1 w-full" data-testid="maint-f-start" />
              </label>
              <label className="block text-sm">Selesai · WIB
                <input required type="datetime-local" value={editing.end_at} onChange={(e) => set("end_at", e.target.value)} className="rm-input mt-1 w-full" data-testid="maint-f-end" />
              </label>
            </div>
            <fieldset className="text-sm">
              <legend className="mb-1 text-xs font-bold uppercase tracking-wider text-zinc-500">Modul terdampak</legend>
              <div className="flex flex-wrap gap-2">
                {MODULES.map(([k, n]) => (
                  <label key={k} className={`cursor-pointer rounded-full border px-3 py-1 text-xs font-semibold ${editing.modules.includes(k) ? "border-pink-400/50 bg-pink-500/15 text-pink-200" : "border-white/10 text-zinc-400"}`}>
                    <input type="checkbox" className="hidden" checked={editing.modules.includes(k)} onChange={() => toggleModule(k)} />{n}
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="block text-sm">Pesan untuk member
              <textarea required maxLength={1000} rows={3} value={editing.message} onChange={(e) => set("message", e.target.value)} className="rm-input mt-1 w-full" data-testid="maint-f-message" />
            </label>
            <label className="block text-sm">Pengumuman mulai tampil
              <select value={editing.notify} onChange={(e) => set("notify", e.target.value)} className="rm-input mt-1 w-full">{NOTIFY.map(([k, n]) => <option key={k} value={k}>{n}</option>)}</select>
            </label>
            <label className="block text-sm">Catatan internal — tidak tampil ke member
              <textarea maxLength={1000} rows={2} value={editing.note} onChange={(e) => set("note", e.target.value)} className="rm-input mt-1 w-full" />
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="rm-btn-ghost text-sm">Batal</button>
              <button type="submit" disabled={busy} className="rm-btn-primary text-sm disabled:opacity-40" data-testid="maint-save">{busy ? "Menyimpan…" : "Simpan jadwal"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
