import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/api/client";
import AdminChatWidget from "./AdminChatWidget";

jest.mock("@/api/client", () => ({ api: { get: jest.fn(), post: jest.fn() }, fileUrl: (path) => path }));
jest.mock("@/api/AuthContext", () => ({ useAuth: () => ({ user: { id: "agent", role: "admin_support" }, hasPermission: () => true }) }));
jest.mock("@/contexts/AppPreferencesContext", () => ({ useAppPreferences: () => ({ t: (text) => text, locale: "id" }) }));
jest.mock("@/components/ui/sonner", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock("@/lib/notificationSound", () => ({ playNotificationSound: jest.fn() }));
jest.mock("@/components/shared/QuickChatButton", () => ({ OPEN_CHAT_EVENT: "test:open-chat", CHAT_UNREAD_EVENT: "test:chat-unread" }));

const msg = (i) => ({ id: `m${i}`, sender_id: "label", sender_name: "Label", body: `body-m${i}`, created_at: `2026-10-01T00:${String(i).padStart(2, "0")}:00+00:00` });
const history = Array.from({ length: 6 }, (_, i) => msg(i));
const deferred = () => { let resolve; const promise = new Promise((done) => { resolve = done; }); return { promise, resolve }; };
let root, container, threadCalls, pendingPoll;
const click = async (testId) => { await act(async () => container.querySelector(`[data-testid="${testId}"]`).click()); };
const bodies = () => Array.from(container.querySelectorAll('[data-testid^="chat-message-body-"]')).map((node) => node.textContent);

beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  jest.useFakeTimers();
  jest.clearAllMocks();
  Object.defineProperty(document, "visibilityState", { configurable: true, value: "visible" });
  Element.prototype.scrollTo = () => {};
  threadCalls = [];
  pendingPoll = null;
  api.post.mockResolvedValue({ data: {} });
  api.get.mockImplementation((url, config = {}) => {
    if (url === "/chat/unread") return Promise.resolve({ data: { unread: 0 } });
    if (url === "/chat/admin/admins") return Promise.resolve({ data: { items: [] } });
    if (url === "/chat/admin/labels") return Promise.resolve({ data: { items: [{ conversation_id: "A", label_id: "la", label_name: "Label A", unread: 0, status: "active" }] } });
    if (url === "/chat/admin/thread/A") {
      threadCalls.push(config.params || {});
      if (config.params?.since) {
        pendingPoll = deferred();
        return pendingPoll.promise;
      }
      return Promise.resolve({ data: { messages: history, incremental: false, typing: [], status: "active" } });
    }
    return Promise.resolve({ data: {} });
  });
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); jest.useRealTimers(); });

test("reopening a conversation during an in-flight poll reloads the full history", async () => {
  await act(async () => root.render(<AdminChatWidget />));
  await act(async () => window.dispatchEvent(new Event("test:open-chat")));
  await click("admin-chat-label-item-la");
  expect(bodies()).toHaveLength(6);

  // The 3 s poll asks only for the recent tail and stays in flight.
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(threadCalls.at(-1).since).toBe(history[5].created_at);

  // Back to the list and straight into the same conversation again.
  await click("chat-thread-back");
  await click("admin-chat-label-item-la");
  expect(threadCalls.at(-1)).toEqual({});

  // The stale tail response must not replace the freshly loaded history.
  await act(async () => pendingPoll.resolve({ data: { messages: [history[5]], incremental: true, typing: [], status: "active" } }));
  expect(bodies()).toHaveLength(6);
  expect(container.querySelector('[data-testid="chat-thread-loading"]')).toBeNull();
});
