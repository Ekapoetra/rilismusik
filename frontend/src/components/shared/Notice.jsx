import React from "react";

const TONES = {
  error: "bg-red-500/15 text-red-300",
  success: "bg-emerald-500/15 text-emerald-300",
  info: "bg-sky-500/15 text-sky-300",
  warning: "bg-amber-500/15 text-amber-300",
};

/** Inline feedback banner shared across pages (error/success/info/warning). */
export default function Notice({ kind = "error", children, testId, className = "" }) {
  if (!children) return null;
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`rounded-2xl px-4 py-3 text-sm ${TONES[kind] || TONES.info} ${className}`} data-testid={testId}>
      {children}
    </div>
  );
}
