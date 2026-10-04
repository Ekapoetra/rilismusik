import React from "react";
import { List, LayoutGrid } from "lucide-react";

// List / Cover view switcher, persisted per page via storageKey.
export function useReleaseView(storageKey = "rm-release-view") {
  const [view, setView] = React.useState(() => {
    try { return localStorage.getItem(storageKey) === "cover" ? "cover" : "list"; }
    catch { return "list"; }
  });
  const update = (v) => {
    if (!["list", "cover"].includes(v)) return;
    setView(v);
    try { localStorage.setItem(storageKey, v); } catch { /* Keep the switch usable when storage is blocked. */ }
  };
  return [view, update];
}

export const ReleaseViewToggle = ({ view, onChange, prefix = "release" }) => (
  <div role="group" aria-label="Tampilan rilisan" className="inline-flex rounded-lg border border-white/10 bg-white/[0.03] p-0.5" data-testid={`${prefix}-view-toggle`}>
    {[["list", List, "List"], ["cover", LayoutGrid, "Cover"]].map(([key, Icon, label]) => (
      <button
        key={key}
        type="button"
        aria-pressed={view === key}
        onClick={() => onChange(key)}
        className={`inline-flex min-h-10 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-bold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-pink-400 ${view === key ? "bg-[#FF1F8E] text-white" : "text-zinc-400 hover:text-white"}`}
        data-testid={`${prefix}-view-${key}`}
      >
        <Icon className="h-3.5 w-3.5" /> {label}
      </button>
    ))}
  </div>
);

export default ReleaseViewToggle;
