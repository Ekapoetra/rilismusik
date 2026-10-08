import React from "react";
import { RELEASE_STATUS_LABELS } from "@/utils/releasePresentation";

export const STATUS_LABELS = RELEASE_STATUS_LABELS;

// V13 status pills: one compact design, tone by meaning.
const TONES = {
  draft: undefined, submitted: "blue", awaiting_payment: "mustard", paid: "green",
  under_review: "blue", need_revision: "mustard", approved: "green", delivered: "blue",
  live: "green", rejected: "red", takedown_requested: "mustard", taken_down: undefined,
};

export default function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] || status;
  return <span className="v13-pill" data-tone={TONES[status]} data-testid={`status-badge-${status}`}>{label}</span>;
}
