import React from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { todayPlus } from "./releaseFormState";

const Field = ({ label, children, span = "" }) => <label className={span}><span className="rm-label">{label}</span>{children}</label>;

export const ReleaseInfoStep = ({ form, updateForm, labelName, responsibleName, onNext }) => {
  const change = (field) => (event) => updateForm({ [field]: event.target.value });
  return <section className="space-y-7" data-testid="upload-release-info-step"><div><h2 className="font-display text-2xl font-bold">Informasi rilisan</h2><p className="mt-1 text-sm text-zinc-400">Data utama yang tampil di DSP dan dokumen distribusi.</p></div><div className="grid gap-5 md:grid-cols-2">
    <Field label="Judul Rilisan"><input className="rm-input" value={form.release_title} onChange={change("release_title")} data-testid="upload-release-title-input" /></Field>
    <Field label="Tipe Rilisan"><select className="rm-input" value={form.release_type} onChange={change("release_type")} data-testid="upload-release-type-select"><option value="single">SINGLE</option><option value="ep">EP</option><option value="album">ALBUM</option></select></Field>
    <Field label="Genre"><input className="rm-input" value={form.genre} onChange={change("genre")} data-testid="upload-release-genre-input" /></Field>
    <Field label="Sub Genre"><input className="rm-input" value={form.subgenre} onChange={change("subgenre")} data-testid="upload-release-subgenre-input" /></Field>
    <Field label="Nama Label"><div className="rm-input flex items-center justify-between text-zinc-300" data-testid="upload-release-label-name"><span>{labelName || "—"}</span><LockKeyhole className="h-4 w-4 text-zinc-600" /></div></Field>
    <Field label="Nama Penanggung Jawab"><div className="rm-input flex items-center justify-between text-zinc-300" data-testid="upload-release-responsible-name"><span>{responsibleName || "—"}</span><LockKeyhole className="h-4 w-4 text-zinc-600" /></div></Field>
    <Field label="Nama Pemilik Karya — C Line"><input className="rm-input font-mono" value={form.copyright_line} onChange={change("copyright_line")} data-testid="upload-release-copyright-input" /></Field>
    <Field label="Nama Pemilik Master — P Line"><input className="rm-input font-mono" value={form.p_line} onChange={change("p_line")} data-testid="upload-release-pline-input" /></Field>
    <Field label="Tahun Produksi"><input type="number" min="1900" max="2100" className="rm-input" value={form.year} onChange={change("year")} data-testid="upload-release-year-input" /></Field>
    <Field label="Tanggal Rilis Digital — minimal 7 hari"><input type="date" min={todayPlus(7)} className="rm-input" value={form.release_date} onChange={change("release_date")} data-testid="upload-release-date-input" /></Field>
    <Field label="URL Web Artist / Channel YouTube Asli" span="md:col-span-2"><input type="url" className="rm-input" placeholder="https://youtube.com/channel/UC…" value={form.artist_web_url} onChange={change("artist_web_url")} data-testid="upload-release-artist-web-input" /><span className="mt-1 block text-xs text-zinc-500">Untuk YouTube gunakan URL asli /channel/UC… dari YouTube Studio, bukan URL custom.</span></Field>
  </div><div className="flex justify-end border-t border-white/10 pt-5"><button type="button" className="rm-btn-primary inline-flex items-center gap-2" onClick={onNext} data-testid="upload-release-info-next-button">Lanjut ke Artist <ArrowRight className="h-4 w-4" /></button></div></section>;
};