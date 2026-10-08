import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Menu, Moon, Search, Sparkles, Sun } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

const MastheadContext = createContext(null);

export function MastheadProvider({ children }) {
  const [content, setContent] = useState(null);
  const value = useMemo(() => ({ content, setContent }), [content]);
  return <MastheadContext.Provider value={value}>{children}</MastheadContext.Provider>;
}

// Pages publish their greeting summary and insight as plain data while mounted.
export function useMasthead(content) {
  const context = useContext(MastheadContext);
  const setContent = context?.setContent;
  const key = JSON.stringify(content ?? null);
  useEffect(() => { if (setContent) setContent(key === "null" ? null : JSON.parse(key)); }, [key, setContent]);
  useEffect(() => () => { if (setContent) setContent(null); }, [setContent]);
}

// The V13 tokens apply only while a dashboard layout is mounted.
export function useV13Document() {
  useEffect(() => {
    document.documentElement.classList.add("v13");
    return () => document.documentElement.classList.remove("v13");
  }, []);
}

export function ThemeSwitch() {
  const { theme, setMode, t } = useAppPreferences();
  const [switching, setSwitching] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);
  const dark = theme === "dark";
  const toggle = () => {
    setSwitching(true);
    setMode(dark ? "light" : "dark");
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setSwitching(false), 450);
  };
  return <button type="button" role="switch" aria-checked={dark} aria-label={t(dark ? "Mode gelap" : "Mode terang")} title={t(dark ? "Mode gelap" : "Mode terang")} onClick={toggle} className={`v13-theme ${switching ? "is-switching" : ""}`} data-testid="v13-theme-switch"><span>{dark ? <Moon /> : <Sun />}</span></button>;
}

export function LanguageToggle() {
  const { locale, setLocale, t } = useAppPreferences();
  return <button type="button" className="v13-lang" title={t("Bahasa")} aria-label={t("Bahasa")} onClick={() => setLocale(locale === "id" ? "en" : "id")} data-testid="v13-language-toggle">{locale.toUpperCase()}</button>;
}

// Searches the menus this account can actually open.
function MenuSearch({ items }) {
  const { t } = useAppPreferences();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const wrap = useRef(null);
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (q ? items.filter((item) => `${item.label} ${item.hint || ""}`.toLowerCase().includes(q)) : items).slice(0, 12);
  }, [items, query]);
  useEffect(() => {
    if (!open) return undefined;
    const close = (event) => { if (!wrap.current?.contains(event.target)) setOpen(false); };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, [open]);
  const go = (to) => { setOpen(false); setQuery(""); navigate(to); };
  return <div className="v13-search" ref={wrap}>
    <Search aria-hidden="true" />
    <input value={query} placeholder={t("Cari")} aria-label={t("Cari menu")} onFocus={() => setOpen(true)} onClick={() => setOpen(true)} onChange={(event) => { setQuery(event.target.value); setOpen(true); }} onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); if (event.key === "Enter" && matches[0]) go(matches[0].to); }} data-testid="v13-search-input" />
    {open && <div className="v13-popover" role="listbox" data-testid="v13-search-results">{matches.length ? matches.map((item) => <button type="button" key={item.to} onClick={() => go(item.to)}>{item.label}{item.hint && <small>{item.hint}</small>}</button>) : <div className="px-3 py-2 text-sm text-[var(--ui-muted)]">{t("Tidak ada menu yang cocok.")}</div>}</div>}
  </div>;
}

export function Masthead({ name, home, areas = [], searchItems = [], tools, brandTo, onMenu, defaultSummary }) {
  const { t } = useAppPreferences();
  const content = useContext(MastheadContext)?.content;
  const [scrolled, setScrolled] = useState(() => typeof window !== "undefined" && window.scrollY > 48);
  useEffect(() => {
    // Fold after a short scroll; reopen only at the very top so scrolling up mid-page never reopens it.
    const onScroll = () => setScrolled((current) => (current ? window.scrollY > 0 : window.scrollY > 48));
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);
  const folded = !home || scrolled;
  const insight = content?.insight;
  const summary = content?.summary ?? defaultSummary;
  const InsightTag = insight?.to ? Link : "div";
  return <header className={`v13-masthead ${folded ? "is-folded" : ""}`} data-testid="v13-masthead">
    <div className="v13-bar">
      {onMenu && <button type="button" onClick={onMenu} aria-label={t("Buka menu")} className="ui-icon-button md:hidden" data-testid="v13-menu-open"><Menu className="h-5 w-5" /></button>}
      <Link to={brandTo} className="v13-brand" data-testid="v13-brand"><span className="v13-mark" aria-hidden="true">RM</span><strong translate="no">RILIS MUSIK</strong></Link>
      <MenuSearch items={searchItems} />
      <nav className="v13-areas" aria-label={t("Area kerja")}>
        {areas.length > 1 && areas.map((area) => { const Icon = area.icon; return <Link key={area.id} to={area.to} title={t(area.label)} aria-label={t(area.label)} aria-current={area.active ? "page" : undefined} className={`v13-area ${area.active ? "is-active" : ""}`} data-testid={`v13-area-${area.id}`}><Icon /></Link>; })}
      </nav>
      <div className="v13-tools">{tools}</div>
    </div>
    <div className="v13-fold" aria-hidden={folded || undefined}>
      <div>
        <div className="v13-hero" data-testid="v13-greeting">
          <div>
            <h1 translate="no">{t("Halo,")}<br />{name}.</h1>
            {summary && <p data-testid="v13-greeting-summary">{summary}</p>}
          </div>
          {insight && <InsightTag {...(insight.to ? { to: insight.to } : {})} className="v13-insight" data-testid="v13-insight">
            <div className="v13-insight-head"><Sparkles aria-hidden="true" />{t("Wawasan")}</div>
            <div className="v13-insight-body">{insight.value !== undefined && insight.value !== null && <strong>{insight.value}</strong>}<div><b>{insight.title}</b>{insight.detail && <small>{insight.detail}</small>}</div></div>
          </InsightTag>}
        </div>
      </div>
    </div>
  </header>;
}
