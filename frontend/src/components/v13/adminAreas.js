import { BarChart3, Home, SlidersHorizontal, UsersRound } from "lucide-react";

// V13 splits the admin console into the everyday Platform/Staff sidebar and three
// header areas. Items keep the permissions the server already filtered; unknown or
// custom keys stay on the Platform sidebar.
export const ADMIN_AREAS = [
  { id: "platform", label: "Beranda", icon: Home },
  { id: "finance", label: "Pemantauan Keuangan", icon: BarChart3 },
  { id: "access", label: "Staf & Akses", icon: UsersRound },
  { id: "settings", label: "Pengaturan Platform", icon: SlidersHorizontal },
];

const AREA_BY_KEY = {
  finance_funds: "finance", finance_catalogue: "finance", finance_cash: "finance", finance_tokens: "finance", settings_plans: "settings",
  analytics: "finance", analytics_audit: "finance", xendit_recon: "finance",
  staff: "access", attendance: "access", staff_config: "access", performance: "access",
  performance_config: "access", admin_users: "access", roles: "access",
  compensation_payroll: "access", compensation_staff: "access", compensation_bonus: "access",
  compensation_bonus_rules: "access", compensation_adjustments: "access",
  cms: "settings", ui_settings: "settings", activity: "settings",
  status: "staff", my_performance: "staff", compensation_me: "staff",
};

export const areaForKey = (key) => AREA_BY_KEY[key] || "platform";

export const DEDICATED_AREAS = new Set(["finance", "access", "settings"]);

// Routes outside the configurable navigation that still belong to an area.
const EXTRA_ROUTE_AREAS = [["/admin/notifications", "settings"], ["/admin/finance", "finance"], ["/admin/settings", "settings"]];

export function matchNavItem(items, pathname) {
  let best = null;
  for (const item of items) {
    if (!item.route) continue;
    if ((pathname === item.route || pathname.startsWith(`${item.route}/`)) && (!best || item.route.length > best.route.length)) best = item;
  }
  return best;
}

export function areaForPath(items, pathname) {
  const item = matchNavItem(items, pathname);
  if (item) return areaForKey(item.key);
  const extra = EXTRA_ROUTE_AREAS.find(([route]) => pathname === route || pathname.startsWith(`${route}/`));
  return extra ? extra[1] : "platform";
}

export function itemsByArea(items) {
  const result = { platform: [], staff: [], finance: [], access: [], settings: [] };
  for (const item of items) result[areaForKey(item.key)].push(item);
  return result;
}

// V13 sidebar names and order (prototype navSeed115 after the v126 removals).
// Production-only menus are nested under the V13 menu they belong to; keys not
// listed keep their server order after the V13 ones.
const V13_ORDER = ["dashboard", "work", "labels", "contracts", "releases", "royalty", "withdraw", "payments", "addon_orders", "wami", "tickets", "status", "my_performance", "compensation_me"];
const V13_PARENT = { kyc: "labels", migrate: "labels", artists: "releases", royalty_adjustments: "royalty" };
export const V13_LABELS = {
  work: { id: "Pekerjaan Saya", en: "My Work" },
  contracts: { id: "Kontrak Label", en: "Label Contracts" },
  releases: { id: "Rilisan", en: "Releases" },
  royalty: { id: "Royalti", en: "Royalties" },
  withdraw: { id: "Penarikan", en: "Withdrawals" },
  payments: { id: "Transaksi", en: "Transactions" },
  tickets: { id: "Tiket Bantuan", en: "Support Tickets" },
  status: { id: "Ringkasan Tim", en: "Team Overview" },
  compensation_me: { id: "Kompensasi", en: "Compensation" },
};

export function arrangeV13(list) {
  const keys = new Set(list.map((item) => item.key));
  const parentOf = (item) => {
    const parent = V13_PARENT[item.key] || item.parent_key;
    return parent && keys.has(parent) ? parent : null;
  };
  const rank = (item) => { const index = V13_ORDER.indexOf(item.key); return index < 0 ? V13_ORDER.length : index; };
  const roots = list.filter((item) => !parentOf(item)).map((item, index) => ({ item, index }))
    .sort((a, b) => rank(a.item) - rank(b.item) || a.index - b.index).map(({ item }) => item);
  return roots.flatMap((root) => [{ ...root, v13Child: false }, ...list.filter((item) => parentOf(item) === root.key).map((item) => ({ ...item, v13Child: true }))]);
}

// V13 Financial Monitoring tabs (Super Admin only, read-only reports).
export const FINANCE_MONITOR_ITEMS = [
  { key: "finance_funds", route: "/admin/finance/funds", icon: "Wallet", labels: { id: "Pemantauan Dana", en: "Funds Monitoring" } },
  { key: "finance_catalogue", route: "/admin/finance/catalogue", icon: "TrendingUp", labels: { id: "Perkembangan Katalog", en: "Catalogue Growth" } },
  { key: "finance_cash", route: "/admin/finance/cash", icon: "Scale", labels: { id: "Rekonsiliasi Kas", en: "Cash Reconciliation" } },
  { key: "finance_tokens", route: "/admin/finance/tokens", icon: "Coins", labels: { id: "Token", en: "Tokens" } },
  { key: "settings_plans", route: "/admin/settings/plans", icon: "Tags", labels: { id: "Paket & Layanan", en: "Plans & Services" } },
];
