import React from "react";
import { List, LayoutGrid } from "lucide-react";

// List / Cover view switcher, persisted per page via storageKey.
export function useReleaseView(storageKey = "rm-release-view") {
  const [view, setView] = React.useState(() => localStorage.getItem(storageKey) || "list");
  const update = (v) => { setView(v); localStorage.setItem(storageKey, v); };
  return [view, update];
}

export const ReleaseViewToggle = ({ view, onChange, prefix = "release" }) => (
  <div className="inline-flex rounded-lg border border-white/10 bg-white/[0.03] p-0.5" data-testid={`${prefix}-view-toggle`}>
    {[["list", List, "List"], ["cover", LayoutGrid, "Cover"]].map(([key, Icon, label]) => (
      <button
        key={key}
        type="button"
        onClick={() => onChange(key)}
        className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-bold transition-colors ${view === key ? "bg-[#FF1F8E] text-white" : "text-zinc-400 hover:text-white"}`}
        data-testid={`${prefix}-view-${key}`}
      >
        <Icon className="h-3.5 w-3.5" /> {label}
      </button>
    ))}
  </div>
);

export default ReleaseViewToggle;
