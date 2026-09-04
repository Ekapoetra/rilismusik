export const RELEASE_STATUS_LABELS = {
  draft: "Draf", submitted: "Diajukan", awaiting_payment: "Menunggu Pembayaran",
  paid: "Sudah Dibayar", under_review: "Sedang Ditinjau", need_revision: "Perlu Revisi",
  approved: "Disetujui", delivered: "Dikirim ke Believe", live: "Tayang",
  rejected: "Ditolak", takedown_requested: "Permintaan Penurunan", taken_down: "Sudah Diturunkan",
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