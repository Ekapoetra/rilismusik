import React from "react";
import { Link } from "react-router-dom";
import { LockKeyhole } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";

export const initialsOf = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "RM";

// Neutral V13 sidebar: no enclosing card or toggle button; clicking empty space
// collapses it while menu links still navigate.
export function V13Sidebar({ links, switcher, collapsed = false, onToggle, onNavigate, footer, instance = "desktop" }) {
  const { t } = useAppPreferences();
  const onEmptyClick = (event) => { if (onToggle && !event.target.closest("a,button")) onToggle(); };
  return <aside className={`v13-side ${collapsed ? "is-collapsed" : ""}`} onClick={onEmptyClick} aria-label={t("Navigasi")} data-testid={`v13-sidebar-${instance}`}>
    {switcher && <div className="v13-switch" data-mode={switcher.mode} role="group" aria-label={t("Ruang kerja")}>
      {[["platform", "Platform"], ["staff", "Staff"]].map(([mode, label]) => <button key={mode} type="button" aria-pressed={switcher.mode === mode} onClick={() => switcher.onChange(mode)} data-testid={`v13-switch-${mode}-${instance}`}>{t(label)}</button>)}
    </div>}
    <nav>
      {links.map((link) => {
        if (link.group) return collapsed ? null : <div key={link.key} className="v13-side-group">{link.group}</div>;
        const Icon = link.icon;
        return <Link key={link.key} to={link.to} onClick={onNavigate} title={collapsed ? link.label : undefined} aria-current={link.active ? "page" : undefined} className={`v13-side-link ${link.child ? "is-child" : ""} ${link.active ? "is-active" : ""}`} data-testid={link.testId ? (instance === "desktop" ? link.testId : `${link.testId}-${instance}`) : undefined}>
          {!link.child && Icon && <Icon aria-hidden="true" />}<span className="min-w-0 truncate">{link.label}</span>{link.locked && !collapsed && <LockKeyhole className="ml-auto h-3.5 w-3.5 opacity-60" aria-label={t("Perlu verifikasi")} />}
        </Link>;
      })}
    </nav>
    {footer && <div className="v13-side-foot"><span className="v13-avatar" translate="no">{initialsOf(footer.name)}</span><div translate="no"><span>{t("Halo,")}</span><strong>{footer.name}</strong><span>{footer.sub}</span></div></div>}
  </aside>;
}
