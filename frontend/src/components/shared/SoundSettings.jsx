import React, { useState } from "react";
import { Volume2, VolumeX, Play, BellRing, MessageCircle, AlertTriangle, Moon } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { playNotificationSound } from "@/lib/notificationSound";

const get = (k, d) => { const v = localStorage.getItem(k); return v === null ? d : v; };

function Toggle({ checked, onChange, testid }) {
  return (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} data-testid={testid}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${checked ? "bg-[#FF1F8E]" : "bg-white/15"}`}>
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${checked ? "translate-x-[22px]" : "translate-x-0.5"}`} />
    </button>
  );
}

export default function SoundSettings() {
  const { t, volume, setVolume } = useAppPreferences();
  const [mute, setMute] = useState(get("rm-sound-enabled", "true") === "false");
  const [chat, setChat] = useState(get("rm-sound-chat", "true") !== "false");
  const [notif, setNotif] = useState(get("rm-sound-notification", "true") !== "false");
  const [urgent, setUrgent] = useState(get("rm-sound-urgent", "true") !== "false");
  const [quiet, setQuiet] = useState(get("rm-quiet-enabled", "false") === "true");
  const [qs, setQs] = useState(get("rm-quiet-start", "22:00"));
  const [qe, setQe] = useState(get("rm-quiet-end", "07:00"));

  const setMasterMute = (v) => { setMute(v); localStorage.setItem("rm-sound-enabled", v ? "false" : "true"); };
  const setKind = (key, v, setter) => { setter(v); localStorage.setItem(key, String(v)); };
  const saveQuiet = (en, s, e) => { localStorage.setItem("rm-quiet-enabled", String(en)); localStorage.setItem("rm-quiet-start", s); localStorage.setItem("rm-quiet-end", e); };

  const rows = [
    { key: "rm-sound-chat", label: t("Suara Chat"), desc: t("Nada pendek saat ada pesan chat baru."), Icon: MessageCircle, val: chat, set: (v) => setKind("rm-sound-chat", v, setChat), kind: "chat", testid: "sound-toggle-chat" },
    { key: "rm-sound-notification", label: t("Suara Notifikasi"), desc: t("Nada lembut untuk notifikasi umum."), Icon: BellRing, val: notif, set: (v) => setKind("rm-sound-notification", v, setNotif), kind: "notification", testid: "sound-toggle-notification" },
    { key: "rm-sound-urgent", label: t("Suara Mendesak"), desc: t("Nada ganda tegas untuk hal penting/mendesak."), Icon: AlertTriangle, val: urgent, set: (v) => setKind("rm-sound-urgent", v, setUrgent), kind: "urgent", testid: "sound-toggle-urgent" },
  ];

  return (
    <section className="rm-card p-5" data-testid="sound-settings">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("Suara & Notifikasi")}</div>
          <h2 className="mt-1 font-display text-2xl font-extrabold tracking-tight">{t("Pengaturan Suara")}</h2>
        </div>
        <button type="button" onClick={() => setMasterMute(!mute)} className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-bold ${mute ? "border-red-400/40 bg-red-500/10 text-red-300" : "border-white/10 text-zinc-300"}`} data-testid="sound-master-mute">
          {mute ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />} {mute ? t("Bisukan semua suara: AKTIF") : t("Bisukan semua suara")}
        </button>
      </div>

      <div className={`space-y-3 ${mute ? "opacity-40 pointer-events-none" : ""}`}>
        {rows.map((r) => (
          <div key={r.key} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.02] p-3">
            <div className="flex min-w-0 items-center gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-md bg-white/5"><r.Icon className="h-4 w-4 text-pink-300" /></span>
              <div className="min-w-0"><div className="text-sm font-bold">{r.label}</div><div className="truncate text-xs text-zinc-500">{r.desc}</div></div>
            </div>
            <div className="flex items-center gap-2">
              <button type="button" onClick={() => playNotificationSound(r.kind, null, true)} className="rm-btn-ghost inline-flex items-center gap-1.5 text-xs" data-testid={`sound-test-${r.kind}`}><Play className="h-3.5 w-3.5" /> {t("Uji")}</button>
              <Toggle checked={r.val} onChange={r.set} testid={r.testid} />
            </div>
          </div>
        ))}

        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <div className="flex items-center gap-3">
            <Volume2 className="h-4 w-4 text-zinc-400" />
            <input type="range" min="0" max="1" step="0.05" value={volume} onChange={(e) => setVolume(Number(e.target.value))} className="w-full accent-[#FF1F8E]" data-testid="sound-volume" />
            <span className="w-10 text-right text-xs tabular-nums text-zinc-400">{Math.round(volume * 100)}%</span>
          </div>
        </div>

        <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3"><span className="grid h-9 w-9 place-items-center rounded-md bg-white/5"><Moon className="h-4 w-4 text-indigo-300" /></span><div><div className="text-sm font-bold">{t("Jam Tenang")}</div><div className="text-xs text-zinc-500">{t("Bisukan suara non-mendesak pada rentang jam ini.")}</div></div></div>
            <Toggle checked={quiet} onChange={(v) => { setQuiet(v); saveQuiet(v, qs, qe); }} testid="sound-quiet-toggle" />
          </div>
          {quiet && (
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <label className="text-xs text-zinc-400">{t("Mulai")} <input type="time" value={qs} onChange={(e) => { setQs(e.target.value); saveQuiet(true, e.target.value, qe); }} className="rm-input ml-1 inline-block w-32 py-1" data-testid="sound-quiet-start" /></label>
              <label className="text-xs text-zinc-400">{t("Selesai")} <input type="time" value={qe} onChange={(e) => { setQe(e.target.value); saveQuiet(true, qs, e.target.value); }} className="rm-input ml-1 inline-block w-32 py-1" data-testid="sound-quiet-end" /></label>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
