import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { LabelTransferCard } from "./LabelTransferCard";

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock("@/api/client", () => ({
  api: { get: (...args) => mockGet(...args), post: (...args) => mockPost(...args) },
  formatApiError: (detail) => String(detail || "error"),
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

const LABEL = { id: "pel", label_name: "Pelpendo" };
const setInput = (element, value) => {
  const setter = Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value").set;
  setter.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
};
const render = async (labels) => {
  mockGet.mockImplementation(async (url) => (url === "/label/transfers" ? { data: [] } : { data: { labels } }));
  await act(async () => root.render(<LabelTransferCard label={LABEL} />));
};
const q = (id) => container.querySelector(`[data-testid="${id}"]`);

test("single-label account can only rename, and must preview before submitting", async () => {
  await render([{ id: "pel", label_name: "Pelpendo", former_names: [] }]);
  await act(async () => q("label-transfer-open").click());
  expect(q("label-transfer-mode-merge").disabled).toBe(true);
  expect(q("label-transfer-submit").disabled).toBe(true);
  await act(async () => { setInput(q("label-transfer-new-name"), "Elfnon"); setInput(q("label-transfer-reason"), "Sudah pindah di Believe"); });
  mockPost.mockResolvedValueOnce({ data: { summary: "Ganti nama Pelpendo → Elfnon", plan: { mode: "rename" } } });
  await act(async () => q("label-transfer-preview").click());
  expect(mockPost).toHaveBeenCalledWith("/label/transfers/preview", expect.objectContaining({ mode: "rename", source_label_id: "pel", new_name: "Elfnon" }));
  expect(container.textContent).toContain("Ganti nama Pelpendo → Elfnon");
  expect(q("label-transfer-submit").disabled).toBe(false);
});

test("multi-label account can merge into its other label and sees what moves", async () => {
  await render([{ id: "pel", label_name: "Pelpendo", former_names: [] }, { id: "elf", label_name: "Elfnon", former_names: [] }]);
  await act(async () => q("label-transfer-open").click());
  await act(async () => q("label-transfer-mode-merge").click());
  expect(q("label-transfer-target").value).toBe("elf");
  await act(async () => setInput(q("label-transfer-reason"), "Gabung katalog"));
  mockPost.mockResolvedValueOnce({ data: { summary: "Gabung semua rilisan Pelpendo → Elfnon", plan: { mode: "merge", release_count: 2, available_idr: 3000, adjustment_idr: 300, pending_idr: 500, line_count: 3 } } });
  await act(async () => q("label-transfer-preview").click());
  expect(q("label-transfer-plan").textContent).toContain("3.300");
  expect(mockPost).toHaveBeenCalledWith("/label/transfers/preview", expect.objectContaining({ mode: "merge", target_label_id: "elf" }));
});
