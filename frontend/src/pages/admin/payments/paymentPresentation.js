export const PAYMENT_STATUS = {
  paid: "Dibayar",
  pending: "Menunggu Pembayaran",
  expired: "Kedaluwarsa",
  failed: "Gagal",
  cancelled: "Dibatalkan",
};

export const PAYMENT_TYPES = {
  pay_per_release: "Pay Per Release",
  annual_subscription: "Langganan Tahunan",
  wami_addon: "Pendaftaran WAMI",
  custom_service: "Layanan Tambahan",
};

export const SERVICE_STATUS = {
  paid: "Menunggu Dikerjakan",
  in_progress: "Sedang Dikerjakan",
  completed: "Selesai",
  pending: "Menunggu Diproses",
  registered: "Terdaftar",
  approved: "Siap Didistribusikan",
  under_review: "Menunggu Review",
  delivered: "Sudah Didistribusikan",
  live: "Live",
  automatic: "Aktif Otomatis",
  unknown: "Perlu Ditinjau",
};

export const formatIDR = (value) => new Intl.NumberFormat("id-ID", {
  style: "currency", currency: "IDR", maximumFractionDigits: 0,
}).format(value || 0);

export const formatDateTime = (value) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Jakarta",
  }).format(parsed);
};

export const paymentMethodLabel = (value) => value
  ? String(value).replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase())
  : "Belum tersedia dari Xendit";