import { lazy, useEffect } from "react";
import { useAuth } from "@/api/AuthContext";

// Route pages are split into separate chunks. Without prefetching, the first
// click on every menu waits for its chunk download before anything changes.
// After sign-in the pages of the user's own area are fetched while the
// browser is idle, so later navigation only waits for its data.
const loaders = { label: [], admin: [], artist: [] };

export function rolePage(group, factory) {
  loaders[group].push(factory);
  return lazy(factory);
}

const ADMIN_ROLES = new Set(["super_admin", "admin_release", "admin_finance", "admin_support", "admin_content", "admin_marketing", "admin_ui", "admin_custom", "admin_package_manager"]);
const prefetched = new Set();

function groupFor(user) {
  if (!user) return null;
  if (user.role === "label") return "label";
  if (user.role === "artist") return "artist";
  return user.is_admin || ADMIN_ROLES.has(user.role) ? "admin" : null;
}

const whenIdle = (callback) => (typeof window.requestIdleCallback === "function"
  ? window.requestIdleCallback(callback, { timeout: 4000 })
  : window.setTimeout(callback, 1500));
const cancelIdle = (handle) => (typeof window.cancelIdleCallback === "function"
  ? window.cancelIdleCallback(handle)
  : window.clearTimeout(handle));

export async function prefetchGroup(group, concurrency = 2) {
  if (!group || prefetched.has(group)) return;
  prefetched.add(group);
  const queue = [...loaders[group]];
  const worker = async () => {
    while (queue.length) {
      const load = queue.shift();
      try { await load(); } catch { /* the route retries on navigation */ }
    }
  };
  await Promise.all(Array.from({ length: concurrency }, worker));
}

export function RoutePrefetch() {
  const { user } = useAuth();
  const group = groupFor(user);
  useEffect(() => {
    if (!group || prefetched.has(group) || navigator.connection?.saveData) return undefined;
    const handle = whenIdle(() => { prefetchGroup(group); });
    return () => cancelIdle(handle);
  }, [group]);
  return null;
}
