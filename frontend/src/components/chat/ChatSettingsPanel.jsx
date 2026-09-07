import React, { useEffect, useState } from "react";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { api } from "@/api/client";
import { toast } from "@/components/ui/sonner";

const DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

export const ChatSettingsPanel = ({ onBack }) => {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get("/chat/admin/settings").then((r) => setS(r.data)).catch(() => setS(null)); }, []);
  if (!s) return <div className="grid h-full place-items-center text-sm text-zinc-500">Memuat…</div>;

  const toggleDay = (i) => setS({ ...s, workdays: s.workdays.includes(i) ? s.workdays.filter((d) => d !== i) : [...s.workdays, i].sort() });
  const setSession = (idx, key, val) => setS({ ...s, sessions: s.sessions.map((x, i) => (i === idx ? { ...x, [key]: val } : x)) });
  const save = async () => {
    setBusy(true);
    try {
      await api.put("/chat/admin/settings", {
        timezone: s.timezone || "Asia/Jakarta", workdays: s.workdays, sessions: s.sessions,
        holidays: (Array.isArray(s.holidays) ? s.holidays : String(s.holidays || "").split(",")).map((x) => x.trim()).filter(Boolean),
        auto_reply_enabled: s.auto_reply_enabled, auto_reply_message: s.auto_reply_message,
      });
      toast.success("Pengaturan chat tersimpan.");
      onBack();
    } catch (e) { toast.error(e.response?.data?.detail || "Gagal menyimpan"); }
    finally { setBusy(false); }
  };

  return (
    <div className="flex h-full flex-col" data-testid="admin-chat-settings">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
        <button onClick={onBack} className="text-zinc-400 hover:text-white"><ArrowLeft className="h-4 w-4" /></button>
        <div className="text-sm font-bold text-white">Jam Operasional & Auto-Reply</div>
      </div>
      <div className="flex-1 space-y-4 overflow-y-auto p-4 text-sm">
        <div>
          <div className="mb-1.5 text-xs font-bold uppercase tracking-widest text-zinc-500">Hari Kerja (WIB)</div>
          <div className="flex flex-wrap gap-1.5">
            {DAYS.map((d, i) => (
              <button key={i} onClick={() => toggleDay(i)} className={`rounded-full px-3 py-1.5 text-xs font-semibold ${s.workdays.includes(i) ? "bg-[#FF1F8E] text-white" : "bg-white/[0.05] text-zinc-400"}`} data-testid={`chat-settings-day-${i}`}>{d}</button>
            ))}
          </div>
        </div>
        <div>
          <div className="mb-1.5 text-xs font-bold uppercase tracking-widest text-zinc-500">Sesi Jam Kerja</div>
          {s.sessions.map((sess, i) => (
            <div key={i} className="mb-2 flex items-center gap-2">
              <input type="time" className="rm-input" value={sess.start} onChange={(e) => setSession(i, "start", e.target.value)} data-testid={`chat-settings-session-${i}-start`} />
              <span className="text-zinc-500">—</span>
              <input type="time" className="rm-input" value={sess.end} onChange={(e) => setSession(i, "end", e.target.value)} data-testid={`chat-settings-session-${i}-end`} />
            </div>
          ))}
          <p className="text-[11px] text-zinc-500">Jeda di antara dua sesi otomatis dianggap jam istirahat.</p>
        </div>
        <div>
          <div className="mb-1.5 text-xs font-bold uppercase tracking-widest text-zinc-500">Hari Libur (opsional)</div>
          <input className="rm-input" placeholder="2026-06-01, 2026-08-17" value={Array.isArray(s.holidays) ? s.holidays.join(", ") : s.holidays || ""} onChange={(e) => setS({ ...s, holidays: e.target.value })} data-testid="chat-settings-holidays" />
        </div>
        <div>
          <label className="flex items-center gap-2"><input type="checkbox" checked={!!s.auto_reply_enabled} onChange={(e) => setS({ ...s, auto_reply_enabled: e.target.checked })} data-testid="chat-settings-autoreply-toggle" /> <span className="font-semibold">Aktifkan auto-reply di luar jam operasional</span></label>
          <textarea className="rm-input mt-2 min-h-[90px]" value={s.auto_reply_message || ""} onChange={(e) => setS({ ...s, auto_reply_message: e.target.value })} data-testid="chat-settings-autoreply-message" />
        </div>
      </div>
      <div className="border-t border-white/10 p-3">
        <button onClick={save} disabled={busy} className="rm-btn-primary inline-flex w-full items-center justify-center gap-2" data-testid="chat-settings-save">{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Simpan</button>
      </div>
    </div>
  );
};
