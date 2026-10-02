import React, { act } from "react";
import { createRoot } from "react-dom/client";
import AdminDashboard from "./Dashboard";
import { api } from "@/api/client";

let mockRole = "super_admin";
let mockMetricsReady = true;
let mockMoneyError = false;
jest.mock("@/api/client", () => ({ api: { get: jest.fn() } }));
// This render regression does not test navigation. CRA's Jest resolver predates
// React Router 7's export map, so replace only its Link boundary in this test.
jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => require("react").createElement("a", { href: to, ...props }, children),
}), { virtual: true });
jest.mock("@/api/AuthContext", () => ({
  useAuth: () => ({ user: { id: "admin-1", name: "Admin", role: mockRole }, hasPermission: () => true }),
}));
jest.mock("@/contexts/AppPreferencesContext", () => ({ useAppPreferences: () => ({ t: (text) => text }) }));
jest.mock("@/hooks/usePollingRead", () => ({
  usePollingRead: (path, params) => {
    let data;
    if (path.endsWith("/metrics")) data = mockMetricsReady ? { total_labels: { value: 12 } } : null;
    else if (path.endsWith("/money")) return { data: mockMoneyError ? null : { value: params.period === "month" ? 250000 : 125000 }, error: mockMoneyError };
    else if (path.endsWith("/queue")) data = { items: [], team_items: [], is_manager: mockRole === "super_admin", synchronizing: false };
    else if (path.endsWith("/in-progress")) data = { items: [] };
    else data = { completed: 0, open: 0, overdue: 0 };
    return { data, error: false };
  },
}));

let root, container;
const element = (id) => container.querySelector(`[data-testid="${id}"]`);
const render = async () => { await act(async () => root.render(<AdminDashboard />)); };
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  mockRole = "super_admin"; mockMetricsReady = true; mockMoneyError = false;
  jest.clearAllMocks();
  api.get.mockResolvedValue({ data: [] });
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

test("super admin dashboard renders money cards after metrics finish loading", async () => {
  mockMetricsReady = false;
  await render(); expect(element("kpi-sales-revenue")).toBeNull();
  mockMetricsReady = true;
  await render();
  expect(element("admin-greeting-message")).not.toBeNull();
  expect(element("kpi-sales-revenue-value").textContent).toContain("125.000");
  expect(element("kpi-requested-withdrawal-value").textContent).toContain("250.000");
  expect(element("kpi-sales-revenue").querySelector(".text-emerald-300")).not.toBeNull();
  expect(element("kpi-requested-withdrawal").querySelector(".text-amber-300")).not.toBeNull();
});

test("staff dashboard renders sales card and updates its independent period", async () => {
  mockRole = "staff";
  await render();
  expect(element("kpi-requested-withdrawal")).toBeNull();
  expect(element("kpi-sales-revenue-value").textContent).toContain("125.000");
  await act(async () => {
    element("kpi-sales-revenue-period").value = "month";
    element("kpi-sales-revenue-period").dispatchEvent(new Event("change", { bubbles: true }));
  });
  expect(element("kpi-sales-revenue-value").textContent).toContain("250.000");
});

test("failed money reads leave dashboard visible with an error instead of zero", async () => {
  mockMoneyError = true;
  await render();
  expect(element("admin-greeting-message")).not.toBeNull();
  expect(element("kpi-sales-revenue-value").textContent).toBe("—");
  expect(element("kpi-sales-revenue").querySelector('[role="alert"]').textContent).toContain("belum dapat diperbarui");
});
