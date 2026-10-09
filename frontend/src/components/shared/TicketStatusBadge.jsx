import React from "react";

export const TICKET_STATUS_LABELS = {
  open: "Open",
  waiting_admin: "Menunggu Admin",
  waiting_label: "Menunggu Label",
  in_progress: "Sedang Diproses",
  submitted_to_believe: "Submitted ke Believe",
  done: "Selesai",
  rejected: "Ditolak",
  cancelled: "Dibatalkan",
};

export const TICKET_CATEGORY_LABELS = {
  takedown: "Takedown Rilisan",
  edit_metadata: "Edit Metadata",
  edit_audio: "Edit Audio",
  edit_cover: "Edit Cover",
  content_id_claim: "Pengajuan Content ID",
  content_id_release: "Cabut Content ID",
  royalty_issue: "Masalah Royalti",
  other: "Lainnya",
};

const STYLES = {
  open: { bg: "rgba(99,102,241,0.15)", color: "#A5B4FC", dot: "#818CF8" },
  waiting_admin: { bg: "rgba(245,158,11,0.18)", color: "#FCD34D", dot: "#F59E0B" },
  waiting_label: { bg: "rgba(168,85,247,0.18)", color: "#D8B4FE", dot: "#A855F7" },
  in_progress: { bg: "rgba(255,31,142,0.18)", color: "#FF8AC0", dot: "#FF1F8E" },
  submitted_to_believe: { bg: "rgba(59,130,246,0.18)", color: "#93C5FD", dot: "#3B82F6" },
  done: { bg: "rgba(16,185,129,0.18)", color: "#6EE7B7", dot: "#10B981" },
  rejected: { bg: "rgba(239,68,68,0.18)", color: "#FCA5A5", dot: "#EF4444" },
  cancelled: { bg: "rgba(255,255,255,0.06)", color: "#A1A1B5", dot: "#71717A" },
};

export default function TicketStatusBadge({ status }) {
  const s = STYLES[status] || STYLES.open;
  const label = TICKET_STATUS_LABELS[status] || status;
  return (
    <span
      className="rm-badge"
      style={{ background: s.bg, color: s.color }}
      data-testid={`ticket-status-badge-${status}`}
    >
      <span className="rm-badge-dot" style={{ background: s.dot }} />
      {label}
    </span>
  );
}
