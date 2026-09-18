import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Layers, CheckCircle2, ArrowLeft } from "lucide-react";
import { api, formatApiError } from "@/api/client";

export default function MultiLabelRequest() {
  const [form, setForm] = useState({ name: "", email: "", whatsapp: "", label_info: "", message: "" });
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setErr("");
    try {
      await api.post("/multi-label/request", form);
      setDone(true);
    } catch (e2) { setErr(formatApiError(e2.response?.data?.detail || e2.message)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-[#0a0a0f] px-4 py-16 text-white">
      <div className="mx-auto max-w-lg">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm text-zinc-400 hover:text-white"><ArrowLeft className="h-4 w-4" /> Kembali</Link>
        <div className="rm-glass-strong rounded-3xl border border-[#A24EFF]/30 p-8">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full bg-[#A24EFF]/15 px-3 py-1 text-xs font-bold uppercase tracking-widest text-[#C79BFF]"><Layers className="h-4 w-4" /> Multi Label</div>
          {done ? (
            <div className="text-center" data-testid="ml-request-success">
              <CheckCircle2 className="mx-auto mb-4 h-12 w-12 text-emerald-400" />
              <h1 className="font-display text-2xl font-extrabold">Permintaan terkirim!</h1>
              <p className="mt-2 text-sm text-zinc-400">Tim kami akan menghubungi Anda untuk mengaktifkan akun Multi Label.</p>
              <Link to="/" className="rm-btn-primary mt-6 inline-block">Selesai</Link>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4" data-testid="ml-request-form">
              <div><h1 className="font-display text-2xl font-extrabold">Ajukan Multi Label</h1><p className="mt-1 text-sm text-zinc-400">Kelola banyak label dalam satu akun — Rp1.500.000/tahun.</p></div>
              {err && <div className="rounded-xl bg-red-500/15 px-3 py-2 text-sm text-red-300" data-testid="ml-request-error">{err}</div>}
              <label className="block text-xs font-semibold text-zinc-400">Nama Penanggung Jawab<input required value={form.name} onChange={set("name")} className="rm-input mt-1 w-full" data-testid="ml-request-name" /></label>
              <label className="block text-xs font-semibold text-zinc-400">Email<input required type="email" value={form.email} onChange={set("email")} className="rm-input mt-1 w-full" data-testid="ml-request-email" /></label>
              <label className="block text-xs font-semibold text-zinc-400">WhatsApp<input required value={form.whatsapp} onChange={set("whatsapp")} className="rm-input mt-1 w-full" data-testid="ml-request-whatsapp" /></label>
              <label className="block text-xs font-semibold text-zinc-400">Label yang ingin digabung (opsional)<textarea value={form.label_info} onChange={set("label_info")} rows={2} className="rm-input mt-1 w-full" placeholder="Nama label / email akun existing" data-testid="ml-request-labels" /></label>
              <label className="block text-xs font-semibold text-zinc-400">Pesan (opsional)<textarea value={form.message} onChange={set("message")} rows={2} className="rm-input mt-1 w-full" data-testid="ml-request-message" /></label>
              <button type="submit" disabled={busy} className="rm-btn-primary w-full disabled:opacity-50" data-testid="ml-request-submit">{busy ? "Mengirim…" : "Kirim Permintaan"}</button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
