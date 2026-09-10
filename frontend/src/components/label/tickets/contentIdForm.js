import { api } from "@/api/client";

export const newContentIdCreator = () => ({ key: crypto.randomUUID(), full_name: "", nik: "", domicile: "", signing_city: "", authorship: "sole", track_ids: [], signature_file: null, signature_mode: "upload", ktp_file: null });
export const newContentIdState = () => ({ content_id_request_id: crypto.randomUUID(), content_id_track_ids: [], content_id_creators: [newContentIdCreator()], content_id_consent: false });

export async function prepareContentIdPayload(form) {
  const creators = form.content_id_creators || [];
  const selected = form.content_id_track_ids || [];
  if (!selected.length) throw new Error("Pilih minimal satu lagu untuk Pengajuan Content ID.");
  if (!form.content_id_consent) throw new Error("Persetujuan penggunaan data dan tanda tangan wajib dicentang.");
  const covered = new Set();
  for (const creator of creators) {
    if (creator.full_name.trim().length < 3 || !/^\d{16}$/.test(creator.nik) || creator.domicile.trim().length < 3 || creator.signing_city.trim().length < 2) throw new Error("Lengkapi nama sesuai KTP, NIK 16 digit, domisili, dan kota penandatanganan setiap pencipta.");
    if (!creator.signature_file || !creator.ktp_file) throw new Error("Tanda tangan dan foto KTP setiap pencipta wajib dilengkapi.");
    if (!creator.track_ids.length) throw new Error("Pilih lagu milik setiap pencipta.");
    creator.track_ids.forEach((id) => covered.add(id));
  }
  if (selected.some((id) => !covered.has(id))) throw new Error("Setiap lagu yang diajukan wajib memiliki pencipta.");
  const uploaded = [];
  const cleanup = () => Promise.allSettled(uploaded.map((id) => api.delete(`/tickets/content-id/assets/${id}`)));
  const upload = async (file, kind, signatureMode) => {
    const data = new FormData(); data.append("file", file); data.append("release_id", form.release_id); data.append("kind", kind); data.append("signature_mode", signatureMode || "upload");
    const result = await api.post("/tickets/content-id/assets", data, { headers: { "Content-Type": "multipart/form-data" } });
    uploaded.push(result.data.id); return result.data.id;
  };
  try {
    const records = [];
    for (const creator of creators) records.push({ full_name: creator.full_name.trim(), nik: creator.nik, domicile: creator.domicile.trim(), signing_city: creator.signing_city.trim(), authorship: creator.authorship, track_ids: creator.track_ids,
      signature_asset_id: await upload(creator.signature_file, "signature", creator.signature_mode), ktp_asset_id: await upload(creator.ktp_file, "ktp") });
    return { payload: { content_id_request_id: form.content_id_request_id, content_id_track_ids: selected, content_id_creators: records, content_id_consent: true }, cleanup };
  } catch (error) { await cleanup(); throw error; }
}