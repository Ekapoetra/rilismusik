import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles, X } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { APP_VERSION } from "@/version";
import { SECTIONS, updatesActive, UPDATES_PUBLISHED_AT } from "@/pages/label/Updates";

// Shown once per account per release version. Acknowledgement is stored
// server-side (users.updates_seen_version) so it follows the member across
// devices — not just this browser. The archive stays at /label/updates.
export default function UpdatesPopup() {
  const { user } = useAuth();
  const { locale, t } = useAppPreferences();
  const lang = locale === "en" ? "en" : "id";
  const navigate = useNavigate();
  const [closed, setClosed] = useState(false);

  const show = !closed && user?.role === "label" && updatesActive() && user?.updates_seen_version !== APP_VERSION;
  if (!show) return null;

  const acknowledge = () => {
    api.post("/label/updates/seen", { version: APP_VERSION }).catch(() => {});
    setClosed(true);
  };
  const openArchive = () => { acknowledge(); navigate("/label/updates"); };
  const total = SECTIONS.reduce((n, s) => n + s.items.length, 0);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 px-4" data-testid="updates-popup-backdrop">
      <div className="w-full max-w-md rounded-lg border border-white/10 bg-[#0F0F0F]/95 p-6 shadow-2xl backdrop-blur-xl rm-fade-up" role="dialog" aria-modal="true" aria-labelledby="updates-popup-title" data-testid="updates-popup">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-pink-500/15 text-pink-300"><Sparkles className="h-5 w-5" /></span>
            <div>
              <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">{t("Apa yang baru")} · {UPDATES_PUBLISHED_AT}</div>
              <h2 id="updates-popup-title" className="font-display text-xl font-extrabold tracking-tight" data-testid="updates-popup-title">
                {t("Pembaruan")} — v{APP_VERSION}
              </h2>
            </div>
          </div>
          <button type="button" onClick={acknowledge} className="ui-icon-button -mr-1 -mt-1" aria-label={t("Tutup")} data-testid="updates-popup-close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mt-3 text-sm text-zinc-400" data-testid="updates-popup-summary">
          {lang === "en" ? `${total} changes across ${SECTIONS.length} areas since your last visit:` : `${total} perubahan di ${SECTIONS.length} area sejak kunjungan terakhir Anda:`}
        </p>
        <ul className="mt-3 space-y-1.5" data-testid="updates-popup-sections">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <li key={s.id} className="flex items-center gap-2.5 rounded-md border border-white/5 bg-white/[0.03] px-3 py-2 text-sm" data-testid={`updates-popup-section-${s.id}`}>
                <Icon className="h-4 w-4 shrink-0 text-pink-300" />
                <span className="min-w-0 flex-1 truncate font-semibold">{s.title[lang]}</span>
                <span className="shrink-0 text-xs text-zinc-500">{s.items.length}</span>
              </li>
            );
          })}
        </ul>
        <div className="mt-5 flex gap-2">
          <button type="button" onClick={openArchive} className="rm-btn-primary flex-1" data-testid="updates-popup-more">
            {lang === "en" ? "See details" : "Lihat selengkapnya"}
          </button>
          <button type="button" onClick={acknowledge} className="rm-btn-secondary" data-testid="updates-popup-ok">
            {lang === "en" ? "Got it" : "Mengerti"}
          </button>
        </div>
      </div>
    </div>
  );
}
