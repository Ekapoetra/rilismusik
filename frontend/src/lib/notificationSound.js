let context;
const played = new Set();
let lastTime = 0;

export async function unlockNotificationSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return false;
    context ||= new AudioContext();
    if (context.state === "suspended") await context.resume();
    return context.state === "running";
  } catch { return false; }
}

export function installSoundUnlock() {
  const unlock = () => { unlockNotificationSound(); };
  window.addEventListener("pointerdown", unlock, { capture: true, once: true });
  window.addEventListener("keydown", unlock, { capture: true, once: true });
  return () => { window.removeEventListener("pointerdown", unlock, true); window.removeEventListener("keydown", unlock, true); };
}

function _kindEnabled(kind) {
  if (localStorage.getItem("rm-sound-enabled") === "false") return false; // master mute
  const key = kind === "chat" ? "rm-sound-chat" : kind === "urgent" ? "rm-sound-urgent" : "rm-sound-notification";
  return localStorage.getItem(key) !== "false";
}

function _inQuietHours() {
  if (localStorage.getItem("rm-quiet-enabled") !== "true") return false;
  const start = localStorage.getItem("rm-quiet-start") || "22:00";
  const end = localStorage.getItem("rm-quiet-end") || "07:00";
  const now = new Date();
  const cur = now.getHours() * 60 + now.getMinutes();
  const toMin = (s) => { const [h, m] = String(s).split(":").map(Number); return (h || 0) * 60 + (m || 0); };
  const s = toMin(start), e = toMin(end);
  if (s === e) return false;
  return s < e ? (cur >= s && cur < e) : (cur >= s || cur < e); // wrap past midnight
}

export async function playNotificationSound(kind = "notification", eventId = null, force = false) {
  if (!force && !_kindEnabled(kind)) return false;
  if (!force && kind !== "urgent" && _inQuietHours()) return false; // urgent bypasses quiet hours
  if (eventId && played.has(eventId)) return false;
  if (!force && Date.now() - lastTime < 500) return false;
  if (!context || context.state !== "running") { if (!force || !await unlockNotificationSound()) return false; }
  const storedVolume = Number(localStorage.getItem("rm-sound-volume") ?? 0.75);
  const volume = Number.isFinite(storedVolume) ? Math.max(0, Math.min(1, storedVolume)) : 0.75;
  if (!volume) return false;
  lastTime = Date.now();
  if (eventId) { played.add(eventId); if (played.size > 500) played.delete(played.values().next().value); }
  const notes = kind === "chat" ? [740, 988, 1175]
    : kind === "online" ? [523, 784]
    : kind === "urgent" ? [988, 1319, 988, 1319]
    : [880, 659];
  const step = kind === "urgent" ? 0.11 : 0.14;
  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const start = context.currentTime + index * step;
    oscillator.type = kind === "urgent" ? "triangle" : "sine"; oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime((kind === "urgent" ? 0.38 : 0.3) * volume, start + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.3);
    oscillator.connect(gain); gain.connect(context.destination);
    oscillator.start(start); oscillator.stop(start + 0.32);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
  });
  return true;
}