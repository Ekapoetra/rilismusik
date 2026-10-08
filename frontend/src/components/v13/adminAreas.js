import { BarChart3, Home, SlidersHorizontal, UsersRound } from "lucide-react";

// V13 splits the admin console into the everyday Platform/Staff sidebar and three
// header areas. Items keep the permissions the server already filtered; unknown or
// custom keys stay on the Platform sidebar.
export const ADMIN_AREAS = [
  { id: "platform", label: "Beranda", icon: Home },
  { id: "finance", label: "Monitoring Keuangan", icon: BarChart3 },
  { id: "access", label: "Staf & Akses", icon: UsersRound },
  { id: "settings", label: "Pengaturan Platform", icon: SlidersHorizontal },
];

const AREA_BY_KEY = {
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
const EXTRA_ROUTE_AREAS = [["/admin/notifications", "settings"]];

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
