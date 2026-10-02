import { workspaceForRoute, workspaceItems } from "./workspaceNavigation";

test("staff detail routes stay in Staff while operational detail routes stay in Platform", () => {
  expect(workspaceForRoute("/admin/staff/configuration")).toBe("staff");
  expect(workspaceForRoute("/admin/compensation/payroll")).toBe("staff");
  expect(workspaceForRoute("/admin/releases/release-123")).toBe("platform");
  expect(workspaceForRoute("/admin/staffing-other")).toBe("platform");
});

test("grouping only preserves the server-authorized visible navigation", () => {
  const authorized = [{ key: "attendance", route: "/admin/attendance", parent_key: "staff" }, { key: "payroll", route: "/admin/compensation/payroll", visible: false }, { key: "releases", route: "/admin/releases" }];
  expect(workspaceItems(authorized, "staff").map(item => item.key)).toEqual(["attendance"]);
  expect(workspaceItems(authorized, "platform").map(item => item.key)).toEqual(["releases"]);
  expect(workspaceItems([], "staff")).toEqual([]);
});
