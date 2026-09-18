import React, { useEffect, useState } from "react";
import { api } from "@/api/client";
import { Layers, ChevronDown } from "lucide-react";

// Global Active Label switcher — visible on every label page for Multi Label accounts.
export default function LabelSwitcher() {
  const [account, setAccount] = useState(null);
  useEffect(() => { api.get("/label/account").then((r) => setAccount(r.data)).catch(() => {}); }, []);
  if (!account?.is_multi_label) return null;
  const onChange = async (id) => {
    if (!id || id === account.active_label_id) return;
    try { await api.post("/label/active-label", { label_id: id }); window.location.reload(); }
    catch (_) { /* silent */ }
  };
  return (
    <div className="relative" data-testid="label-global-switcher" title="Label Aktif">
      <Layers className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#C79BFF]" />
      <select
        value={account.active_label_id || ""}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 max-w-[190px] appearance-none truncate rounded-full border border-[#A24EFF]/40 bg-white/[0.04] pl-8 pr-8 text-xs font-semibold text-[var(--ui-text)] outline-none focus:border-[#A24EFF]"
        data-testid="label-global-switcher-select"
      >
        {account.labels.map((l) => <option key={l.id} value={l.id}>{l.label_name}</option>)}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-500" />
    </div>
  );
}
