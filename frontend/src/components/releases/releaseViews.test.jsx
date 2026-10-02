import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "@/api/client";
import LabelReleases from "@/pages/label/Releases";
import AdminReleases from "@/pages/admin/Releases";
import { ReleaseCoverGrid } from "./ReleaseCoverGrid";
import { ReleaseViewToggle, useReleaseView } from "./ReleaseViewToggle";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }) => require("react").createElement("a", { href: to, ...props }, children),
  useSearchParams: () => [new URLSearchParams()],
}), { virtual: true });
jest.mock("@/api/client", () => ({ api: { get: jest.fn(), delete: jest.fn() }, fileUrl: (path) => path, formatApiError: String }));
jest.mock("@/contexts/AppPreferencesContext", () => ({ useAppPreferences: () => ({ t: (text) => text }) }));
jest.mock("@/components/ui/sonner", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock("@/components/label/SubmissionQuota", () => ({ SubmissionQuota: () => null }));
jest.mock("./ReleaseArtwork", () => ({ ReleaseArtwork: () => null }));
jest.mock("./GoLiveModal", () => () => null);
jest.mock("./MassGoLiveModal", () => () => null);
jest.mock("./TakedownImportModal", () => () => null);
jest.mock("./AdminDeleteReleaseButton", () => ({ AdminDeleteReleaseButton: () => <button type="button">Hapus rilisan</button> }));

const release = { id: "r1", release_title: "Cerita Baru", artist_name: "Eka Poetra", release_type: "single", release_date: "2026-09-01", status: "draft", cover_url: "/cover.jpg", label_name: "Label A", revenue_idr: 150000 };
let root, container;
const el = (id) => container.querySelector(`[data-testid="${id}"]`);
const click = async (element) => { await act(async () => element.dispatchEvent(new MouseEvent("click", { bubbles: true }))); };
const render = async (element) => { await act(async () => root.render(element)); };
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true; localStorage.clear(); jest.clearAllMocks();
  api.get.mockImplementation(async (path) => ({ data: path.endsWith("/periods") ? { periods: [] } : [release] }));
  container = document.createElement("div"); document.body.appendChild(container); root = createRoot(container);
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); jest.restoreAllMocks(); });

test("label switches between the same releases without fetching again and remembers Cover", async () => {
  await render(<LabelReleases />);
  expect(el("label-release-row-r1")).not.toBeNull();
  const reads = api.get.mock.calls.length;
  await click(el("label-releases-view-cover"));
  expect(el("label-release-row-r1")).toBeNull();
  expect(el("label-release-cover-title-r1").textContent).toBe("Cerita Baru");
  expect(el("label-release-cover-open-r1").getAttribute("href")).toBe("/label/releases/r1");
  expect(el("label-release-cover-artists-r1").textContent).toBe("Eka Poetra");
  expect(el("label-release-delete-r1").closest("a")).toBeNull();
  expect(api.get).toHaveBeenCalledTimes(reads);
  expect(el("label-releases-view-cover").getAttribute("aria-pressed")).toBe("true");
  await render(<div />); await render(<LabelReleases />);
  expect(el("label-release-cover-grid")).not.toBeNull();
  await click(el("label-releases-view-list"));
  expect(el("label-release-row-r1")).not.toBeNull();
});

test("admin Cover keeps status filtering, operational info, and independent actions", async () => {
  await render(<AdminReleases />);
  await click(el("admin-releases-view-cover"));
  expect(el("admin-release-cover-open-r1").getAttribute("href")).toBe("/admin/releases/r1");
  expect(el("admin-release-label-r1").textContent).toBe("Label A");
  expect(container.textContent).toContain("150.000");
  expect(container.querySelector("details")).not.toBeNull();
  expect(Array.from(container.querySelectorAll("button")).find((b) => b.textContent === "Hapus rilisan").closest("a")).toBeNull();
  await act(async () => { el("admin-releases-status").value = "live"; el("admin-releases-status").dispatchEvent(new Event("change", { bubbles: true })); });
  expect(api.get).toHaveBeenCalledWith("/admin/releases", { params: { status: "live" } });
  expect(el("admin-release-cover-grid")).not.toBeNull();
});

test("broken cover falls back and a replacement URL can load; internal cover takes priority", async () => {
  await render(<ReleaseCoverGrid items={[{ ...release, imported_legacy: true, internal_cover_url: "/internal.jpg" }]} basePath="/label/releases" />);
  expect(el("release-cover-img-r1").getAttribute("src")).toBe("/internal.jpg");
  await act(async () => el("release-cover-img-r1").dispatchEvent(new Event("error")));
  expect(el("release-cover-placeholder-r1")).not.toBeNull();
  await render(<ReleaseCoverGrid items={[{ ...release, cover_url: "/new.jpg" }]} basePath="/label/releases" />);
  expect(el("release-cover-img-r1").getAttribute("src")).toBe("/new.jpg");
});

function PreferenceProbe() { const [view, setView] = useReleaseView(); return <ReleaseViewToggle view={view} onChange={setView} />; }
test("blocked storage still allows changing view", async () => {
  jest.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("blocked"); });
  jest.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("blocked"); });
  await render(<PreferenceProbe />);
  await click(el("release-view-cover"));
  expect(el("release-view-cover").getAttribute("aria-pressed")).toBe("true");
});
test("invalid saved mode falls back to List", async () => {
  localStorage.setItem("rm-release-view", "unknown");
  await render(<PreferenceProbe />);
  expect(el("release-view-list").getAttribute("aria-pressed")).toBe("true");
});
