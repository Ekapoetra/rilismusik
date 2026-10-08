import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { ReleaseModePicker } from "./Tokens";
import { api } from "@/api/client";

jest.mock("@/api/client", () => ({ api: { get: jest.fn(), post: jest.fn() }, formatApiError: (value) => String(value) }));
jest.mock("@/api/payments", () => ({ openXenditCheckout: jest.fn() }));
jest.mock("@/api/AuthContext", () => ({ useAuth: () => ({ user: { id: "u1" } }) }));
jest.mock("@/contexts/AppPreferencesContext", () => ({ useAppPreferences: () => ({ t: (text) => text }) }));

const modes = { balance: 3, modes: [
  { id: "standard", name: "Standar", lead_working_days: 7, earliest_date: "2026-10-19", available: true, tokens_per_track: 0, tokens: 0 },
  { id: "express", name: "Express", lead_working_days: 5, earliest_date: "2026-10-15", available: true, tokens_per_track: 2, tokens: 4 },
  { id: "max", name: "MAX", lead_working_days: 3, earliest_date: null, available: false, tokens_per_track: 3, tokens: 6 },
] };

let root, container;
const element = (id) => container.querySelector(`[data-testid="${id}"]`);
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  api.get.mockImplementation((path) => Promise.resolve({ data: path === "/tokens/me" ? { balance: 3, ledger: [], token_price_idr: 35000 } : modes }));
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

test("mode picker warns about early dates and missing tokens", async () => {
  const onMode = jest.fn();
  await act(async () => root.render(<ReleaseModePicker trackCount={2} releaseDate="2026-10-16" mode="standard" onMode={onMode} packageName="Basic" />));
  expect(element("release-mode-max").disabled).toBe(true);
  expect(container.textContent).toContain("Tanggal rilis lebih awal");
  await act(async () => element("release-mode-express").click());
  expect(onMode).toHaveBeenCalledWith("express");
  await act(async () => root.render(<ReleaseModePicker trackCount={2} releaseDate="2026-10-16" mode="express" onMode={onMode} packageName="Basic" />));
  expect(container.textContent).toContain("Saldo token kurang");
  expect(container.textContent).not.toContain("Tanggal rilis lebih awal");
});
