import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useUiLocale } from "@/i18n/SystemText";
import { setLocale, translateUi } from "@/i18n/languageStore";
import { useLocation } from "react-router-dom";
import "@/styles/dashboard-theme.css";
import "@/styles/theme-compat.css";
import { installSoundUnlock } from "@/lib/notificationSound";

const Context = createContext(null);
export const themeForWib = (now = new Date()) => {
  const hour = Number(new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Jakarta", hour: "2-digit", hourCycle: "h23" }).format(now));
  return hour >= 6 && hour < 18 ? "light" : "dark";
};
export const AppPreferencesProvider = ({ children, preview = false }) => {
  const locale = useUiLocale();
  const location = useLocation();
  const [mode, setModeState] = useState(() => { const stored = localStorage.getItem("rm-theme-mode"); return ["light", "dark", "auto"].includes(stored) ? stored : "dark"; });
  const [clock, setClock] = useState(() => new Date());
  useEffect(() => preview ? undefined : installSoundUnlock(), [preview]);
  const [sound, setSoundState] = useState(localStorage.getItem("rm-sound-enabled") !== "false");
  const [volume, setVolumeState] = useState(() => { const stored = Number(localStorage.getItem("rm-sound-volume") ?? "0.75"); return Number.isFinite(stored) ? Math.max(0, Math.min(1, stored)) : 0.75; });
  const dashboard = preview || /^\/(admin|label)(\/|$)/.test(location.pathname);
  const theme = dashboard ? (mode === "auto" ? themeForWib(clock) : mode) : "dark";
  useEffect(() => { const update = () => setClock(new Date()); const timer = setInterval(update, 15000); window.addEventListener("focus", update); return () => { clearInterval(timer); window.removeEventListener("focus", update); }; }, []);
  useEffect(() => { document.documentElement.dataset.appTheme = theme; document.documentElement.classList.toggle("dark", theme === "dark"); document.documentElement.lang = locale; }, [theme, locale]);
  const setMode = useCallback((value) => { if (["light", "dark", "auto"].includes(value)) { setModeState(value); setClock(new Date()); if (!preview) localStorage.setItem("rm-theme-mode", value); } }, [preview]);
  const setSound = useCallback((value) => { setSoundState(Boolean(value)); localStorage.setItem("rm-sound-enabled", String(Boolean(value))); }, []);
  const setVolume = useCallback((value) => { const next = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0.75; setVolumeState(next); localStorage.setItem("rm-sound-volume", String(next)); }, []);
  const value = useMemo(() => ({ locale, setLocale, t: (text) => translateUi(text, locale), mode, theme, setMode, sound, setSound, volume, setVolume }), [locale, mode, theme, setMode, sound, setSound, volume, setVolume]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
};
export const useAppPreferences = () => {
  const context = useContext(Context);
  if (!context) throw new Error("App preferences provider missing");
  return context;
};
export const useOptionalAppPreferences = () => useContext(Context);