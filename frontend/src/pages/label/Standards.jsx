import React from "react";
import { Check } from "lucide-react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import StatusBadge, { STATUS_LABELS } from "@/components/shared/StatusBadge";
import TicketStatusBadge, { TICKET_STATUS_LABELS } from "@/components/shared/TicketStatusBadge";
import { PAYMENT_STATUS } from "@/pages/admin/payments/paymentPresentation";

const VERIFY_LABEL = ["Nama label dan penanggung jawab", "Logo label", "Email aktif dan WhatsApp", "Alamat dan kota", "Kontrak distribusi aktif", "Rekening penerima lengkap", "KTP penanggung jawab disetujui"];
const VERIFY_MASTER = ["Paket Business aktif", "Setiap label dalam akun terverifikasi", "Satu penanggung jawab dan satu rekening pencairan"];
const WITHDRAW = [["requested", "Diajukan", "blue"], ["approved", "Disetujui", "blue"], ["paid", "Dibayar", "green"], ["rejected", "Ditolak", "red"]];
const PAYMENT_TONES = { paid: "green", pending: "mustard", expired: undefined, failed: "red", cancelled: undefined };
const MODES = [["Standar", "7 hari kerja", "Mengikuti paket"], ["Express", "5 hari kerja", "2 token per lagu"], ["MAX", "3 hari kerja · Jumat sebelum 12.00 WIB dapat tayang Minggu", "3 token per lagu"]];
const STEPS = ["Pemeriksaan", "Siap dikirim", "Distribusi", "Tayang"];

function Block({ title, children }) {
  return <section className="v13-card"><div className="v13-card-head"><h2>{title}</h2></div><div className="v13-card-body">{children}</div></section>;
}

// V13 standardsPage9: read-only reference of rules and markers used across the app.
export default function LabelStandards() {
  const { t } = useAppPreferences();
  return <div className="max-w-5xl space-y-5" data-testid="label-standards">
    <header><div className="v13-section-label">{t("Standar & Penanda")}</div><h1 className="mt-1 text-3xl">{t("Aturan dan penanda yang dipakai di Rilis Musik.")}</h1><p className="mt-2 text-sm text-[var(--ui-muted)]">{t("Versi aturan")}: V13 · {t("Oktober 2026")}</p></header>
    <div className="grid gap-5 lg:grid-cols-2">
      <Block title={t("Verifikasi Label")}>{VERIFY_LABEL.map((item) => <div key={item} className="flex gap-2 py-1.5 text-sm"><Check className="mt-0.5 h-4 w-4 text-[var(--v13-up)]" />{t(item)}</div>)}</Block>
      <Block title={t("Verifikasi Master Multi-label")}>{VERIFY_MASTER.map((item) => <div key={item} className="flex gap-2 py-1.5 text-sm"><Check className="mt-0.5 h-4 w-4 text-[var(--v13-up)]" />{t(item)}</div>)}</Block>
    </div>
    <Block title={t("Kamus Penanda")}>
      <div className="grid gap-6 md:grid-cols-2">
        <div><div className="v13-section-label mb-2">{t("Rilisan")}</div><div className="flex flex-wrap gap-2">{Object.keys(STATUS_LABELS).map((key) => <StatusBadge key={key} status={key} />)}</div></div>
        <div><div className="v13-section-label mb-2">{t("Penarikan")}</div><div className="flex flex-wrap gap-2">{WITHDRAW.map(([key, name, tone]) => <span key={key} className="v13-pill" data-tone={tone}>{t(name)}</span>)}</div></div>
        <div><div className="v13-section-label mb-2">{t("Tiket bantuan")}</div><div className="flex flex-wrap gap-2">{Object.keys(TICKET_STATUS_LABELS).map((key) => <TicketStatusBadge key={key} status={key} />)}</div></div>
        <div><div className="v13-section-label mb-2">{t("Transaksi")}</div><div className="flex flex-wrap gap-2">{Object.entries(PAYMENT_STATUS).map(([key, name]) => <span key={key} className="v13-pill" data-tone={PAYMENT_TONES[key]}>{t(name)}</span>)}</div></div>
      </div>
    </Block>
    <div className="grid gap-5 lg:grid-cols-2">
      <Block title={t("Mode rilis")}>{MODES.map(([name, lead, cost]) => <div key={name} className="v13-row"><div><div className="v13-row-title">{name}</div><div className="v13-row-sub">{t(lead)}</div></div><span className="text-sm text-[var(--ui-muted)]">{t(cost)}</span></div>)}<p className="mt-2 text-xs text-[var(--ui-muted)]">{t("Tanggal tercepat bukan jaminan tayang. Hari libur belum diperhitungkan.")}</p></Block>
      <Block title={t("Tahap pekerjaan rilisan")}>
        <div className="v13-steps" style={{ "--steps": STEPS.length, "--fraction": 1 / 3 }}>{STEPS.map((step, index) => <i key={step} className={index < 1 ? "is-done" : index === 1 ? "is-current" : ""}>{index < 1 && <Check strokeWidth={3} />}</i>)}</div>
        <div className="mt-2 grid text-center text-xs text-[var(--ui-muted)]" style={{ gridTemplateColumns: `repeat(${STEPS.length}, minmax(0, 1fr))` }}>{STEPS.map((step) => <span key={step}>{t(step)}</span>)}</div>
        <div className="mt-6 v13-section-label">{t("Warna perhatian")}</div>
        <div className="mt-2 flex flex-wrap gap-2"><span className="v13-pill" data-tone="mustard">{t("Mustard · perlu tindakan")}</span><span className="v13-pill" data-tone="red" data-pulse>{t("Merah · mendesak")}</span><span className="v13-pill" data-tone="blue">{t("Biru · informasi")}</span></div>
      </Block>
    </div>
  </div>;
}
