export const validateCoverFile = (file) => new Promise((resolve, reject) => {
  if (!["image/jpeg", "image/png"].includes(file.type)) { reject(new Error("Cover wajib JPG atau PNG")); return; }
  const image = new Image(); const url = URL.createObjectURL(file);
  image.onload = () => { URL.revokeObjectURL(url); image.width === 3000 && image.height === 3000 ? resolve() : reject(new Error("Cover harus tepat 3000×3000 px")); };
  image.onerror = () => { URL.revokeObjectURL(url); reject(new Error("File cover tidak dapat dibaca")); };
  image.src = url;
});

export const readWavSampleRate = async (file) => {
  if (!file.name.toLowerCase().endsWith(".wav")) throw new Error("Audio wajib berformat WAV");
  const buffer = await file.slice(0, 65536).arrayBuffer(); const view = new DataView(buffer);
  const text = (offset, length) => Array.from({ length }, (_, index) => String.fromCharCode(view.getUint8(offset + index))).join("");
  if (view.byteLength < 28 || text(0, 4) !== "RIFF" || text(8, 4) !== "WAVE") throw new Error("File WAV tidak valid");
  let offset = 12;
  while (offset + 8 <= view.byteLength) {
    const chunk = text(offset, 4); const size = view.getUint32(offset + 4, true);
    if (chunk === "fmt " && offset + 16 <= view.byteLength) {
      const sampleRate = view.getUint32(offset + 12, true);
      if (![44100, 48000].includes(sampleRate)) throw new Error("Sample rate WAV harus 44,1 kHz atau 48 kHz");
      return sampleRate;
    }
    offset += 8 + size + (size % 2);
  }
  throw new Error("Metadata sample rate WAV tidak ditemukan");
};