import React from "react";
import { BadgeCheck } from "lucide-react";

// Small pill shown on releases whose tracks are registered in WAMI.
export const WamiBadge = ({ className = "", testid = "wami-badge", title = "Terdaftar di WAMI" }) => (
  <span
    title={title}
    className={`inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/15 px-2 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-emerald-300 ${className}`}
    data-testid={testid}
  >
    <BadgeCheck className="h-3 w-3" /> WAMI
  </span>
);

export default WamiBadge;
