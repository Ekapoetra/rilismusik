import React, { useEffect, useState } from "react";
import { api, formatApiError } from "@/api/client";
import { ARTIST_MGMT } from "@/constants/testIds";
import { Plus, UserSquare2, X } from "lucide-react";

export default function LabelArtists() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ artist_name: "", email: "", whatsapp: "", password: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const load = async () => {
    const { data } = await api.get("/artists/");
    setItems(data);
  };
  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    if (form.password.length < 8) { setErr("Password minimal 8 karakter"); return; }
    setSaving(true);
    try {
      await api.post("/artists/", form);
      setOpen(false);
      setForm({ artist_name: "", email: "", whatsapp: "", password: "" });
      await load();
    } catch (e) { setErr(formatApiError(e.response?.data?.detail) || "Gagal"); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-5 max-w-5xl">
      <div className="flex justify-between items-center flex-wrap gap-3">
        <div>
          <div className="text-xs uppercase tracking-widest text-zinc-500 font-bold">Artist</div>
          <h1 className="font-display text-3xl font-extrabold tracking-tighter">Kelola Artist</h1>
        </div>
        <button className="rm-btn-primary flex items-center gap-2" onClick={() => setOpen(true)} data-testid={ARTIST_MGMT.addButton}>
          <Plus className="w-4 h-4" /> Tambah Artist
        </button>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {items.length === 0 ? (
          <div className="col-span-full rm-card p-10 text-center text-zinc-500 text-sm">Belum ada artist. Klik &quot;Tambah Artist&quot; untuk membuat akun artist baru.</div>
        ) : items.map((a) => (
          <div key={a.id} className="rm-card p-5">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#FF1F8E] to-[#A24EFF] grid place-items-center text-white"><UserSquare2 className="w-5 h-5" /></div>
              <div className="min-w-0">
                <div className="font-display font-bold tracking-tight truncate">{a.artist_name}</div>
                <div className="text-xs text-zinc-500 truncate">{a.email}</div>
              </div>
            </div>
            {(a.revenue_idr > 0 || a.last_active_period) && (
              <div className="mt-3 rounded-xl bg-emerald-500/5 border border-emerald-500/15 px-3 py-2">
                <div className="text-[9px] uppercase tracking-widest font-bold text-emerald-400/70">Royalti Aktif</div>
                <div className="mt-1 flex items-baseline justify-between gap-2">
                  <div className="font-mono font-bold text-emerald-300 text-sm">{new Intl.NumberFormat("id-ID", { style: "currency", currency: "IDR", maximumFractionDigits: 0 }).format(a.revenue_idr || 0)}</div>
                  <div className="text-[10px] text-zinc-500">{a.last_active_period ? fmtPeriodInline(a.last_active_period) : "—"}</div>
                </div>
                <div className="text-[10px] text-zinc-500 mt-0.5">{(a.royalty_lines_count || 0).toLocaleString("id-ID")} baris royalti</div>
              </div>
            )}
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
              <Cap k="Status" v={a.status} />
              <Cap k="WhatsApp" v={a.whatsapp || "—"} />
            </div>
            <div className="mt-4 text-xs text-zinc-500">
              <div className="font-bold mb-1.5">Visibilitas royalti:</div>
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(a.visibility_settings || {}).map(([k, v]) => (
                  <span key={k} className={`px-2 py-0.5 rounded-full text-[10px] ${v ? "bg-emerald-500/15 text-emerald-300" : "bg-white/[0.06] text-zinc-500"}`}>{k}: {v ? "yes" : "no"}</span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-black/40 grid place-items-center p-4" onClick={() => setOpen(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="w-full max-w-md rm-glass-strong rounded-[24px] p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-display font-extrabold text-xl tracking-tighter">Tambah Artist</h3>
              <button type="button" onClick={() => setOpen(false)}><X className="w-5 h-5" /></button>
            </div>
            <div>
              <label className="rm-label">Nama Artist</label>
              <input data-testid={ARTIST_MGMT.nameInput} className="rm-input" value={form.artist_name} onChange={(e) => setForm({ ...form, artist_name: e.target.value })} required />
            </div>
            <div>
              <label className="rm-label">Email</label>
              <input data-testid={ARTIST_MGMT.emailInput} type="email" className="rm-input" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            </div>
            <div>
              <label className="rm-label">WhatsApp (opsional)</label>
              <input className="rm-input" value={form.whatsapp} onChange={(e) => setForm({ ...form, whatsapp: e.target.value })} />
            </div>
            <div>
              <label className="rm-label">Password Sementara</label>
              <input data-testid={ARTIST_MGMT.passwordInput} type="text" className="rm-input" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} placeholder="Min. 8 karakter" />
              <div className="text-[11px] text-zinc-500 mt-1">Bagikan password ini ke artist Anda.</div>
            </div>
            {err && <div className="text-sm text-red-600 bg-red-50 rounded-xl px-3 py-2">{err}</div>}
            <div className="flex justify-end gap-2">
              <button type="button" className="rm-btn-ghost" onClick={() => setOpen(false)}>Batal</button>
              <button className="rm-btn-primary" disabled={saving} data-testid={ARTIST_MGMT.saveButton}>{saving ? "Menyimpan…" : "Simpan"}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
function Cap({ k, v }) { return <div><div className="text-zinc-500">{k}</div><div className="font-semibold capitalize">{v}</div></div>; }

function fmtPeriodInline(p) {
  if (!p || p.length !== 7) return p || "—";
  const [y, m] = p.split("-");
  const months = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
  return `${months[parseInt(m, 10) - 1] || m} ${y}`;
}
