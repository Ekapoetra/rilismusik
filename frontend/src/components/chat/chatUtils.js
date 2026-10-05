import { api } from "@/api/client";

let audioCtx = null;

export function playChatSound() {
  try {
    if (!audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      audioCtx = new Ctx();
    }
    if (audioCtx.state === "suspended") audioCtx.resume();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(880, audioCtx.currentTime);
    osc.frequency.setValueAtTime(1180, audioCtx.currentTime + 0.09);
    gain.gain.setValueAtTime(0.001, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.16, audioCtx.currentTime + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + 0.32);
    osc.start(); osc.stop(audioCtx.currentTime + 0.34);
  } catch (e) { /* noop */ }
}

export const timeLabel = (iso) => {
  try { return new Date(iso).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }); }
  catch { return ""; }
};

export async function uploadChatAttachment(file) {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/chat/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
  return data;
}

// Merge a full or incremental thread response into the current list. Polls
// repeat a short overlap, so messages are de-duplicated by id and kept in
// chronological order; a full response replaces the list.
export function mergeMessages(current, incoming, incremental) {
  if (!incremental) return incoming || [];
  if (!incoming?.length) return current;
  const byId = new Map(current.map((m) => [m.id, m]));
  let changed = false;
  for (const m of incoming) {
    if (!byId.has(m.id)) changed = true;
    byId.set(m.id, m);
  }
  if (!changed) return current;
  return Array.from(byId.values()).sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)));
}

export const lastMessageAt = (messages) => (messages?.length ? messages[messages.length - 1].created_at : undefined);
