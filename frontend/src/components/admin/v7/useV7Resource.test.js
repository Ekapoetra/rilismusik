import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { api } from "../../../api/client";
import { useV7Resource } from "./useV7Resource";

let mockUser = { id: "manager", role: "admin_custom", permissions: ["dashboard.view"] };
jest.mock("../../../api/AuthContext", () => ({ useAuth: () => ({ user: mockUser }) }));
jest.mock("../../../api/client", () => ({ api: { get: jest.fn() }, formatApiError: detail => detail || "Unavailable" }));

function Probe({ url }) {
  const resource = useV7Resource(url);
  return <><output>{resource.error || resource.data?.label || "loading"}</output><button onClick={resource.reload}>reload</button></>;
}
let host, root, requests;
beforeEach(() => {
  global.IS_REACT_ACT_ENVIRONMENT = true;
  mockUser = { id: "manager", role: "admin_custom", permissions: ["dashboard.view"] };
  host = document.createElement("div"); document.body.appendChild(host); root = createRoot(host);
  requests = [];
  api.get.mockImplementation((url, options) => new Promise((resolve, reject) => requests.push({ url, signal: options.signal, resolve, reject })));
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); api.get.mockReset(); });
const render = url => act(async () => root.render(<Probe url={url} />));

test("an older filter response cannot replace the latest filter", async () => {
  await render("/queue?bucket=new");
  await render("/queue?bucket=waiting");
  expect(requests[0].signal.aborted).toBe(true);
  await act(async () => requests[1].resolve({ data: { label: "waiting results" } }));
  await act(async () => requests[0].resolve({ data: { label: "obsolete results" } }));
  expect(host.querySelector("output").textContent).toBe("waiting results");
});

test("switching accounts discards the previous account's data for the same URL", async () => {
  await render("/queue");
  await act(async () => requests[0].resolve({ data: { label: "manager records" } }));
  mockUser = { id: "staff", role: "admin_custom", permissions: ["dashboard.view"] };
  await render("/queue");
  expect(host.textContent).not.toContain("manager records");
  await act(async () => requests[1].resolve({ data: { label: "staff records" } }));
  expect(host.querySelector("output").textContent).toBe("staff records");
});

test("refresh keeps visible data until completion and reports errors explicitly", async () => {
  await render("/queue");
  await act(async () => requests[0].resolve({ data: { label: "27 active" } }));
  await act(async () => host.querySelector("button").click());
  expect(host.querySelector("output").textContent).toBe("27 active");
  await act(async () => requests[1].reject({ response: { data: { detail: "Database unavailable" } } }));
  expect(host.querySelector("output").textContent).toBe("Database unavailable");
});
