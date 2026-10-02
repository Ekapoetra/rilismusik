import { api } from "./client";

// Share only requests currently in flight. Never retain settled financial data.
const pending = new Map();
let generation = 0;
export function resetSharedReads() { generation += 1; pending.clear(); }
export function sharedRead(scope, url, params = {}) {
  const key = JSON.stringify([generation, scope, url, Object.entries(params).sort()]);
  if (!pending.has(key)) {
    const request = api.get(url, { params });
    pending.set(key, request);
    const clear = () => { if (pending.get(key) === request) pending.delete(key); };
    request.then(clear, clear);
  }
  return pending.get(key);
}
