// V13 status names (prototype status10/mark105) for production release statuses.
export const RELEASE_STATUS_LABELS = {
  draft: "Draft", submitted: "Menunggu pemeriksaan", awaiting_payment: "Menunggu pembayaran",
  paid: "Sudah dibayar", under_review: "Dalam pemeriksaan", need_revision: "Menunggu perbaikan label",
  approved: "Siap dikirim", delivered: "Dalam distribusi", live: "Tayang",
  rejected: "Ditolak", takedown_requested: "Penurunan diajukan", taken_down: "Diturunkan",
};

export const releaseStatusLabel = (status) => RELEASE_STATUS_LABELS[status] || status;

export const releaseWhatsAppUrl = (release) => {
  let phone = String(release?.label_whatsapp || "").replace(/\D/g, "");
  if (phone.startsWith("0")) phone = `62${phone.slice(1)}`;
  if (!phone) return null;
  const label = release.label_name_snapshot || "Label";
  const title = release.release_title || "rilisan";
  const status = releaseStatusLabel(release.status);
  const note = release.admin_note ? `\nCatatan: ${release.admin_note}` : "";
  const message = `Halo ${label}, kami menghubungi Anda terkait rilisan “${title}”. Status saat ini: ${status}.${note}\nMohon segera ditindaklanjuti melalui dashboard RILIS MUSIK.`;
  return `https://wa.me/${phone}?text=${encodeURIComponent(message)}`;
};