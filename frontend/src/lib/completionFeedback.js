import { toast } from "@/components/ui/sonner";
import { playNotificationSound } from "@/lib/notificationSound";

// Ephemeral completion feedback (NOT a notification, does not raise the badge).
// Message library per Work Type + a default set, with a little variety.
const LIBRARY = {
  release_go_live: [
    "Yeay 🎉 rilisan berhasil ditayangkan!",
    "Mantap! Rilisanmu kini sudah live 🎶",
    "Sip! Satu rilisan sukses tayang ✨",
  ],
  release_review: [
    "Yeay 🎉 kamu telah menyelesaikan review rilisan.",
    "Review beres! Terima kasih sudah teliti 👏",
  ],
  ticket: [
    "Mantap! Tiket support selesai ditangani ✅",
    "Yeay 🎉 satu tiket kelar!",
  ],
  withdraw: [
    "Sip! Penarikan dana selesai diproses 💸",
    "Yeay 🎉 penarikan tuntas!",
  ],
  default: [
    "Yeay 🎉 pekerjaan selesai!",
    "Kerja bagus! Satu tugas tuntas ✅",
    "Mantap! Beres satu lagi ✨",
  ],
};

export function celebrateWork(workType) {
  const arr = LIBRARY[workType] || LIBRARY.default;
  const msg = arr[Math.floor(Math.random() * arr.length)];
  toast.success(msg, { duration: 3500 });
  playNotificationSound("notification", `celebrate:${Date.now()}`);
}
