const STAFF_ROUTES = ["/admin/workspace", "/admin/staff", "/admin/attendance", "/admin/status", "/admin/performance", "/admin/my-performance", "/admin/compensation", "/admin/admin-users", "/admin/access"];

export const workspaceForRoute = (path) => STAFF_ROUTES.some((route) => path === route || path.startsWith(`${route}/`)) ? "staff" : "platform";

// The server already filters navigation by the signed-in user's permissions.
// Grouping must never restore hidden entries or infer extra permissions.
export function workspaceItems(items, mode) {
  return items.filter((item) => item.visible !== false && workspaceForRoute(item.route || "") === mode);
}

export const staffHome = { key: "workspace_v7", route: "/admin/workspace", icon: "LayoutDashboard", labels: { id: "Overview Staff", en: "Staff Overview" }, visible: true, group_id: "v7_home" };
