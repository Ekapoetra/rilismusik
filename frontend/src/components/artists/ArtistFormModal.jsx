import React, { useState } from "react";
import { X } from "lucide-react";
import { api, formatApiError } from "@/api/client";
import { SocialLinksEditor } from "@/components/artists/SocialLinksEditor";
import { newSocialLink, socialLinksAreValid } from "@/constants/socialPlatforms";
import { toast } from "@/components/ui/sonner";
import { ARTIST_MGMT } from "@/constants/testIds";

export const ArtistFormModal = ({ artist, onClose, onSaved }) => {
  const editing = Boolean(artist);
  const [form, setForm] = useState({ artist_name: artist?.artist_name || "", email: artist?.email || "", whatsapp: artist?.whatsapp || "", password: "", social_links: artist?.social_links?.length ? artist.social_links.map((item) => ({ ...item, client_id: crypto.randomUUID() })) : [newSocialLink()] });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault(); setError("");
    if (!socialLinksAreValid(form.social_links)) { setError("Minimal satu tautan sosial yang valid wajib diisi."); return; }
    if (!editing && form.password.length < 8) { setError("Password minimal 8 karakter."); return; }
    setSaving(true);
    try {
      const social_links = form.social_links.map(({ client_id, ...item }) => item);
      if (editing) await api.patch(`/artists/${artist.id}`, { artist_name: form.artist_name, whatsapp: form.whatsapp, social_links });
      else await api.post("/artists/", { ...form, social_links });
      toast.success(editing ? "Data artis diperbarui." : "Artis baru berhasil ditambahkan.");
      await onSaved(); onClose();
    } catch (requestError) { setError(formatApiError(requestError.response?.data?.detail) || "Gagal menyimpan artis."); }
    finally { setSaving(false); }
  };
  return <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-sm" onMouseDown={(event) => event.target === event.currentTarget && onClose()} data-testid="label-artist-form-modal"><form onSubmit={submit} className="max-h-[90vh] w-full max-w-2xl space-y-5 overflow-y-auto rounded-lg border border-white/10 bg-[#0F0F0F] p-6 shadow-2xl" data-testid="label-artist-form"><div className="flex items-center justify-between gap-4"><div><div className="text-xs font-bold uppercase tracking-widest text-zinc-500">Manajemen Artis</div><h2 className="font-display text-2xl font-bold">{editing ? "Edit Artis" : "Tambah Artis"}</h2></div><button type="button" onClick={onClose} className="rounded-md p-2 text-zinc-400 hover:bg-white/5 hover:text-white" data-testid="label-artist-form-close"><X className="h-5 w-5" /></button></div><div className="grid gap-4 md:grid-cols-2"><label><span className="rm-label">Nama Artis</span><input className="rm-input" value={form.artist_name} onChange={(event) => setForm({ ...form, artist_name: event.target.value })} required data-testid={ARTIST_MGMT.nameInput} /></label>{!editing && <label><span className="rm-label">Email Login</span><input type="email" className="rm-input" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required data-testid={ARTIST_MGMT.emailInput} /></label>}<label><span className="rm-label">WhatsApp <span className="normal-case text-zinc-600">(opsional)</span></span><input className="rm-input" value={form.whatsapp} onChange={(event) => setForm({ ...form, whatsapp: event.target.value })} data-testid="label-artist-whatsapp-input" /></label>{!editing && <label><span className="rm-label">Password Sementara</span><input type="text" minLength={8} className="rm-input" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required data-testid={ARTIST_MGMT.passwordInput} /></label>}</div><SocialLinksEditor links={form.social_links} onChange={(social_links) => setForm({ ...form, social_links })} prefix="label-artist-form" />{error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200" data-testid="label-artist-form-error">{error}</div>}<div className="flex justify-end gap-3 border-t border-white/10 pt-5"><button type="button" className="rm-btn-ghost" onClick={onClose} data-testid="label-artist-form-cancel">Batal</button><button type="submit" className="rm-btn-primary" disabled={saving} data-testid={ARTIST_MGMT.saveButton}>{saving ? "Menyimpan…" : "Simpan Artis"}</button></div></form></div>;
};