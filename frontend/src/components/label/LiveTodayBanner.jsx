import React, { useState } from "react";
import { api, fileUrl, formatApiError } from "@/api/client";
import { toast } from "@/components/ui/sonner";
import { PartyPopper, Disc3, AlertCircle, X, Send } from "lucide-react";

function todayKey() {
  const wib = new Date(Date.now() + 7 * 3600 * 1000);
  return wib.toISOString().slice(0, 10);
}

function Cover({ url }) {
  const [failed, setFailed] = useState(false);
  if (url && !failed) return <img src={fileUrl(url)} alt="" loading="lazy" className="h-14 w-14 shrink-0 rounded-lg object-cover" onError={() => setFailed(true)} />;
  return <div className="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] text-white"><Disc3 className="h-6 w-6" /></div>;
}

export function LiveTodayBanner({ releases = [] }) {
  const [dismissed, setDismissed] = useState(() => {
    try { return JSON.parse(localStorage.getItem(`rm:live_seen:${todayKey()}`) || "[]"); } catch { return []; }
  });
  const [reporting, setReporting] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const visible = releases.filter((r) => !dismissed.includes(r.id));
  if (visible.length === 0) return null;

  const dismiss = (id) => {
    const next = [...dismissed, id];
    setDismissed(next);
    try { localStorage.setItem(`rm:live_seen:${todayKey()}`, JSON.stringify(next)); } catch { /* ignore */ }
  };

  const submitReport = async () => {
    setBusy(true);
    try {
      await api.post("/tickets/label/create", {
        release_id: reporting.id,
        category: "not_live",
        subject: `Rilisan tidak tersedia/live — ${reporting.release_title || ""}`.trim(),
        description: note.trim() || "Rilisan belum tersedia di sebagian/seluruh platform.",
      });
      toast.success("Laporan terkirim ke admin. Kami akan menindaklanjuti ke Believe.");
      setReporting(null); setNote("");
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail) || "Gagal mengirim laporan");
    } finally { setBusy(false); }
  };

  return (
    <div className="space-y-3" data-testid="label-live-today">
      {visible.map((r) => (
        <div key={r.id} className="relative overflow-hidden rounded-xl border border-emerald-400/40 bg-gradient-to-r from-emerald-500/[0.12] to-[#FF1F8E]/[0.1] p-4 sm:p-5" data-testid={`label-live-today-${r.id}`}>
          <button onClick={() => dismiss(r.id)} title="Tutup" className="absolute right-3 top-3 text-emerald-200/70 hover:text-white" data-testid={`label-live-today-dismiss-${r.id}`}><X className="h-4 w-4" /></button>
          <div className="flex items-start gap-3 pr-6">
            <Cover url={r.cover_url} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 text-emerald-300"><PartyPopper className="h-5 w-5" /><span className="text-xs font-bold uppercase tracking-widest">Rilis Hari Ini</span></div>
              <h3 className="mt-1 font-display text-lg font-extrabold tracking-tight text-white">Selamat! <span className="rm-gradient-text">{r.release_title}</span> telah rilis hari ini 🎉</h3>
              <p className="text-sm text-emerald-100/80">{r.artist_name || "—"} kini tayang di platform digital.</p>
              <button onClick={() => { setReporting(r); setNote(""); }} className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-200 hover:text-amber-100" data-testid={`label-live-today-report-${r.id}`}>
                <AlertCircle className="h-3.5 w-3.5" /> Rilismu tidak ada di platform tertentu? Laporkan ke admin
              </button>
            </div>
          </div>
        </div>
      ))}

      {reporting && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={() => setReporting(null)} data-testid="label-live-report-modal">
          <div className="w-full max-w-lg rounded-2xl border border-white/10 bg-zinc-950 p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-display text-lg font-bold">Laporkan Rilisan Tidak Tersedia</h3>
            <p className="mt-1 text-sm text-zinc-400"><b>{reporting.release_title}</b> — sebutkan platform mana yang belum tersedia (mis. Spotify, Apple Music, YouTube Music) agar admin bisa menindaklanjuti ke Believe.</p>
            <textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="Contoh: Belum muncul di Spotify & Apple Music." className="rm-input mt-4 min-h-[100px]" data-testid="label-live-report-note" />
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setReporting(null)} className="rm-btn-ghost">Batal</button>
              <button onClick={submitReport} disabled={busy} className="rm-btn-primary inline-flex items-center gap-2" data-testid="label-live-report-submit"><Send className="h-4 w-4" /> {busy ? "Mengirim…" : "Kirim Laporan"}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
