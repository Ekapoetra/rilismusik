import React from "react";

export const STATUS_LABELS = {
  draft: "Draft",
  submitted: "Submitted",
  awaiting_payment: "Awaiting Payment",
  paid: "Paid",
  under_review: "Under Review",
  need_revision: "Need Revision",
  approved: "Approved",
  delivered: "Delivered",
  live: "Live",
  rejected: "Rejected",
  takedown_requested: "Takedown Requested",
  taken_down: "Taken Down",
};

const STYLES = {
  draft: { bg: "#F4F4F5", color: "#6B7280", dot: "#9CA3AF" },
  submitted: { bg: "#EFF6FF", color: "#1D4ED8", dot: "#3B82F6" },
  awaiting_payment: { bg: "#FEF3C7", color: "#92400E", dot: "#F59E0B" },
  paid: { bg: "#ECFDF5", color: "#047857", dot: "#10B981" },
  under_review: { bg: "#FFF7ED", color: "#9A3412", dot: "#F97316" },
  need_revision: { bg: "#FEF9C3", color: "#854D0E", dot: "#EAB308" },
  approved: { bg: "#ECFDF5", color: "#065F46", dot: "#10B981" },
  delivered: { bg: "#EEF2FF", color: "#3730A3", dot: "#6366F1" },
  live: { bg: "#DCFCE7", color: "#166534", dot: "#16A34A" },
  rejected: { bg: "#FEF2F2", color: "#991B1B", dot: "#EF4444" },
  takedown_requested: { bg: "#F3F4F6", color: "#374151", dot: "#6B7280" },
  taken_down: { bg: "#1F2937", color: "#F3F4F6", dot: "#9CA3AF" },
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
