import { TICKET_CATEGORY_LABELS } from "@/components/shared/TicketStatusBadge";

export const ACTIVE_TICKET_CATEGORIES = Object.entries(TICKET_CATEGORY_LABELS).filter(([key]) => !["royalty_issue", "other"].includes(key));
export const AUTO_SUBJECT_CATEGORIES = ["takedown", "edit_metadata", "content_id_claim", "content_id_release"];
export const CONTENT_ID_CATEGORIES = ["content_id_claim", "content_id_release"];
export const TAKEDOWN_REASONS = ["Revisi Metadata", "Pindah Aggregator", "Konflik Hak Cipta", "Konflik Internal"];
export const METADATA_FIELDS = [["Judul Rilisan", "release_title"], ["Artist", "artist_name"], ["Genre", "genre"], ["Bahasa", "language"], ["© Line", "copyright_line"], ["℗ Line", "p_line"]];
export const metadataFromRelease = (release) => Object.fromEntries(METADATA_FIELDS.map(([, key]) => [key, String(release?.[key] || "")]));
const SUBJECT_LABELS = { ...TICKET_CATEGORY_LABELS, content_id_claim: "Pengajuan YouTube Content ID", content_id_release: "Cabut YouTube Content ID" };
export const ticketSubject = (category, release) => release ? `${SUBJECT_LABELS[category]} — ${release.release_title || release.id}`.slice(0, 200) : "";