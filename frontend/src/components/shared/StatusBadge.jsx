import React from "react";
import { RELEASE_STATUS_LABELS } from "@/utils/releasePresentation";

export const STATUS_LABELS = RELEASE_STATUS_LABELS;

// Dark-mode tuned palette
const STYLES = {
  draft: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#A1A1B5" },
  submitted: { bg: "rgba(99,102,241,0.15)", color: "#A5B4FC", dot: "#818CF8" },
  awaiting_payment: { bg: "rgba(245,158,11,0.15)", color: "#FCD34D", dot: "#F59E0B" },
  paid: { bg: "rgba(16,185,129,0.15)", color: "#6EE7B7", dot: "#34D399" },
  under_review: { bg: "rgba(249,115,22,0.15)", color: "#FDBA74", dot: "#FB923C" },
  need_revision: { bg: "rgba(234,179,8,0.15)", color: "#FDE047", dot: "#FACC15" },
  approved: { bg: "rgba(16,185,129,0.15)", color: "#6EE7B7", dot: "#10B981" },
  delivered: { bg: "rgba(99,102,241,0.15)", color: "#C7D2FE", dot: "#6366F1" },
  live: { bg: "rgba(255,31,142,0.18)", color: "#FF8AC0", dot: "#FF1F8E" },
  rejected: { bg: "rgba(239,68,68,0.15)", color: "#FCA5A5", dot: "#EF4444" },
  takedown_requested: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#71717A" },
  taken_down: { bg: "rgba(0,0,0,0.4)", color: "#A1A1B5", dot: "#52525B" },
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] || STYLES.draft;
  const label = STATUS_LABELS[status] || status;
  return (
    <span
      className="rm-badge"
      style={{ background: style.bg, color: style.color }}
      data-testid={`status-badge-${status}`}
    >
      <span className="rm-badge-dot" style={{ background: style.dot }} />
      {label}
    </span>
  );
}
