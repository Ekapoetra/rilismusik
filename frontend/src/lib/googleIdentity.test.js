let loadGoogleIdentity;
beforeEach(() => {
  jest.resetModules(); jest.useFakeTimers(); delete window.google;
  loadGoogleIdentity = require("./googleIdentity").loadGoogleIdentity;
});
afterEach(() => {
  jest.useRealTimers(); delete window.google;
  document.querySelectorAll('script[src="https://accounts.google.com/gsi/client"]').forEach((script) => script.remove());
});

test("loads one official script for concurrent consumers", async () => {
  const first = loadGoogleIdentity(); const second = loadGoogleIdentity();
  expect(first).toBe(second);
  const scripts = document.querySelectorAll('script[src="https://accounts.google.com/gsi/client"]');
  expect(scripts).toHaveLength(1); expect(scripts[0].async).toBe(true);
  const identity = { initialize: jest.fn() }; window.google = { accounts: { id: identity } };
  scripts[0].dispatchEvent(new Event("load"));
  await expect(first).resolves.toBe(identity);
});

test("failed script can be retried instead of caching a rejection", async () => {
  const first = loadGoogleIdentity(); const rejected = expect(first).rejects.toThrow("Google belum dapat dimuat");
  document.querySelector("script").dispatchEvent(new Event("error"));
  await rejected;
  const second = loadGoogleIdentity(); const timedOut = expect(second).rejects.toThrow("Google belum dapat dimuat");
  expect(second).not.toBe(first); jest.advanceTimersByTime(15000); await timedOut;
});
