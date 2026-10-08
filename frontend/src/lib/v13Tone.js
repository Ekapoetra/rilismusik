// Maps the legacy dark-tuned badge dot colours to V13 pill tones.
const TONES = {
  green: ["#10b981", "#34d399", "#22c55e", "#4ade80"],
  red: ["#ef4444", "#f87171", "#dc2626"],
  mustard: ["#f59e0b", "#facc15", "#fb923c", "#eab308", "#f97316"],
  blue: ["#818cf8", "#3b82f6", "#6366f1", "#a855f7", "#ff1f8e", "#60a5fa", "#0ea5e9", "#38bdf8"],
};
export function toneOf(color) {
  const value = String(color || "").toLowerCase();
  return Object.keys(TONES).find((tone) => TONES[tone].includes(value));
}
