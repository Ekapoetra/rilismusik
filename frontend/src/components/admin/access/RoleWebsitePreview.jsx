import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Bell, Languages, Sun, Moon, Menu, Plus, Search, ArrowUpRight, ShieldCheck } from "lucide-react";
import { AdminSidebarView } from "@/components/shared/AdminLayout";
import { DashboardBrand } from "@/components/shared/DashboardBrand";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import { setLocale } from "@/i18n/languageStore";

const allowedNav = (navigation, permissions, superAdmin) => {
  const perms = new Set(permissions);
  const implied = { "access.users.manage": "access.users.view", "access.roles.manage": "access.roles.view", "ui.settings.manage": "ui.settings.view", "migration.claims": "migration.view" };
  Object.entries(implied).forEach(([source, target]) => { if (perms.has(source)) perms.add(target); });
  const visible = navigation.filter((item) => item.visible !== false && (superAdmin || !item.permission || perms.has(item.permission)));
  return visible;
};
const validate = (data) => {
  if (data?.type !== "rilis-role-preview-config" || !Array.isArray(data.navigation) || !Array.isArray(data.permissions) || data.navigation.length > 150 || data.permissions.length > 300) return null;
  const navigation = data.navigation.filter((item) => item && /^[\w-]{1,80}$/.test(item.key) && /^\/admin(?:\/[a-zA-Z0-9_-]+)*$/.test(item.route) && item.key !== "label_rates" && /^[a-zA-Z0-9]+$/.test(item.icon || "Circle")).map((item) => ({ key: item.key, route: item.route, icon: item.icon, permission: String(item.permission || ""), visible: item.visible !== false, parent_key: typeof item.parent_key === "string" ? item.parent_key : null, labels: { id: String(item.labels?.id || item.key).slice(0, 120), en: String(item.labels?.en || item.labels?.id || item.key).slice(0, 120) } }));
  return { navigation, permissions: data.permissions.filter((value) => typeof value === "string" && /^[a-z_.]+$/.test(value)), superAdmin: data.roleKey === "super_admin", active: data.active !== false, roleName: String(data.roleName || "Role").slice(0, 100), locale: data.locale === "en" ? "en" : "id", theme: data.theme === "light" ? "light" : "dark" };
};

export const RoleWebsitePreview = () => {
  const [config, setConfig] = useState(null); const [collapsed, setCollapsed] = useState(false); const [mobile, setMobile] = useState(false);
  const { locale, theme, setMode, t } = useAppPreferences();
  const location = useLocation(); const navigate = useNavigate();
  useEffect(() => {
    if (window.parent === window) return;
    const receive = (event) => { if (event.origin !== window.location.origin || event.source !== window.parent) return; const next = validate(event.data); if (next) { setConfig(next); setLocale(next.locale, false); setMode(next.theme); } };
    window.addEventListener("message", receive);
    window.parent.postMessage({ type: "rilis-role-preview-ready" }, window.location.origin);
    return () => window.removeEventListener("message", receive);
    // This listener is intentionally installed once; no account/session/API is used.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const navigation = useMemo(() => config && (config.active || config.superAdmin) ? allowedNav(config.navigation, config.permissions, config.superAdmin) : [], [config]);
  useEffect(() => { if (navigation.length && !navigation.some((item) => item.route === location.pathname)) navigate(navigation[0].route, { replace: true }); }, [navigation, location.pathname, navigate]);
  if (!config) return <main className="app-shell grid min-h-screen place-items-center p-8 text-sm text-[var(--ui-muted)]" data-testid="role-preview-waiting">{t("Pratinjau Role")}</main>;
  const selected = navigation.find((item) => item.route === location.pathname);
  const title = selected?.labels?.[locale] || selected?.labels?.id || t("Pratinjau Role");
  const user = { name: config.roleName, role_name: t("Simulasi") };
  return <div className="app-shell" data-testid="role-website-simulation">
    <aside className={`dashboard-sidebar fixed inset-y-0 left-0 z-40 hidden border-r md:block ${collapsed ? "w-[72px]" : "w-64"}`}><AdminSidebarView instance="preview" collapsed={collapsed} onCollapse={() => setCollapsed(!collapsed)} items={navigation} user={user} preview /></aside>
    {mobile && <div className="fixed inset-0 z-50 md:hidden" data-testid="role-preview-mobile-drawer"><button type="button" className="absolute inset-0 bg-black/60" aria-label={t("Tutup menu")} onClick={() => setMobile(false)} data-testid="role-preview-mobile-backdrop" /><aside className="dashboard-sidebar absolute inset-y-0 left-0 w-[min(86vw,320px)] border-r"><AdminSidebarView instance="mobile" collapsed={false} onNavigate={() => setMobile(false)} items={navigation} user={user} preview /></aside></div>}
    <div className={collapsed ? "md:ml-[72px]" : "md:ml-64"}><header className="dashboard-header flex h-16 items-center justify-between gap-3 border-b px-4 sm:px-6" data-testid="role-preview-topbar"><div className="flex min-w-0 items-center gap-2"><button type="button" onClick={() => setMobile(!mobile)} className="ui-icon-button md:hidden" aria-label={t("Buka menu")} data-testid="role-preview-mobile-menu"><Menu className="h-4 w-4" /></button><div className="md:hidden"><DashboardBrand compact testId="role-preview-brand" /></div><div className="hidden text-sm font-bold md:block">{t("Admin Console")}</div></div><div className="flex items-center gap-2"><span className="ui-icon-button" aria-hidden="true">{theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}</span><span className="ui-icon-button gap-1 text-[9px]" aria-hidden="true"><Languages className="h-3.5 w-3.5" />{locale.toUpperCase()}</span><span className="ui-icon-button" aria-hidden="true"><Bell className="h-4 w-4" /></span></div></header>
      <main className="space-y-7 p-4 sm:p-6" data-testid="role-preview-page-content"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--ui-border)] pb-5"><div className="min-w-0"><p className="text-[10px] font-bold uppercase text-[var(--ui-muted)]">{t("Simulasi")} · {t("Baca-saja")}</p><h1 className="mt-2 break-words font-display text-3xl font-bold" data-testid="role-preview-page-title">{title}</h1></div><span className="inline-flex items-center gap-1.5 text-xs text-emerald-500"><ShieldCheck className="h-4 w-4" />{config.permissions.length} {t("izin")}</span></div>
        <p className="text-xs text-[var(--ui-muted)]" data-testid="role-preview-data-disclosure">{t("Data contoh — bukan data bisnis asli")}</p>
        {navigation.length ? <PreviewPageContent section={selected?.key} title={title} permissions={config.permissions} superAdmin={config.superAdmin} /> : <div className="py-12 text-center text-sm text-[var(--ui-muted)]" data-testid="role-preview-empty">{t("Tidak ada menu yang diizinkan.")}</div>}
      </main>
    </div>
  </div>;
};

const PreviewPageContent = ({ section, title, permissions, superAdmin }) => {
  const { t } = useAppPreferences();
  const actionPermissions = { labels: ["labels.manage", "labels.rate"], artists: ["artists.manage"], releases: ["releases.review"], payments: ["payments.manage"], royalty: ["royalty.import", "royalty.manage"], royalty_adjustments: ["royalty.manage"], withdraw: ["withdraw.manage"], wami: ["wami.manage"], tickets: ["support.manage"], cms: ["cms.manage"], contracts: ["contracts.manage"], admin_users: ["access.users.manage"], roles: ["access.roles.manage"], ui_settings: ["ui.settings.manage"], migrate: ["migration.manage", "migration.claims"], kyc: ["kyc.review"], analytics: ["analytics.manage"] };
  const canEdit = Boolean(actionPermissions[section]) && (superAdmin || actionPermissions[section].some((value) => permissions.includes(value)));
  const finance = /royalty|withdraw|payments|analytics/.test(section || "");
  return <>
    <div className="grid gap-6 border-b border-[var(--ui-border)] pb-6 sm:grid-cols-3">{[[finance ? "Saldo tersedia" : "Total Rilisan", finance ? "Rp 12.500.000" : "24"], [finance ? "Penarikan Dana" : "Diproses", finance ? "Rp 2.500.000" : "3"], [finance ? "Periode" : "Aktif", finance ? "2026-08" : "21"]].map(([label, value], index) => <div key={index}><div className="text-xs text-[var(--ui-muted)]">{t(label)}</div><div className="mt-2 font-display text-2xl font-bold" translate="no" data-testid={`role-preview-stat-${index}`}>{value}</div></div>)}</div>
    <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2 text-sm text-[var(--ui-muted)]"><Search className="h-4 w-4" />{t("Cari")} {title}</div>{canEdit && <button type="button" disabled className="rm-btn-primary inline-flex items-center gap-2 opacity-60" data-testid="role-preview-action-button"><Plus className="h-4 w-4" />{t("Tambah")}</button>}</div>
    <div className="divide-y divide-[var(--ui-border)] border-y border-[var(--ui-border)]" data-testid="role-preview-example-table"><div className="grid grid-cols-[1fr_100px] gap-3 py-3 text-xs text-[var(--ui-muted)] sm:grid-cols-[1.5fr_1fr_100px]"><span>{t(finance ? "Label" : "Judul Rilisan")}</span><span className="hidden sm:block">{t(finance ? "Jumlah" : "Artis")}</span><span>{t("Status")}</span></div>{[1, 2, 3, 4].map((index) => <div key={index} className="grid grid-cols-[1fr_100px] items-center gap-3 py-4 text-sm sm:grid-cols-[1.5fr_1fr_100px]"><span className="min-w-0 truncate font-semibold" translate="no">{finance ? `Sample Label ${index}` : `Sample Release ${index}`}</span><span className="hidden text-[var(--ui-muted)] sm:block" translate="no">{finance ? `Rp ${(index * 500000).toLocaleString("id-ID")}` : `Sample Artist ${index}`}</span><span className="inline-flex items-center gap-1 text-xs text-emerald-500">{t(index === 1 ? "Diproses" : "Aktif")}<ArrowUpRight className="h-3 w-3" /></span></div>)}</div>
  </>;
};