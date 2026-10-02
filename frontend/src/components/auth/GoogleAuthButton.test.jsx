import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { GoogleAuthButton } from "./GoogleAuthButton";
import { api } from "@/api/client";
import { useAuth } from "@/api/AuthContext";
import { useNavigate } from "react-router-dom";
import { loadGoogleIdentity } from "@/lib/googleIdentity";

jest.mock("@/api/client", () => ({ api: { get: jest.fn(), post: jest.fn() }, formatApiError: (value) => String(value) }));
jest.mock("@/api/AuthContext", () => ({ useAuth: jest.fn() }));
jest.mock("react-router-dom", () => ({ useNavigate: jest.fn() }));
jest.mock("@/lib/googleIdentity", () => ({ loadGoogleIdentity: jest.fn() }));

let container, root, identity, loginWithGoogle, navigate;
const originalClientId = process.env.REACT_APP_GOOGLE_CLIENT_ID;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.clearAllMocks();
  process.env.REACT_APP_GOOGLE_CLIENT_ID = "test.apps.googleusercontent.com";
  container = document.createElement("div"); document.body.appendChild(container);
  root = createRoot(container);
  loginWithGoogle = jest.fn().mockResolvedValue({}); navigate = jest.fn();
  useAuth.mockReturnValue({ loginWithGoogle }); useNavigate.mockReturnValue(navigate);
  api.get.mockResolvedValue({ data: { nonce: "browser-nonce" } });
  api.post.mockResolvedValue({ data: { ok: true } });
  identity = { initialize: jest.fn(), renderButton: jest.fn() };
  loadGoogleIdentity.mockResolvedValue(identity);
});
afterEach(async () => {
  await act(async () => root.unmount()); container.remove();
  if (originalClientId === undefined) delete process.env.REACT_APP_GOOGLE_CLIENT_ID;
  else process.env.REACT_APP_GOOGLE_CLIENT_ID = originalClientId;
});
async function render(props = {}) {
  await act(async () => root.render(<GoogleAuthButton source="login" {...props} />));
}

test("uses Google's renderer with nonce and Indonesian official button", async () => {
  await render();
  expect(api.get).toHaveBeenCalledWith("/auth/google/nonce");
  expect(identity.initialize).toHaveBeenCalledWith(expect.objectContaining({
    client_id: "test.apps.googleusercontent.com", nonce: "browser-nonce", auto_select: false,
  }));
  expect(identity.renderButton).toHaveBeenCalledWith(expect.any(HTMLElement), expect.objectContaining({
    type: "standard", text: "continue_with", locale: "id", theme: "outline",
  }));
});

test("accepted credential uses same-origin auth and opens label dashboard", async () => {
  await render();
  const callback = identity.initialize.mock.calls[0][0].callback;
  await act(async () => callback({ credential: "google-id-token" }));
  expect(loginWithGoogle).toHaveBeenCalledWith("google-id-token");
  expect(navigate).toHaveBeenCalledWith("/label/dashboard", { replace: true });
});

test("failed auth shows error and permits renewing the browser challenge", async () => {
  loginWithGoogle.mockRejectedValue({ response: { data: { detail: "Sesi sudah berakhir" } } });
  await render();
  await act(async () => identity.initialize.mock.calls[0][0].callback({ credential: "expired" }));
  expect(container.querySelector('[role="alert"]').textContent).toContain("Sesi sudah berakhir");
  expect(navigate).not.toHaveBeenCalled();
  await act(async () => container.querySelector("button").click());
  expect(api.get).toHaveBeenCalledTimes(2);
});

test("linking stays on profile and refreshes account identity", async () => {
  const onLinked = jest.fn();
  await render({ mode: "link", onLinked });
  await act(async () => identity.initialize.mock.calls[0][0].callback({ credential: "link-token" }));
  expect(api.post).toHaveBeenCalledWith("/auth/google/link", { credential: "link-token" });
  expect(onLinked).toHaveBeenCalledTimes(1);
  expect(loginWithGoogle).not.toHaveBeenCalled(); expect(navigate).not.toHaveBeenCalled();
  expect(container.textContent).toContain("berhasil dihubungkan");
});

test("missing env or failed SDK does not break password login page", async () => {
  delete process.env.REACT_APP_GOOGLE_CLIENT_ID;
  await render();
  expect(container.textContent).toContain("Gunakan email dan password");
  expect(loadGoogleIdentity).not.toHaveBeenCalled();
});

test("SDK/network failure is shown with a retry action", async () => {
  loadGoogleIdentity.mockRejectedValue(new Error("Google tidak dapat dimuat"));
  await render();
  expect(container.querySelector('[role="alert"]').textContent).toContain("Google tidak dapat dimuat");
  expect(container.querySelector("button")).not.toBeNull();
});

test("callbacks received after leaving the page cannot start login", async () => {
  await render(); const callback = identity.initialize.mock.calls[0][0].callback;
  await act(async () => root.render(null));
  await act(async () => callback({ credential: "stale-token" }));
  expect(loginWithGoogle).not.toHaveBeenCalled();
});
