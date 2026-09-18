import english from "./catalog.en.json";
import indonesian from "./catalog.id.json";
import systemTemplates from "./catalog.patterns.json";
import reviewed from "./catalog.reviewed.json";

const listeners = new Set();
let locale = localStorage.getItem("rm-ui-locale") || localStorage.getItem("admin-ui-locale") || "id";
if (!["id", "en"].includes(locale)) locale = "id";
const overrides = {
  "Admin Console": ["Konsol Admin", "Admin Console"], "Dashboard": ["Dasbor", "Dashboard"],
  "Support Tickets": ["Tiket Bantuan", "Support Tickets"], "Role & Permission": ["Role & Izin", "Roles & Permissions"],
  "Bahasa": ["Bahasa", "Language"], "Terang": ["Terang", "Light"], "Gelap": ["Gelap", "Dark"], "Otomatis": ["Otomatis", "Auto"],
  "Mode tampilan": ["Mode tampilan", "Appearance"], "Suara notifikasi": ["Suara notifikasi", "Notification sounds"],
  "Aktifkan suara": ["Aktifkan suara", "Enable sound"], "Uji suara": ["Uji suara", "Test sound"], "Volume": ["Volume", "Volume"],
  "Pesan Chat Baru": ["Pesan Chat Baru", "New Chat Message"], "Buka chat": ["Buka chat", "Open chat"],
  "Tutup": ["Tutup", "Close"], "Putar": ["Putar", "Play"], "Jeda": ["Jeda", "Pause"], "Unduh WAV": ["Unduh WAV", "Download WAV"],
  "Berikutnya": ["Berikutnya", "Next"], "Sebelumnya": ["Sebelumnya", "Previous"], "Kembali": ["Kembali", "Back"],
  "Notifikasi": ["Notifikasi", "Notifications"], "Keluar": ["Keluar", "Sign out"], "Logout": ["Keluar", "Sign out"],
  "Manajemen Label": ["Manajemen Label", "Label Management"], "Manajemen Rilisan": ["Manajemen Rilisan", "Release Management"],
  "Simpan": ["Simpan", "Save"], "Batal": ["Batal", "Cancel"], "Hapus": ["Hapus", "Delete"], "Cari": ["Cari", "Search"],
  "Memuat…": ["Memuat…", "Loading…"], "Tidak ada data": ["Tidak ada data", "No data available"],
  "Status": ["Status", "Status"], "Idle": ["Idle", "Idle"], "Online": ["Online", "Online"], "Offline": ["Offline", "Offline"],
  "Profil": ["Profil", "Profile"], "Chat": ["Chat", "Chat"],
  "Ringkasan Platform": ["Ringkasan Platform", "Platform Summary"], "Ringkasan Kerja": ["Ringkasan Kerja", "Work Summary"],
  "Distribusi tugas": ["Distribusi tugas", "Task distribution"], "Total Tugas": ["Total Tugas", "Total Tasks"],
  "Total Label": ["Total Label", "Total Labels"], "Total Artist": ["Total Artist", "Total Artists"],
  "Total Rilis": ["Total Rilis", "Total Releases"], "Active Member": ["Active Member", "Active Members"],
  "Sales Revenue": ["Sales Revenue", "Sales Revenue"], "Requested Withdrawal": ["Permintaan Penarikan", "Requested Withdrawal"],
  "Royalty Income": ["Royalty Income", "Royalty Income"], "via Xendit": ["via Xendit", "via Xendit"],
  "impor CSV Believe": ["impor CSV Believe", "Believe CSV import"], "aktivasi akun": ["aktivasi akun", "account activation"],
  "Hari ini": ["Hari ini", "Today"], "Minggu ini": ["Minggu ini", "This week"], "Bulan ini": ["Bulan ini", "This month"],
  "Aktivitas Terbaru": ["Aktivitas Terbaru", "Recent Activity"], "Aktivitas Anda": ["Aktivitas Anda", "Your activity"],
  "Kerja & Keuangan": ["Kerja & Keuangan", "Work & Finance"], "Belum ada aktivitas.": ["Belum ada aktivitas.", "No activity yet."],
  "Anda": ["Anda", "You"], "Sedang Dikerjakan": ["Sedang Dikerjakan", "In Progress"],
  "Pekerjaan yang sedang berjalan": ["Pekerjaan yang sedang berjalan", "Work currently in progress"],
  "Tidak ada pekerjaan berjalan.": ["Tidak ada pekerjaan berjalan.", "No work in progress."],
  "Completed": ["Completed", "Completed"], "In Progress": ["In Progress", "In Progress"], "Open": ["Open", "Open"], "Overdue": ["Overdue", "Overdue"],
};
// Invalid/missing entries fail back to the authored text, never a guessed reverse translation.
const catalogText = (catalog, key) => {
  const value = catalog && Object.prototype.hasOwnProperty.call(catalog, key) ? catalog[key] : null;
  return typeof value === "string" && !/@@|&apos;|&quot;/.test(value) ? value : null;
};
const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const patterns = [...new Set([...(Array.isArray(systemTemplates) ? systemTemplates : []), ...Object.keys(reviewed).filter((key) => /\{\d+\}/.test(key))])].filter((source) => typeof source === "string").map((source) => {
  const indices = [];
  const expression = source.split(/(\{\d+\})/).map((part) => { if (/^\{\d+\}$/.test(part)) { indices.push(Number(part.slice(1, -1))); return "([\\s\\S]*?)"; } return escapeRegex(part).replace(/\s+/g, "\\s+"); }).join("");
  return { source, indices, expression: new RegExp(`^${expression}$`) };
}).sort((a, b) => b.source.length - a.source.length);

export const getLocale = () => locale;
export const subscribeLocale = (callback) => { listeners.add(callback); return () => listeners.delete(callback); };
export const setLocale = (next, persist = true) => {
  if (!["id", "en"].includes(next) || next === locale) return;
  locale = next; if (persist) { localStorage.setItem("rm-ui-locale", next); localStorage.setItem("admin-ui-locale", next); }
  listeners.forEach((callback) => callback());
};
window.addEventListener("storage", (event) => {
  if (event.key === "rm-ui-locale" && ["id", "en"].includes(event.newValue)) {
    locale = event.newValue; listeners.forEach((callback) => callback());
  }
});

export function translateUi(source, selected = locale) {
  if (typeof source !== "string") return source;
  const key = source.replace(/\s+/g, " ").trim();
  const explicit = overrides[key];
  let result = explicit ? explicit[selected === "en" ? 1 : 0] : selected === "en" ? catalogText(reviewed, key) || catalogText(english, key) : catalogText(indonesian, key);
  if (!result && selected === "en") {
    for (const pattern of patterns) {
      const match = key.match(pattern.expression);
      if (!match) continue;
      const values = Object.fromEntries(pattern.indices.map((index, position) => [index, match[position + 1]]));
      result = (catalogText(reviewed, pattern.source) || catalogText(english, pattern.source) || pattern.source).replace(/\{(\d+)\}/g, (_, index) => values[Number(index)] ?? "");
      break;
    }
  }
  result ||= key;
  return key ? `${source.match(/^\s*/)[0]}${result}${source.match(/\s*$/)[0]}` : source;
}
export const translateTemplate = (source, values = [], selected = locale) => translateUi(source, selected).replace(/\{(\d+)\}/g, (_, index) => String(values[Number(index)] ?? ""));