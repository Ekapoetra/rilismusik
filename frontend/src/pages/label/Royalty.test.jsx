import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/api/client";
import LabelRoyalty from "./Royalty";

jest.mock("react-router-dom", () => ({ Link: ({ children, to, ...props }) => <a href={to} {...props}>{children}</a> }), { virtual: true });
jest.mock("@/api/client", () => ({
  api: { get: jest.fn(), post: jest.fn() },
  formatApiError: (value) => (typeof value === "string" ? value : "error"),
}));
jest.mock("@/api/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1", role: "label", claim_status: "linked" } }) }));
jest.mock("@/hooks/useRoyaltyBalance", () => ({ useRoyaltyBalance: () => ({ balance: { balance_available_idr: 0 }, error: false }) }));

const summary = { summary: { total_idr: 1000, total_streams: 10, total_lines: 1 }, by_platform: [], by_country: [], by_track: [] };
let root, container, assign;
const flush = async () => { await act(async () => { await Promise.resolve(); }); };

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  assign = jest.fn();
  delete window.location;
  window.location = { assign };
  api.get.mockImplementation((url) => Promise.resolve({ data: url === "/royalty/months" ? ["2026-05"] : url === "/royalty/summary" ? summary : [] }));
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

const render = async () => {
  await act(async () => root.render(<LabelRoyalty />));
  await flush();
};

test("download buttons are usable before the report summary arrives", async () => {
  api.get.mockImplementation((url) => (url === "/royalty/months" ? Promise.resolve({ data: ["2026-05"] }) : new Promise(() => {})));
  await render();
  expect(container.querySelector('[data-testid="royalty-loading"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="royalty-export-excel"]').disabled).toBe(false);
  expect(api.get).not.toHaveBeenCalledWith("/royalty/summary", { params: { period: undefined } });
});

test("excel download requests a prepared link and opens it", async () => {
  api.post.mockResolvedValue({ data: { url: "https://r2.example.invalid/report.xlsx" } });
  await render();
  await act(async () => container.querySelector('[data-testid="royalty-export-excel"]').click());
  await flush();
  expect(api.post).toHaveBeenCalledWith("/royalty/export-link", { format: "xlsx", period: "2026-05", artist: null }, { timeout: 300000 });
  expect(assign).toHaveBeenCalledWith("https://r2.example.invalid/report.xlsx");
});

test("export errors are shown instead of a blank download", async () => {
  api.post.mockRejectedValue({ response: { data: { detail: "Belum ada data royalti setelah periode legacy untuk diunduh." } } });
  await render();
  await act(async () => container.querySelector('[data-testid="royalty-export-csv"]').click());
  await flush();
  expect(container.querySelector('[data-testid="royalty-export-error"]').textContent).toContain("setelah periode legacy");
  expect(assign).not.toHaveBeenCalled();
});
