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

export async function playNotificationSound(kind = "notification", eventId = null, force = false) {
  if (!force && localStorage.getItem("rm-sound-enabled") === "false") return false;
  if (eventId && played.has(eventId)) return false;
  if (!force && Date.now() - lastTime < 500) return false;
  if (!context || context.state !== "running") { if (!force || !await unlockNotificationSound()) return false; }
  const storedVolume = Number(localStorage.getItem("rm-sound-volume") ?? 0.75);
  const volume = Number.isFinite(storedVolume) ? Math.max(0, Math.min(1, storedVolume)) : 0.75;
  if (!volume) return false;
  lastTime = Date.now();
  if (eventId) { played.add(eventId); if (played.size > 500) played.delete(played.values().next().value); }
  const notes = kind === "chat" ? [740, 988, 1175] : kind === "online" ? [523, 784] : [880, 659];
  notes.forEach((frequency, index) => {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    const start = context.currentTime + index * 0.14;
    oscillator.type = "sine"; oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.0001, start);
    gain.gain.exponentialRampToValueAtTime(0.3 * volume, start + 0.015);
    gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.3);
    oscillator.connect(gain); gain.connect(context.destination);
    oscillator.start(start); oscillator.stop(start + 0.32);
    oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
  });
  return true;
}