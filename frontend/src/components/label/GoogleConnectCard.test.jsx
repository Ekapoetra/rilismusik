import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { GoogleConnectCard } from "./GoogleConnectCard";

let mockUser;
const mockRefresh = jest.fn();
jest.mock("@/api/AuthContext", () => ({ useAuth: () => ({ user: mockUser, refresh: mockRefresh }) }));
jest.mock("@/components/auth/GoogleAuthButton", () => ({
  GoogleAuthButton: ({ source, mode, onLinked }) => <button type="button" data-testid={`${source}-google-auth-button`} data-mode={mode} onClick={onLinked}>Google</button>,
}));

let root, container;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });
const render = async () => { await act(async () => root.render(<GoogleConnectCard />)); };

test("label without Google sees a connect button that only adds a sign-in method", async () => {
  mockUser = { email: "label@gmail.com" };
  await render();
  const button = container.querySelector('[data-testid="profile-google-auth-button"]');
  expect(button.dataset.mode).toBe("link");
  expect(container.textContent).toContain("label@gmail.com");
  expect(container.textContent).toContain("tidak mengubah status verifikasi");
  await act(async () => button.click());
  expect(mockRefresh).toHaveBeenCalledTimes(1);
});

test("connected label sees the linked Google account and no button", async () => {
  mockUser = { email: "label@gmail.com", google_subject: "sub", google_email: "label@gmail.com", google_linked_at: "2026-10-05T07:00:00+00:00" };
  await render();
  expect(container.querySelector('[data-testid="profile-google-auth-button"]')).toBeNull();
  expect(container.querySelector('[data-testid="label-google-connected"]').textContent).toContain("label@gmail.com");
  expect(container.textContent).toContain("2026");
});
