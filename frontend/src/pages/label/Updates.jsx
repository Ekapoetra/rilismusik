import React from "react";
import { useAppPreferences } from "@/contexts/AppPreferencesContext";
import PageHeader from "@/components/shared/PageHeader";
import { Sparkles, Rocket, FileSearch, Gift, Disc3, Wallet, Settings } from "lucide-react";

/* D14 — panduan pembaruan, bukan log pengembangan: hanya memuat fitur yang
   benar-benar tersedia saat ini. Entri diperbarui setiap fitur ditambah,
   diubah, atau dihapus — ganti isi SECTIONS lalu naikkan PUBLISHED_AT.
   Bilingual inline (id/en) — konten terkurasi, bukan string UI yang
   diterjemahkan mesin.

   Siklus hidup: titik masuk (kartu di Dashboard label) hanya tampil selama
   WINDOW_DAYS sejak PUBLISHED_AT, lalu hilang sampai batch pembaruan
   berikutnya. Halaman /label/updates sendiri tetap bisa diakses langsung
   sebagai arsip. */
export const UPDATES_PUBLISHED_AT = "2026-10-13";
export const UPDATES_WINDOW_DAYS = 30;

export function updatesActive(now = new Date()) {
  const published = new Date(`${UPDATES_PUBLISHED_AT}T00:00:00+07:00`);
  return now.getTime() <= published.getTime() + UPDATES_WINDOW_DAYS * 86400e3;
}
const KINDS = {
  baru: { id: "Baru", en: "New", bg: "rgba(16,185,129,0.15)", color: "#6EE7B7", dot: "#34D399" },
  berubah: { id: "Berubah", en: "Changed", bg: "rgba(245,158,11,0.15)", color: "#FCD34D", dot: "#F59E0B" },
  dihapus: { id: "Dihapus", en: "Removed", bg: "rgba(239,68,68,0.15)", color: "#FCA5A5", dot: "#EF4444" },
};

const SECTIONS = [
  {
    id: "aktivasi", icon: Rocket,
    title: { id: "Mulai & aktivasi", en: "Getting started & activation" },
    items: [
      ["baru", {
        id: "Kontrak digital dibuat otomatis — tanggal kesepakatan tercatat dan bisa diunduh dari menu Kontrak.",
        en: "Your digital contract is generated automatically — the acceptance date is recorded and it can be downloaded from Contracts.",
      }],
      ["baru", {
        id: "Aktivasi akun lewat pemeriksaan admin: identitas label dan rekening bank diverifikasi sebelum fitur penuh terbuka.",
        en: "Account activation goes through admin review: label identity and bank details are verified before full access opens.",
      }],
    ],
  },
  {
    id: "klaim", icon: FileSearch,
    title: { id: "Klaim label lama", en: "Legacy label claims" },
    items: [
      ["baru", {
        id: "Label lama bisa diklaim dari dashboard — admin memverifikasi kepemilikan sebelum label terhubung ke akun.",
        en: "Legacy labels can be claimed from the dashboard — an admin verifies ownership before the label links to your account.",
      }],
      ["baru", {
        id: "Persetujuan klaim hanya oleh Super Admin; akses label yang bermasalah dapat dicabut kembali.",
        en: "Claim approval is Super Admin only; problematic label access can be revoked.",
      }],
      ["baru", {
        id: "Member lama yang terverifikasi mendapat masa paket satu tahun terhitung dari tanggal verifikasi admin.",
        en: "Verified legacy members get a one-year package period counted from the admin's verification date.",
      }],
    ],
  },
  {
    id: "paket", icon: Gift,
    title: { id: "Paket, benefit & token", en: "Plans, benefits & tokens" },
    items: [
      ["berubah", {
        id: "Empat jenjang paket: Basic (Pay Per Release), Studio (Annual), Pro (Annual VIP), dan Business (Multi Label).",
        en: "Four plan tiers: Basic (Pay Per Release), Studio (Annual), Pro (Annual VIP), and Business (Multi Label).",
      }],
      ["baru", {
        id: "Kuota layanan gratis bulanan per paket — berlaku untuk registrasi WAMI dan layanan tambahan, reset setiap tanggal 1 (WIB).",
        en: "A monthly free-service quota per plan — covers WAMI registration and add-on services, resetting on the 1st (GMT+7).",
      }],
      ["baru", {
        id: "Bonus dari admin — layanan gratis tambahan dengan batas waktu, tampil di halaman Token dan dipakai lebih dulu sebelum kuota bulanan.",
        en: "Admin-granted bonuses — extra free services with an expiry, shown on the Token page and used before the monthly quota.",
      }],
      ["baru", {
        id: "Dompet Token — invoice bisa dibayar dengan token saat penawaran token lebih murah dari harga Rupiah.",
        en: "Token wallet — invoices can be paid with tokens whenever the token offer is cheaper than the Rupiah price.",
      }],
    ],
  },
  {
    id: "rilisan", icon: Disc3,
    title: { id: "Rilisan", en: "Releases" },
    items: [
      ["berubah", {
        id: "Status rilisan lebih jelas — klarifikasi admin, permintaan pembatalan, tayang parsial, dan ditutup kini terlihat di detail rilisan.",
        en: "Clearer release statuses — admin clarification, cancel requests, partial release, and closed are now visible on the release detail.",
      }],
      ["baru", {
        id: "Batas pengajuan rilisan harian mengikuti paket — kuota reset setiap hari (WIB).",
        en: "Daily release-submission limits follow your plan — the quota resets every day (GMT+7).",
      }],
    ],
  },
  {
    id: "uang", icon: Wallet,
    title: { id: "Penarikan & royalti", en: "Withdrawals & royalties" },
    items: [
      ["berubah", {
        id: "Jadwal penarikan — pengajuan dibuka tanggal 1–14, pencairan diproses tanggal 15–20 (WIB).",
        en: "Withdrawal schedule — requests open on the 1st–14th, payouts are processed on the 15th–20th (GMT+7).",
      }],
    ],
  },
  {
    id: "sistem", icon: Settings,
    title: { id: "Di balik layar", en: "Behind the scenes" },
    items: [
      ["baru", {
        id: "Banner pemeliharaan tampil otomatis saat sistem dijadwalkan maintenance.",
        en: "A maintenance banner appears automatically whenever maintenance is scheduled.",
      }],
      ["baru", {
        id: "Menu Pembaruan ini — panduan perubahan yang selalu mengikuti fitur yang tersedia.",
        en: "This Updates menu — a guide to changes that always follows the features actually available.",
      }],
    ],
  },
];

function KindBadge({ kind, lang }) {
  const s = KINDS[kind] || KINDS.baru;
  return (
    <span className="rm-badge" style={{ background: s.bg, color: s.color }}
      data-testid={`update-kind-${kind}`}>
      <span className="rm-badge-dot" style={{ background: s.dot }} />
      {s[lang]}
    </span>
  );
}

export default function LabelUpdates() {
  const { locale, t } = useAppPreferences();
  const lang = locale === "en" ? "en" : "id";
  const usedKinds = [...new Set(SECTIONS.flatMap((s) => s.items.map((i) => i[0])))];
  return (
    <div className="space-y-7 max-w-3xl" data-testid="updates-page">
      <PageHeader icon={Sparkles} eyebrow={t("Apa yang baru")}
        title={t("Pembaruan")}
        sub={t("Catatan perubahan — hanya fitur yang benar-benar tersedia saat ini.")} />
      <div className="flex flex-wrap gap-2" data-testid="updates-legend">
        {usedKinds.map((k) => <KindBadge key={k} kind={k} lang={lang} />)}
      </div>
      {SECTIONS.map((s) => {
        const Icon = s.icon;
        return (
          <section key={s.id} className="rm-card p-5 space-y-3" data-testid={`updates-section-${s.id}`}>
            <div className="flex items-center gap-2 text-sm font-bold">
              <Icon className="w-4 h-4 text-pink-300" />{s.title[lang]}
            </div>
            <ul className="space-y-2.5">
              {s.items.map(([kind, text], i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-zinc-300">
                  <span className="mt-0.5 shrink-0"><KindBadge kind={kind} lang={lang} /></span>
                  <span>{text[lang]}</span>
                </li>
              ))}
            </ul>
          </section>
        );
      })}
      <p className="text-xs text-zinc-500" data-testid="updates-policy-note">
        {lang === "en"
          ? `Published ${UPDATES_PUBLISHED_AT} — this list is a usage guide, not a development log. The updates shortcut on your dashboard shows for ${UPDATES_WINDOW_DAYS} days after each release.`
          : `Terbit ${UPDATES_PUBLISHED_AT} — daftar ini panduan penggunaan, bukan riwayat pengembangan. Pintasan pembaruan di dashboard tampil ${UPDATES_WINDOW_DAYS} hari setelah setiap rilis.`}
      </p>
    </div>
  );
}
